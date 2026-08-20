"""Tests for corpus-wide export: discourse summary, ministry rollup, glossary."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from commoner_analyse.discourse import DISCOURSE_LABEL_DESCRIPTIONS
from commoner_analyse.export import (
    build_discourse_summary,
    build_glossary,
    build_ministry_discourse,
)


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")


class DiscourseSummaryTests(unittest.TestCase):

    def test_returns_none_when_analysis_discourse_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(build_discourse_summary(Path(tmp)))

    def test_counts_previously_unclassified_v2_labels_as_evasive(self):
        # Regression test: CONSTITUTIONAL_DEFAULT, FEDERAL_DEFLECTION,
        # STRUCTURAL_REFUSAL, and REPRESENTATIONAL_SILENCE (the
        # "Instrumented Discourse Tier v2" labels) were missing from
        # aggregations._EVASIVE, so every evasion rate silently undercounted
        # them as unclassified. Fixed 2026-07-06.
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            _write_jsonl(out / "manifest.jsonl", [{"key": f"k{i}"} for i in range(4)])
            _write_jsonl(out / "analysis_discourse.jsonl", [
                {"key": "k1", "label": "CONSTITUTIONAL_DEFAULT"},
                {"key": "k2", "label": "FEDERAL_DEFLECTION"},
                {"key": "k3", "label": "ACCEPTED"},
                {"key": "k4", "label": "REJECTED"},
            ])
            summary = build_discourse_summary(out)
            self.assertEqual(summary["evasiveCount"], 2)
            self.assertEqual(summary["substantiveCount"], 2)
            self.assertEqual(summary["responsesClassified"], 4)
            self.assertAlmostEqual(summary["evasionRateClassified"], 0.5)

    def test_evasion_rate_none_when_nothing_classified(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            _write_jsonl(out / "manifest.jsonl", [{"key": "k1"}])
            _write_jsonl(out / "analysis_discourse.jsonl", [
                {"key": "k1", "label": "UNCLASSIFIED"},
            ])
            summary = build_discourse_summary(out)
            self.assertIsNone(summary["evasionRateClassified"])


class ExportTierGuardTests(unittest.TestCase):
    """The export is what a downstream site reads, so the guard must reach it.

    `tiers.py` protects `mp_summary.jsonl` and `ministry_summary_*.jsonl`. Until
    2026-08-17 the export published `evasionRateClassified` with no
    publishability verdict at all, so a consumer reading only the export could
    not tell whether the rate was safe to quote.
    """

    def test_export_reports_the_tiers_behind_the_rate(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            _write_jsonl(out / "manifest.jsonl", [{"key": f"k{i}"} for i in range(2)])
            _write_jsonl(out / "analysis_discourse.jsonl", [
                {"key": "k1", "label": "DEFLECTED", "classifier": "regex_v2"},
                {"key": "k2", "label": "ACCEPTED", "classifier": "regex_v2"},
            ])
            summary = build_discourse_summary(out)
            self.assertEqual(summary["tiersSeen"], {"regex_v2": 2})
            self.assertTrue(summary["ratePublishable"])

    def test_an_unregistered_tier_marks_the_rate_unpublishable(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            _write_jsonl(out / "manifest.jsonl", [{"key": "k1"}])
            _write_jsonl(out / "analysis_discourse.jsonl", [
                {"key": "k1", "label": "DEFLECTED", "classifier": "mystery_v1"},
            ])
            summary = build_discourse_summary(out)
            self.assertFalse(summary["ratePublishable"])

    def test_an_unclassified_row_does_not_make_the_rate_unpublishable(self):
        """An UNCLASSIFIED row is on neither side of the rate.

        Counting its tier would mark the rate unpublishable over a tier that
        never touched it, and an unclassified row is the normal case.
        """
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            _write_jsonl(out / "manifest.jsonl", [{"key": f"k{i}"} for i in range(2)])
            _write_jsonl(out / "analysis_discourse.jsonl", [
                {"key": "k1", "label": "DEFLECTED", "classifier": "regex_v2"},
                {"key": "k2", "label": "UNCLASSIFIED"},
            ])
            summary = build_discourse_summary(out)
            self.assertEqual(summary["tiersSeen"], {"regex_v2": 1})
            self.assertTrue(summary["ratePublishable"])


class MinistryDiscourseTests(unittest.TestCase):

    def test_returns_none_when_ministry_summary_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(build_ministry_discourse(Path(tmp)))

    def test_reshapes_and_sorts_by_records_total_desc(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            _write_jsonl(out / "ministry_summary_qa.jsonl", [
                {"ministry": "SMALL", "records_total": 2, "evasion_rate_classified": 0.5},
                {"ministry": "BIG", "records_total": 10, "evasion_rate_classified": 0.8},
            ])
            rows = build_ministry_discourse(out)
            self.assertEqual([r["ministry"] for r in rows], ["BIG", "SMALL"])
            self.assertEqual(rows[0]["recordsTotal"], 10)
            self.assertEqual(rows[0]["evasionRateClassified"], 0.8)

    def test_legacy_row_without_tiers_is_not_publishable(self):
        """A pre-v2.4.0 file carries no tier fields. The verdict must be False,
        not null — a real rate beside a null verdict is the gap the guard closes.
        """
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            _write_jsonl(out / "ministry_summary_qa.jsonl", [
                {"ministry": "LEGACY", "records_total": 9, "evasion_rate_classified": 0.4},
            ])
            row = build_ministry_discourse(out)[0]
            self.assertEqual(row["evasionRateClassified"], 0.4)
            self.assertIs(row["ratePublishable"], False)
            self.assertEqual(row["tiersSeen"], {})

    def test_verdict_is_recomputed_from_tiers_seen(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            _write_jsonl(out / "ministry_summary_qa.jsonl", [
                {"ministry": "TWO_SIDED", "records_total": 9, "tiers_seen": {"regex_v2": 3}},
                {"ministry": "UNKNOWN_TIER", "records_total": 4, "tiers_seen": {"mystery": 1}},
            ])
            rows = {r["ministry"]: r for r in build_ministry_discourse(out)}
            self.assertIs(rows["TWO_SIDED"]["ratePublishable"], True)
            self.assertIs(rows["UNKNOWN_TIER"]["ratePublishable"], False)


class GlossaryTests(unittest.TestCase):

    def test_every_taxonomy_label_present_and_classified(self):
        glossary = build_glossary()
        labels = {row["label"]: row for row in glossary["labels"]}
        self.assertEqual(set(labels), set(DISCOURSE_LABEL_DESCRIPTIONS))
        for label, row in labels.items():
            self.assertIn(row["function"], {"substantive", "evasive", "unclassified"})
            self.assertEqual(row["description"], DISCOURSE_LABEL_DESCRIPTIONS[label])

    def test_v2_tier_labels_classified_as_evasive_not_unclassified(self):
        glossary = build_glossary()
        labels = {row["label"]: row["function"] for row in glossary["labels"]}
        for label in (
            "CONSTITUTIONAL_DEFAULT",
            "FEDERAL_DEFLECTION",
            "STRUCTURAL_REFUSAL",
            "REPRESENTATIONAL_SILENCE",
        ):
            self.assertEqual(labels[label], "evasive")


if __name__ == "__main__":
    unittest.main()

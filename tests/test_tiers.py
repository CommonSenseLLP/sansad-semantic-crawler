"""Tier capability, the outcome-rate guard, and the drift tests around them.

The behaviour tests are ordinary. The three registry tests are the point of the
module, and each one exists because a hand-kept registry drifted:

* ``test_every_emitted_tier_is_registered`` — ``discourse.py``'s own docstring
  claimed ``regex_v1`` while its constant read ``regex_v2``. A registry keyed on
  the docstring would have refused every row in the corpus and reported it as
  an unregistered tier.
* ``test_declared_capability_matches_the_taxonomy`` — a declaration nobody
  checks is the same defect one level up.
* ``test_the_substantive_evasive_split_has_one_source`` — ``dossier.py`` held a
  copy of the split until 2026-08-17. The copy never took three labels, so
  every dossier under-counted evasion.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from commoner_analyse import discourse, tiers
from commoner_analyse.aggregations import _EVASIVE, _SUBSTANTIVE, label_function
from commoner_analyse.tiers import (
    BOTH,
    TIER_CAPABILITY,
    Row,
    outcome_rate,
    rate_publishable,
    two_sided,
)

PACKAGE = Path(__file__).resolve().parents[1] / "commoner_analyse"


def _regex_tier_labels() -> set[str]:
    """Every label the deterministic tier can reach, over both channels."""
    return {
        d.name
        for d in (*discourse._PRIORITY_QA, *discourse._PRIORITY_COMMITTEE)
    }


# --- the registry tests -----------------------------------------------------


def test_every_emitted_tier_is_registered():
    """A tier name the classifier writes must have a capability entry.

    Rename a CLASSIFIER_VERSION constant without touching the registry and
    every row it writes becomes an unregistered tier. `outcome_rate` then
    refuses the whole corpus, and `rate_publishable` reads False everywhere.
    Both failures are silent in the sense that matters: the pipeline still
    runs and still writes a file.
    """
    emitted = {discourse.CLASSIFIER_VERSION, discourse.LLM_CLASSIFIER_VERSION}
    unregistered = emitted - set(TIER_CAPABILITY)
    assert not unregistered, (
        f"discourse.py emits {sorted(unregistered)}, which tiers.py does not "
        f"register. Add it to TIER_CAPABILITY with its measured capability."
    )


def test_declared_capability_matches_the_taxonomy():
    """A tier declared two-sided must actually reach both families."""
    reachable = _regex_tier_labels()
    families = {label_function(name) for name in reachable}
    assert "substantive" in families
    assert "evasive" in families
    assert TIER_CAPABILITY[discourse.CLASSIFIER_VERSION] == BOTH

    # The LLM tier accepts any label in the taxonomy, so its capability is the
    # taxonomy's own span.
    llm_families = {
        label_function(name) for name in discourse.DISCOURSE_LABEL_DESCRIPTIONS
    }
    assert {"substantive", "evasive"} <= llm_families
    assert TIER_CAPABILITY[discourse.LLM_CLASSIFIER_VERSION] == BOTH


def test_the_substantive_evasive_split_has_one_source():
    """No module may keep a second copy of the split.

    `dossier.py` kept one and it drifted by three labels. A copy is not caught
    by any behaviour test, because each copy is internally consistent.
    """
    # Match on the CONTENTS, not the variable name. A copy called
    # EVASIVE_LABELS is the plausible thing for the next author to write, and a
    # name-bound check would not see it. `ast.AnnAssign` is walked too, because
    # `_EVASIVE: frozenset[str] = frozenset({...})` is not an `ast.Assign`.
    known = _SUBSTANTIVE | _EVASIVE
    owners: dict[str, list[str]] = {}

    def _literal_strings(node: ast.AST) -> set[str]:
        return {
            n.value for n in ast.walk(node)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)
        }

    for path in sorted(PACKAGE.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                names = [t.id for t in node.targets if isinstance(t, ast.Name)]
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                names = [node.target.id]
            else:
                continue
            if node.value is None:
                continue
            # A copy of the split is a literal collection of taxonomy labels
            # that lies wholly inside ONE family. The full taxonomy — the label
            # descriptions, the per-label confidences — spans both, so it is
            # not a copy and is not flagged.
            labels = _literal_strings(node.value) & known
            if len(labels) >= 3 and (labels <= _SUBSTANTIVE or labels <= _EVASIVE):
                owners.setdefault(path.name, []).extend(names)

    assert set(owners) == {"aggregations.py"}, (
        f"the substantive/evasive split is defined in {sorted(owners)}. "
        f"It belongs in aggregations.py alone. Import it from there."
    )


# --- capability -------------------------------------------------------------


def test_unregistered_tier_is_refused_not_assumed():
    assert not two_sided("some_tier_nobody_registered")
    assert tiers.tier_families("some_tier_nobody_registered") == frozenset()


def test_rate_publishable_is_false_on_an_empty_corpus():
    """No rows is not a publishable rate. It is no rate."""
    assert rate_publishable([]) is False


def test_rate_publishable_fails_closed_on_an_unknown_tier():
    assert rate_publishable([discourse.CLASSIFIER_VERSION]) is True
    assert rate_publishable([discourse.CLASSIFIER_VERSION, "mystery_v1"]) is False


# --- outcome_rate -----------------------------------------------------------


def _row(key, label, conf=0.9, clf=None):
    return Row(key=key, label=label, confidence=conf,
               classifier=clf or discourse.CLASSIFIER_VERSION)


def test_outcome_rate_splits_the_families():
    rows = [
        _row("a", "FACTUAL_DISCLOSURE"),
        _row("b", "DEFLECTED"),
        _row("c", "DATA_WITHHELD"),
    ]
    rate = outcome_rate(rows, min_n=1)
    assert rate.n == 3
    assert rate.substantive == 1
    assert rate.evasive == 2
    assert rate.evasion_rate == pytest.approx(2 / 3)
    assert rate.citable


def test_outcome_rate_drops_an_unregistered_tier_and_says_so():
    rows = [_row("a", "DEFLECTED", clf="mystery_v1")]
    rate = outcome_rate(rows, min_n=1)
    assert rate.n == 0
    assert rate.excluded == {"unregistered_tier": 1}


def test_outcome_rate_drops_below_confidence():
    rows = [_row("a", "DEFLECTED", conf=0.5)]
    rate = outcome_rate(rows, min_n=1)
    assert rate.excluded == {"below_confidence": 1}


def test_a_null_confidence_row_does_not_raise():
    """`analysis_discourse.jsonl` holds rows with a null label and confidence.

    A `dfg_recommendation_passthrough` row is a committee ask with no response
    yet. It carries a real classifier, so it passes the capability gate. A
    caller building Row(**row) straight from the file must not hit a TypeError.
    """
    rows = [Row(key="a", label=None, confidence=None,
                classifier=discourse.CLASSIFIER_VERSION)]
    rate = outcome_rate(rows, min_n=1)
    assert rate.n == 0
    assert rate.excluded == {"below_confidence": 1}


def test_a_refusal_at_the_top_confidence_refuses_the_record():
    """A weaker tier must not overturn a stronger tier's UNCLASSIFIED.

    Filtering unclassified rows out first would let the 0.80 label decide,
    and the override always lands on the benign side.
    """
    rows = [
        _row("a", "UNCLASSIFIED", conf=0.99),
        _row("a", "FACTUAL_DISCLOSURE", conf=0.80,
             clf=discourse.LLM_CLASSIFIER_VERSION),
    ]
    rate = outcome_rate(rows, min_n=1)
    assert rate.n == 0
    assert rate.excluded == {"top_unclassified": 1}


def test_a_tie_that_disagrees_refuses_the_record():
    """Iteration order must never decide a published rate."""
    rows = [
        _row("a", "FACTUAL_DISCLOSURE", conf=0.9),
        _row("a", "DEFLECTED", conf=0.9, clf=discourse.LLM_CLASSIFIER_VERSION),
    ]
    rate = outcome_rate(rows, min_n=1)
    assert rate.n == 0
    assert rate.excluded == {"tied_conflict": 1}


def test_a_tie_that_agrees_still_counts():
    rows = [
        _row("a", "DEFLECTED", conf=0.9),
        _row("a", "ABSORBED", conf=0.9, clf=discourse.LLM_CLASSIFIER_VERSION),
    ]
    rate = outcome_rate(rows, min_n=1)
    assert rate.n == 1
    assert rate.evasive == 1


# --- the fields on the summary rows -----------------------------------------
#
# tiers.py in isolation cannot show what the summarisers put in the file. The
# first version of these fields counted a sentinel tier for every record with
# no discourse row, and read rate_publishable=False on any realistic corpus.
# A unit test over hand-built tier lists cannot see that. This can.


def _corpus(tmp_path, manifest_rows, discourse_rows):
    import json
    (tmp_path / "manifest.jsonl").write_text(
        "\n".join(json.dumps(r) for r in manifest_rows), encoding="utf-8")
    (tmp_path / "analysis_discourse.jsonl").write_text(
        "\n".join(json.dumps(r) for r in discourse_rows), encoding="utf-8")
    return tmp_path


def _first_row(path):
    import json
    return json.loads(path.read_text(encoding="utf-8").splitlines()[0])


def test_a_record_with_no_discourse_row_does_not_make_a_rate_unpublishable(tmp_path):
    """An unclassified record is in neither side of the rate.

    `analyse-discourse` reads answers.jsonl and skips a record whose answer is
    empty, so a manifest record with no discourse row is the normal case. Its
    tier is unknown, but no unknown tier touched the rate.
    """
    from commoner_analyse.aggregations import write_ministry_summary, write_mp_summary

    d = _corpus(
        tmp_path,
        [
            {"key": "k1", "kind": "qa", "ministry": "M", "house": "Lok Sabha",
             "askers": ["Shri A"]},
            {"key": "k2", "kind": "qa", "ministry": "M", "house": "Lok Sabha",
             "askers": ["Shri A"]},
        ],
        [
            {"key": "k1", "kind": "qa_response_analysis", "label": "DEFLECTED",
             "confidence": 0.9, "classifier": discourse.CLASSIFIER_VERSION},
        ],
    )
    write_ministry_summary(d)
    write_mp_summary(d)

    ministry = _first_row(d / "ministry_summary_qa.jsonl")
    assert ministry["tiers_seen"] == {discourse.CLASSIFIER_VERSION: 1}
    assert ministry["rate_publishable"] is True
    assert ministry["records_unclassified"] == 1

    mp = _first_row(d / "mp_summary.jsonl")
    assert mp["tiers_seen"] == {discourse.CLASSIFIER_VERSION: 1}
    assert mp["rate_publishable"] is True


def test_an_unregistered_tier_in_the_corpus_makes_the_rate_unpublishable(tmp_path):
    from commoner_analyse.aggregations import write_ministry_summary

    d = _corpus(
        tmp_path,
        [{"key": "k1", "kind": "qa", "ministry": "M", "house": "Lok Sabha",
          "askers": ["Shri A"]}],
        [{"key": "k1", "kind": "qa_response_analysis", "label": "DEFLECTED",
          "confidence": 0.9, "classifier": "mystery_v1"}],
    )
    write_ministry_summary(d)
    row = _first_row(d / "ministry_summary_qa.jsonl")
    assert row["tiers_seen"] == {"mystery_v1": 1}
    assert row["rate_publishable"] is False


def test_min_n_gates_citability_without_hiding_the_number():
    rows = [_row(str(i), "DEFLECTED") for i in range(5)]
    rate = outcome_rate(rows, min_n=30)
    assert rate.n == 5
    assert not rate.citable
    assert "NOT citable" in rate.summary()

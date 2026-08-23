"""The five commands that assume no legislature.

They exist because an audit found the capability sitting in this package,
importable only, while sibling repos rebuilt it by hand. A capability nobody
can reach from a shell is a capability nobody uses.

Each check here runs the parser and the handler, not the module underneath.
The modules have their own tests. What can break here is the wiring.
"""

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from commoner_analyse.cli import build_parser


def _run(argv: list[str]) -> tuple[str, int]:
    args = build_parser().parse_args(argv)
    buffer = io.StringIO()
    code = 0
    try:
        with redirect_stdout(buffer):
            args.func(args)
    except SystemExit as exit_:
        code = int(exit_.code or 0)
    return buffer.getvalue(), code


def _write(directory: str, name: str, text: str) -> str:
    path = Path(directory) / name
    path.write_text(text)
    return str(path)


class NormalizeNamesTests(unittest.TestCase):

    def test_two_spellings_of_one_name_reach_one_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(tmp, "n.txt", "Joshi, Shri P.V.\nP V Joshi\n")
            out, code = _run(["normalize-names", "--file", path])
        self.assertEqual(code, 0)
        lines = out.strip().splitlines()
        self.assertEqual(lines[0], lines[1])
        self.assertEqual(lines[0], "joshi p v")

    def test_slug_preserves_word_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(tmp, "n.txt", "Shri P.V. Joshi\n")
            out, _ = _run(["normalize-names", "--file", path, "--slug"])
        self.assertEqual(out.strip(), "p_v_joshi")

    def test_extra_honorifics_reach_the_module(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(tmp, "n.txt", "Rev Fr John Doe\n")
            out, _ = _run(["normalize-names", "--file", path, "--extra-honorifics", "Rev,Fr"])
        self.assertEqual(out.strip(), "doe john")


class GateExitCodeTests(unittest.TestCase):
    """A gate that only prints is a gate a pipeline ignores."""

    def test_check_pooling_exits_non_zero_on_refusal(self):
        out, code = _run(["check-pooling", "--pooled", "0.047", "--strata", "0.44,0.68"])
        self.assertEqual(code, 1)
        self.assertFalse(json.loads(out)["ok"])

    def test_check_pooling_exits_zero_when_valid(self):
        out, code = _run(["check-pooling", "--pooled", "0.5", "--strata", "0.4,0.9"])
        self.assertEqual(code, 0)
        self.assertTrue(json.loads(out)["ok"])

    def test_check_units_exits_non_zero_and_reports_the_denominator(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(tmp, "u.jsonl", '{"k":"a"}\n{"k":"a"}\n{"k":"b"}\n')
            out, code = _run(["check-units", path, "--unit-key", "k"])
        self.assertEqual(code, 1)
        payload = json.loads(out)
        self.assertEqual(payload["row_total"], 3)
        self.assertEqual(payload["unit_total"], 2)

    def test_check_claims_names_the_overclaiming_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(
                tmp, "s.jsonl",
                '{"key":"ok","reply_split_ok":true,"question":"q","answer":"a"}\n'
                '{"key":"liar","reply_split_ok":true}\n',
            )
            out, code = _run(["check-claims", path])
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(out)["unsupported"], ["liar"])


class GateRefusesUnusableInputTests(unittest.TestCase):
    """A gate that reports ok when it cannot evaluate is worse than no gate.

    Both defects below returned `ok: true` and exit 0. Each is a silent pass,
    which a pipeline reads as a clean corpus and publishes.
    """

    @staticmethod
    def _run_gate(argv: list[str]) -> tuple[str, str, int]:
        """Mirror what a shell sees: stdout, stderr, and the exit code.

        Python prints a string `SystemExit` to stderr and exits 1.
        """
        args = build_parser().parse_args(argv)
        out, err = io.StringIO(), io.StringIO()
        code = 0
        try:
            with redirect_stdout(out), redirect_stderr(err):
                args.func(args)
        except SystemExit as exit_:
            if isinstance(exit_.code, str):
                print(exit_.code, file=err)
                code = 1
            else:
                code = int(exit_.code or 0)
        return out.getvalue(), err.getvalue(), code

    def test_a_nan_pooled_value_does_not_pass_the_range_check(self):
        out, err, code = self._run_gate(["check-pooling", "--pooled", "nan", "--strata", "0.4,0.9"])
        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertIn("--pooled", err)
        self.assertNotIn("NaN", out)

    def test_a_nan_tolerance_does_not_pass_the_range_check(self):
        _, err, code = self._run_gate(
            ["check-pooling", "--pooled", "0.5", "--strata", "0.4,0.9", "--tolerance", "nan"]
        )
        self.assertEqual(code, 1)
        self.assertIn("--tolerance", err)

    def test_a_nan_stratum_does_not_pass_the_range_check(self):
        _, err, code = self._run_gate(["check-pooling", "--pooled", "0.5", "--strata", "0.4,nan"])
        self.assertEqual(code, 1)
        self.assertIn("--strata", err)

    def test_an_infinite_pooled_value_is_refused_too(self):
        _, err, code = self._run_gate(["check-pooling", "--pooled", "inf", "--strata", "0.4,0.9"])
        self.assertEqual(code, 1)
        self.assertIn("--pooled", err)

    def test_an_absent_file_is_not_a_clean_corpus(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = str(Path(tmp) / "missing.jsonl")
            out, err, code = self._run_gate(["check-units", missing, "--unit-key", "k"])
        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertIn("no such file", err)

    def test_a_malformed_line_names_its_line_number(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(tmp, "u.jsonl", '{"k":"a"}\n{"k":\n{"k":"b"}\n')
            _, err, code = self._run_gate(["check-units", path, "--unit-key", "k"])
        self.assertEqual(code, 1)
        self.assertIn(":2:", err)

    def test_check_claims_cannot_miss_the_overclaiming_record_to_a_parse_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(tmp, "s.jsonl", '{"key":"ok","reply_split_ok":true,"question":"q","answer":"a"}\n{oops\n')
            _, err, code = self._run_gate(["check-claims", path])
        self.assertEqual(code, 1)
        self.assertIn("malformed JSON", err)

    def test_an_empty_file_is_not_a_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(tmp, "u.jsonl", "\n\n")
            _, err, code = self._run_gate(["check-units", path, "--unit-key", "k"])
        self.assertEqual(code, 1)
        self.assertIn("no rows", err)

    def test_a_json_line_that_is_not_an_object_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(tmp, "u.jsonl", '{"k":"a"}\n[1,2]\n')
            _, err, code = self._run_gate(["check-units", path, "--unit-key", "k"])
        self.assertEqual(code, 1)
        self.assertIn("not a JSON object", err)


class MergeFragmentsTests(unittest.TestCase):

    def test_a_disagreeing_repeat_lands_in_conflicted(self):
        with tempfile.TemporaryDirectory() as tmp:
            one = _write(tmp, "f1.jsonl", '{"key":"q1","limbs":[{"letter":"a","label":"X"}]}\n')
            two = _write(
                tmp, "f2.jsonl",
                '{"key":"q1","limbs":[{"letter":"a","label":"Y"}]}\n'
                '{"key":"q2","limbs":[{"letter":"a","label":"X"}]}\n',
            )
            target = _write(
                tmp, "t.jsonl",
                '{"key":"q1","letters":["a"]}\n{"key":"q2","letters":["a"]}\n'
                '{"key":"q3","letters":["a"]}\n',
            )
            out, code = _run(["merge-fragments", one, two, "--target", target])
        payload = json.loads(out)
        self.assertEqual(payload["conflicted"], ["q1"])
        self.assertEqual(payload["unlabelled"], ["q3"])
        self.assertEqual(sorted(payload["accepted"]), ["q2"])
        self.assertEqual(payload["repeatedKeys"], {"q1": 2})
        self.assertEqual(sorted(payload["redo"]), ["q1", "q3"])


class SurfaceTests(unittest.TestCase):

    def test_all_five_are_registered(self):
        choices = build_parser()._subparsers._group_actions[0].choices
        for name in (
            "normalize-names", "check-pooling", "check-units",
            "check-claims", "merge-fragments",
        ):
            with self.subTest(command=name):
                self.assertIn(name, choices)


if __name__ == "__main__":
    unittest.main()

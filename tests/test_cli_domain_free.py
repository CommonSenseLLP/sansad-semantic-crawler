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
from contextlib import redirect_stdout
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

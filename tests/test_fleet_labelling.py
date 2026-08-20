import unittest

from commoner_analyse.fragment_merge import collect, reconcile
from commoner_analyse.staging import (
    NOT_ATTEMPTED,
    NO_BOUNDARY,
    OK,
    split_state,
    stage,
    unsupported_claims,
)


def _limbs(*pairs):
    return [{"letter": letter, "label": label} for letter, label in pairs]


class StagingTests(unittest.TestCase):

    def test_no_splitter_is_not_a_failed_split(self):
        staged = stage({"key": "k1", "ministry": "M"}, "full text")
        self.assertEqual(staged["reply_split"], NOT_ATTEMPTED)
        self.assertFalse(staged["reply_split_ok"])
        self.assertNotIn("question", staged)

    def test_a_successful_split_carries_both_halves(self):
        staged = stage({"key": "k1"}, "Q. ask A. reply", lambda _: ("ask", "reply"))
        self.assertEqual(staged["reply_split"], OK)
        self.assertTrue(staged["reply_split_ok"])
        self.assertEqual(staged["question"], "ask")
        self.assertEqual(staged["answer"], "reply")

    def test_a_splitter_that_finds_no_boundary_says_so(self):
        staged = stage({"key": "k1"}, "text", lambda _: None)
        self.assertEqual(staged["reply_split"], NO_BOUNDARY)
        self.assertFalse(staged["reply_split_ok"])
        self.assertNotIn("question", staged)

    def test_a_blank_half_is_an_absent_half(self):
        """An empty string is what a parser returns when its anchor missed."""
        self.assertEqual(split_state("ask", "   "), NO_BOUNDARY)
        self.assertEqual(split_state("", "reply"), NO_BOUNDARY)
        self.assertEqual(split_state(None, None), NOT_ATTEMPTED)
        self.assertEqual(split_state("ask", "reply"), OK)

    def test_the_flag_can_never_outrun_the_fields(self):
        staged = stage({"key": "k1"}, "text", lambda _: ("ask", ""))
        self.assertFalse(staged["reply_split_ok"])
        self.assertEqual(unsupported_claims([staged]), [])

    def test_unsupported_claims_names_a_flag_with_no_fields_under_it(self):
        records = [
            {"key": "honest", "reply_split_ok": False},
            {"key": "liar", "reply_split_ok": True},
            {"key": "sound", "reply_split_ok": True, "question": "q", "answer": "a"},
        ]
        self.assertEqual(unsupported_claims(records), ["liar"])

    def test_carried_fields_are_overridable(self):
        staged = stage({"key": "k1", "docket": "D"}, "t", carried=("key", "docket"))
        self.assertEqual(staged["docket"], "D")
        self.assertNotIn("ministry", staged)


class FragmentMergeTests(unittest.TestCase):

    def test_a_disagreeing_repeat_conflicts_instead_of_last_writer_winning(self):
        first = [{"key": "q1", "limbs": _limbs(("a", "ACCEPTED"))}]
        second = [{"key": "q1", "limbs": _limbs(("a", "DEFLECTED"))}]
        rows, repeats = collect([first, second])
        self.assertTrue(rows["q1"]["conflict"])
        self.assertEqual(repeats, {"q1": 2})

    def test_an_agreeing_repeat_is_reported_but_not_a_conflict(self):
        fragment = [{"key": "q1", "limbs": _limbs(("a", "ACCEPTED"))}]
        rows, repeats = collect([fragment, list(fragment)])
        self.assertNotIn("conflict", rows["q1"])
        self.assertEqual(repeats, {"q1": 2})

    def test_merge_is_keyed_not_positional(self):
        first = [{"key": "q2", "limbs": _limbs(("a", "X"))}]
        second = [{"key": "q1", "limbs": _limbs(("a", "X"))}]
        rows, _ = collect([first, second])
        self.assertEqual(set(rows), {"q1", "q2"})

    def test_every_bucket(self):
        rows, _ = collect([[
            {"key": "good", "limbs": _limbs(("a", "X"), ("b", "Y"))},
            {"key": "short", "limbs": _limbs(("a", "X"))},
            {"key": "extra", "limbs": _limbs(("a", "X"), ("z", "Y"))},
            {"key": "clash", "limbs": _limbs(("a", "X")), "conflict": True},
            {"key": "stale", "limbs": _limbs(("a", "X"))},
        ]])
        target = {
            "good": ["a", "b"],
            "short": ["a", "b"],
            "extra": ["a"],
            "clash": ["a"],
            "missing": ["a"],
        }
        result = reconcile(target, rows)
        self.assertEqual(set(result.accepted), {"good"})
        self.assertEqual(result.partial, {"short": ("b",)})
        self.assertEqual(result.invented, {"extra": ("z",)})
        self.assertEqual(result.conflicted, ("clash",))
        self.assertEqual(result.unlabelled, ("missing",))
        self.assertEqual(result.orphan, ("stale",))
        self.assertEqual(result.target_total, 5)

    def test_the_buckets_partition_the_target_and_orphans_sit_outside(self):
        rows, _ = collect([[
            {"key": "good", "limbs": _limbs(("a", "X"))},
            {"key": "stale", "limbs": _limbs(("a", "X"))},
        ]])
        target = {"good": ["a"], "missing": ["a"]}
        result = reconcile(target, rows)
        buckets = (
            set(result.accepted) | set(result.unlabelled) | set(result.partial)
            | set(result.invented) | set(result.conflicted)
        )
        self.assertEqual(buckets, set(target))
        self.assertNotIn("stale", buckets)

    def test_redo_is_the_next_fleet_input(self):
        rows, _ = collect([[{"key": "short", "limbs": _limbs(("a", "X"))}]])
        result = reconcile({"short": ["a", "b"], "missing": ["a"]}, rows)
        self.assertEqual(result.redo, ("missing", "short"))

    def test_summary_reports_every_bucket(self):
        result = reconcile({"missing": ["a"]}, {})
        self.assertIn("target=1", result.summary())
        self.assertIn("unlabelled=1", result.summary())


if __name__ == "__main__":
    unittest.main()

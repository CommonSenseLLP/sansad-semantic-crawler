import unittest

from commoner_analyse.inference_gates import (
    InferenceGateError,
    assert_one_row_per_unit,
    assert_pooling_valid,
    build_pooling_verdict,
    build_unit_verdict,
)


class PoolingGateTests(unittest.TestCase):

    def test_a_pooled_figure_outside_every_stratum_is_refused(self):
        """The first case is the one the gate exists for: pooled below all strata."""
        broken = build_pooling_verdict(0.047, [0.44, 0.68])
        self.assertFalse(broken.ok)
        self.assertIn("outside the stratum range", broken.reason)

        sound = build_pooling_verdict(0.549, [0.418, 0.624, 0.671, 0.681])
        self.assertTrue(sound.ok)

    def test_pooled_on_the_boundary_passes(self):
        self.assertTrue(build_pooling_verdict(0.4, [0.4, 0.9]))
        self.assertTrue(build_pooling_verdict(0.9, [0.4, 0.9]))

    def test_tolerance_covers_rounding_not_a_real_gap(self):
        self.assertTrue(build_pooling_verdict(0.399, [0.4, 0.9], tolerance=0.01))
        self.assertFalse(build_pooling_verdict(0.2, [0.4, 0.9], tolerance=0.01))

    def test_empty_strata_refuse_rather_than_pass(self):
        verdict = build_pooling_verdict(0.5, [])
        self.assertFalse(verdict.ok)
        self.assertIn("no strata", verdict.reason)

    def test_a_null_stratum_refuses(self):
        self.assertFalse(build_pooling_verdict(0.5, [0.4, None]))

    def test_a_single_stratum_must_equal_the_pooled_figure(self):
        self.assertTrue(build_pooling_verdict(0.5, [0.5]))
        self.assertFalse(build_pooling_verdict(0.6, [0.5]))

    def test_assert_raises_with_the_reason(self):
        with self.assertRaises(InferenceGateError) as caught:
            assert_pooling_valid(0.047, [0.44, 0.68])
        self.assertIn("0.047", str(caught.exception))
        assert_pooling_valid(0.549, [0.418, 0.681])

    def test_verdict_is_falsy_when_it_refuses(self):
        self.assertFalse(bool(build_pooling_verdict(0.047, [0.44, 0.68])))
        self.assertTrue(bool(build_pooling_verdict(0.5, [0.4, 0.9])))


class UnitGateTests(unittest.TestCase):

    def test_multi_part_units_refuse_and_report_the_denominator(self):
        """More rows than units: a multi-part unit contributes two rows."""
        rows = [
            {"shrid2": "a"}, {"shrid2": "a"}, {"shrid2": "b"}, {"shrid2": "c"},
        ]
        verdict = build_unit_verdict(rows, unit_key="shrid2")
        self.assertFalse(verdict.ok)
        self.assertEqual(verdict.detail["row_total"], 4)
        self.assertEqual(verdict.detail["unit_total"], 3)
        self.assertEqual(verdict.detail["multi_part_total"], 1)
        self.assertEqual(verdict.detail["rows_by_multi_part_unit"], {"a": 2})

    def test_one_row_per_unit_passes(self):
        rows = [{"shrid2": "a"}, {"shrid2": "b"}]
        verdict = build_unit_verdict(rows, unit_key="shrid2")
        self.assertTrue(verdict.ok)
        self.assertEqual(verdict.detail["unit_total"], 2)

    def test_a_row_without_the_key_is_unattributed_not_its_own_unit(self):
        rows = [{"shrid2": "a"}, {"village": "no key here"}]
        verdict = build_unit_verdict(rows, unit_key="shrid2")
        self.assertFalse(verdict.ok)
        self.assertEqual(verdict.detail["unattributed_total"], 1)
        self.assertEqual(verdict.detail["unit_total"], 1)
        self.assertIn("cannot be attributed", verdict.reason)

    def test_empty_frame_passes_with_zero_units(self):
        verdict = build_unit_verdict([], unit_key="shrid2")
        self.assertTrue(verdict.ok)
        self.assertEqual(verdict.detail["row_total"], 0)

    def test_assert_raises_with_the_reason(self):
        with self.assertRaises(InferenceGateError) as caught:
            assert_one_row_per_unit([{"k": "a"}, {"k": "a"}], unit_key="k")
        self.assertIn("more than one row", str(caught.exception))
        assert_one_row_per_unit([{"k": "a"}, {"k": "b"}], unit_key="k")

    def test_it_consumes_a_generator_once(self):
        rows = ({"k": str(i)} for i in range(3))
        self.assertTrue(build_unit_verdict(rows, unit_key="k"))


if __name__ == "__main__":
    unittest.main()

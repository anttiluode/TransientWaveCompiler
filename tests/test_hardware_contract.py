import unittest

from transientwave.hardware_contract import (
    TW1AHardwareProfile,
    architecture_dynamic_range_budget,
    required_signed_midtread_bits,
    schedule_kind,
    signed_midtread_positive_codes,
)
from transientwave.order_benchmarks import compile_temporal_order_task


class HardwareContractMathTests(unittest.TestCase):
    def test_signed_midtread_code_count(self):
        self.assertEqual(signed_midtread_positive_codes(8), 127)
        self.assertEqual(signed_midtread_positive_codes(10), 511)

    def test_closed_form_g8_budget(self):
        b = architecture_dynamic_range_budget(8.0, min_codes=4)
        self.assertAlmostEqual(b["amplitude_decay_compensation"], 8.0)
        self.assertAlmostEqual(b["broadband_drive_envelope_span"], 8.0)
        self.assertAlmostEqual(b["quadratic_error_envelope_span"], 64.0)
        self.assertEqual(b["broadband_drive_bits"], 7)
        self.assertEqual(b["impulse_drive_bits"], 4)
        self.assertEqual(b["quadratic_error_bits"], 10)
        self.assertAlmostEqual(b["amplitude_dynamic_range_db"], 18.0617997398, places=8)
        self.assertAlmostEqual(b["quadratic_error_dynamic_range_db"], 36.1235994797, places=8)

    def test_required_bits_matches_code_inequality(self):
        for span in (1.0, 2.0, 8.0, 64.0, 100.0):
            bits = required_signed_midtread_bits(span, min_codes=4)
            self.assertGreaterEqual(signed_midtread_positive_codes(bits) / span, 4.0)
            if bits > 2:
                self.assertLess(signed_midtread_positive_codes(bits - 1) / span, 4.0)

    def test_schedule_classification(self):
        self.assertEqual(schedule_kind([0, 0, 0]), "silent")
        self.assertEqual(schedule_kind([0, 1, 0]), "impulse")
        self.assertEqual(schedule_kind([0, 1, 0.5]), "broadband")


class CompiledHardwareContractTests(unittest.TestCase):
    def test_tw1a_manifest_carries_hardware_contract(self):
        task = compile_temporal_order_task(810)
        manifest = task["target"]
        contract = manifest["hardware_contract"]

        self.assertEqual(contract["version"], "tw1a-hardware-contract-v0.1")
        self.assertEqual(
            manifest["physical"]["programmable_edge_semantics"]["kind"],
            "reciprocal_rank1_edge_cell",
        )
        self.assertEqual(
            contract["dynamic_range"]["quantizer_semantics"],
            "signed_midtread_zero_preserving",
        )
        self.assertEqual(
            contract["dynamic_range"]["architecture_worst_case"]["quadratic_error_bits"],
            10,
        )
        self.assertTrue(
            contract["profile_checks"]["profile_error_dac_meets_full_boundary_gain_promise"]
        )
        self.assertTrue(
            contract["profile_checks"]["rank1_edge_cell_semantics_required"]
        )
        self.assertTrue(
            contract["profile_checks"]["zero_preserving_codes_required"]
        )
        self.assertTrue(
            contract["profile_checks"]["complete_gradient_operator_coherence_recommended"]
        )

        drives = contract["dynamic_range"]["program"]["drive_ports"]
        self.assertEqual(len(drives), 2)
        self.assertTrue(all(d["source_schedule_kind"] == "impulse" for d in drives))
        self.assertTrue(all(d["compiled_amplitude_span"] == 1.0 for d in drives))
        self.assertTrue(all(d["required_signed_bits_at_margin"] == 4 for d in drives))

    def test_reference_profile_distinguishes_drive_and_error_dac(self):
        p = TW1AHardwareProfile()
        self.assertEqual(p.edge_bits, 8)
        self.assertEqual(p.drive_dac_bits, 8)
        self.assertEqual(p.error_dac_bits, 10)
        self.assertEqual(p.sense_adc_bits, 8)
        self.assertTrue(p.static_sense_pga)
        self.assertTrue(p.coherent_complete_gradient_evaluation)


if __name__ == "__main__":
    unittest.main()

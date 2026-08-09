import unittest

from transientwave.active_summing_budget import (
    averaged_echo_ideal_cap_energy_ratio,
    thermal_capacitance_ratio,
)


class CostTradeoffTests(unittest.TestCase):
    def test_doubling_thermal_base_quarters_capacitance(self):
        self.assertAlmostEqual(thermal_capacitance_ratio(1e-5, 2e-5), 0.25)

    def test_two_echo_average_at_double_b_halves_ideal_cap_work(self):
        self.assertAlmostEqual(
            averaged_echo_ideal_cap_energy_ratio(1e-5, 2e-5, 2), 0.5
        )

    def test_four_echo_average_at_double_b_breaks_even_ideal_cap_work(self):
        self.assertAlmostEqual(
            averaged_echo_ideal_cap_energy_ratio(1e-5, 2e-5, 4), 1.0
        )

    def test_eight_echo_average_at_double_b_doubles_ideal_cap_work(self):
        self.assertAlmostEqual(
            averaged_echo_ideal_cap_energy_ratio(1e-5, 2e-5, 8), 2.0
        )

    def test_invalid_repeat_count_rejected(self):
        with self.assertRaises(ValueError):
            averaged_echo_ideal_cap_energy_ratio(1e-5, 2e-5, 0)


if __name__ == "__main__":
    unittest.main()

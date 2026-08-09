import unittest

from transientwave.active_summing_budget import (
    architecture_cap_area_ratio,
    averaged_echo_ideal_cap_energy_ratio,
    kick_drift_known_cap_factor,
    thermal_capacitance_ratio,
    v08_known_cap_factor,
)


class CostTradeoffTests(unittest.TestCase):
    def test_doubling_thermal_base_quarters_capacitance(self):
        self.assertAlmostEqual(thermal_capacitance_ratio(1e-5,2e-5),0.25)

    def test_gradient_averaging_ideal_cap_work(self):
        self.assertAlmostEqual(averaged_echo_ideal_cap_energy_ratio(1e-5,2e-5,2),0.5)
        self.assertAlmostEqual(averaged_echo_ideal_cap_energy_ratio(1e-5,2e-5,4),1.0)
        self.assertAlmostEqual(averaged_echo_ideal_cap_energy_ratio(1e-5,2e-5,8),2.0)

    def test_invalid_repeat_count_rejected(self):
        with self.assertRaises(ValueError): averaged_echo_ideal_cap_energy_ratio(1e-5,2e-5,0)

    def test_known_v08_cap_factor(self):
        self.assertAlmostEqual(v08_known_cap_factor(),381.68)

    def test_known_kick_drift_cap_factor_includes_drift_bank(self):
        self.assertAlmostEqual(kick_drift_known_cap_factor(),357.68)

    def test_kick_drift_double_b_area_ratio(self):
        ratio=architecture_cap_area_ratio(reference_factor=v08_known_cap_factor(),candidate_factor=kick_drift_known_cap_factor(),reference_b=1e-5,candidate_b=2e-5)
        self.assertAlmostEqual(ratio,357.68/(4.0*381.68))
        self.assertGreater(1.0/ratio,4.26)


if __name__=="__main__": unittest.main()

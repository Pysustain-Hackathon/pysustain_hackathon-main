"""
Automated Unit Tests for FASAL Digital Farm Twin.
Validates database, ML yield model, simulation engine, sustainability scorecard,
recommender, SMS generator, and persistence.
"""

import unittest
import pandas as pd
from core.db import get_farm_unified_df, get_farm_by_id
from core.models import get_yield_predictor
from core.simulation import simulate_scenario, calculate_pump_energy_kwh, get_bau_baseline
from core.sustainability import calculate_sustainability_score
from core.recommender import recommend_crops
from core.advisory import generate_sms_advisory
from core.persistence import get_default_scenarios, scenarios_to_dataframe, export_scenarios_csv


class TestFasalComponents(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.farm = get_farm_by_id("plot_001")

    def test_01_db_loads_data(self):
        df, mp, src = get_farm_unified_df()
        self.assertGreaterEqual(len(df), 250, "Unified dataset should contain at least 250 farms")
        self.assertIn("farm_id", df.columns)
        self.assertIn("ph", df.columns)
        self.assertIn("organic_carbon", df.columns)
        self.assertIn("current_crop", df.columns)
        self.assertFalse(mp.empty, "Market prices table should not be empty")

    def test_02_yield_model_predictions_and_intervals(self):
        predictor = get_yield_predictor()
        sample = {
            "crop": "Wheat",
            "soil_ph": 7.0,
            "soil_n": 80.0,
            "applied_n": 100.0,
            "irrigation_method": "Drip",
            "irrigation_mm": 350.0,
            "temp_max": 29.0,
            "rainfall_mm": 100.0,
            "weather_scenario": "Normal"
        }
        res = predictor.predict(sample)
        self.assertIn("yield_mean", res)
        self.assertIn("yield_lower_80", res)
        self.assertIn("yield_upper_80", res)
        self.assertLessEqual(res["yield_lower_80"], res["yield_mean"])
        self.assertGreaterEqual(res["yield_upper_80"], res["yield_mean"])
        self.assertGreater(len(res["drivers"]), 0, "Model should return plain-language drivers")

    def test_03_model_rmse_improvement_over_baseline(self):
        predictor = get_yield_predictor()
        metrics = predictor.metrics
        self.assertGreaterEqual(metrics["rmse_improvement_pct"], 10.0, "Model RMSE improvement must be >= 10% (Objective O1)")

    def test_04_physics_pump_energy(self):
        # 1,000 m3 of water lifted 40m with 65% efficiency
        # E = (1000 * 9.81 * 1000 * 40) / (3.6e6 * 0.65) = 392,400,000 / 2,340,000 = ~167.69 kWh
        kwh = calculate_pump_energy_kwh(1000.0)
        self.assertAlmostEqual(kwh, 167.69, places=0)
        zero_kwh = calculate_pump_energy_kwh(0.0)
        self.assertEqual(zero_kwh, 0.0)

    def test_05_simulation_water_savings(self):
        # Test Drip vs Flood for Wheat
        sim_flood = simulate_scenario(self.farm, crop="Wheat", irrigation_method="Flood / Furrow", irrigation_mm=450.0)
        sim_drip = simulate_scenario(self.farm, crop="Wheat", irrigation_method="Drip", irrigation_mm=300.0)
        self.assertLess(sim_drip["water_liters"], sim_flood["water_liters"], "Drip should consume less water than Flood")
        self.assertGreater(sim_drip["water_saved_pct"], 0.0)

    def test_06_sustainability_scorecard(self):
        sim = simulate_scenario(self.farm, crop="Moong Dal", irrigation_method="Drip", irrigation_mm=180.0, applied_n=20.0)
        sust = calculate_sustainability_score(sim, self.farm)
        self.assertGreaterEqual(sust["composite_score"], 0.0)
        self.assertLessEqual(sust["composite_score"], 100.0)
        self.assertIn("Water Efficiency", sust["pillars"])
        self.assertIn("Soil Health Trend", sust["pillars"])

    def test_07_profit_first_crop_recommender(self):
        rec = recommend_crops(self.farm, water_cap_mm=500.0)
        self.assertIsNotNone(rec["top_recommendation_1"])
        self.assertIsNotNone(rec["current_crop"])
        self.assertGreater(len(rec["ranked_crops"]), 0)
        # Verify water cap checking works
        for r in rec["ranked_crops"]:
            self.assertEqual(r["is_within_cap"], r["applied_mm"] <= 500.0)

    def test_08_sms_advisory_character_limit(self):
        sim = simulate_scenario(self.farm, crop="Maize", irrigation_method="Drip", irrigation_mm=350.0)
        # English
        sms_en = generate_sms_advisory(self.farm, sim, language="English")
        self.assertTrue(sms_en["is_valid_sms"], f"English SMS exceeded 160 characters: {sms_en['char_count']}")
        self.assertLessEqual(sms_en["char_count"], 160)
        # Hindi
        sms_hi = generate_sms_advisory(self.farm, sim, language="Hindi")
        self.assertTrue(sms_hi["is_valid_sms"], f"Hindi SMS exceeded 160 characters: {sms_hi['char_count']}")
        self.assertLessEqual(sms_hi["char_count"], 160)

    def test_09_scenario_persistence_and_csv_export(self):
        scenarios = get_default_scenarios(self.farm)
        self.assertGreaterEqual(len(scenarios), 3)
        df = scenarios_to_dataframe(scenarios)
        self.assertEqual(len(df), len(scenarios))
        self.assertIn("Net Profit (Rs)", df.columns)
        csv_str = export_scenarios_csv(scenarios)
        self.assertIn("Scenario Name", csv_str)
        self.assertIn("Net Profit (Rs)", csv_str)


if __name__ == "__main__":
    unittest.main()

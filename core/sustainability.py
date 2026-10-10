"""
Sustainability Scorecard for FASAL.
Implements Objective O6 and UN SDG alignment (SDG 2, 6, 12, 13, 15).
Transparent 5-pillar composite scoring (0-100) quantifying:
1. Water Efficiency & Stewardship (0-25)
2. Nutrient Management & N-Surplus (0-20)
3. Energy & Carbon Footprint (0-20)
4. Soil Health & Legume Benefit (0-20)
5. Climate & Diversity Resilience (0-15)
"""

from core.config import CROP_AGRONOMY, IRRIGATION_METHODS


def calculate_sustainability_score(sim_result: dict, farm_state: dict) -> dict:
    """
    Computes componentized sustainability score and returns pillar breakdowns,
    ratings, and plain-language agronomic recommendations.
    """
    crop = sim_result["crop"]
    agro = CROP_AGRONOMY.get(crop, CROP_AGRONOMY["Wheat"])
    method = sim_result["irrigation_method"]
    applied_n = sim_result["applied_n"]
    applied_p = sim_result["applied_p"]
    applied_k = sim_result["applied_k"]
    water_saved_pct = sim_result.get("water_saved_pct", 0.0)
    energy_kwh = sim_result.get("energy_kwh", 100.0)
    total_yield_q = max(0.1, sim_result.get("total_yield_q", 10.0))
    risk_score = sim_result.get("risk_score", 30)

    organic_carbon = float(farm_state.get("organic_carbon", 0.55))
    soil_ph = float(farm_state.get("ph", 7.0))

    # ----------------------------------------------------
    # Pillar 1: Water Efficiency & Stewardship (0 - 25 pts)
    # ----------------------------------------------------
    if method == "Rainfed":
        water_score = 25.0
    elif method == "Drip":
        water_score = 21.0 + min(4.0, max(0.0, water_saved_pct / 15.0))
    elif method == "Sprinkler":
        water_score = 16.0 + min(4.0, max(0.0, water_saved_pct / 20.0))
    else:  # Flood / Furrow
        if water_saved_pct > 15:
            water_score = 13.0
        elif water_saved_pct >= 0:
            water_score = 9.0
        else:
            water_score = max(4.0, 8.0 + (water_saved_pct / 10.0))

    # Water productivity bonus
    wp = sim_result.get("water_prod_kg_m3", 1.0)
    if wp > 2.0:
        water_score = min(25.0, water_score + 2.0)

    # ----------------------------------------------------
    # Pillar 2: Nutrient Management & N-Surplus (0 - 20 pts)
    # ----------------------------------------------------
    opt_n = (agro["N"][0] + agro["N"][1]) / 2.0
    n_surplus = applied_n - opt_n  # kg N / ha

    if agro["is_legume"]:
        # Legumes need minimal nitrogen, so low applied N is rewarded
        if applied_n <= agro["N"][1]:
            nutrient_score = 20.0
        else:
            nutrient_score = max(10.0, 20.0 - (applied_n - agro["N"][1]) * 0.3)
    else:
        if abs(n_surplus) <= 15:
            nutrient_score = 20.0
        elif n_surplus > 15:
            # Over-application penalty (nitrate runoff into groundwater)
            nutrient_score = max(5.0, 20.0 - (n_surplus - 15) * 0.25)
        else:
            # Under-application
            nutrient_score = max(10.0, 20.0 - abs(n_surplus) * 0.2)

    # ----------------------------------------------------
    # Pillar 3: Energy & Carbon Intensity (0 - 20 pts)
    # ----------------------------------------------------
    # Pumping kWh per quintal of yield
    energy_intensity = energy_kwh / total_yield_q
    if energy_intensity < 8.0:
        energy_score = 20.0
    elif energy_intensity < 20.0:
        energy_score = 18.0 - ((energy_intensity - 8.0) / 12.0) * 5.0
    elif energy_intensity < 45.0:
        energy_score = 12.0 - ((energy_intensity - 20.0) / 25.0) * 6.0
    else:
        energy_score = max(4.0, 6.0 - ((energy_intensity - 45.0) / 30.0) * 2.0)

    # ----------------------------------------------------
    # Pillar 4: Soil Health & Legume Bonus (0 - 20 pts)
    # ----------------------------------------------------
    soil_score = 10.0
    # Organic carbon bonus
    if organic_carbon >= 0.70:
        soil_score += 4.0
    elif organic_carbon >= 0.50:
        soil_score += 2.5
    else:
        soil_score += 1.0

    # Legume nitrogen fixation bonus (+6 points directly into soil fertility)
    if agro["is_legume"]:
        soil_score += 6.0

    # pH suitability bonus
    if agro["pH"][0] <= soil_ph <= agro["pH"][1]:
        soil_score += 0.0  # Already in baseline
    else:
        soil_score = max(5.0, soil_score - 2.0)
    soil_score = min(20.0, soil_score)

    # ----------------------------------------------------
    # Pillar 5: Climate & Diversity Resilience (0 - 15 pts)
    # ----------------------------------------------------
    drought_tol = agro["drought_tolerance"]
    resilience_score = (drought_tol * 10.0) + max(0.0, (100 - risk_score) * 0.05)
    resilience_score = min(15.0, max(3.0, resilience_score))

    # Composite Total Score
    total_score = round(water_score + nutrient_score + energy_score + soil_score + resilience_score, 1)
    total_score = float(min(100.0, max(10.0, total_score)))

    # Classification & Badge
    if total_score >= 80.0:
        rating = "Excellent (Regenerative)"
        badge_color = "#16a34a"  # Green
        summary = "Highly sustainable plan conserving groundwater and enriching soil health."
    elif total_score >= 65.0:
        rating = "Good (Resource-Smart)"
        badge_color = "#2d6a4f"  # Forest green
        summary = "Balanced resource consumption with significant water and input efficiency."
    elif total_score >= 50.0:
        rating = "Moderate (Standard Practice)"
        badge_color = "#d97706"  # Amber
        summary = "Average sustainability; opportunities exist to reduce water and pumping energy."
    else:
        rating = "Stressed (Resource Heavy)"
        badge_color = "#dc2626"  # Red
        summary = "High groundwater depletion and input pressure. Consider drip micro-irrigation or legume rotation."

    # Actionable improvement recommendations
    recommendations = []
    if method == "Flood / Furrow":
        recommendations.append("Switch from Flood to Drip or Sprinkler to recover up to 40% conveyance loss.")
    if n_surplus > 20:
        recommendations.append(f"Reduce synthetic nitrogen by {n_surplus:.0f} kg/ha to mitigate nitrate leaching.")
    if not agro["is_legume"]:
        recommendations.append("Introduce a short-duration pulse (Moong or Chickpea) in rotation for biological nitrogen fixation.")
    if energy_intensity > 25.0:
        recommendations.append("High pumping energy intensity detected. Schedule early morning irrigation to cut evapotranspiration.")

    return {
        "composite_score": total_score,
        "rating": rating,
        "badge_color": badge_color,
        "summary": summary,
        "pillars": {
            "Water Efficiency": {"score": round(water_score, 1), "max": 25, "pct": round((water_score / 25) * 100, 0)},
            "Nutrient Management": {"score": round(nutrient_score, 1), "max": 20, "pct": round((nutrient_score / 20) * 100, 0)},
            "Energy & Carbon": {"score": round(energy_score, 1), "max": 20, "pct": round((energy_score / 20) * 100, 0)},
            "Soil Health Trend": {"score": round(soil_score, 1), "max": 20, "pct": round((soil_score / 20) * 100, 0)},
            "Climate Resilience": {"score": round(resilience_score, 1), "max": 15, "pct": round((resilience_score / 15) * 100, 0)}
        },
        "n_surplus_kg_ha": round(n_surplus, 1),
        "energy_kwh_per_q": round(energy_intensity, 1),
        "recommendations": recommendations
    }

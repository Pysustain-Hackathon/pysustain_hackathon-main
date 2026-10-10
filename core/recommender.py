"""
Profit-First Crop Recommender with Water Cap for FASAL.
Implements Objective O3 and Research Gap G4.
Ranks viable crop alternatives by Net Profit while strictly respecting or penalizing
water usage against an officer-defined or aquifer-based Water Cap.
Highlights the baseline MSP monoculture alongside the top-2 sustainable alternatives.
"""

import pandas as pd
from core.config import CROP_AGRONOMY, IRRIGATION_METHODS
from core.simulation import simulate_scenario, get_bau_baseline
from core.sustainability import calculate_sustainability_score


def recommend_crops(
    farm_state: dict,
    water_cap_mm: float = 600.0,
    preferred_irrigation: str = "Drip",
    weather_scenario: str = "Normal",
    use_msp: bool = True
) -> dict:
    """
    Evaluates all 8 regional crops for the given farm parcel and ranks them by Net Profit,
    flagging feasibility against the water cap.
    """
    baseline_bau = get_bau_baseline(farm_state)
    current_crop = baseline_bau["crop"]

    results = []

    for crop_name, agro in CROP_AGRONOMY.items():
        # Recommend appropriate irrigation method based on crop nature
        method = preferred_irrigation
        if crop_name in ["Moong Dal", "Pearl Millet (Bajra)"] and preferred_irrigation == "Flood / Furrow":
            method = "Sprinkler"

        # Optimal irrigation depth for this crop
        target_irrig_mm = (agro["irrig_mm"][0] + agro["irrig_mm"][1]) / 2.0
        eff = IRRIGATION_METHODS.get(method, IRRIGATION_METHODS["Drip"])["efficiency"]
        # With efficient irrigation, applied mm can be reduced proportionally
        applied_mm = round(target_irrig_mm * (0.65 / eff), 1)

        # Optimal nitrogen for this crop
        applied_n = (agro["N"][0] + agro["N"][1]) / 2.0
        applied_p = (agro["P"][0] + agro["P"][1]) / 2.0
        applied_k = (agro["K"][0] + agro["K"][1]) / 2.0

        # Simulate
        sim = simulate_scenario(
            farm_state=farm_state,
            crop=crop_name,
            irrigation_method=method,
            irrigation_mm=applied_mm,
            applied_n=applied_n,
            applied_p=applied_p,
            applied_k=applied_k,
            weather_scenario=weather_scenario,
            use_msp=use_msp
        )

        sust = calculate_sustainability_score(sim, farm_state)

        # Check water cap compliance
        is_within_cap = applied_mm <= water_cap_mm
        cap_delta_mm = applied_mm - water_cap_mm

        results.append({
            "crop": crop_name,
            "display_name": agro["display_name"],
            "season": agro["season"],
            "category": agro["category"],
            "is_msp_staple": agro["is_msp_staple"],
            "is_current": (crop_name == current_crop),
            "method": method,
            "applied_mm": applied_mm,
            "is_within_cap": is_within_cap,
            "cap_delta_mm": round(cap_delta_mm, 1),
            "yield_q_acre": sim["yield_q_acre"],
            "gross_revenue": sim["gross_revenue"],
            "total_cost": sim["total_cost"],
            "net_profit": sim["net_profit"],
            "net_profit_acre": sim["net_profit_acre"],
            "water_liters": sim["water_liters"],
            "water_saved_pct": sim["water_saved_pct"],
            "profit_delta_rs": sim["profit_delta_rs"],
            "profit_per_drop_rs_m3": sim["profit_per_drop_rs_m3"],
            "sustainability_score": sust["composite_score"],
            "sustainability_rating": sust["rating"],
            "risk_level": sim["risk_level"]
        })

    # Sort crops: prioritize crops within water cap, then rank by net profit descending
    within_cap_crops = [r for r in results if r["is_within_cap"]]
    exceeds_cap_crops = [r for r in results if not r["is_within_cap"]]

    within_cap_crops.sort(key=lambda x: x["net_profit_acre"], reverse=True)
    exceeds_cap_crops.sort(key=lambda x: x["net_profit_acre"], reverse=True)

    ranked_all = within_cap_crops + exceeds_cap_crops

    # Identify Top 2 Alternatives (excluding current crop if possible)
    alternatives = [r for r in within_cap_crops if r["crop"] != current_crop]
    top_1 = alternatives[0] if len(alternatives) > 0 else (within_cap_crops[0] if within_cap_crops else ranked_all[0])
    top_2 = alternatives[1] if len(alternatives) > 1 else (within_cap_crops[1] if len(within_cap_crops) > 1 else (ranked_all[1] if len(ranked_all) > 1 else None))

    current_crop_res = next((r for r in ranked_all if r["crop"] == current_crop), ranked_all[0])

    return {
        "water_cap_mm": water_cap_mm,
        "current_crop": current_crop_res,
        "top_recommendation_1": top_1,
        "top_recommendation_2": top_2,
        "ranked_crops": ranked_all,
        "bau_baseline": baseline_bau
    }

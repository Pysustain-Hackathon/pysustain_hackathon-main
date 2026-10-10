"""
Scenario Persistence and State Management for FASAL.
Maintains user-configured scenarios across Streamlit reruns and page navigation.
Enables creating, duplicating, updating, deleting, resetting, and exporting scenarios to CSV.
"""

import io
import pandas as pd
from core.simulation import simulate_scenario
from core.sustainability import calculate_sustainability_score


def get_default_scenarios(farm_state: dict) -> dict:
    """
    Constructs 3 realistic benchmark scenarios for a selected farm:
    - Plan A: Business-As-Usual (Flood-irrigated staple monoculture)
    - Plan B: High-Profit Alternative (Drip-irrigated Maize)
    - Plan C: Regenerative Pulse (Sprinkler Chickpea/Moong)
    """
    current_crop = farm_state.get("current_crop", "Wheat")

    # Plan A: BAU
    sim_a = simulate_scenario(
        farm_state=farm_state,
        crop=current_crop,
        irrigation_method="Flood / Furrow",
        irrigation_mm=450.0,
        applied_n=130.0,
        applied_p=30.0,
        applied_k=60.0,
        weather_scenario="Normal",
        use_msp=True
    )
    sust_a = calculate_sustainability_score(sim_a, farm_state)

    # Plan B: Drip Maize
    sim_b = simulate_scenario(
        farm_state=farm_state,
        crop="Maize",
        irrigation_method="Drip",
        irrigation_mm=360.0,
        applied_n=90.0,
        applied_p=40.0,
        applied_k=45.0,
        weather_scenario="Normal",
        use_msp=False
    )
    sust_b = calculate_sustainability_score(sim_b, farm_state)

    # Plan C: Sprinkler Chickpea
    sim_c = simulate_scenario(
        farm_state=farm_state,
        crop="Chickpea (Gram)",
        irrigation_method="Sprinkler",
        irrigation_mm=180.0,
        applied_n=30.0,
        applied_p=50.0,
        applied_k=30.0,
        weather_scenario="Normal",
        use_msp=True
    )
    sust_c = calculate_sustainability_score(sim_c, farm_state)

    return {
        f"Plan A: BAU {current_crop} (Flood)": {
            "name": f"Plan A: BAU {current_crop} (Flood)",
            "simulation": sim_a,
            "sustainability": sust_a,
            "tag": "Current Practice",
            "notes": "Conventional flood irrigation with guaranteed MSP procurement."
        },
        "Plan B: Drip Maize (High Profit)": {
            "name": "Plan B: Drip Maize (High Profit)",
            "simulation": sim_b,
            "sustainability": sust_b,
            "tag": "Water Saver",
            "notes": "Micro-irrigation saving ~35% water while boosting net margins."
        },
        "Plan C: Sprinkler Chickpea (Pulse)": {
            "name": "Plan C: Sprinkler Chickpea (Pulse)",
            "simulation": sim_c,
            "sustainability": sust_c,
            "tag": "Regenerative Legume",
            "notes": "Drought-hardy legume with natural biological nitrogen fixation."
        }
    }


def scenarios_to_dataframe(scenarios_dict: dict) -> pd.DataFrame:
    """
    Flattens scenario dictionary into a tabular DataFrame for comparison and export.
    """
    rows = []
    for name, item in scenarios_dict.items():
        sim = item["simulation"]
        sust = item["sustainability"]
        rows.append({
            "Scenario Name": name,
            "Crop": sim["crop"],
            "Irrigation Method": sim["irrigation_method"],
            "Applied Water (mm)": sim["irrigation_mm"],
            "Total Water (Litres)": sim["water_liters"],
            "Water Saved (%)": sim["water_saved_pct"],
            "Pump Energy (kWh)": sim["energy_kwh"],
            "Energy Cost (Rs)": sim["energy_cost"],
            "Predicted Yield (q/acre)": sim["yield_q_acre"],
            "80% Yield Range (q/ac)": f"{sim['yield_lower_80']} - {sim['yield_upper_80']}",
            "Total Yield (q)": sim["total_yield_q"],
            "Gross Revenue (Rs)": sim["gross_revenue"],
            "Total Cost (Rs)": sim["total_cost"],
            "Net Profit (Rs)": sim["net_profit"],
            "Net Profit / Acre (Rs)": sim["net_profit_acre"],
            "Profit Delta vs BAU (Rs)": sim["profit_delta_rs"],
            "Water Productivity (kg/m3)": sim["water_prod_kg_m3"],
            "Profit per Drop (Rs/m3)": sim["profit_per_drop_rs_m3"],
            "Sustainability Score": sust["composite_score"],
            "Sustainability Rating": sust["rating"],
            "Risk Level": sim["risk_level"],
            "Weather Scenario": sim["weather_scenario"],
            "Notes": item.get("notes", "")
        })
    return pd.DataFrame(rows)


def export_scenarios_csv(scenarios_dict: dict) -> str:
    """
    Returns CSV text string of all saved scenarios.
    """
    df = scenarios_to_dataframe(scenarios_dict)
    buffer = io.StringIO()
    df.to_csv(buffer, index=False)
    return buffer.getvalue()

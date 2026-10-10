"""
Digital Twin Simulation Engine for FASAL.
Executes what-if agronomic simulations across irrigation, nutrients, weather, and crops.
Computes water balance, physics-based pump energy (kWh), full economics (Gross revenue, costs, net profit),
water productivity (kg/m3 and Rs/m3), risk index, and BAU baseline comparisons.
"""

from core.config import (
    CROP_AGRONOMY, IRRIGATION_METHODS, WEATHER_SCENARIOS,
    PUMP_PARAMETERS, INPUT_COSTS, LITERS_PER_MM_ACRE, M3_PER_MM_ACRE, KG_PER_QUINTAL
)
from core.models import get_yield_predictor


def calculate_pump_energy_kwh(water_volume_m3: float) -> float:
    """
    Physics-style pump energy calculation:
    E (kWh) = (rho * g * V * H) / (3.6e6 * efficiency)
    """
    if water_volume_m3 <= 0:
        return 0.0
    rho = PUMP_PARAMETERS["water_density_kg_m3"]
    g = PUMP_PARAMETERS["gravity_m_s2"]
    h = PUMP_PARAMETERS["dynamic_head_m"]
    eff = PUMP_PARAMETERS["pump_efficiency"]

    energy_kwh = (rho * g * water_volume_m3 * h) / (3.6e6 * eff)
    return round(float(energy_kwh), 2)


def get_bau_baseline(farm_state: dict, baseline_crop: str = None):
    """
    Computes Business-As-Usual (BAU) baseline for the farm:
    Conventional flood-irrigated practice for the evaluated crop (or farm default).
    """
    current_crop = baseline_crop or farm_state.get("current_crop", "Wheat")
    if current_crop not in CROP_AGRONOMY:
        current_crop = "Wheat"

    agro = CROP_AGRONOMY[current_crop]
    area = float(farm_state.get("area_acres", 2.0))
    # BAU practice is Flood irrigation with middle of conventional water requirement
    bau_irrig_mm = (agro["irrig_mm"][0] + agro["irrig_mm"][1]) / 2.0
    bau_water_liters = bau_irrig_mm * LITERS_PER_MM_ACRE * area
    bau_water_m3 = bau_water_liters / 1000.0
    bau_energy_kwh = calculate_pump_energy_kwh(bau_water_m3)
    bau_energy_cost = bau_energy_kwh * PUMP_PARAMETERS["electricity_tariff_rs_kwh"]

    # Baseline yield
    base_yield_q_acre = (agro["yield_range"][0] + agro["yield_range"][1]) / 2.0
    base_total_yield_q = base_yield_q_acre * area
    base_price = agro["msp"]
    gross_rev = base_total_yield_q * base_price

    # Costs
    n_kg = (agro["N"][0] + agro["N"][1]) / 2.0 * area * 0.4047
    p_kg = (agro["P"][0] + agro["P"][1]) / 2.0 * area * 0.4047
    k_kg = (agro["K"][0] + agro["K"][1]) / 2.0 * area * 0.4047
    fert_cost = (
        n_kg * INPUT_COSTS["nitrogen_rs_kg"] +
        p_kg * INPUT_COSTS["phosphorus_rs_kg"] +
        k_kg * INPUT_COSTS["potassium_rs_kg"]
    )
    seed_cost = agro["seed_cost_acre"] * area
    labour_cost = agro["base_labour_cost_acre"] * area
    total_cost = seed_cost + labour_cost + fert_cost + bau_energy_cost
    net_profit = gross_rev - total_cost

    return {
        "crop": current_crop,
        "method": "Flood / Furrow",
        "irrig_mm": round(bau_irrig_mm, 1),
        "water_liters": round(bau_water_liters, 0),
        "water_m3": round(bau_water_m3, 1),
        "energy_kwh": round(bau_energy_kwh, 1),
        "energy_cost": round(bau_energy_cost, 0),
        "yield_q_acre": round(base_yield_q_acre, 2),
        "total_yield_q": round(base_total_yield_q, 2),
        "gross_revenue": round(gross_rev, 0),
        "total_cost": round(total_cost, 0),
        "net_profit": round(net_profit, 0),
        "net_profit_acre": round(net_profit / area, 0)
    }


def simulate_scenario(
    farm_state: dict,
    crop: str = "Wheat",
    irrigation_method: str = "Drip",
    irrigation_mm: float = 380.0,
    applied_n: float = 110.0,
    applied_p: float = 30.0,
    applied_k: float = 120.0,
    weather_scenario: str = "Normal",
    use_msp: bool = True
) -> dict:
    """
    Executes a complete digital twin farm simulation run.
    """
    agro = CROP_AGRONOMY.get(crop, CROP_AGRONOMY["Wheat"])
    method_cfg = IRRIGATION_METHODS.get(irrigation_method, IRRIGATION_METHODS["Drip"])
    weather_cfg = WEATHER_SCENARIOS.get(weather_scenario, WEATHER_SCENARIOS["Normal"])

    area_acres = float(farm_state.get("area_acres", 2.0))
    soil_ph = float(farm_state.get("ph", 7.0))
    soil_n = float(farm_state.get("nitrogen_kg_ha", 60.0))
    soil_p = float(farm_state.get("phosphorus_kg_ha", 30.0))
    soil_k = float(farm_state.get("potassium_kg_ha", 50.0))

    # Base weather
    temp_max = 30.0 + weather_cfg["temp_delta"]
    rainfall = max(0.0, 120.0 * weather_cfg["rainfall_mult"])

    if irrigation_method == "Rainfed":
        actual_irrig_mm = 0.0
    else:
        actual_irrig_mm = float(irrigation_mm)

    # ML Yield Prediction
    sample = {
        "crop": crop,
        "soil_ph": soil_ph,
        "soil_n": soil_n,
        "applied_n": applied_n,
        "applied_p": applied_p,
        "applied_k": applied_k,
        "irrigation_method": irrigation_method,
        "irrigation_mm": actual_irrig_mm,
        "weather_scenario": weather_scenario,
        "temp_max": temp_max,
        "rainfall_mm": rainfall
    }

    predictor = get_yield_predictor()
    ml_res = predictor.predict(sample)

    yield_q_acre = ml_res["yield_mean"]
    yield_lower_80 = ml_res["yield_lower_80"]
    yield_upper_80 = ml_res["yield_upper_80"]
    drivers = ml_res["drivers"]

    total_yield_q = yield_q_acre * area_acres
    total_yield_kg = total_yield_q * KG_PER_QUINTAL

    # Water balance
    water_liters = actual_irrig_mm * LITERS_PER_MM_ACRE * area_acres
    water_m3 = water_liters / 1000.0
    water_per_acre_liters = actual_irrig_mm * LITERS_PER_MM_ACRE

    # Pump energy
    energy_kwh = calculate_pump_energy_kwh(water_m3)
    energy_cost = energy_kwh * PUMP_PARAMETERS["electricity_tariff_rs_kwh"]

    # Price
    price_per_q = agro["msp"] if use_msp else agro["market_price"]
    gross_revenue = total_yield_q * price_per_q

    # Fertilizer Costs (converted from kg/ha to kg/acre: 1 ha = 2.471 acres => * 0.4047)
    ha_equiv = area_acres * 0.4047
    cost_n = applied_n * ha_equiv * INPUT_COSTS["nitrogen_rs_kg"]
    cost_p = applied_p * ha_equiv * INPUT_COSTS["phosphorus_rs_kg"]
    cost_k = applied_k * ha_equiv * INPUT_COSTS["potassium_rs_kg"]
    fert_cost = cost_n + cost_p + cost_k

    # Seed and Labour
    seed_cost = agro["seed_cost_acre"] * area_acres
    labour_cost = agro["base_labour_cost_acre"] * area_acres * method_cfg["cost_multiplier"]

    total_cost = seed_cost + labour_cost + fert_cost + energy_cost
    net_profit = gross_revenue - total_cost
    net_profit_acre = net_profit / area_acres

    # Water Productivity (kg per m³ and Rs per m³)
    if water_m3 > 0:
        water_prod_kg_m3 = total_yield_kg / water_m3
        profit_per_drop_rs_m3 = net_profit / water_m3
    else:
        # Rainfed
        water_prod_kg_m3 = total_yield_kg / max(1.0, (rainfall * M3_PER_MM_ACRE * area_acres))
        profit_per_drop_rs_m3 = net_profit / max(1.0, (rainfall * M3_PER_MM_ACRE * area_acres))

    # BAU Comparison (conventional flood practice for this crop)
    bau = get_bau_baseline(farm_state, baseline_crop=crop)
    water_saved_liters = max(0.0, bau["water_liters"] - water_liters)
    water_saved_pct = ((bau["water_liters"] - water_liters) / max(1.0, bau["water_liters"])) * 100.0
    profit_delta_rs = net_profit - bau["net_profit"]
    profit_delta_pct = (profit_delta_rs / max(1.0, abs(bau["net_profit"]))) * 100.0
    energy_saved_kwh = max(0.0, bau["energy_kwh"] - energy_kwh)

    # Risk Index Classification
    tolerance = agro["drought_tolerance"]
    if weather_scenario == "Heatwave":
        risk_level = "High" if tolerance < 0.6 else "Moderate"
        risk_score = 75 if tolerance < 0.6 else 45
    elif weather_scenario == "Dry / Drought":
        risk_level = "High" if (actual_irrig_mm < agro["irrig_mm"][0] * 0.6 and tolerance < 0.5) else ("Moderate" if tolerance < 0.7 else "Low")
        risk_score = 65 if risk_level == "High" else (40 if risk_level == "Moderate" else 20)
    elif irrigation_method == "Flood / Furrow":
        risk_level = "Moderate"
        risk_score = 35
    else:
        risk_level = "Low"
        risk_score = 15

    return {
        "crop": crop,
        "irrigation_method": irrigation_method,
        "irrigation_mm": round(actual_irrig_mm, 1),
        "applied_n": round(applied_n, 1),
        "applied_p": round(applied_p, 1),
        "applied_k": round(applied_k, 1),
        "weather_scenario": weather_scenario,
        "pricing_mode": "MSP" if use_msp else "Market Price",
        "price_per_quintal": price_per_q,

        # Yield
        "yield_q_acre": round(yield_q_acre, 2),
        "yield_lower_80": round(yield_lower_80, 2),
        "yield_upper_80": round(yield_upper_80, 2),
        "total_yield_q": round(total_yield_q, 2),
        "total_yield_kg": round(total_yield_kg, 1),
        "drivers": drivers,

        # Water
        "water_liters": round(water_liters, 0),
        "water_m3": round(water_m3, 1),
        "water_per_acre_liters": round(water_per_acre_liters, 0),
        "water_prod_kg_m3": round(water_prod_kg_m3, 2),
        "profit_per_drop_rs_m3": round(profit_per_drop_rs_m3, 2),

        # Energy
        "energy_kwh": round(energy_kwh, 1),
        "energy_cost": round(energy_cost, 0),

        # Financials
        "gross_revenue": round(gross_revenue, 0),
        "seed_cost": round(seed_cost, 0),
        "labour_cost": round(labour_cost, 0),
        "fert_cost": round(fert_cost, 0),
        "total_cost": round(total_cost, 0),
        "net_profit": round(net_profit, 0),
        "net_profit_acre": round(net_profit_acre, 0),

        # BAU Comparisons
        "bau_crop": bau["crop"],
        "bau_water_liters": bau["water_liters"],
        "bau_profit": bau["net_profit"],
        "water_saved_liters": round(water_saved_liters, 0),
        "water_saved_pct": round(water_saved_pct, 1),
        "profit_delta_rs": round(profit_delta_rs, 0),
        "profit_delta_pct": round(profit_delta_pct, 1),
        "energy_saved_kwh": round(energy_saved_kwh, 1),

        # Risk
        "risk_level": risk_level,
        "risk_score": risk_score
    }

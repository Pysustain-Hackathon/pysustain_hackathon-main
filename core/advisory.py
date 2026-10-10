"""
Low-Bandwidth Farmer Advisory and SMS Generator for FASAL.
Implements Objective O7 and Research Gap G5.
Generates compliant SMS messages (<= 160 characters) in English and Hindi
containing actionable management guidance, expected yield range, and water impact.
"""


def generate_sms_advisory(farm_state: dict, sim_result: dict, language: str = "English") -> dict:
    """
    Generates an SMS advisory strictly <= 160 characters for feature phones.
    """
    farm_id = farm_state.get("farm_id", "P01")
    farmer_name = farm_state.get("farmer_name", "Farmer").split()[0]
    crop = sim_result["crop"]
    method = sim_result["irrigation_method"]
    y_low = sim_result["yield_lower_80"]
    y_high = sim_result["yield_upper_80"]
    water_saved_pct = sim_result.get("water_saved_pct", 0.0)
    profit_delta = sim_result.get("profit_delta_rs", 0.0)

    # Simplified method names
    method_short_en = {
        "Drip": "drip",
        "Sprinkler": "sprinkler",
        "Flood / Furrow": "furrow",
        "Rainfed": "rainfed"
    }.get(method, "drip")

    method_short_hi = {
        "Drip": "ड्रिप",
        "Sprinkler": "फव्वारा",
        "Flood / Furrow": "नाली",
        "Rainfed": "वर्षा"
    }.get(method, "ड्रिप")

    crop_hi = {
        "Wheat": "गेहूं",
        "Rice": "धान",
        "Cotton": "कपास",
        "Maize": "मक्का",
        "Chickpea (Gram)": "चना",
        "Moong Dal": "मूँग",
        "Sugarcane": "गन्ना",
        "Pearl Millet (Bajra)": "बाजरा"
    }.get(crop, crop)

    if language == "Hindi":
        # Formulate concise Hindi SMS
        sign = "+" if profit_delta >= 0 else ""
        msg = f"फसल {farm_id}: {farmer_name} जी, {method_short_hi} से {crop_hi} लगाएं। उपज {y_low:.0f}-{y_high:.0f}क्विं/एकड़। पानी बचत {water_saved_pct:.0f}%, लाभ {sign}₹{profit_delta:.0f}। -कृषि विभाग"
        # If over 160 chars, compress
        if len(msg) > 160:
            msg = f"फसल {farm_id}: {method_short_hi} से {crop_hi} लगाएं। उपज {y_low:.0f}-{y_high:.0f}क्विं/एकड़। पानी बचत {water_saved_pct:.0f}%, लाभ +₹{profit_delta:.0f}। -कृषि"
    else:
        # Formulate concise English SMS
        sign = "+" if profit_delta >= 0 else ""
        msg = f"FASAL {farm_id}: {farmer_name}, plant {crop} w/ {method_short_en}. Exp yield {y_low:.0f}-{y_high:.0f} q/ac. Save {water_saved_pct:.0f}% water, profit {sign}Rs {profit_delta:.0f}. -Agri Dept"
        if len(msg) > 160:
            msg = f"FASAL {farm_id}: Plant {crop} w/ {method_short_en}. Yield {y_low:.0f}-{y_high:.0f} q/ac. Save {water_saved_pct:.0f}% water, {sign}Rs {profit_delta:.0f} profit. -Agri"

    return {
        "message": msg,
        "char_count": len(msg),
        "is_valid_sms": len(msg) <= 160,
        "language": language
    }


def generate_officer_detailed_note(farm_state: dict, sim_result: dict, sust_result: dict) -> str:
    """
    Generates an agronomic briefing for the field extension officer.
    """
    farm_id = farm_state.get("farm_id", "plot_001")
    farmer = farm_state.get("farmer_name", "Farmer")
    area = farm_state.get("area_acres", 2.0)
    district = farm_state.get("district", "Region")
    state = farm_state.get("state", "State")

    note = (
        f"OFFICER FIELD NOTE — FASAL DIGITAL TWIN\n"
        f"Farm: {farm_id} ({farmer}, {area} acres) | District: {district}, {state}\n"
        f"Proposed Strategy: {sim_result['crop']} under {sim_result['irrigation_method']} ({sim_result['irrigation_mm']} mm applied)\n"
        f"• Expected Yield: {sim_result['yield_q_acre']} q/acre (80% Confidence: {sim_result['yield_lower_80']} – {sim_result['yield_upper_80']} q/ac)\n"
        f"• Water Footprint: {sim_result['water_liters']:,.0f} L ({sim_result['water_saved_pct']}% saved vs BAU)\n"
        f"• Groundwater Pumping Energy: {sim_result['energy_kwh']} kWh (₹{sim_result['energy_cost']})\n"
        f"• Net Profit: ₹{sim_result['net_profit']:,.0f} (₹{sim_result['net_profit_acre']:,.0f}/acre | Delta: ₹{sim_result['profit_delta_rs']:,.0f})\n"
        f"• Sustainability Score: {sust_result['composite_score']}/100 [{sust_result['rating']}]\n"
        f"Key Action: Verify soil moisture prior to first fertigation cycle."
    )
    return note

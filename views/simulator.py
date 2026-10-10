"""
Mobile-First Digital Twin Simulator Screen for FASAL.
Core interactive what-if simulation tool with controllable levers for
crop, irrigation, fertilizer, weather, and pricing.
Provides real-time yield prediction with 80% intervals, water balance,
pump energy, economics, SHAP drivers, and low-bandwidth SMS delivery.
"""

import streamlit as st
from core.config import CROP_AGRONOMY, IRRIGATION_METHODS, WEATHER_SCENARIOS
from core.db import get_farm_by_id
from core.simulation import simulate_scenario
from core.sustainability import calculate_sustainability_score
from core.advisory import generate_sms_advisory


def render_simulator():
    current_farm = st.session_state.get("current_farm", get_farm_by_id("plot_001"))
    farm_id = current_farm.get("farm_id", "plot_001")
    farmer_name = current_farm.get("farmer_name", "Farmer")
    area_acres = current_farm.get("area_acres", 2.0)

    st.markdown('<div class="fasal-card-title">🧪 Digital Twin Simulator</div>', unsafe_allow_html=True)
    st.caption(f"Simulating Parcel **{farm_id}** ({farmer_name}, {area_acres} acres) — Adjust levers below to test what-if scenarios.")

    # Accordion / Expander for Controllable Levers to keep mobile view compact
    with st.expander("🎛️ Simulation Levers & Inputs", expanded=True):
        # 1. Crop Selection
        crops_list = list(CROP_AGRONOMY.keys())
        default_crop = current_farm.get("current_crop", "Wheat")
        if default_crop not in crops_list:
            default_crop = "Wheat"

        sim_crop = st.selectbox(
            "Target Crop Choice",
            options=crops_list,
            index=crops_list.index(default_crop),
            key="sim_crop_select"
        )
        crop_data = CROP_AGRONOMY[sim_crop]

        # 2. Irrigation Method & Depth
        methods_list = list(IRRIGATION_METHODS.keys())
        sim_method = st.selectbox(
            "Irrigation Technique",
            options=methods_list,
            index=2 if sim_crop in ["Rice", "Sugarcane"] else 0, # Default to Drip
            key="sim_method_select",
            help="Drip (90% eff), Sprinkler (75% eff), Flood (50% eff), Rainfed (0 groundwater)"
        )

        # Baseline crop irrigation recommendations
        min_rec, max_rec = crop_data["irrig_mm"]
        def_irrig = (min_rec + max_rec) / 2.0
        if sim_method == "Drip":
            def_irrig *= 0.60
        elif sim_method == "Sprinkler":
            def_irrig *= 0.75

        sim_irrig_mm = st.slider(
            "Applied Irrigation Depth (mm)",
            min_value=0.0 if sim_method == "Rainfed" else 50.0,
            max_value=2000.0,
            value=0.0 if sim_method == "Rainfed" else float(round(def_irrig, 0)),
            step=10.0,
            disabled=(sim_method == "Rainfed")
        )

        # 3. Fertilizer Inputs
        st.markdown("**Fertilizer Application (kg/ha)**")
        col_n, col_p, col_k = st.columns(3)
        with col_n:
            sim_n = st.number_input(
                "Nitrogen (N)",
                min_value=0.0, max_value=300.0,
                value=float(crop_data["N"][0]),
                step=5.0
            )
        with col_p:
            sim_p = st.number_input(
                "Phosphorus (P)",
                min_value=0.0, max_value=120.0,
                value=float(crop_data["P"][0]),
                step=5.0
            )
        with col_k:
            sim_k = st.number_input(
                "Potassium (K)",
                min_value=0.0, max_value=250.0,
                value=float(crop_data["K"][0]),
                step=10.0
            )

        # 4. Weather Scenario & Pricing Mode
        col_w, col_pr = st.columns(2)
        with col_w:
            sim_weather = st.selectbox(
                "Weather Scenario",
                options=list(WEATHER_SCENARIOS.keys()),
                index=0
            )
        with col_pr:
            sim_pricing = st.radio(
                "Pricing Basis",
                options=["MSP (Govt)", "Market Price"],
                index=0,
                horizontal=True
            )

    use_msp = (sim_pricing == "MSP (Govt)")

    # Execute Real-Time Simulation
    sim_res = simulate_scenario(
        farm_state=current_farm,
        crop=sim_crop,
        irrigation_method=sim_method,
        irrigation_mm=sim_irrig_mm,
        applied_n=sim_n,
        applied_p=sim_p,
        applied_k=sim_k,
        weather_scenario=sim_weather,
        use_msp=use_msp
    )

    sust_res = calculate_sustainability_score(sim_res, current_farm)

    # Display 4 Key Metric Cards
    delta_profit_sign = "+" if sim_res["profit_delta_rs"] >= 0 else ""
    delta_profit_class = "delta-pos" if sim_res["profit_delta_rs"] >= 0 else "delta-neg"

    st.markdown(f"""
    <div class="metric-grid">
        <div class="metric-pill">
            <span class="metric-label">Predicted Yield</span>
            <span class="metric-val">{sim_res['yield_q_acre']} q/ac</span>
            <span class="metric-delta delta-pos">80% CI: {sim_res['yield_lower_80']}–{sim_res['yield_upper_80']}</span>
        </div>
        <div class="metric-pill">
            <span class="metric-label">Water Footprint</span>
            <span class="metric-val">{sim_res['water_liters']:,.0f} L</span>
            <span class="metric-delta {'delta-pos' if sim_res['water_saved_pct'] >= 0 else 'delta-neg'}">
                {sim_res['water_saved_pct']:.1f}% vs BAU
            </span>
        </div>
        <div class="metric-pill">
            <span class="metric-label">Net Profit</span>
            <span class="metric-val">₹{sim_res['net_profit']:,.0f}</span>
            <span class="metric-delta {delta_profit_class}">
                {delta_profit_sign}₹{sim_res['profit_delta_rs']:,.0f} vs BAU
            </span>
        </div>
        <div class="metric-pill">
            <span class="metric-label">Sustainability</span>
            <span class="metric-val">{sust_res['composite_score']}/100</span>
            <span class="metric-delta" style="color: {sust_res['badge_color']};">
                {sust_res['rating'].split()[0]}
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Detailed Farm Economics & Energy Card
    st.markdown(f"""
    <div class="fasal-card">
        <div class="fasal-card-title">⚡ Resource & Pumping Intelligence</div>
        <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; font-size: 13px;">
            <div>
                <span style="color: #64748b;">Groundwater Lift:</span><br>
                <strong>{sim_res['water_m3']} m³</strong> ({sim_res['water_per_acre_liters']:,.0f} L/ac)
            </div>
            <div>
                <span style="color: #64748b;">Pump Energy:</span><br>
                <strong>{sim_res['energy_kwh']} kWh</strong> (₹{sim_res['energy_cost']:,.0f})
            </div>
            <div>
                <span style="color: #64748b;">Water Productivity:</span><br>
                <strong>{sim_res['water_prod_kg_m3']} kg/m³</strong>
            </div>
            <div>
                <span style="color: #64748b;">Profit per Drop:</span><br>
                <strong>₹{sim_res['profit_per_drop_rs_m3']} / m³</strong>
            </div>
            <div>
                <span style="color: #64748b;">Gross Revenue:</span><br>
                <strong>₹{sim_res['gross_revenue']:,.0f}</strong> (@ ₹{sim_res['price_per_quintal']}/q)
            </div>
            <div>
                <span style="color: #64748b;">Total Operational Cost:</span><br>
                <strong>₹{sim_res['total_cost']:,.0f}</strong> (Inputs + Power + Prep)
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Top-3 Explainable Feature Attribution Drivers (SHAP-Style)
    st.markdown('<div class="fasal-card-title">🔍 Plain-Language Model Drivers (SHAP Attribution)</div>', unsafe_allow_html=True)
    for d in sim_res["drivers"]:
        color = "#16a34a" if d["type"] == "positive" else ("#dc2626" if d["type"] == "negative" else "#64748b")
        icon = "✅" if d["type"] == "positive" else ("⚠️" if d["type"] == "negative" else "ℹ️")
        st.markdown(f"""
        <div style="background: #ffffff; border-left: 3px solid {color}; border-radius: 6px; padding: 8px 12px; margin-bottom: 6px; box-shadow: 0 1px 2px rgba(0,0,0,0.04);">
            <div style="display: flex; justify-content: space-between; font-size: 13px; font-weight: 700;">
                <span>{icon} {d['driver']}</span>
                <span style="color: {color};">{d['impact']}</span>
            </div>
            <div style="font-size: 11px; color: #64748b; margin-top: 2px;">
                {d['detail']}
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Low-Bandwidth SMS Advisory Delivery
    st.markdown('<div class="fasal-card-title" style="margin-top: 14px;">📲 Farmer SMS Advisory Generator (<= 160 Chars)</div>', unsafe_allow_html=True)
    lang_choice = st.radio("Advisory Language", options=["English", "Hindi (हिंदी)"], horizontal=True, key="sms_lang_choice")
    target_lang = "Hindi" if "Hindi" in lang_choice else "English"
    sms_obj = generate_sms_advisory(current_farm, sim_res, language=target_lang)

    st.markdown(f"""
    <div style="background: #f1f5f9; border: 1.5px dashed #94a3b8; border-radius: 12px; padding: 12px 14px; margin-bottom: 12px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
            <span style="font-size: 11px; font-weight: 700; color: #475569; text-transform: uppercase;">
                SMS Preview (Basic Feature Phone)
            </span>
            <span style="background: {'#dcfce7' if sms_obj['is_valid_sms'] else '#fee2e2'}; color: {'#166534' if sms_obj['is_valid_sms'] else '#991b1b'}; padding: 2px 8px; border-radius: 10px; font-size: 10px; font-weight: 700;">
                {sms_obj['char_count']}/160 chars
            </span>
        </div>
        <div style="font-family: monospace; font-size: 13px; color: #0f172a; line-height: 1.4; word-break: break-word;">
            {sms_obj['message']}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Scenario Save Action
    st.markdown("##### 💾 Save Plan to Scenario Comparison")
    scenario_name = st.text_input(
        "Scenario Name",
        value=f"Plan: {sim_crop} ({sim_method})"
    )
    col_save, col_view = st.columns(2)
    with col_save:
        if st.button("➕ Save to Compare List", key="btn_save_scenario"):
            scenarios = st.session_state.get("saved_scenarios", {})
            scenarios[scenario_name] = {
                "name": scenario_name,
                "simulation": sim_res,
                "sustainability": sust_res,
                "tag": "User Plan",
                "notes": f"Generated for {farm_id} using {sim_method}."
            }
            st.session_state["saved_scenarios"] = scenarios
            st.success(f"Saved '{scenario_name}'! Head to 'Compare' to inspect.")
    with col_view:
        if st.button("📑 Go to Scenario Comparison", key="btn_to_compare"):
            st.session_state["current_tab"] = "Compare"
            st.rerun()

"""
Mobile-First Profit-Ranked Crop Recommender Screen for FASAL.
Implements Objective O3 and Research Gap G4.
Ranks all regional crops by Net Profit under an aquifer Water Cap constraint,
highlighting the baseline MSP monoculture alongside the top sustainable alternatives.
"""

import streamlit as st
from core.db import get_farm_by_id
from core.recommender import recommend_crops


def render_recommendations():
    current_farm = st.session_state.get("current_farm", get_farm_by_id("plot_001"))
    farm_id = current_farm.get("farm_id", "plot_001")
    farmer_name = current_farm.get("farmer_name", "Farmer")
    area_acres = current_farm.get("area_acres", 2.0)

    st.markdown('<div class="fasal-card-title">💡 Profit-Ranked Crop Recommender</div>', unsafe_allow_html=True)
    st.caption(f"Recommending high-margin, water-smart crop switches for parcel **{farm_id}** ({farmer_name}, {area_acres} acres).")

    # Controllable Constraints
    with st.expander("⚙️ Water Cap & Policy Constraints", expanded=True):
        water_cap_mm = st.slider(
            "Seasonal Water Cap Budget (mm)",
            min_value=150.0,
            max_value=1200.0,
            value=500.0,
            step=25.0,
            help="Maximum groundwater volume permitted based on block aquifer stress category."
        )

        col_ir, col_sc = st.columns(2)
        with col_ir:
            pref_method = st.selectbox(
                "Delivery Infrastructure",
                options=["Drip", "Sprinkler", "Flood / Furrow"],
                index=0
            )
        with col_sc:
            pref_weather = st.selectbox(
                "Seasonal Weather Outlook",
                options=["Normal", "Dry / Drought", "Wet / Monsoon Surge", "Heatwave"],
                index=0
            )

    # Compute Recommendations
    rec_res = recommend_crops(
        farm_state=current_farm,
        water_cap_mm=water_cap_mm,
        preferred_irrigation=pref_method,
        weather_scenario=pref_weather
    )

    cur_crop = rec_res["current_crop"]
    top_1 = rec_res["top_recommendation_1"]
    top_2 = rec_res["top_recommendation_2"]

    # Current Practice Monoculture Card
    st.markdown("##### 🌾 Current Practice (Baseline Monoculture)")
    st.markdown(f"""
    <div class="fasal-card" style="border-left: 4px solid #94a3b8; background: #f8fafc;">
        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
            <div>
                <h4 style="margin: 0; font-size: 15px; font-weight: 700; color: #334155;">
                    {cur_crop['display_name']}
                </h4>
                <div style="font-size: 11px; color: #64748b; margin-top: 2px;">
                    Water: <strong>{cur_crop['applied_mm']} mm</strong> | {cur_crop['method']}
                </div>
            </div>
            <div style="text-align: right;">
                <div style="font-size: 15px; font-weight: 800; color: #0f172a;">₹{cur_crop['net_profit_acre']:,.0f} / ac</div>
                <div style="font-size: 10px; color: #64748b;">Net Margin</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Top-2 Recommended Alternatives
    st.markdown("##### ⭐ AI Recommended Alternatives (Ranked by Profit)")

    if top_1:
        delta_sign = "+" if top_1["profit_delta_rs"] >= 0 else ""
        st.markdown(f"""
        <div class="fasal-card" style="border: 2px solid #2d6a4f; background: #ffffff;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                <div>
                    <span style="background: #d8f3dc; color: #1b4332; font-size: 10px; font-weight: 800; padding: 3px 8px; border-radius: 10px; text-transform: uppercase;">
                        Top Pick #1 (Best ROI)
                    </span>
                    <h4 style="margin: 4px 0 2px 0; font-size: 17px; font-weight: 800; color: #1b4332;">
                        {top_1['display_name']}
                    </h4>
                    <div style="font-size: 11px; color: #64748b;">
                        💧 {top_1['applied_mm']} mm ({top_1['method']}) | Cap: <strong>Within Budget</strong>
                    </div>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 17px; font-weight: 800; color: #16a34a;">₹{top_1['net_profit_acre']:,.0f} / ac</div>
                    <div style="font-size: 11px; font-weight: 700; color: #16a34a;">
                        {delta_sign}₹{top_1['profit_delta_rs']:,.0f} extra profit
                    </div>
                </div>
            </div>
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; background: #f8faf7; padding: 8px; border-radius: 8px; margin-top: 10px; font-size: 11px; text-align: center;">
                <div>
                    <div style="color: #64748b; font-size: 9px; text-transform: uppercase;">Water Saved</div>
                    <div style="font-weight: 700; color: #16a34a;">{top_1['water_saved_pct']:.0f}%</div>
                </div>
                <div>
                    <div style="color: #64748b; font-size: 9px; text-transform: uppercase;">Profit / Drop</div>
                    <div style="font-weight: 700; color: #0284c7;">₹{top_1['profit_per_drop_rs_m3']} / m³</div>
                </div>
                <div>
                    <div style="color: #64748b; font-size: 9px; text-transform: uppercase;">Sustainability</div>
                    <div style="font-weight: 700; color: #2d6a4f;">{top_1['sustainability_score']}/100</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    if top_2:
        delta_sign_2 = "+" if top_2["profit_delta_rs"] >= 0 else ""
        st.markdown(f"""
        <div class="fasal-card" style="border: 1px solid #cbd5e1; background: #ffffff;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                <div>
                    <span style="background: #e0f2fe; color: #0369a1; font-size: 10px; font-weight: 800; padding: 3px 8px; border-radius: 10px; text-transform: uppercase;">
                        Alternative #2 (Pulse / Diversification)
                    </span>
                    <h4 style="margin: 4px 0 2px 0; font-size: 16px; font-weight: 800; color: #0f172a;">
                        {top_2['display_name']}
                    </h4>
                    <div style="font-size: 11px; color: #64748b;">
                        💧 {top_2['applied_mm']} mm ({top_2['method']})
                    </div>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 16px; font-weight: 800; color: #1e293b;">₹{top_2['net_profit_acre']:,.0f} / ac</div>
                    <div style="font-size: 11px; font-weight: 700; color: #16a34a;">
                        {delta_sign_2}₹{top_2['profit_delta_rs']:,.0f} extra
                    </div>
                </div>
            </div>
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; background: #f8faf7; padding: 8px; border-radius: 8px; margin-top: 10px; font-size: 11px; text-align: center;">
                <div>
                    <div style="color: #64748b; font-size: 9px; text-transform: uppercase;">Water Saved</div>
                    <div style="font-weight: 700; color: #16a34a;">{top_2['water_saved_pct']:.0f}%</div>
                </div>
                <div>
                    <div style="color: #64748b; font-size: 9px; text-transform: uppercase;">Profit / Drop</div>
                    <div style="font-weight: 700; color: #0284c7;">₹{top_2['profit_per_drop_rs_m3']} / m³</div>
                </div>
                <div>
                    <div style="color: #64748b; font-size: 9px; text-transform: uppercase;">Sustainability</div>
                    <div style="font-weight: 700; color: #2d6a4f;">{top_2['sustainability_score']}/100</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Full Ranked Evaluation Table (Stacked for mobile)
    st.markdown("##### 📊 Full Crop Portfolio Ranking")
    for r in rec_res["ranked_crops"]:
        cap_pill = (
            '<span style="background: #dcfce7; color: #166534; font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 8px;">Within Cap</span>'
            if r["is_within_cap"]
            else f'<span style="background: #fee2e2; color: #991b1b; font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 8px;">Exceeds Cap (+{r["cap_delta_mm"]}mm)</span>'
        )

        st.markdown(f"""
        <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px 12px; margin-bottom: 6px; display: flex; justify-content: space-between; align-items: center;">
            <div>
                <div style="font-size: 13px; font-weight: 700; color: #1e293b;">{r['crop']}</div>
                <div style="font-size: 11px; color: #64748b; margin-top: 2px;">
                    {r['applied_mm']} mm | {cap_pill}
                </div>
            </div>
            <div style="text-align: right;">
                <div style="font-size: 14px; font-weight: 800; color: #1e293b;">₹{r['net_profit_acre']:,.0f}/ac</div>
                <div style="font-size: 10px; color: #64748b;">Score: {r['sustainability_score']}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

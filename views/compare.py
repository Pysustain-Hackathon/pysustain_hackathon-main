"""
Mobile-First Scenario Comparison Screen for FASAL.
Replaces unwieldy wide tables with stacked responsive cards on mobile screens.
Provides interactive Plotly comparison charts, scenario duplication, deletion,
reset, and CSV data export.
"""

import streamlit as st
import plotly.graph_objects as go
from core.db import get_farm_by_id
from core.persistence import get_default_scenarios, export_scenarios_csv, scenarios_to_dataframe


def render_compare():
    current_farm = st.session_state.get("current_farm", get_farm_by_id("plot_001"))

    # Ensure saved_scenarios is initialized
    if "saved_scenarios" not in st.session_state or not st.session_state["saved_scenarios"]:
        st.session_state["saved_scenarios"] = get_default_scenarios(current_farm)

    scenarios = st.session_state["saved_scenarios"]

    st.markdown('<div class="fasal-card-title">📑 Multi-Scenario Comparison</div>', unsafe_allow_html=True)
    st.caption("Compare alternative crop and irrigation strategies side-by-side. Stacked card layout optimized for Android viewports.")

    # Management controls row
    col_ctrl1, col_ctrl2 = st.columns([1, 1])
    with col_ctrl1:
        csv_data = export_scenarios_csv(scenarios)
        st.download_button(
            label="📥 Export Scenarios (CSV)",
            data=csv_data,
            file_name=f"FASAL_scenarios_{current_farm.get('farm_id')}.csv",
            mime="text/csv",
            key="btn_download_csv"
        )
    with col_ctrl2:
        if st.button("🔄 Reset Scenarios", key="btn_reset_scenarios"):
            st.session_state["saved_scenarios"] = get_default_scenarios(current_farm)
            st.success("Reset scenarios to default benchmarks!")
            st.rerun()

    # Stacked Responsive Scenario Cards (Zero horizontal scroll on phones)
    st.markdown("##### 🗂️ Active Strategy Cards")
    for name, data in list(scenarios.items()):
        sim = data["simulation"]
        sust = data["sustainability"]
        badge_tag = data.get("tag", "Plan")

        # Color-coded badge
        badge_style = "scenario-badge-current" if "Current" in badge_tag or "BAU" in name else ("scenario-badge-saver" if "Saver" in badge_tag or "Drip" in name else "scenario-badge-regen")
        profit_delta_sign = "+" if sim["profit_delta_rs"] >= 0 else ""

        st.markdown(f"""
        <div class="scenario-card">
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                <div>
                    <span class="scenario-badge {badge_style}">{badge_tag}</span>
                    <h4 style="margin: 2px 0 6px 0; font-size: 16px; font-weight: 700; color: #1b4332;">{name}</h4>
                    <div style="font-size: 12px; color: #64748b;">
                        🌾 {sim['crop']} | 💧 {sim['irrigation_method']} ({sim['irrigation_mm']} mm)
                    </div>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 16px; font-weight: 800; color: #1e293b;">₹{sim['net_profit']:,.0f}</div>
                    <div style="font-size: 11px; font-weight: 700; color: {'#16a34a' if sim['profit_delta_rs'] >= 0 else '#dc2626'};">
                        {profit_delta_sign}₹{sim['profit_delta_rs']:,.0f} vs BAU
                    </div>
                </div>
            </div>
            
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; background: #f8faf7; padding: 10px; border-radius: 8px; margin-top: 10px; font-size: 12px; text-align: center;">
                <div>
                    <div style="color: #64748b; font-size: 10px; text-transform: uppercase;">Water Used</div>
                    <div style="font-weight: 700; color: #0284c7;">{sim['water_liters']:,.0f} L</div>
                    <div style="font-size: 10px; color: {'#16a34a' if sim['water_saved_pct'] >= 0 else '#dc2626'}; font-weight: 600;">
                        {sim['water_saved_pct']:.0f}% saved
                    </div>
                </div>
                <div>
                    <div style="color: #64748b; font-size: 10px; text-transform: uppercase;">Yield (q/ac)</div>
                    <div style="font-weight: 700; color: #1e293b;">{sim['yield_q_acre']}</div>
                    <div style="font-size: 10px; color: #64748b;">({sim['yield_lower_80']}–{sim['yield_upper_80']})</div>
                </div>
                <div>
                    <div style="color: #64748b; font-size: 10px; text-transform: uppercase;">Sustainability</div>
                    <div style="font-weight: 700; color: {sust['badge_color']};">{sust['composite_score']}/100</div>
                    <div style="font-size: 10px; color: #64748b;">{sust['rating'].split()[0]}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Card Action Buttons (Compact horizontal row)
        c_dup, c_del = st.columns([1, 1])
        with c_dup:
            if st.button(f"📑 Duplicate", key=f"dup_{name}"):
                new_key = f"{name} (Copy)"
                scenarios[new_key] = dict(data)
                scenarios[new_key]["name"] = new_key
                st.session_state["saved_scenarios"] = scenarios
                st.rerun()
        with c_del:
            if len(scenarios) > 1 and st.button(f"🗑️ Delete", key=f"del_{name}"):
                del scenarios[name]
                st.session_state["saved_scenarios"] = scenarios
                st.rerun()

    # Interactive Comparison Chart
    st.markdown('<div class="fasal-card-title" style="margin-top: 18px;">📊 Visual Trade-off: Profit vs Water Footprint</div>', unsafe_allow_html=True)

    names_list = list(scenarios.keys())
    profits = [scenarios[k]["simulation"]["net_profit"] for k in names_list]
    waters_m3 = [scenarios[k]["simulation"]["water_m3"] for k in names_list]

    # Clean short labels for mobile
    short_labels = [k.replace("Plan ", "P").split(":")[0] + ("..." if len(k) > 18 else "") for k in names_list]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=short_labels,
        y=profits,
        name="Net Profit (₹)",
        marker_color="#2d6a4f",
        yaxis="y"
    ))
    fig.add_trace(go.Bar(
        x=short_labels,
        y=waters_m3,
        name="Water Used (m³)",
        marker_color="#0284c7",
        yaxis="y2"
    ))

    fig.update_layout(
        margin=dict(l=10, r=10, t=20, b=30),
        height=280,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        yaxis=dict(title="Profit (₹)", showgrid=True),
        yaxis2=dict(title="Water (m³)", overlaying="y", side="right", showgrid=False),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        barmode="group",
        font=dict(size=11)
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False, "responsive": True})

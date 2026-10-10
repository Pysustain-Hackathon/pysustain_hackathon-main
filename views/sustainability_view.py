"""
Mobile-First Sustainability Scorecard Screen for FASAL.
Implements Objective O6 and UN Sustainable Development Goals (SDG 2, 6, 12, 13, 15).
Visualizes the transparent 5-pillar sustainability breakdown and actionable agronomic steps.
"""

import streamlit as st
import plotly.graph_objects as go
from core.db import get_farm_by_id
from core.simulation import simulate_scenario
from core.sustainability import calculate_sustainability_score


def render_sustainability():
    current_farm = st.session_state.get("current_farm", get_farm_by_id("plot_001"))
    farm_id = current_farm.get("farm_id", "plot_001")

    # Load active simulation or run default for current farm
    scenarios = st.session_state.get("saved_scenarios", {})
    if scenarios:
        selected_plan = st.selectbox(
            "Select Evaluated Plan for Scorecard:",
            options=list(scenarios.keys()),
            index=0,
            key="sust_plan_selector"
        )
        sim_res = scenarios[selected_plan]["simulation"]
    else:
        sim_res = simulate_scenario(current_farm)

    sust = calculate_sustainability_score(sim_res, current_farm)

    st.markdown('<div class="fasal-card-title">🌱 Sustainability Scorecard</div>', unsafe_allow_html=True)
    st.caption("Comprehensive 5-pillar ESG scorecard measuring aquifer stewardship, nutrient balance, and climate resilience.")

    # Main Composite Score Pill
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #1b4332 0%, #2d6a4f 100%); border-radius: 16px; padding: 18px; color: #ffffff; margin-bottom: 16px; text-align: center; box-shadow: 0 4px 12px rgba(27,67,50,0.12);">
        <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: #d8f3dc; font-weight: 700;">
            FASAL Composite Sustainability Index
        </div>
        <div style="font-size: 42px; font-weight: 800; margin: 4px 0; line-height: 1;">
            {sust['composite_score']}<span style="font-size: 20px; font-weight: 500; opacity: 0.8;">/100</span>
        </div>
        <div style="display: inline-block; background: rgba(255,255,255,0.2); padding: 4px 14px; border-radius: 20px; font-size: 13px; font-weight: 700;">
            {sust['rating']}
        </div>
        <div style="font-size: 12px; color: #d8f3dc; margin-top: 8px; line-height: 1.3;">
            {sust['summary']}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 5-Pillar Score Cards (Stacked on mobile)
    st.markdown("##### 🏛️ Transparent 5-Pillar Breakdown")
    pillars = sust["pillars"]
    pillar_icons = {
        "Water Efficiency": "💧",
        "Nutrient Management": "🧪",
        "Energy & Carbon": "⚡",
        "Soil Health Trend": "🍂",
        "Climate Resilience": "🌤️"
    }

    for name, p_data in pillars.items():
        score = p_data["score"]
        max_s = p_data["max"]
        pct = p_data["pct"]
        icon = pillar_icons.get(name, "📌")

        st.markdown(f"""
        <div class="fasal-card" style="padding: 10px 14px; margin-bottom: 8px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                <span style="font-size: 13px; font-weight: 700; color: #1e293b;">
                    {icon} {name}
                </span>
                <span style="font-size: 13px; font-weight: 800; color: #2d6a4f;">
                    {score} / {max_s} pts
                </span>
            </div>
            <div style="background: #e2e8f0; border-radius: 6px; height: 7px; overflow: hidden;">
                <div style="background: #2d6a4f; width: {pct}%; height: 100%;"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Radar Chart of Pillars (Responsive for mobile viewports)
    st.markdown('<div class="fasal-card-title" style="margin-top: 14px;">🕸️ Multi-Dimensional Sustainability Radar</div>', unsafe_allow_html=True)
    categories = list(pillars.keys())
    scores_pct = [pillars[k]["pct"] for k in categories]

    # Close loop for radar
    categories_closed = categories + [categories[0]]
    scores_closed = scores_pct + [scores_pct[0]]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=scores_closed,
        theta=categories_closed,
        fill="toself",
        fillcolor="rgba(45, 106, 79, 0.25)",
        line=dict(color="#2d6a4f", width=2),
        name="Performance %"
    ))
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100], tickfont=dict(size=9)),
            angularaxis=dict(tickfont=dict(size=10))
        ),
        margin=dict(l=20, r=20, t=20, b=20),
        height=260,
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False, "responsive": True})

    # Actionable Agronomic Recommendations
    st.markdown("##### 📋 Recommended Actions to Maximize Score")
    for rec in sust["recommendations"]:
        st.markdown(f"""
        <div style="background: #ffffff; border-left: 3px solid #2d6a4f; border-radius: 6px; padding: 8px 12px; margin-bottom: 6px; font-size: 12px; color: #1e293b; box-shadow: 0 1px 2px rgba(0,0,0,0.04);">
            💡 {rec}
        </div>
        """, unsafe_allow_html=True)

    # UN SDG Alignment Pills
    st.markdown("##### 🎯 Aligned UN Sustainable Development Goals")
    st.markdown("""
    <div style="display: flex; flex-wrap: wrap; gap: 6px; margin-top: 6px;">
        <span style="background: #d8f3dc; color: #1b4332; font-size: 11px; font-weight: 700; padding: 4px 10px; border-radius: 12px;">
            SDG 2.3: Smallholder Incomes
        </span>
        <span style="background: #e0f2fe; color: #0369a1; font-size: 11px; font-weight: 700; padding: 4px 10px; border-radius: 12px;">
            SDG 6.4: Water-Use Efficiency
        </span>
        <span style="background: #fef3c7; color: #92400e; font-size: 11px; font-weight: 700; padding: 4px 10px; border-radius: 12px;">
            SDG 12.2: Sustainable Resources
        </span>
        <span style="background: #f1f5f9; color: #475569; font-size: 11px; font-weight: 700; padding: 4px 10px; border-radius: 12px;">
            SDG 13: Climate Action
        </span>
    </div>
    """, unsafe_allow_html=True)

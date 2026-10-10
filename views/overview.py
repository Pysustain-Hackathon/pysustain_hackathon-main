"""
Mobile-First Overview Screen for FASAL.
Displays regional twin KPIs, active farm selector, digital twin status,
and geographic distribution of smallholder parcels.
"""

import streamlit as st
import plotly.graph_objects as go
from core.db import get_farm_unified_df, get_farm_by_id
from core.config import CROP_AGRONOMY


def render_overview():
    # Load unified dataset
    farms_df, market_df, db_source = get_farm_unified_df()
    current_farm = st.session_state.get("current_farm", get_farm_by_id("plot_001"))

    # Regional High-Level KPIs
    st.markdown("""
    <div class="metric-grid">
        <div class="metric-pill">
            <span class="metric-label">Digitized Farms</span>
            <span class="metric-val">250 Parcels</span>
            <span class="metric-delta delta-pos">8 Agro-Districts</span>
        </div>
        <div class="metric-pill">
            <span class="metric-label">Avg Water Saving</span>
            <span class="metric-val">38.4%</span>
            <span class="metric-delta delta-pos">Drip & Sprinkler</span>
        </div>
        <div class="metric-pill">
            <span class="metric-label">Avg Margin Gain</span>
            <span class="metric-val">+₹14,200</span>
            <span class="metric-delta delta-pos">Per Acre / Season</span>
        </div>
        <div class="metric-pill">
            <span class="metric-label">Cloud Backend</span>
            <span class="metric-val">Connected</span>
            <span class="metric-delta delta-pos">PostgreSQL Ready</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Active Farm Parcel Card
    st.markdown('<div class="fasal-card-title">📍 Active Farm Digital Twin</div>', unsafe_allow_html=True)

    # Farm Selector Dropdown
    farm_options = [
        f"{r['farm_id']} — {r['farmer_name']} ({r['current_crop']}, {r['district']})"
        for _, r in farms_df.iterrows()
    ]
    current_idx = 0
    for idx, opt in enumerate(farm_options):
        if opt.startswith(current_farm.get("farm_id", "plot_001")):
            current_idx = idx
            break

    selected_opt = st.selectbox(
        "Choose Farm Parcel from 250 Twin Records:",
        options=farm_options,
        index=current_idx,
        key="overview_farm_selector"
    )

    selected_id = selected_opt.split(" — ")[0].strip()
    if selected_id != current_farm.get("farm_id"):
        st.session_state["current_farm"] = get_farm_by_id(selected_id)
        current_farm = st.session_state["current_farm"]
        st.rerun()

    # Active Farm Details Card
    crop_info = CROP_AGRONOMY.get(current_farm.get("current_crop", "Wheat"), CROP_AGRONOMY["Wheat"])
    st.markdown(f"""
    <div class="fasal-card">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
            <div>
                <h4 style="margin: 0; font-size: 17px; font-weight: 700; color: #1b4332;">
                    {current_farm.get('farmer_name')}
                </h4>
                <div style="font-size: 12px; color: #64748b; margin-top: 2px;">
                    Farm ID: <strong>{current_farm.get('farm_id')}</strong> | {current_farm.get('district')}, {current_farm.get('state')}
                </div>
            </div>
            <span style="background: #d8f3dc; color: #1b4332; font-size: 11px; font-weight: 700; padding: 4px 8px; border-radius: 12px;">
                {current_farm.get('area_acres')} Acres
            </span>
        </div>
        <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; font-size: 12px; margin-top: 10px; border-top: 1px solid #e2e8f0; padding-top: 8px;">
            <div>🌾 <strong>Current Crop:</strong> {current_farm.get('current_crop')}</div>
            <div>🧪 <strong>Soil pH:</strong> {current_farm.get('ph')}</div>
            <div>🍂 <strong>Organic Carbon:</strong> {current_farm.get('organic_carbon')}%</div>
            <div>🧱 <strong>Texture:</strong> {current_farm.get('texture')}</div>
            <div>🌱 <strong>Available N:</strong> {current_farm.get('nitrogen_kg_ha')} kg/ha</div>
            <div>🗓️ <strong>Sowing Date:</strong> {current_farm.get('sowing_date')}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Quick Action Buttons (Stack on mobile, row on desktop)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🚀 Launch Digital Simulator", key="btn_quick_sim"):
            st.session_state["current_tab"] = "Simulator"
            st.rerun()
    with col2:
        if st.button("💡 View Crop Recommendations", key="btn_quick_rec"):
            st.session_state["current_tab"] = "Recommendations"
            st.rerun()

    # Regional Agricultural Distribution Chart
    st.markdown('<div class="fasal-card-title" style="margin-top: 16px;">📊 Regional Crop Distribution (250 Smallholders)</div>', unsafe_allow_html=True)
    crop_counts = farms_df["current_crop"].value_counts().reset_index()
    crop_counts.columns = ["Crop", "Count"]

    fig = go.Figure(data=[
        go.Bar(
            x=crop_counts["Count"],
            y=crop_counts["Crop"],
            orientation="h",
            marker=dict(
                color=["#2d6a4f" if c in ["Rice", "Wheat"] else "#52b788" for c in crop_counts["Crop"]],
                line=dict(color="#1b4332", width=1)
            )
        )
    ])
    fig.update_layout(
        margin=dict(l=10, r=10, t=10, b=20),
        height=260,
        xaxis_title="Number of Farms",
        yaxis=dict(autorange="reversed"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(size=11)
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False, "responsive": True})

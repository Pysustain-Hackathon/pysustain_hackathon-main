"""
Mobile-First Farm Setup and Soil Configuration Screen for FASAL.
Allows configuring farm dimensions, soil health indicators, and baseline crop.
"""

import streamlit as st
from core.db import get_farm_unified_df, get_farm_by_id
from core.config import CROP_AGRONOMY


def render_farm_setup():
    farms_df, _, _ = get_farm_unified_df()
    current_farm = st.session_state.get("current_farm", get_farm_by_id("plot_001"))

    st.markdown('<div class="fasal-card-title">⚙️ Farm Parcel & Soil Configuration</div>', unsafe_allow_html=True)
    st.caption("Configure digital twin soil chemistry and parcel parameters for precision what-if simulation.")

    # Select Farm Parcel from DB
    farm_options = [
        f"{r['farm_id']} — {r['farmer_name']} ({r['district']})"
        for _, r in farms_df.iterrows()
    ]
    cur_id = current_farm.get("farm_id", "plot_001")
    cur_idx = 0
    for idx, opt in enumerate(farm_options):
        if opt.startswith(cur_id):
            cur_idx = idx
            break

    chosen_opt = st.selectbox(
        "Load Farm Profile:",
        options=farm_options,
        index=cur_idx,
        key="farm_setup_dropdown"
    )

    chosen_id = chosen_opt.split(" — ")[0].strip()
    if chosen_id != cur_id:
        st.session_state["current_farm"] = get_farm_by_id(chosen_id)
        st.rerun()

    # Form to modify Farm Parameters
    with st.form("farm_edit_form"):
        st.markdown("##### 📍 Parcel Demographics")
        f_name = st.text_input("Farmer Name", value=current_farm.get("farmer_name", "Farmer"))
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            f_district = st.text_input("District", value=current_farm.get("district", "Ludhiana"))
        with col_d2:
            f_state = st.text_input("State", value=current_farm.get("state", "Punjab"))

        f_area = st.number_input(
            "Farm Landholding (Acres)",
            min_value=0.25,
            max_value=25.0,
            value=float(current_farm.get("area_acres", 2.0)),
            step=0.25,
            help="Smallholder farms are typically < 5 acres (2 ha)"
        )

        f_crop = st.selectbox(
            "Current Baseline Monoculture Crop",
            options=list(CROP_AGRONOMY.keys()),
            index=list(CROP_AGRONOMY.keys()).index(current_farm.get("current_crop", "Wheat")) if current_farm.get("current_crop") in CROP_AGRONOMY else 0
        )

        st.markdown("##### 🧪 Soil Chemistry & Health")
        f_ph = st.slider(
            "Soil pH Level",
            min_value=4.5,
            max_value=9.0,
            value=float(current_farm.get("ph", 7.0)),
            step=0.1,
            help="Ideal range is 6.0 to 7.5 for most cereals and pulses."
        )

        f_oc = st.slider(
            "Soil Organic Carbon (%)",
            min_value=0.20,
            max_value=1.50,
            value=float(current_farm.get("organic_carbon", 0.55)),
            step=0.05,
            help="Indicator of soil biology and microbial moisture retention."
        )

        f_texture = st.selectbox(
            "Soil Texture Class",
            options=["Sandy Loam", "Clay Loam", "Loam", "Sandy Clay Loam", "Black Cotton Soil", "Heavy Clay", "Sandy"],
            index=["Sandy Loam", "Clay Loam", "Loam", "Sandy Clay Loam", "Black Cotton Soil", "Heavy Clay", "Sandy"].index(current_farm.get("texture", "Sandy Loam")) if current_farm.get("texture") in ["Sandy Loam", "Clay Loam", "Loam", "Sandy Clay Loam", "Black Cotton Soil", "Heavy Clay", "Sandy"] else 0
        )

        col_n, col_p, col_k = st.columns(3)
        with col_n:
            f_n = st.number_input("Available N (kg/ha)", min_value=10.0, max_value=300.0, value=float(current_farm.get("nitrogen_kg_ha", 60.0)), step=5.0)
        with col_p:
            f_p = st.number_input("Available P (kg/ha)", min_value=5.0, max_value=150.0, value=float(current_farm.get("phosphorus_kg_ha", 30.0)), step=5.0)
        with col_k:
            f_k = st.number_input("Available K (kg/ha)", min_value=10.0, max_value=400.0, value=float(current_farm.get("potassium_kg_ha", 120.0)), step=10.0)

        submitted = st.form_submit_button("💾 Save Farm Twin Profile")
        if submitted:
            updated = dict(current_farm)
            updated["farmer_name"] = f_name
            updated["district"] = f_district
            updated["state"] = f_state
            updated["area_acres"] = f_area
            updated["current_crop"] = f_crop
            updated["ph"] = f_ph
            updated["organic_carbon"] = f_oc
            updated["texture"] = f_texture
            updated["nitrogen_kg_ha"] = f_n
            updated["phosphorus_kg_ha"] = f_p
            updated["potassium_kg_ha"] = f_k
            st.session_state["current_farm"] = updated
            st.success("✅ Farm Twin profile updated successfully!")
            st.rerun()

    # Diagnostic Soil Status Pill Card
    ph_status = "Optimal" if 6.0 <= f_ph <= 7.5 else ("Acidic" if f_ph < 6.0 else "Alkaline")
    oc_status = "Good" if f_oc >= 0.75 else ("Medium" if f_oc >= 0.50 else "Low")
    st.markdown(f"""
    <div class="fasal-card" style="margin-top: 14px; background: #fdfbf7; border-color: #fde68a;">
        <div style="font-size: 13px; font-weight: 700; color: #92400e; margin-bottom: 4px;">
            🔍 Agronomic Soil Diagnostic Summary
        </div>
        <div style="font-size: 12px; color: #78350f;">
            • pH {f_ph} is <strong>{ph_status}</strong>. Micronutrient availability is stable.<br>
            • Organic Carbon is <strong>{oc_status} ({f_oc}%)</strong>. Incorporating legume green manure recommended to increase moisture holding capacity.
        </div>
    </div>
    """, unsafe_allow_html=True)

"""
FASAL — Mobile-First Android Browser Adaptation & Digital Farm Twin.
PySustain-2026 Sustainable Agriculture Decision-Support Prototype.

Authors: Team FASAL (Gargi Bhojkar, Srijon Sarkar, Shansita Padhi, Diya Elizabeth Reji)
"""

import os
import streamlit as st

# Configure Streamlit page for mobile-first Android viewports & wide desktops
st.set_page_config(
    page_title="FASAL — Farm Digital Twin",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Load Mobile-First CSS Stylesheet
css_path = os.path.join(os.path.dirname(__file__), "static", "style.css")
if os.path.exists(css_path):
    with open(css_path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Imports from core and views
from core.db import get_farm_by_id, get_farm_unified_df
from core.persistence import get_default_scenarios
from views.overview import render_overview
from views.farm_setup import render_farm_setup
from views.simulator import render_simulator
from views.compare import render_compare
from views.sustainability_view import render_sustainability
from views.recommendations_view import render_recommendations
from views.model_info_view import render_model_info

# Initialize Session State
if "current_farm" not in st.session_state:
    st.session_state["current_farm"] = get_farm_by_id("plot_001")

if "saved_scenarios" not in st.session_state:
    st.session_state["saved_scenarios"] = get_default_scenarios(st.session_state["current_farm"])

if "current_tab" not in st.session_state:
    st.session_state["current_tab"] = "Overview"

current_farm = st.session_state["current_farm"]

# Render Consistent FASAL Header
st.markdown(f"""
<div class="fasal-header">
    <div class="fasal-brand">
        <div class="fasal-icon">🌾</div>
        <div>
            <h1 class="fasal-title">FASAL</h1>
            <p class="fasal-tagline">Farm Analytics for Sustainable &amp; Lucrative Farming</p>
        </div>
    </div>
    <div class="fasal-badge">
        {current_farm.get('farm_id', 'plot_001')} • {current_farm.get('area_acres', 2.0)} ac
    </div>
</div>
""", unsafe_allow_html=True)

# Navigation tabs definition
PAGES = [
    "Overview",
    "Farm Setup",
    "Simulator",
    "Compare",
    "Sustainability",
    "Recommendations",
    "Model Info"
]

# Mobile-First Segmented / Pill Navigation
# Streamlit's radio with horizontal=True provides native responsive touch-friendly navigation
selected_page = st.radio(
    "Navigation",
    options=PAGES,
    index=PAGES.index(st.session_state["current_tab"]) if st.session_state["current_tab"] in PAGES else 0,
    horizontal=True,
    label_visibility="collapsed",
    key="nav_radio"
)

# Synchronize tab selection
if selected_page != st.session_state["current_tab"]:
    st.session_state["current_tab"] = selected_page
    st.rerun()

current_tab = st.session_state["current_tab"]

# Render the Selected View
if current_tab == "Overview":
    render_overview()
elif current_tab == "Farm Setup":
    render_farm_setup()
elif current_tab == "Simulator":
    render_simulator()
elif current_tab == "Compare":
    render_compare()
elif current_tab == "Sustainability":
    render_sustainability()
elif current_tab == "Recommendations":
    render_recommendations()
elif current_tab == "Model Info":
    render_model_info()

# Sidebar: Quick Info & Live Connectivity
with st.sidebar:
    st.markdown("### 🌾 FASAL Twin Control")
    st.caption("PySustain-2026 Agricultural Decision Support")
    st.markdown(f"""
    **Active Farm:** `{current_farm.get('farm_id')}`  
    **Farmer:** {current_farm.get('farmer_name')}  
    **District:** {current_farm.get('district')}, {current_farm.get('state')}  
    **Holding:** {current_farm.get('area_acres')} Acres  
    **Soil pH:** {current_farm.get('ph')}  
    **Texture:** {current_farm.get('texture')}  
    """)
    st.divider()
    st.markdown("##### 📱 Mobile Wi-Fi Instructions")
    st.caption("To open on an Android phone over local Wi-Fi, run:")
    st.code("python -m streamlit run app.py --server.address 0.0.0.0", language="bash")
    st.divider()
    st.caption("BACSE101 — Intelligent Solutions for Sustainable Agriculture")

"""
fasal_app.py - FASAL farm simulation website (Streamlit)

Tab 1 "Simulation": pick a plot, see its crop growing, change the crop / irrigation / weather scenario,
                    and watch a week of growth driven by that plot's weather rows in the database.
Tab 2 "Input":      placeholder for now.

Run:   streamlit run fasal_app.py
Needs: DATABASE_URL in .env (same as your other scripts), and the tables farms, soil, weather, satellite_data.

IMPORTANT: this is a simplified, illustrative growth model. Crop parameters are generic textbook-style values,
the weather rows are synthetic, and nothing here is calibrated. Replace CROPS values with FAO/ICAR numbers
and add real field data before making any real-world claim.
"""
import os

os.environ["DISABLE_SQLALCHEMY_CEXT"] = "1"

import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from matplotlib.patches import Circle, Ellipse, Polygon, Rectangle
from sqlalchemy import create_engine, text

load_dotenv()
st.set_page_config(page_title="FASAL Simulator", page_icon="🌾", layout="wide")

# ---- Crop parameters: tb/to1/to2/tmax = cardinal temperatures (C), kc = water-use factor,
# ---- r = early canopy growth rate per day, hmax = mature height (cm), leaf = drawing style. Illustrative only.
CROPS = {
    "Wheat": dict(tb=3, to1=15, to2=24, tmax=35, kc=1.15, r=0.25, hmax=100, leaf="blade"),
    "Rice": dict(tb=10, to1=25, to2=33, tmax=40, kc=1.20, r=0.28, hmax=110, leaf="blade"),
    "Cotton": dict(tb=15, to1=25, to2=35, tmax=42, kc=1.15, r=0.26, hmax=120, leaf="round"),
    "Maize": dict(tb=8, to1=22, to2=32, tmax=40, kc=1.20, r=0.35, hmax=250, leaf="blade"),
    "Chickpea (Gram)": dict(tb=5, to1=18, to2=28, tmax=38, kc=1.00, r=0.22, hmax=50, leaf="round"),
    "Moong Dal": dict(tb=10, to1=25, to2=35, tmax=42, kc=1.05, r=0.30, hmax=55, leaf="round"),
    "Sugarcane": dict(tb=12, to1=27, to2=35, tmax=42, kc=1.25, r=0.30, hmax=300, leaf="blade"),
    "Pearl Millet (Bajra)": dict(tb=12, to1=28, to2=36, tmax=44, kc=1.00, r=0.32, hmax=200, leaf="blade"),
}
SOIL_WATER_CAPACITY = {"Alluvial": 140, "Black": 190, "Red": 90, "Clay": 170, "Laterite": 80}  # mm, rough
SOIL_COLOR = {"Alluvial": "#8b7355", "Black": "#3a3030", "Red": "#a0522d", "Clay": "#6b4f3a", "Laterite": "#b0613f"}
RA = 12.0  # simplified solar term for the Hargreaves evapotranspiration estimate


# ------------------------------------------------------------------ database
def get_url():
    try:
        if "DATABASE_URL" in st.secrets:
            return st.secrets["DATABASE_URL"]
    except Exception:
        pass
    return os.getenv("DATABASE_URL")


@st.cache_resource
def get_engine():
    url = get_url()
    if not url:
        st.error("DATABASE_URL not found. Add it to your .env file.")
        st.stop()
    return create_engine(url, connect_args={"sslmode": "require", "prepare_threshold": None}, pool_pre_ping=True)


@st.cache_data(ttl=600)
def load_plots():
    q = """SELECT f.farm_id, f.farmer_name, f.district, f.state, f.area_acres, f.current_crop,
                  s.soil_group, sd.ndvi_real, sd.ndmi_real, sd.image_url, sd.image_path
           FROM farms f
           LEFT JOIN soil s ON s.farm_id = f.farm_id
           LEFT JOIN satellite_data sd ON sd.farm_id = f.farm_id
           ORDER BY f.farm_id"""
    with get_engine().connect() as conn:
        return pd.read_sql(text(q), conn)


@st.cache_data(ttl=600)
def load_weather(farm_id):
    q = text("SELECT date, temp_max_c, temp_min_c, rainfall_mm, humidity_pct "
             "FROM weather WHERE farm_id = :fid ORDER BY date")
    with get_engine().connect() as conn:
        return pd.read_sql(q, conn, params={"fid": farm_id})


# ------------------------------------------------------------------ simulation model
def temp_factor(t, p):
    if t <= p["tb"] or t >= p["tmax"]:
        return 0.0
    if t < p["to1"]:
        return (t - p["tb"]) / (p["to1"] - p["tb"])
    if t <= p["to2"]:
        return 1.0
    return (p["tmax"] - t) / (p["tmax"] - p["to2"])


def simulate(crop, wx, cover0, w_frac0, taw, irrigation):
    """Day-by-day canopy growth with a simple soil-water bucket. Returns one row per day (day 0 = start)."""
    p = CROPS[crop]
    cover, water = cover0, w_frac0 * taw
    rows = [dict(day=0, cover=cover, height=p["hmax"] * cover * 0.5, soil_water=water / taw, ks=1.0, ft=1.0, etc=0.0)]
    for i, r in enumerate(wx.itertuples(), start=1):
        tmean = (r.temp_max_c + r.temp_min_c) / 2
        et0 = max(0.0, 0.0023 * RA * (tmean + 17.8) * max(r.temp_max_c - r.temp_min_c, 0) ** 0.5)
        etc = p["kc"] * (0.3 + 0.7 * cover) * et0
        water = min(taw, water + 0.8 * r.rainfall_mm + irrigation)           # 20% of rain lost as runoff
        ks = 1.0 if water >= 0.5 * taw else max(0.0, water / (0.5 * taw))     # water-stress factor
        water = max(0.0, water - ks * etc)
        ft = temp_factor(tmean, p)
        cover = min(0.98, cover + p["r"] * ft * ks * cover * (1 - cover))
        rows.append(dict(day=i, cover=cover, height=p["hmax"] * cover * 0.5, soil_water=water / taw,
                         ks=ks, ft=ft, etc=ks * etc))
    return pd.DataFrame(rows)


def cover_from_ndvi(ndvi):
    if pd.isna(ndvi):
        return 0.2
    return float(np.clip((ndvi - 0.15) / 0.70, 0.05, 0.9))


def apply_scenario(wx, scenario):
    wx = wx.copy()
    if scenario == "Hotter (+3 °C)":
        wx["temp_max_c"] += 3
        wx["temp_min_c"] += 3
    elif scenario == "Dry (no rain)":
        wx["rainfall_mm"] = 0.0
    return wx


# ------------------------------------------------------------------ drawing
def mix(c1, c2, t):
    a, b = np.array(plt.matplotlib.colors.to_rgb(c1)), np.array(plt.matplotlib.colors.to_rgb(c2))
    return tuple(a + (b - a) * t)


def draw_scene(crop, state, wx_day, soil_group):
    p = CROPS[crop]
    fig, ax = plt.subplots(figsize=(9, 3.4))
    ax.set_xlim(0, 10)
    ax.set_ylim(-22, 115)
    ax.axis("off")
    rain = wx_day is not None and wx_day.rainfall_mm >= 1
    hot = wx_day is not None and wx_day.temp_max_c >= 36
    ax.add_patch(Rectangle((0, 0), 10, 115, color="#a9b4bf" if rain else "#c4e5f7", zorder=0))
    ax.add_patch(Rectangle((0, -22), 10, 22, color=SOIL_COLOR.get(soil_group, "#7a5c3e"), zorder=1))
    ax.add_patch(Circle((9.2, 98), 6, color="#ff9800" if hot else "#ffe082", zorder=1))
    if rain:
        for cx in (2, 4.5, 7):
            ax.add_patch(Ellipse((cx, 104), 2.4, 12, color="#78838f", zorder=1))
        for x in np.linspace(0.5, 9.5, 24):
            ax.plot([x, x - 0.08], [92, 84], color="#3f6fb5", lw=1, zorder=1)

    health = state.ks * (0.5 + 0.5 * state.ft) if state.day > 0 else 1.0
    color = mix("#d4b43c", "#2e7d32", float(np.clip(health, 0, 1)))
    h, cover = min(state.height, 100), state.cover
    n_leaves = 2 + int(round(10 * cover))
    dx, dy = 0.25 + 0.30 * cover, 6 + 11 * cover
    for i in range(9):
        x = 0.8 + i * 1.05
        ax.plot([x, x], [0, h], color="#4e7d34", lw=2, zorder=2)
        for k in range(n_leaves):
            y = h * (k + 1) / (n_leaves + 1)
            side = 1 if k % 2 == 0 else -1
            if p["leaf"] == "blade":
                leaf = Polygon([(x, y), (x + side * dx, y + dy * 1.5), (x + side * dx * 0.4, y + dy * 0.1)],
                               color=color, zorder=3)
            else:
                leaf = Ellipse((x + side * dx * 0.6, y + dy * 0.4), dx * 1.1, dy, color=color, zorder=3)
            ax.add_patch(leaf)
    ax.text(0.1, 112, f"{crop}  |  Day {int(state.day)}", fontsize=11, weight="bold", va="top", zorder=5)
    ax.text(0.1, -11, f"canopy {cover * 100:.0f}%   height about {state.height:.0f} cm", fontsize=9, color="white", zorder=5)
    fig.tight_layout(pad=0.2)
    return fig


# ------------------------------------------------------------------ page
st.title("🌾 FASAL: farm simulator")
tab_sim, tab_input = st.tabs(["Simulation", "Input"])

with tab_input:
    st.info("Input tab: coming soon.")

with tab_sim:
    try:
        plots = load_plots()
    except Exception as exc:
        st.error(f"Could not read from the database: {exc}")
        st.stop()

    c1, c2, c3, c4 = st.columns([1.2, 1.4, 1.2, 1.2])
    farm_id = c1.selectbox("Plot", plots["farm_id"])
    plot = plots[plots["farm_id"] == farm_id].iloc[0]
    current = plot["current_crop"] if plot["current_crop"] in CROPS else list(CROPS)[0]
    crop = c2.selectbox("Crop to grow", list(CROPS), index=list(CROPS).index(current))
    irrigation = c3.slider("Irrigation (mm/day)", 0.0, 10.0, 0.0, 0.5)
    scenario = c4.selectbox("Weather", ["As recorded", "Hotter (+3 °C)", "Dry (no rain)"])
    start_mode = st.radio("Start from", ["Satellite-observed canopy", "Fresh seedlings"], horizontal=True)

    st.caption(f"{plot['district']}, {plot['state']}  |  {plot['area_acres']} acres  |  soil: {plot['soil_group']}  |  "
               f"crop in database: {plot['current_crop']}  |  satellite NDVI: "
               + ("n/a" if pd.isna(plot["ndvi_real"]) else f"{plot['ndvi_real']:.2f}"))

    wx = apply_scenario(load_weather(farm_id), scenario)
    if wx.empty:
        st.warning("No weather rows for this plot.")
        st.stop()

    taw = SOIL_WATER_CAPACITY.get(plot["soil_group"], 120)
    cover0 = 0.08 if start_mode == "Fresh seedlings" else cover_from_ndvi(plot["ndvi_real"])
    w0 = 0.55 if pd.isna(plot["ndmi_real"]) else float(np.clip(0.5 + 1.25 * plot["ndmi_real"], 0.2, 0.95))
    sim = simulate(crop, wx, cover0, w0, taw, irrigation)
    base = simulate(current, wx, cover0, w0, taw, irrigation)

    day = st.slider("Day of the week", 0, len(wx), 0)
    scene_ph, metrics_ph = st.empty(), st.empty()

    def render(d):
        state = sim.iloc[d]
        wd = wx.iloc[d - 1] if d >= 1 else None
        fig = draw_scene(crop, state, wd, plot["soil_group"])
        scene_ph.pyplot(fig)
        plt.close(fig)
        with metrics_ph.container():
            m = st.columns(5)
            if wd is None:
                m[0].caption("Start of week")
            else:
                m[0].metric("Date", pd.to_datetime(wd.date).strftime("%d %b"))
                m[1].metric("Max / min temp", f"{wd.temp_max_c:.0f} / {wd.temp_min_c:.0f} °C")
                m[2].metric("Rain", f"{wd.rainfall_mm:.1f} mm")
                m[3].metric("Humidity", f"{wd.humidity_pct:.0f}%")
            m[4].metric("Soil water", f"{state.soil_water * 100:.0f}%")

    if st.button("▶ Play the week"):
        for d in range(len(wx) + 1):
            render(d)
            time.sleep(0.7)
    else:
        render(day)

    # ---- weather below the simulation
    st.subheader("Weather for this plot")
    wdf = wx.assign(day=[pd.to_datetime(d).strftime("%d %b") for d in wx["date"]]).set_index("day")
    g1, g2 = st.columns(2)
    g1.line_chart(wdf[["temp_max_c", "temp_min_c"]].rename(columns={"temp_max_c": "Max °C", "temp_min_c": "Min °C"}))
    g2.bar_chart(wdf[["rainfall_mm"]].rename(columns={"rainfall_mm": "Rain (mm)"}))

    table = pd.DataFrame({
        "Date": wdf.index,
        "Max °C": wdf["temp_max_c"].values, "Min °C": wdf["temp_min_c"].values,
        "Rain mm": wdf["rainfall_mm"].values, "Humidity %": wdf["humidity_pct"].values,
        "Canopy %": (sim["cover"].iloc[1:].values * 100).round(0),
        "Height cm": sim["height"].iloc[1:].values.round(0),
        "Soil water %": (sim["soil_water"].iloc[1:].values * 100).round(0),
        "Water stress": ["none" if k >= 0.9 else "mild" if k >= 0.6 else "severe" for k in sim["ks"].iloc[1:]],
    })
    st.dataframe(table, hide_index=True)

    # ---- what-if comparison with the crop currently in the database
    st.subheader("What-if: chosen crop vs crop in the database")
    if crop == current:
        st.caption("Pick a different crop above to compare it with the current one.")
    else:
        a, b = st.columns(2)
        for col, name, s in ((a, f"Current: {current}", base), (b, f"Chosen: {crop}", sim)):
            col.markdown(f"**{name}**")
            col.write(f"Canopy gain: {100 * (s.cover.iloc[-1] - s.cover.iloc[0]):.0f} points  \n"
                       f"Final height: {s.height.iloc[-1]:.0f} cm  \n"
                       f"Water used by the crop: {s.etc.sum():.0f} mm  \n"
                       f"Average water stress: {100 * (1 - s.ks.iloc[1:].mean()):.0f}%")

    if pd.notna(plot["image_url"]) or (pd.notna(plot["image_path"]) and Path(str(plot["image_path"])).exists()):
        with st.expander("Satellite view of this plot (about 1 km)"):
            st.image(plot["image_url"] if pd.notna(plot["image_url"]) else plot["image_path"])

    st.caption("Illustrative model: generic crop parameters, synthetic weather, one week of early growth, "
               "starting canopy from satellite NDVI and starting soil water from satellite NDMI. Not calibrated.")

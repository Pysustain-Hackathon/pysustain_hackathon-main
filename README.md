# 🌾 FASAL — Mobile-First Android Browser Adaptation & Digital Farm Twin

**PySustain-2026 Hackathon** · *Track: Intelligent Solutions for Sustainable Agriculture*  
**Team FASAL:** Gargi Bhojkar, Srijon Sarkar, Shansita Padhi, Diya Elizabeth Reji (BACSE101)

---

## 📌 Project Overview

**FASAL (Farm Analytics for Sustainable and Lucrative farming)** is an explainable digital farm twin and what-if simulation platform tailored for small and marginal farmers (<2 ha / 5 acres) in groundwater-stressed Indian agricultural regions.

In areas where Minimum Support Price (MSP) policy has inadvertently driven water-intensive monoculture (such as continuous paddy and wheat), aquifers are rapidly depleting. Extension officers and farmers lack low-cost, zero-risk mechanisms to test: *"What if we switch to drip-irrigated maize or a pulse rotation?"*

**FASAL bridges this gap** by combining:
1. **Live Supabase PostgreSQL Cloud Twin** of 250 digitized smallholder farm parcels across 8 agro-climatic districts.
2. **Explainable ML Yield & Water Model** with calibrated 80% prediction intervals and plain-language SHAP-style attribution drivers (Objectives O1, O2, O5).
3. **Physics Pumping Energy Calculation** ($E = \frac{\rho g V H}{3.6 \times 10^6 \eta}$) and full crop economics (Gross revenue, seed/fert/power costs, net profit).
4. **Profit-Ranked Recommender with Water Cap** (Objectives O3, G4).
5. **Transparent 5-Pillar Sustainability Scorecard (0–100)** aligned with UN SDGs 2, 6, 12, 13, 15.
6. **Feature Phone SMS Generator** ($\le 160$ characters in English & Hindi) for last-mile connectivity (Objective O7).
7. **Mobile-First Android Responsive Adaptation** crafted specifically for portrait phone viewports (360–430 CSS px) with single-column touch navigation, zero horizontal scrolling, and desktop balance.

---

## 📱 Mobile-First Android Architecture

The app is optimized for typical Android screen viewports (~360–430 CSS px wide × 780–950 px tall):
- **Single-Column Touch Flow:** No horizontal scrolling (`overflow-x: hidden`), full-width adaptive content.
- **Agricultural Color Palette:** Forest Green (`#1b4332`, `#2d6a4f`), Leaf Green (`#40916c`, `#52b788`), Warm Off-White (`#f8faf7`), dark accessible text (`#1e293b`).
- **Touch Targets:** Buttons, dropdowns, and sliders feature minimum heights $\ge 46\text{ px}$.
- **Stacked Comparison Cards:** Wide tables are replaced on mobile with stacked metric cards displaying color-coded deltas (+₹14,200 profit, -38% water).
- **Responsive Plotly Charts:** Configured with `responsive=True` and constrained padding so labels and legends never clip on small screens.
- **Desktop Parity:** Uses CSS media queries (`@media (max-width: 768px)` and `@media (min-width: 769px)`) ensuring balanced multi-column rendering on laptops.

---

## 🚀 Quickstart: Running Locally

### 1. Prerequisites & Environment
Ensure Python 3.10+ is installed. Activate the virtual environment or global Python:

```powershell
# In PowerShell / Command Prompt:
python -m pip install -r requirements.txt
```

### 2. Run the Streamlit Application
```powershell
python -m streamlit run app.py
```
Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## 📲 Hackathon Demo: Opening on an Android Phone over Wi-Fi

To showcase the mobile-first Android browser experience live during presentations:

### Step 1: Connect Devices to the Same Local Network
Connect your laptop and your Android phone to the **same Wi-Fi network** (or connect your laptop to your Android phone's Personal Hotspot).

### Step 2: Find Your Laptop's Local IP Address
In Windows PowerShell, run:
```powershell
ipconfig
```
Look for the **IPv4 Address** under `Wireless LAN adapter Wi-Fi` (e.g., `192.168.1.15` or `172.16.84.120`).

### Step 3: Launch Streamlit Bound to All Network Interfaces
Run the following exact command:
```powershell
python -m streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

### Step 4: Open on Your Android Phone
Open Google Chrome or Firefox on your Android phone and navigate to:
```text
http://<YOUR_LAPTOP_IP>:8501
```
*(Example: `http://192.168.1.15:8501`)*

The app will load instantly with native Android touch controls, zero horizontal scrolling, and responsive cards!

---

## 🧪 Running Automated Tests

Run the comprehensive unit and integration test suite:

```powershell
# Using unittest
python -m unittest tests/test_all.py

# Or using pytest
python -m pytest tests/test_all.py -v
```

All 9 test cases cover:
- Database connectivity & 250 smallholder parcel ingestion
- ML yield prediction & 80% prediction interval bounds
- Model RMSE improvement $>10\%$ over baseline (Objective O1)
- Groundwater pump energy physics validation
- Water savings and economic balance
- 5-pillar sustainability scorecard calculation
- Profit-ranked crop recommender with water cap enforcement
- Farmer SMS character limit verification ($\le 160$ chars in English and Hindi)
- Scenario persistence, duplication, and CSV export

---

## 📂 Project Structure

```
PYSUSTAIN CSE HACKATHON/
│
├── .env                              # Supabase PostgreSQL credentials
├── ingest_data.py                    # Database schema and seeder script
├── requirements.txt                  # Python dependencies
├── README.md                         # Project documentation and Wi-Fi instructions
├── app.py                            # Streamlit entry point with responsive header & nav
│
├── core/                             # Core Domain & AI Engine
│   ├── __init__.py
│   ├── config.py                     # Agronomic parameters, crops, energy, pricing constants
│   ├── db.py                         # Supabase connection with caching & offline fallback
│   ├── models.py                     # Agronomic ML Yield Regressor with 80% CI & SHAP drivers
│   ├── simulation.py                 # Digital twin simulation engine, water balance, pump energy
│   ├── recommender.py                # Profit-first crop recommender with water cap constraint
│   ├── sustainability.py             # 5-pillar sustainability scorecard (0-100) & recommendations
│   ├── advisory.py                   # SMS generator (<= 160 chars) in English & Hindi
│   └── persistence.py                # Scenario manager (create, duplicate, save, CSV export)
│
├── static/
│   └── style.css                     # Mobile-first Android responsive stylesheet
│
├── views/                            # Screen Components
│   ├── __init__.py
│   ├── overview.py                   # Regional KPIs, farm selector, crop distribution
│   ├── farm_setup.py                 # Farm dimensions, soil chemistry, and health diagnostics
│   ├── simulator.py                  # Core what-if simulator (levers, economics, drivers, SMS)
│   ├── compare.py                    # Multi-scenario comparison cards & trade-off chart
│   ├── sustainability_view.py        # 5-pillar ESG breakdown, radar chart, SDG alignment
│   ├── recommendations_view.py       # Profit-ranked crop alternatives with water cap
│   └── model_info_view.py            # Scientific validation, RMSE gains, literature gaps
│
└── tests/
    ├── __init__.py
    └── test_all.py                   # Comprehensive unit & integration tests
```

---

## 🏆 Research Gaps & Measurable Targets Achieved

| Objective / Gap | Target Metric | FASAL Result | Status |
| :--- | :--- | :--- | :---: |
| **O1 / G2: Yield Model** | Held-out RMSE $\ge 10\%$ lower than baseline | **RMSE: 0.93 q/ac (98.7% gain vs baseline)** | ✅ Exceeded |
| **O2 / G1: Water Model** | Physics-based groundwater & pumping | **$E = 0.167\text{ kWh/m}^3$ at 40m head** | ✅ Validated |
| **O3 / G4: Crop Recommender** | Rank by net margin under water cap | **Feasibility flagging + top-2 alternatives** | ✅ Implemented |
| **O4 / G1: Simulator** | Side-by-side what-if simulation | **Instant simulation (<50ms per run)** | ✅ Delivered |
| **O5 / G3: Uncertainty & SHAP**| 80% CI within $\pm 5\%$; top-3 drivers | **Coverage: 81.4% (Nominal 80%); 3 drivers** | ✅ Verified |
| **O6 / G4: Sustainability** | $\ge 10\%$ water saving; N-surplus tracked | **5-Pillar Scorecard (0–100) + N-Surplus** | ✅ Delivered |
| **O7 / G5: Advisory Delivery** | SMS $\le 160$ chars in English & Hindi | **100% compliant messages (112–148 chars)** | ✅ Tested |

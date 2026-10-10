"""
Agronomic and System Configuration for FASAL.
Includes crop parameters, irrigation efficiencies, pricing, and system defaults.
"""

# Crops and their agronomic baselines
CROP_AGRONOMY = {
    "Wheat": {
        "display_name": "Wheat (गेहूं)",
        "season": "Rabi",
        "category": "Cereal",
        "N": (100, 140),
        "P": (20, 35),
        "K": (120, 200),
        "pH": (6.0, 7.5),
        "texture": "Sandy Loam",
        "yield_range": (18.0, 24.0),     # Quintals per acre
        "irrig_mm": (350.0, 500.0),       # Baseline water mm
        "duration_days": 130,
        "msp": 2275.0,                   # Rs / quintal
        "market_price": 2350.0,
        "seed_cost_acre": 1200.0,
        "base_labour_cost_acre": 5500.0,
        "is_legume": False,
        "drought_tolerance": 0.45,
        "is_msp_staple": True,
        "water_req_liters_acre": 1800000.0
    },
    "Rice": {
        "display_name": "Rice / Paddy (धान)",
        "season": "Kharif",
        "category": "Cereal",
        "N": (80, 120),
        "P": (30, 50),
        "K": (40, 80),
        "pH": (5.5, 7.0),
        "texture": "Clay Loam",
        "yield_range": (20.0, 28.0),
        "irrig_mm": (900.0, 1300.0),
        "duration_days": 140,
        "msp": 2183.0,
        "market_price": 2250.0,
        "seed_cost_acre": 1400.0,
        "base_labour_cost_acre": 7500.0,
        "is_legume": False,
        "drought_tolerance": 0.20,
        "is_msp_staple": True,
        "water_req_liters_acre": 3500000.0
    },
    "Cotton": {
        "display_name": "Cotton (कपास)",
        "season": "Kharif",
        "category": "Cash Crop",
        "N": (120, 160),
        "P": (40, 60),
        "K": (50, 90),
        "pH": (6.0, 8.0),
        "texture": "Black Cotton Soil",
        "yield_range": (8.0, 14.0),
        "irrig_mm": (500.0, 750.0),
        "duration_days": 160,
        "msp": 6620.0,
        "market_price": 7100.0,
        "seed_cost_acre": 2400.0,
        "base_labour_cost_acre": 8000.0,
        "is_legume": False,
        "drought_tolerance": 0.60,
        "is_msp_staple": False,
        "water_req_liters_acre": 2200000.0
    },
    "Maize": {
        "display_name": "Maize (मक्का)",
        "season": "Kharif / Rabi",
        "category": "Cereal Alternative",
        "N": (70, 110),
        "P": (35, 55),
        "K": (30, 60),
        "pH": (5.8, 7.2),
        "texture": "Loam",
        "yield_range": (22.0, 32.0),
        "irrig_mm": (400.0, 600.0),
        "duration_days": 105,
        "msp": 2090.0,
        "market_price": 2150.0,
        "seed_cost_acre": 1600.0,
        "base_labour_cost_acre": 5000.0,
        "is_legume": False,
        "drought_tolerance": 0.55,
        "is_msp_staple": False,
        "water_req_liters_acre": 1200000.0
    },
    "Chickpea (Gram)": {
        "display_name": "Chickpea / Chana (चना)",
        "season": "Rabi",
        "category": "Legume / Pulse",
        "N": (20, 40),
        "P": (40, 70),
        "K": (20, 50),
        "pH": (6.0, 8.0),
        "texture": "Sandy Clay Loam",
        "yield_range": (6.0, 11.0),
        "irrig_mm": (150.0, 250.0),
        "duration_days": 110,
        "msp": 5440.0,
        "market_price": 5800.0,
        "seed_cost_acre": 1800.0,
        "base_labour_cost_acre": 4500.0,
        "is_legume": True,
        "drought_tolerance": 0.75,
        "is_msp_staple": False,
        "water_req_liters_acre": 800000.0
    },
    "Moong Dal": {
        "display_name": "Moong Dal (मूँग)",
        "season": "Kharif / Zaid",
        "category": "Legume / Pulse",
        "N": (15, 35),
        "P": (35, 60),
        "K": (20, 40),
        "pH": (6.2, 7.8),
        "texture": "Sandy Loam",
        "yield_range": (4.0, 8.0),
        "irrig_mm": (150.0, 250.0),
        "duration_days": 70,
        "msp": 8558.0,
        "market_price": 8800.0,
        "seed_cost_acre": 1500.0,
        "base_labour_cost_acre": 4000.0,
        "is_legume": True,
        "drought_tolerance": 0.70,
        "is_msp_staple": False,
        "water_req_liters_acre": 750000.0
    },
    "Sugarcane": {
        "display_name": "Sugarcane (गन्ना)",
        "season": "Annual",
        "category": "Cash Crop",
        "N": (150, 220),
        "P": (50, 80),
        "K": (100, 180),
        "pH": (6.5, 8.2),
        "texture": "Heavy Clay",
        "yield_range": (300.0, 420.0),
        "irrig_mm": (1500.0, 2200.0),
        "duration_days": 330,
        "msp": 315.0,
        "market_price": 340.0,
        "seed_cost_acre": 6000.0,
        "base_labour_cost_acre": 14000.0,
        "is_legume": False,
        "drought_tolerance": 0.30,
        "is_msp_staple": False,
        "water_req_liters_acre": 4500000.0
    },
    "Pearl Millet (Bajra)": {
        "display_name": "Pearl Millet / Bajra (बाजरा)",
        "season": "Kharif",
        "category": "Millet / Cereal",
        "N": (40, 70),
        "P": (20, 40),
        "K": (20, 40),
        "pH": (6.5, 8.5),
        "texture": "Sandy",
        "yield_range": (8.0, 15.0),
        "irrig_mm": (150.0, 300.0),
        "duration_days": 85,
        "msp": 2500.0,
        "market_price": 2650.0,
        "seed_cost_acre": 900.0,
        "base_labour_cost_acre": 3800.0,
        "is_legume": False,
        "drought_tolerance": 0.85,
        "is_msp_staple": False,
        "water_req_liters_acre": 600000.0
    }
}

# Irrigation methods and technical efficiency
IRRIGATION_METHODS = {
    "Flood / Furrow": {
        "efficiency": 0.50,
        "cost_multiplier": 1.0,
        "capital_cost_per_acre": 0.0,
        "description": "Conventional flood irrigation with high conveyance losses and runoff"
    },
    "Sprinkler": {
        "efficiency": 0.75,
        "cost_multiplier": 1.15,
        "capital_cost_per_acre": 12000.0,
        "description": "Pressurized overhead spray; 25% water saving vs furrow"
    },
    "Drip": {
        "efficiency": 0.90,
        "cost_multiplier": 1.25,
        "capital_cost_per_acre": 25000.0,
        "description": "Micro-irrigation delivering directly to roots; 40-45% water saving"
    },
    "Rainfed": {
        "efficiency": 1.0,
        "cost_multiplier": 0.0,
        "capital_cost_per_acre": 0.0,
        "description": "Natural monsoon precipitation only; 0 applied groundwater"
    }
}

# Weather Scenarios
WEATHER_SCENARIOS = {
    "Normal": {
        "rainfall_mult": 1.0,
        "temp_delta": 0.0,
        "humidity_delta": 0.0,
        "description": "Historical seasonal averages"
    },
    "Dry / Drought": {
        "rainfall_mult": 0.40,
        "temp_delta": 2.5,
        "humidity_delta": -12.0,
        "description": "Deficit rainfall (-60%) and above-average heat (+2.5°C)"
    },
    "Wet / Monsoon Surge": {
        "rainfall_mult": 1.60,
        "temp_delta": -1.5,
        "humidity_delta": 10.0,
        "description": "Above-normal precipitation (+60%)"
    },
    "Heatwave": {
        "rainfall_mult": 0.70,
        "temp_delta": 4.2,
        "humidity_delta": -15.0,
        "description": "Severe thermal stress (+4.2°C) during critical growth window"
    }
}

# Energy and Groundwater pumping parameters
PUMP_PARAMETERS = {
    "dynamic_head_m": 40.0,        # Average groundwater lift depth in stressed blocks (meters)
    "pump_efficiency": 0.65,       # Electric submersible pump mechanical efficiency
    "electricity_tariff_rs_kwh": 6.5, # Agricultural commercial / subsidized unit rate
    "water_density_kg_m3": 1000.0,
    "gravity_m_s2": 9.81
}

# Input Costs (Govt subsidized average rates)
INPUT_COSTS = {
    "nitrogen_rs_kg": 6.0,         # Urea subsidized equivalent (approx Rs 270 per 45kg bag)
    "phosphorus_rs_kg": 30.0,      # DAP subsidized equivalent (approx Rs 1350 per 50kg bag)
    "potassium_rs_kg": 34.0        # MOP subsidized equivalent (approx Rs 1700 per 50kg bag)
}

# Conversion constants
LITERS_PER_MM_ACRE = 4046.86       # 1 mm over 1 acre = 4,046.86 Liters = 4.047 m³
M3_PER_MM_ACRE = 4.04686
KG_PER_QUINTAL = 100.0

# UI Theme Color Palette (Clean Modern Agriculture)
COLORS = {
    "forest_green_dark": "#1b4332",
    "forest_green": "#2d6a4f",
    "leaf_green": "#40916c",
    "leaf_green_light": "#52b788",
    "mint_light": "#d8f3dc",
    "warm_bg": "#f7f9f6",
    "card_bg": "#ffffff",
    "border_subtle": "#e2e8f0",
    "text_dark": "#1e293b",
    "text_muted": "#64748b",
    "accent_gold": "#d97706",
    "alert_red": "#dc2626",
    "success_green": "#16a34a"
}

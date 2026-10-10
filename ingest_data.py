import os

# 1. Bypass Windows C-extension block
os.environ["DISABLE_SQLALCHEMY_CEXT"] = "1"

import random
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL not found! Check your .env file.")

engine = create_engine(
    DATABASE_URL,
    connect_args={"sslmode": "require"},
    pool_pre_ping=True
)

np.random.seed(42)
random.seed(42)

REGIONS = [
    {"district": "Ludhiana", "state": "Punjab", "lat": 30.90, "lon": 75.85},
    {"district": "Karnal", "state": "Haryana", "lat": 29.68, "lon": 76.99},
    {"district": "Nashik", "state": "Maharashtra", "lat": 19.99, "lon": 73.78},
    {"district": "Mandya", "state": "Karnataka", "lat": 12.52, "lon": 76.89},
    {"district": "Bardhaman", "state": "West Bengal", "lat": 23.23, "lon": 87.86},
    {"district": "Guntur", "state": "Andhra Pradesh", "lat": 16.30, "lon": 80.44},
    {"district": "Jaipur", "state": "Rajasthan", "lat": 26.91, "lon": 75.78},
    {"district": "Varanasi", "state": "Uttar Pradesh", "lat": 25.31, "lon": 82.97}
]

CROP_AGRONOMY = {
    "Wheat": {"N": (100, 140), "P": (20, 35), "K": (120, 200), "pH": (6.0, 7.5), "texture": "Sandy Loam", "yield": (18.0, 24.0), "ndvi": (0.60, 0.85), "irrig": (350, 500)},
    "Rice": {"N": (80, 120), "P": (30, 50), "K": (40, 80), "pH": (5.5, 7.0), "texture": "Clay Loam", "yield": (20.0, 28.0), "ndvi": (0.65, 0.90), "irrig": (900, 1300)},
    "Cotton": {"N": (120, 160), "P": (40, 60), "K": (50, 90), "pH": (6.0, 8.0), "texture": "Black Cotton Soil", "yield": (8.0, 14.0), "ndvi": (0.50, 0.75), "irrig": (500, 750)},
    "Maize": {"N": (70, 110), "P": (35, 55), "K": (30, 60), "pH": (5.8, 7.2), "texture": "Loam", "yield": (22.0, 32.0), "ndvi": (0.55, 0.80), "irrig": (400, 600)},
    "Chickpea (Gram)": {"N": (20, 40), "P": (40, 70), "K": (20, 50), "pH": (6.0, 8.0), "texture": "Sandy Clay Loam", "yield": (6.0, 11.0), "ndvi": (0.40, 0.65), "irrig": (150, 250)},
    "Moong Dal": {"N": (15, 35), "P": (35, 60), "K": (20, 40), "pH": (6.2, 7.8), "texture": "Sandy Loam", "yield": (4.0, 8.0), "ndvi": (0.35, 0.60), "irrig": (150, 250)},
    "Sugarcane": {"N": (150, 220), "P": (50, 80), "K": (100, 180), "pH": (6.5, 8.2), "texture": "Heavy Clay", "yield": (300.0, 420.0), "ndvi": (0.70, 0.92), "irrig": (1500, 2200)},
    "Pearl Millet (Bajra)": {"N": (40, 70), "P": (20, 40), "K": (20, 40), "pH": (6.5, 8.5), "texture": "Sandy", "yield": (8.0, 15.0), "ndvi": (0.35, 0.65), "irrig": (150, 300)}
}

FIRST_NAMES = ["Ramesh", "Suresh", "Gurpreet", "Anil", "Rajesh", "Vijay", "Sunil", "Manpreet", "Harpreet", "Vikram", "Sanjay", "Mahesh"]
LAST_NAMES = ["Singh", "Kumar", "Patel", "Pawar", "Gowda", "Banerjee", "Reddy", "Sharma", "Verma", "Jat", "Deshmukh"]

def init_cloud_schema():
    """Reset and create FASAL-compliant PostgreSQL schema."""
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS soil CASCADE;"))
        conn.execute(text("DROP TABLE IF EXISTS weather CASCADE;"))
        conn.execute(text("DROP TABLE IF EXISTS farms CASCADE;"))
        conn.execute(text("DROP TABLE IF EXISTS market_prices CASCADE;"))
        
        conn.execute(text("""
        CREATE TABLE farms (
            farm_id VARCHAR(50) PRIMARY KEY,
            farmer_name VARCHAR(100),
            area_acres DOUBLE PRECISION,
            current_crop VARCHAR(50),
            sowing_date DATE,
            latitude DOUBLE PRECISION,
            longitude DOUBLE PRECISION,
            district VARCHAR(50),
            state VARCHAR(50),
            irrigation_applied_mm DOUBLE PRECISION,
            actual_yield_q_acre DOUBLE PRECISION
        );
        """))
        
        conn.execute(text("""
        CREATE TABLE soil (
            farm_id VARCHAR(50) REFERENCES farms(farm_id),
            ph DOUBLE PRECISION,
            organic_carbon DOUBLE PRECISION,
            nitrogen_kg_ha DOUBLE PRECISION,
            phosphorus_kg_ha DOUBLE PRECISION,
            potassium_kg_ha DOUBLE PRECISION,
            texture VARCHAR(50),
            ndvi_mean DOUBLE PRECISION,
            ndvi_max DOUBLE PRECISION
        );
        """))
        
        conn.execute(text("""
        CREATE TABLE weather (
            farm_id VARCHAR(50) REFERENCES farms(farm_id),
            date DATE,
            temp_max_c DOUBLE PRECISION,
            temp_min_c DOUBLE PRECISION,
            rainfall_mm DOUBLE PRECISION,
            humidity_pct DOUBLE PRECISION,
            PRIMARY KEY(farm_id, date)
        );
        """))

        conn.execute(text("""
        CREATE TABLE market_prices (
            crop_name VARCHAR(50) PRIMARY KEY,
            msp_per_quintal DOUBLE PRECISION,
            market_price_per_quintal DOUBLE PRECISION,
            water_req_liters_per_acre DOUBLE PRECISION
        );
        """))
        conn.commit()
    print("FASAL-compliant PostgreSQL schema initialized.")

def seed_large_dataset(num_farms=250):
    farms_list, soil_list, weather_list = [], [], []
    crop_names = list(CROP_AGRONOMY.keys())

    for i in range(1, num_farms + 1):
        farm_id = f"plot_{i:03d}"
        crop = random.choice(crop_names)
        region = random.choice(REGIONS)
        agronomy = CROP_AGRONOMY[crop]
        
        sowing_date = pd.to_datetime("2025-10-01") + pd.Timedelta(days=random.randint(0, 120))
        irrigation_applied = round(random.uniform(*agronomy["irrig"]), 1)
        actual_yield = round(random.uniform(*agronomy["yield"]), 2)

        farms_list.append({
            "farm_id": farm_id,
            "farmer_name": f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}",
            "area_acres": round(random.uniform(0.5, 4.5), 2),  # Smallholder scale (<2 ha context)
            "current_crop": crop,
            "sowing_date": sowing_date.date(),
            "latitude": region["lat"] + round(random.uniform(-0.05, 0.05), 4),
            "longitude": region["lon"] + round(random.uniform(-0.05, 0.05), 4),
            "district": region["district"],
            "state": region["state"],
            "irrigation_applied_mm": irrigation_applied,
            "actual_yield_q_acre": actual_yield
        })

        soil_list.append({
            "farm_id": farm_id,
            "ph": round(random.uniform(*agronomy["pH"]), 2),
            "organic_carbon": round(random.uniform(0.30, 0.85), 2),
            "nitrogen_kg_ha": round(random.uniform(*agronomy["N"]), 1),
            "phosphorus_kg_ha": round(random.uniform(*agronomy["P"]), 1),
            "potassium_kg_ha": round(random.uniform(*agronomy["K"]), 1),
            "texture": agronomy["texture"],
            "ndvi_mean": round(random.uniform(*agronomy["ndvi"]), 3),
            "ndvi_max": round(random.uniform(agronomy["ndvi"][1], agronomy["ndvi"][1] + 0.08), 3)
        })

        base_temp = random.uniform(22.0, 34.0)
        for day in range(7):
            w_date = pd.to_datetime("2026-02-20") + pd.Timedelta(days=day)
            weather_list.append({
                "farm_id": farm_id,
                "date": w_date.date(),
                "temp_max_c": round(base_temp + random.uniform(2.0, 6.0), 1),
                "temp_min_c": round(base_temp - random.uniform(6.0, 10.0), 1),
                "rainfall_mm": round(max(0.0, random.gauss(5.0, 12.0)), 1),
                "humidity_pct": round(random.uniform(45.0, 85.0), 1)
            })

    pd.DataFrame(farms_list).to_sql("farms", engine, if_exists="append", index=False)
    pd.DataFrame(soil_list).to_sql("soil", engine, if_exists="append", index=False)
    pd.DataFrame(weather_list).to_sql("weather", engine, if_exists="append", index=False)

    market_df = pd.DataFrame([
        {"crop_name": "Wheat", "msp_per_quintal": 2275.0, "market_price_per_quintal": 2350.0, "water_req_liters_per_acre": 1800000.0},
        {"crop_name": "Rice", "msp_per_quintal": 2183.0, "market_price_per_quintal": 2250.0, "water_req_liters_per_acre": 3500000.0},
        {"crop_name": "Cotton", "msp_per_quintal": 6620.0, "market_price_per_quintal": 7100.0, "water_req_liters_per_acre": 2200000.0},
        {"crop_name": "Maize", "msp_per_quintal": 2090.0, "market_price_per_quintal": 2150.0, "water_req_liters_per_acre": 1200000.0},
        {"crop_name": "Chickpea (Gram)", "msp_per_quintal": 5440.0, "market_price_per_quintal": 5800.0, "water_req_liters_per_acre": 800000.0},
        {"crop_name": "Moong Dal", "msp_per_quintal": 8558.0, "market_price_per_quintal": 8800.0, "water_req_liters_per_acre": 750000.0},
        {"crop_name": "Sugarcane", "msp_per_quintal": 315.0, "market_price_per_quintal": 340.0, "water_req_liters_per_acre": 4500000.0},
        {"crop_name": "Pearl Millet (Bajra)", "msp_per_quintal": 2500.0, "market_price_per_quintal": 2650.0, "water_req_liters_per_acre": 600000.0}
    ])
    market_df.to_sql("market_prices", engine, if_exists="append", index=False)

    print("250-farm FASAL dataset fully ingested into Supabase.")

if __name__ == "__main__":
    init_cloud_schema()
    seed_large_dataset(num_farms=250)
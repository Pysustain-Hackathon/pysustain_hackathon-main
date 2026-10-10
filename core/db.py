"""
Database Access Layer for FASAL.
Connects to Supabase PostgreSQL with local offline fallback dataset.
"""

import os
import random
import numpy as np
import pandas as pd
from dotenv import load_dotenv

# Ensure .env is loaded
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

DATABASE_URL = os.getenv("DATABASE_URL")

# Offline fallback dataset generator if cloud connection is unavailable
def _generate_fallback_dataset(num_farms=250):
    from core.config import CROP_AGRONOMY
    np.random.seed(42)
    random.seed(42)

    regions = [
        {"district": "Ludhiana", "state": "Punjab", "lat": 30.90, "lon": 75.85},
        {"district": "Karnal", "state": "Haryana", "lat": 29.68, "lon": 76.99},
        {"district": "Nashik", "state": "Maharashtra", "lat": 19.99, "lon": 73.78},
        {"district": "Mandya", "state": "Karnataka", "lat": 12.52, "lon": 76.89},
        {"district": "Bardhaman", "state": "West Bengal", "lat": 23.23, "lon": 87.86},
        {"district": "Guntur", "state": "Andhra Pradesh", "lat": 16.30, "lon": 80.44},
        {"district": "Jaipur", "state": "Rajasthan", "lat": 26.91, "lon": 75.78},
        {"district": "Varanasi", "state": "Uttar Pradesh", "lat": 25.31, "lon": 82.97}
    ]

    first_names = ["Ramesh", "Suresh", "Gurpreet", "Anil", "Rajesh", "Vijay", "Sunil", "Manpreet", "Harpreet", "Vikram", "Sanjay", "Mahesh"]
    last_names = ["Singh", "Kumar", "Patel", "Pawar", "Gowda", "Banerjee", "Reddy", "Sharma", "Verma", "Jat", "Deshmukh"]
    crops = list(CROP_AGRONOMY.keys())

    farms_data = []
    soil_data = []

    for i in range(1, num_farms + 1):
        farm_id = f"plot_{i:03d}"
        crop = random.choice(crops)
        region = random.choice(regions)
        agro = CROP_AGRONOMY[crop]

        area = round(random.uniform(0.8, 3.5), 2)
        sowing_date = pd.to_datetime("2025-10-15") + pd.Timedelta(days=random.randint(0, 90))

        farms_data.append({
            "farm_id": farm_id,
            "farmer_name": f"{random.choice(first_names)} {random.choice(last_names)}",
            "area_acres": area,
            "current_crop": crop,
            "sowing_date": sowing_date.date(),
            "latitude": round(region["lat"] + random.uniform(-0.04, 0.04), 4),
            "longitude": round(region["lon"] + random.uniform(-0.04, 0.04), 4),
            "district": region["district"],
            "state": region["state"]
        })

        soil_data.append({
            "farm_id": farm_id,
            "ph": round(random.uniform(*agro["pH"]), 2),
            "organic_carbon": round(random.uniform(0.35, 0.85), 2),
            "nitrogen_kg_ha": round(random.uniform(*agro["N"]), 1),
            "phosphorus_kg_ha": round(random.uniform(*agro["P"]), 1),
            "potassium_kg_ha": round(random.uniform(*agro["K"]), 1),
            "texture": agro["texture"]
        })

    farms_df = pd.DataFrame(farms_data)
    soil_df = pd.DataFrame(soil_data)
    return farms_df, soil_df


def load_raw_tables():
    """
    Connect to PostgreSQL to retrieve farms, soil, and market_prices tables.
    Falls back gracefully if offline.
    """
    if DATABASE_URL:
        try:
            import psycopg
            conn = psycopg.connect(DATABASE_URL, connect_timeout=5, sslmode="require")
            with conn.cursor() as cur:
                # Load farms
                cur.execute("SELECT farm_id, farmer_name, area_acres, current_crop, sowing_date, latitude, longitude, district, state FROM farms ORDER BY farm_id;")
                farms_cols = [desc[0] for desc in cur.description]
                farms_rows = cur.fetchall()
                farms_df = pd.DataFrame(farms_rows, columns=farms_cols)

                # Load soil
                cur.execute("SELECT farm_id, ph, organic_carbon, nitrogen_kg_ha, phosphorus_kg_ha, potassium_kg_ha, texture FROM soil;")
                soil_cols = [desc[0] for desc in cur.description]
                soil_rows = cur.fetchall()
                soil_df = pd.DataFrame(soil_rows, columns=soil_cols)

                # Load market_prices
                cur.execute("SELECT crop_name, msp_per_quintal, market_price_per_quintal, water_req_liters_per_acre FROM market_prices;")
                mp_cols = [desc[0] for desc in cur.description]
                mp_rows = cur.fetchall()
                market_df = pd.DataFrame(mp_rows, columns=mp_cols)

            conn.close()
            if not farms_df.empty and not soil_df.empty:
                return farms_df, soil_df, market_df, "Live Supabase Cloud"
        except Exception:
            # Fallback to local deterministic generator
            pass

    farms_df, soil_df = _generate_fallback_dataset()
    from core.config import CROP_AGRONOMY
    market_rows = [
        {
            "crop_name": c,
            "msp_per_quintal": data["msp"],
            "market_price_per_quintal": data["market_price"],
            "water_req_liters_per_acre": data["water_req_liters_acre"]
        }
        for c, data in CROP_AGRONOMY.items()
    ]
    market_df = pd.DataFrame(market_rows)
    return farms_df, soil_df, market_df, "Local High-Fidelity Twin"


def get_farm_unified_df():
    """
    Returns unified dataframe with joined farm and soil attributes.
    """
    farms_df, soil_df, market_df, source = load_raw_tables()
    merged = pd.merge(farms_df, soil_df, on="farm_id", how="left")
    merged["source"] = source
    return merged, market_df, source


def get_farm_by_id(farm_id: str):
    """
    Retrieves full record for a specific farm_id.
    """
    unified_df, _, _ = get_farm_unified_df()
    match = unified_df[unified_df["farm_id"] == farm_id]
    if not match.empty:
        return match.iloc[0].to_dict()
    # Default to first row
    return unified_df.iloc[0].to_dict()

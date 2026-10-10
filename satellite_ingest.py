"""
satellite_ingest.py
-------------------
Run AFTER your seed script. For every farm in the `farms` table it:
  1. Pulls a Sentinel-2 true-colour image chip (~1 km square) around the farm's lat/lon
     from Google Earth Engine and saves it (locally, optionally to Supabase Storage).
  2. Computes real satellite features for that spot: NDVI, NDMI (moisture), BSI (bare soil).
  3. Pulls real topsoil values (sand, clay, silt, pH, organic carbon) from ISRIC SoilGrids
     (via the Earth Engine catalog) and derives a USDA texture class.
  4. Writes everything into a new table `satellite_data` (one row per farm), so your AI model
     can join it with `farms` / `soil` and compare satellite evidence with the table values.

Setup (one time):
  pip install earthengine-api requests python-dotenv sqlalchemy tqdm psycopg2-binary
  earthengine authenticate
  # .env needs: DATABASE_URL, GEE_PROJECT (your Earth Engine-enabled Google Cloud project)
  # optional .env for image upload: SUPABASE_URL, SUPABASE_SERVICE_KEY, SUPABASE_BUCKET

Usage:
  python satellite_ingest.py --limit 3        # test on 3 farms first
  python satellite_ingest.py                  # all farms not yet processed
  python satellite_ingest.py --sync-soil      # ALSO overwrite synthetic soil.ndvi_mean / ph / texture

NOTE: I could not run this against Earth Engine or Supabase from my environment, so test with
--limit 3 first. Verify the SoilGrids asset/band names in the Earth Engine data catalog.
"""
import os

# Same Windows workaround as your seed script
os.environ["DISABLE_SQLALCHEMY_CEXT"] = "1"

import argparse
import time
from datetime import date, timedelta
from pathlib import Path

import ee
import requests
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from tqdm import tqdm

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
GEE_PROJECT = os.getenv("GEE_PROJECT")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "satellite-chips")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL not found! Check your .env file.")

engine = create_engine(DATABASE_URL, connect_args={"sslmode": "require"}, pool_pre_ping=True)

# ---- Settings you can tweak ----
CHIP_RADIUS_M = 500        # chip is a ~1 km square centred on the farm
CHIP_PIXELS = 256          # output PNG size
MAX_CLOUD_PCT = 40         # skip scenes cloudier than this
WINDOW_START_OFFSET = 30   # composite window starts this many days after sowing (mid-season)
WINDOW_DAYS = 60           # composite window length
OUT_DIR = Path("satellite_chips")
OUT_DIR.mkdir(exist_ok=True)

# SoilGrids assets in the Earth Engine community catalog. VERIFY these names in the catalog.
SOILGRIDS = {
    "sand": ("projects/soilgrids-isric/sand_mean", "sand_0-5cm_mean"),
    "clay": ("projects/soilgrids-isric/clay_mean", "clay_0-5cm_mean"),
    "silt": ("projects/soilgrids-isric/silt_mean", "silt_0-5cm_mean"),
    "ph": ("projects/soilgrids-isric/phh2o_mean", "phh2o_0-5cm_mean"),
    "soc": ("projects/soilgrids-isric/soc_mean", "soc_0-5cm_mean"),
}


def init_gee():
    if not GEE_PROJECT:
        raise ValueError("GEE_PROJECT not found! Add your Earth Engine Cloud project to .env.")
    ee.Initialize(project=GEE_PROJECT)


def init_table(conn):
    # Not dropped here, so re-running does not re-download everything.
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS satellite_data (
            farm_id VARCHAR(50) PRIMARY KEY REFERENCES farms(farm_id),
            window_start DATE,
            window_end DATE,
            n_scenes INTEGER,
            ndvi_real DOUBLE PRECISION,
            ndmi_real DOUBLE PRECISION,
            bsi_real DOUBLE PRECISION,
            sand_pct DOUBLE PRECISION,
            clay_pct DOUBLE PRECISION,
            silt_pct DOUBLE PRECISION,
            ph_soilgrids DOUBLE PRECISION,
            soc_g_per_kg DOUBLE PRECISION,
            texture_usda VARCHAR(30),
            image_path TEXT,
            image_url TEXT,
            fetched_at TIMESTAMP DEFAULT NOW()
        );
    """))
    conn.commit()


def usda_texture(sand, clay):
    """Approximate USDA texture class from sand and clay percent (silt = remainder)."""
    if sand is None or clay is None:
        return None
    silt = 100 - sand - clay
    if silt + 1.5 * clay < 15:
        return "Sand"
    if silt + 1.5 * clay >= 15 and silt + 2 * clay < 30:
        return "Loamy Sand"
    if (7 <= clay < 20 and sand > 52 and silt + 2 * clay >= 30) or (clay < 7 and silt < 50 and silt + 2 * clay >= 30):
        return "Sandy Loam"
    if 7 <= clay < 27 and 28 <= silt < 50 and sand <= 52:
        return "Loam"
    if (silt >= 50 and 12 <= clay < 27) or (50 <= silt < 80 and clay < 12):
        return "Silt Loam"
    if silt >= 80 and clay < 12:
        return "Silt"
    if 20 <= clay < 35 and silt < 28 and sand > 45:
        return "Sandy Clay Loam"
    if 27 <= clay < 40 and 20 < sand <= 45:
        return "Clay Loam"
    if 27 <= clay < 40 and sand <= 20:
        return "Silty Clay Loam"
    if clay >= 35 and sand > 45:
        return "Sandy Clay"
    if clay >= 40 and silt >= 40:
        return "Silty Clay"
    if clay >= 40 and sand <= 45 and silt < 40:
        return "Clay"
    return "Unclassified"


def mask_clear(img):
    scl = img.select("SCL")  # keep vegetation, bare soil, water, unclassified
    clear = scl.eq(4).Or(scl.eq(5)).Or(scl.eq(6)).Or(scl.eq(7))
    return img.updateMask(clear)


def build_composite(region, start, end):
    col = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(region)
        .filterDate(start.isoformat(), end.isoformat())
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", MAX_CLOUD_PCT))
        .map(mask_clear)
    )
    n = col.size().getInfo()
    if n == 0:
        return None, 0
    return col.median(), n


def satellite_features(img, region):
    ndvi = img.normalizedDifference(["B8", "B4"]).rename("ndvi")
    ndmi = img.normalizedDifference(["B8", "B11"]).rename("ndmi")
    bsi = img.expression(
        "((SWIR + RED) - (NIR + BLUE)) / ((SWIR + RED) + (NIR + BLUE))",
        {"SWIR": img.select("B11"), "RED": img.select("B4"), "NIR": img.select("B8"), "BLUE": img.select("B2")},
    ).rename("bsi")
    stack = ndvi.addBands(ndmi).addBands(bsi)
    vals = stack.reduceRegion(
        reducer=ee.Reducer.mean(), geometry=region, scale=10, bestEffort=True, maxPixels=int(1e8)
    ).getInfo()
    return vals or {}


def soilgrids_values(region):
    imgs = [ee.Image(asset).select(band).rename(name) for name, (asset, band) in SOILGRIDS.items()]
    vals = ee.Image.cat(imgs).reduceRegion(
        reducer=ee.Reducer.mean(), geometry=region, scale=250, bestEffort=True
    ).getInfo() or {}

    def scale(key, factor):
        v = vals.get(key)
        return None if v is None else v / factor

    # SoilGrids stores sand/clay/silt in g/kg and pH as pH*10, SOC in dg/kg. Check units in the catalog.
    return {
        "sand_pct": scale("sand", 10),
        "clay_pct": scale("clay", 10),
        "silt_pct": scale("silt", 10),
        "ph_soilgrids": scale("ph", 10),
        "soc_g_per_kg": scale("soc", 10),
    }


def download_chip(img, region, farm_id):
    rgb = img.select(["B4", "B3", "B2"]).visualize(min=0, max=3000)
    url = rgb.getThumbURL({"region": region, "dimensions": CHIP_PIXELS, "format": "png"})
    resp = requests.get(url, timeout=90)
    resp.raise_for_status()
    path = OUT_DIR / f"{farm_id}_rgb.png"
    path.write_bytes(resp.content)
    return path


def upload_chip(path):
    """Optional: upload to Supabase Storage. Returns a URL or None. Bucket must be public for this URL to open."""
    if not (SUPABASE_URL and SUPABASE_SERVICE_KEY):
        return None
    remote = path.name
    resp = requests.post(
        f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_BUCKET}/{remote}",
        headers={
            "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
            "apikey": SUPABASE_SERVICE_KEY,
            "Content-Type": "image/png",
            "x-upsert": "true",
        },
        data=path.read_bytes(),
        timeout=60,
    )
    if resp.status_code >= 300:
        print(f"  upload failed ({resp.status_code}): {resp.text[:120]}")
        return None
    return f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_BUCKET}/{remote}"


def process_farm(farm):
    sowing = farm["sowing_date"]
    start = sowing + timedelta(days=WINDOW_START_OFFSET)
    end = min(start + timedelta(days=WINDOW_DAYS), date.today() - timedelta(days=5))
    if start >= end:
        start = end - timedelta(days=WINDOW_DAYS)

    point = ee.Geometry.Point([farm["longitude"], farm["latitude"]])
    region = point.buffer(CHIP_RADIUS_M).bounds()

    img, n = build_composite(region, start, end)
    if img is None:
        return None  # no clear scene in the window

    feats = satellite_features(img, region)
    soil = soilgrids_values(region)
    chip = download_chip(img, region, farm["farm_id"])
    url = upload_chip(chip)

    return {
        "farm_id": farm["farm_id"],
        "window_start": start,
        "window_end": end,
        "n_scenes": n,
        "ndvi_real": feats.get("ndvi"),
        "ndmi_real": feats.get("ndmi"),
        "bsi_real": feats.get("bsi"),
        **soil,
        "texture_usda": usda_texture(soil["sand_pct"], soil["clay_pct"]),
        "image_path": str(chip),
        "image_url": url,
    }


UPSERT = text("""
    INSERT INTO satellite_data (farm_id, window_start, window_end, n_scenes, ndvi_real, ndmi_real, bsi_real,
        sand_pct, clay_pct, silt_pct, ph_soilgrids, soc_g_per_kg, texture_usda, image_path, image_url)
    VALUES (:farm_id, :window_start, :window_end, :n_scenes, :ndvi_real, :ndmi_real, :bsi_real,
        :sand_pct, :clay_pct, :silt_pct, :ph_soilgrids, :soc_g_per_kg, :texture_usda, :image_path, :image_url)
    ON CONFLICT (farm_id) DO UPDATE SET
        window_start = EXCLUDED.window_start, window_end = EXCLUDED.window_end, n_scenes = EXCLUDED.n_scenes,
        ndvi_real = EXCLUDED.ndvi_real, ndmi_real = EXCLUDED.ndmi_real, bsi_real = EXCLUDED.bsi_real,
        sand_pct = EXCLUDED.sand_pct, clay_pct = EXCLUDED.clay_pct, silt_pct = EXCLUDED.silt_pct,
        ph_soilgrids = EXCLUDED.ph_soilgrids, soc_g_per_kg = EXCLUDED.soc_g_per_kg,
        texture_usda = EXCLUDED.texture_usda, image_path = EXCLUDED.image_path,
        image_url = EXCLUDED.image_url, fetched_at = NOW();
""")

SYNC_SOIL = text("""
    UPDATE soil SET
        ndvi_mean = COALESCE(CAST(:ndvi_real AS DOUBLE PRECISION), ndvi_mean),
        ph = COALESCE(CAST(:ph_soilgrids AS DOUBLE PRECISION), ph),
        texture = COALESCE(CAST(:texture_usda AS VARCHAR), texture)
    WHERE farm_id = :farm_id;
""")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="process only N farms (for testing)")
    parser.add_argument("--sync-soil", action="store_true",
                        help="overwrite synthetic soil.ndvi_mean / ph / texture with the real values")
    args = parser.parse_args()

    init_gee()

    with engine.connect() as conn:
        init_table(conn)
        query = """
            SELECT f.farm_id, f.latitude, f.longitude, f.sowing_date
            FROM farms f LEFT JOIN satellite_data s ON s.farm_id = f.farm_id
            WHERE s.farm_id IS NULL ORDER BY f.farm_id
        """
        if args.limit:
            query += f" LIMIT {int(args.limit)}"
        farms = [dict(r) for r in conn.execute(text(query)).mappings().all()]

    print(f"{len(farms)} farms to process.")
    done = skipped = failed = 0

    for farm in tqdm(farms):
        try:
            row = process_farm(farm)
            if row is None:
                skipped += 1
                continue
            with engine.begin() as conn:  # commit per farm so a crash loses nothing
                conn.execute(UPSERT, row)
                if args.sync_soil:
                    conn.execute(SYNC_SOIL, row)
            done += 1
        except Exception as exc:  # keep going if one farm fails
            failed += 1
            print(f"\n{farm['farm_id']} failed: {exc}")
        time.sleep(0.5)  # be gentle with Earth Engine quotas

    print(f"Done: {done} saved, {skipped} had no clear scene, {failed} failed.")


if __name__ == "__main__":
    main()

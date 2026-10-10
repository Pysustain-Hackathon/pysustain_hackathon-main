"""
relocate_farms.py
-----------------
Your seed script scatters farms within ~5 km of each district's centre, and district centres are
usually the main city, so many farms land on buildings, roads or water.

This script uses the ESA WorldCover land-cover map (via Google Earth Engine) to:
  1. Measure how much of a ~600 m square around every farm is cropland.
  2. For farms below a cropland cutoff, find a nearby random spot in the same district that IS cropland.
  3. (Only with --apply) update farms.latitude / farms.longitude for those farms, and delete their
     rows from satellite_data so satellite_ingest.py re-processes them at the new location.

By default it is a DRY RUN: it prints what it would do and changes nothing.

Usage (run AFTER satellite_ingest.py has finished, never at the same time):
  python relocate_farms.py                 # dry run, look at the numbers first
  python relocate_farms.py --apply         # actually move the farms
  python satellite_ingest.py               # then re-pull satellite data for the moved farms

Options: --min-crop 0.6   cropland fraction a farm must have (0 to 1)
         --radius-deg 0.25   how far from the district centre to search (~28 km per 0.25 degrees)

NOTE: not tested against Earth Engine from my environment. Try the dry run first.
"""
import os

os.environ["DISABLE_SQLALCHEMY_CEXT"] = "1"

import argparse
import random

import ee
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
GEE_PROJECT = os.getenv("GEE_PROJECT")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL not found! Check your .env file.")
if not GEE_PROJECT:
    raise ValueError("GEE_PROJECT not found! Add it to .env.")

engine = create_engine(
    DATABASE_URL,
    connect_args={"sslmode": "require", "prepare_threshold": None},
    pool_pre_ping=True,
)

# District centres, copied from your ingest_data.py
CENTRES = {
    "Ludhiana": (30.90, 75.85),
    "Karnal": (29.68, 76.99),
    "Nashik": (19.99, 73.78),
    "Mandya": (12.52, 76.89),
    "Bardhaman": (23.23, 87.86),
    "Guntur": (16.30, 80.44),
    "Jaipur": (26.91, 75.78),
    "Varanasi": (25.31, 82.97),
}

BUFFER_M = 300      # check a ~600 m square around each point
CANDIDATES = 300    # random candidate spots tried per district
CHUNK = 200         # points per Earth Engine request

random.seed(7)


def crop_fractions(points):
    """points = [(lon, lat), ...] -> fraction (0 to 1) of each square that is cropland (WorldCover class 40)."""
    wc = ee.ImageCollection("ESA/WorldCover/v200").first()
    crop = wc.select("Map").eq(40).rename("crop")
    results = []
    for start in range(0, len(points), CHUNK):
        chunk = points[start:start + CHUNK]
        feats = [
            ee.Feature(ee.Geometry.Point([lon, lat]).buffer(BUFFER_M).bounds(), {"i": i})
            for i, (lon, lat) in enumerate(chunk)
        ]
        out = crop.reduceRegions(
            collection=ee.FeatureCollection(feats), reducer=ee.Reducer.mean(), scale=10
        ).getInfo()
        part = [None] * len(chunk)
        for f in out["features"]:
            part[f["properties"]["i"]] = f["properties"].get("mean")
        results.extend(part)
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="write changes (default is a dry run)")
    parser.add_argument("--min-crop", type=float, default=0.6)
    parser.add_argument("--radius-deg", type=float, default=0.25)
    args = parser.parse_args()

    ee.Initialize(project=GEE_PROJECT)

    with engine.connect() as conn:
        farms = [dict(r) for r in conn.execute(text(
            "SELECT farm_id, latitude, longitude, district FROM farms ORDER BY farm_id"
        )).mappings().all()]
    print(f"{len(farms)} farms loaded.")

    fracs = crop_fractions([(f["longitude"], f["latitude"]) for f in farms])
    low = [f for f, fr in zip(farms, fracs) if fr is None or fr < args.min_crop]
    print(f"{len(low)} farms have under {args.min_crop:.0%} cropland and need moving.")

    moves = []   # (farm_id, new_lat, new_lon)
    unmoved = 0
    for district in sorted({f["district"] for f in low}):
        centre = CENTRES.get(district)
        group = [f for f in low if f["district"] == district]
        if centre is None:
            print(f"  {district}: no centre known, skipping {len(group)} farms")
            unmoved += len(group)
            continue
        lat0, lon0 = centre
        cands = [
            (lon0 + random.uniform(-args.radius_deg, args.radius_deg),
             lat0 + random.uniform(-args.radius_deg, args.radius_deg))
            for _ in range(CANDIDATES)
        ]
        cfr = crop_fractions(cands)
        good = [c for c, fr in zip(cands, cfr) if fr is not None and fr >= args.min_crop]
        random.shuffle(good)
        print(f"  {district}: {len(good)} cropland spots found for {len(group)} farms")
        for farm in group:
            if good:
                lon, lat = good.pop()
                moves.append((farm["farm_id"], round(lat, 5), round(lon, 5)))
            else:
                unmoved += 1

    print(f"\nWould move {len(moves)} farms. {unmoved} could not be moved (not enough cropland spots found).")

    if not args.apply:
        print("Dry run only. Nothing was changed. Re-run with --apply to write the changes.")
        return

    with engine.begin() as conn:
        for farm_id, lat, lon in moves:
            conn.execute(
                text("UPDATE farms SET latitude = :lat, longitude = :lon WHERE farm_id = :id"),
                {"lat": lat, "lon": lon, "id": farm_id},
            )
        ids = [m[0] for m in moves]
        if ids:
            conn.execute(text("DELETE FROM satellite_data WHERE farm_id = ANY(:ids)"), {"ids": ids})
    print(f"Moved {len(moves)} farms and cleared their satellite rows. Now run: python satellite_ingest.py")


if __name__ == "__main__":
    main()

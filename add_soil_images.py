"""
add_soil_images.py
------------------
Creates a `soil_types` table in Supabase with one row per soil type found in your `soil.soil_group`
column (Alluvial, Black, Red, ...; change the column with SOIL_TYPE_COLUMN in .env), uploads one photo per soil type to Supabase Storage, and saves each photo's URL in the table.

How the photos are found:
  Put your photos in a folder called  soil_images/  next to this script. Name each file after the soil
  type, in lowercase with underscores:

      Alluvial           ->  soil_images/alluvial.jpg
      Black              ->  soil_images/black.jpg
      Laterite           ->  soil_images/laterite.png        (.jpg works)

  The script prints which soil types still have no photo, so you can add them and run it again.

.env needs (in addition to DATABASE_URL):
  SUPABASE_URL=https://YOUR-PROJECT-REF.supabase.co
  SUPABASE_SERVICE_KEY=your-service-role-key      (Project Settings > API. Keep it secret.)
  SUPABASE_SOIL_BUCKET=soil-images                (optional, this is the default)

Usage:
  python add_soil_images.py

Safe to re-run: existing rows are kept, photos are overwritten, and your descriptions are not touched.
NOTE: I could not test the upload against Supabase from my environment, so check the table afterwards.
"""
import os

os.environ["DISABLE_SQLALCHEMY_CEXT"] = "1"

import io
import re
from pathlib import Path

import requests
from dotenv import load_dotenv
from PIL import Image
from sqlalchemy import create_engine, text

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
SUPABASE_URL = (os.getenv("SUPABASE_URL") or "").rstrip("/")
SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
BUCKET = os.getenv("SUPABASE_SOIL_BUCKET", "soil-images")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL not found! Check your .env file.")
if not (SUPABASE_URL and SERVICE_KEY):
    raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env to upload images.")

engine = create_engine(
    DATABASE_URL,
    connect_args={"sslmode": "require", "prepare_threshold": None},
    pool_pre_ping=True,
)

# Which column of the `soil` table holds the soil type names, and extra cards to create even if no farm uses them.
SOIL_COLUMN = os.getenv("SOIL_TYPE_COLUMN", "soil_group")
if not re.fullmatch(r"[a-z_]+", SOIL_COLUMN):
    raise ValueError("SOIL_TYPE_COLUMN may only contain lowercase letters and underscores.")
EXTRA_SOIL_TYPES = ["Clay", "Laterite"]

IMAGE_DIR = Path("soil_images")
IMAGE_DIR.mkdir(exist_ok=True)
EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp"]
MAX_SIDE = 900  # photos are shrunk so they load fast in the app

# Short starter descriptions. Edit them, ideally with your local agriculture officer.
SOIL_INFO = {
    "Alluvial": ("Soft, fine soil deposited by rivers. Usually light grey to brown and fertile. Common in river plains.", "Feels smooth and soft. Holds together lightly when squeezed, with a short to medium ribbon."),
    "Black": ("Dark, heavy soil (regur, black cotton). Swells when wet and cracks deeply when dry. Holds water well.", "Very sticky when wet. Long ribbon. Hard clods and wide cracks when dry."),
    "Red": ("Reddish or brown soil coloured by iron. Usually lighter and drains well, with lower fertility.", "Crumbly and loose. Breaks apart easily. Short ribbon or none."),
    "Clay": ("Fine, heavy, sticky soil. Holds water but drains slowly.", "Forms a long, smooth ribbon when wet. Hard clods when dry."),
    "Laterite": ("Reddish-brown, often gravelly and acidic soil found in high-rainfall areas. Drains fast and is low in nutrients.", "Gritty or gravelly. Does not hold together well."),
    "Sandy": ("Loose and gritty. Water drains very fast.", "Squeezed in the hand it falls apart. No ribbon forms."),
    "Sandy Loam": ("Soft and slightly gritty. Drains well.", "Holds together briefly when squeezed. A very short, weak ribbon."),
    "Loam": ("Soft, crumbly and balanced. Holds moisture and drains.", "Holds its shape when squeezed. A short ribbon forms."),
    "Sandy Clay Loam": ("Gritty but sticky when wet.", "Forms a medium ribbon but feels gritty."),
    "Clay Loam": ("Smooth and sticky when wet. Holds water well.", "Forms a medium to long ribbon. Feels smooth."),
    "Black Cotton Soil": ("Dark, heavy clay. Swells when wet and cracks deeply when dry. Holds water well.", "Very sticky when wet. Long ribbon. Hard clods and cracks when dry."),
    "Heavy Clay": ("Very sticky when wet, hard when dry. Drains slowly.", "Forms a long, smooth ribbon. Hard clods when dry."),
}

# Fill in who took or owns each photo (Soil type -> credit/licence text). Important if photos are not your own.
CREDITS = {}


def slug(name):
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def find_image(soil_type):
    for ext in EXTENSIONS:
        p = IMAGE_DIR / f"{slug(soil_type)}{ext}"
        if p.exists():
            return p
    return None


def prepare_jpeg(path):
    """Open any supported image, shrink it and return JPEG bytes."""
    with Image.open(path) as im:
        im = im.convert("RGB")
        im.thumbnail((MAX_SIDE, MAX_SIDE))
        buf = io.BytesIO()
        im.save(buf, format="JPEG", quality=85)
        return buf.getvalue()


def storage_headers(content_type=None):
    h = {"Authorization": f"Bearer {SERVICE_KEY}", "apikey": SERVICE_KEY}
    if content_type:
        h["Content-Type"] = content_type
    return h


def ensure_bucket():
    """Create a public bucket if it does not exist yet. An 'already exists' reply is fine."""
    resp = requests.post(
        f"{SUPABASE_URL}/storage/v1/bucket",
        headers=storage_headers("application/json"),
        json={"id": BUCKET, "name": BUCKET, "public": True},
        timeout=30,
    )
    if resp.status_code < 300:
        print(f"Created public bucket '{BUCKET}'.")
    else:
        print(f"Bucket '{BUCKET}': {resp.status_code} (usually means it already exists).")


def upload(soil_type, jpeg_bytes):
    remote = f"{slug(soil_type)}.jpg"
    resp = requests.post(
        f"{SUPABASE_URL}/storage/v1/object/{BUCKET}/{remote}",
        headers={**storage_headers("image/jpeg"), "x-upsert": "true"},
        data=jpeg_bytes,
        timeout=90,
    )
    if resp.status_code >= 300:
        raise RuntimeError(f"upload failed ({resp.status_code}): {resp.text[:150]}")
    return f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET}/{remote}"


def main():
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS soil_types (
                soil_type VARCHAR(50) PRIMARY KEY,
                description TEXT,
                hand_test TEXT,
                image_path TEXT,
                image_url TEXT,
                image_credit TEXT
            );
        """))
        types = [r[0] for r in conn.execute(text(
            f"SELECT DISTINCT {SOIL_COLUMN} FROM soil WHERE {SOIL_COLUMN} IS NOT NULL ORDER BY {SOIL_COLUMN}"
        )).all()]
        types = sorted(set(types) | set(EXTRA_SOIL_TYPES))
        for t in types:
            desc, hand = SOIL_INFO.get(t, (None, None))
            conn.execute(text("""
                INSERT INTO soil_types (soil_type, description, hand_test)
                VALUES (:t, :d, :h) ON CONFLICT (soil_type) DO NOTHING
            """), {"t": t, "d": desc, "h": hand})
    print(f"{len(types)} soil types (from the soil table plus extras): {', '.join(types)}")

    ensure_bucket()

    missing, done = [], 0
    for t in types:
        path = find_image(t)
        if path is None:
            missing.append(t)
            continue
        try:
            url = upload(t, prepare_jpeg(path))
        except Exception as exc:
            print(f"  {t}: {exc}")
            missing.append(t)
            continue
        with engine.begin() as conn:
            conn.execute(text("""
                UPDATE soil_types SET image_path = :p, image_url = :u,
                    image_credit = COALESCE(:c, image_credit)
                WHERE soil_type = :t
            """), {"p": str(path), "u": url, "c": CREDITS.get(t), "t": t})
        done += 1
        print(f"  {t}: uploaded -> {url}")

    print(f"\nDone: {done} photos uploaded.")
    if missing:
        print("No photo yet for: " + ", ".join(f"{m} (expected {slug(m)}.jpg)" for m in missing))
        print(f"Add them to the '{IMAGE_DIR}' folder and run the script again.")


if __name__ == "__main__":
    main()

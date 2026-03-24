"""
Convert local gallery images to base64 data URIs and store in MongoDB.
This way photos are served directly from the database — no static file hosting needed.
"""

import os
import sys
import io
import base64
from pathlib import Path
from dotenv import load_dotenv
from pymongo import MongoClient

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
load_dotenv()

MONGO_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
GALLERY_DIR = Path(__file__).parent / "static" / "gallery"

# Map folder slug -> actress name in DB
SLUG_TO_NAME = {
    "kim-ji-won": "Kim Ji-won",
    "jun-ji-hyun": "Jun Ji-hyun",
    "song-hye-kyo": "Song Hye-kyo",
    "park-shin-hye": "Park Shin-hye",
    "bae-suzy": "Bae Suzy",
    "iu": "IU (Lee Ji-eun)",
    "kim-so-hyun": "Kim So-hyun",
    "moon-ga-young": "Moon Ga-young",
    "han-so-hee": "Han So-hee",
    "kim-yoo-jung": "Kim Yoo-jung",
    "shin-min-a": "Shin Min-a",
    "son-ye-jin": "Son Ye-jin",
    "kim-tae-ri": "Kim Tae-ri",
    "jeon-yeo-been": "Jeon Yeo-been",
    "lim-ji-yeon": "Lim Ji-yeon",
    "go-min-si": "Go Min-si",
    "park-bo-young": "Park Bo-young",
    "seo-ye-ji": "Seo Ye-ji",
    "nam-ji-hyun": "Nam Ji-hyun",
    "kim-se-jeong": "Kim Se-jeong",
    "park-min-young": "Park Min-young",
    "shin-hye-sun": "Shin Hye-sun",
    "kim-go-eun": "Kim Go-eun",
    "lee-sung-kyung": "Lee Sung-kyung",
    "jung-so-min": "Jung So-min",
    "chun-woo-hee": "Chun Woo-hee",
    "lee-se-young": "Lee Se-young",
    "moon-chae-won": "Moon Chae-won",
    "kim-da-mi": "Kim Da-mi",
    "hwang-jung-eum": "Hwang Jung-eum",
    "kim-hye-yoon": "Kim Hye-yoon",
    "lee-bo-young": "Lee Bo-young",
    "gong-hyo-jin": "Gong Hyo-jin",
    "ha-ji-won": "Ha Ji-won",
    "jang-na-ra": "Jang Na-ra",
    "seo-hyun-jin": "Seo Hyun-jin",
}

MIME_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


def image_to_data_uri(filepath: Path) -> str:
    """Convert an image file to a base64 data URI."""
    ext = filepath.suffix.lower()
    mime = MIME_TYPES.get(ext, "image/jpeg")
    with open(filepath, "rb") as f:
        data = base64.b64encode(f.read()).decode("ascii")
    return f"data:{mime};base64,{data}"


def main():
    mongo = MongoClient(MONGO_URI)
    db = mongo["kdrama_ranking"]
    col = db["actresses"]

    if not GALLERY_DIR.exists():
        print(f"Gallery directory not found: {GALLERY_DIR}")
        return

    for slug_dir in sorted(GALLERY_DIR.iterdir()):
        if not slug_dir.is_dir():
            continue
        slug = slug_dir.name
        name = SLUG_TO_NAME.get(slug)
        if not name:
            print(f"  SKIP {slug} - no name mapping")
            continue

        # Convert images to data URIs
        gallery = []
        for img_file in sorted(slug_dir.iterdir()):
            if img_file.suffix.lower() in MIME_TYPES:
                data_uri = image_to_data_uri(img_file)
                gallery.append(data_uri)

        # Update MongoDB
        result = col.update_one({"name": name}, {"$set": {"gallery": gallery}})
        status = "updated" if result.modified_count else "no change"
        print(f"  {name}: {len(gallery)} photos ({status})")

    # Summary
    print("\n" + "=" * 50)
    all_docs = list(col.find({}, {"name": 1, "gallery": 1}))
    for doc in all_docs:
        g = doc.get("gallery", [])
        count = len(g)
        is_b64 = g[0].startswith("data:") if g else False
        print(f"  {doc['name']}: {count} photos {'(base64)' if is_b64 else '(urls)'}")

    mongo.close()


if __name__ == "__main__":
    main()

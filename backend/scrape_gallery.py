"""
Download portrait photos for all 36 actresses using Bing Image Search (via icrawler).
Saves to static/gallery/<slug>/ and updates MongoDB gallery URLs.
"""

import os
import sys
import io
import shutil
from pathlib import Path
from PIL import Image
from icrawler.builtin import BingImageCrawler
from pymongo import MongoClient

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

MONGO_URI = "mongodb+srv://canhtoan0411_db_user:oonHHJmqe9Boivut@kdrama-actresses.fyyflro.mongodb.net/?appName=kdrama-actresses"
GALLERY_DIR = Path(__file__).parent / "static" / "gallery"
TARGET = 10
MIN_FILE_SIZE = 15_000   # 15KB minimum
MIN_WIDTH = 200
MIN_HEIGHT = 250

# Backend URL where static files will be served
# Will be set to the actual deployed URL later
BASE_URL = "/static/gallery"

# All 36 actresses with search keywords and folder slugs
ACTRESSES = [
    {"name": "Kim Ji-won", "slug": "kim-ji-won", "search": "Kim Ji-won Korean actress"},
    {"name": "Jun Ji-hyun", "slug": "jun-ji-hyun", "search": "Jun Ji-hyun Gianna actress"},
    {"name": "Song Hye-kyo", "slug": "song-hye-kyo", "search": "Song Hye-kyo Korean actress"},
    {"name": "Park Shin-hye", "slug": "park-shin-hye", "search": "Park Shin-hye Korean actress"},
    {"name": "Bae Suzy", "slug": "bae-suzy", "search": "Bae Suzy Korean actress"},
    {"name": "IU (Lee Ji-eun)", "slug": "iu", "search": "IU Lee Ji-eun Korean singer actress"},
    {"name": "Kim So-hyun", "slug": "kim-so-hyun", "search": "Kim So-hyun Korean actress"},
    {"name": "Moon Ga-young", "slug": "moon-ga-young", "search": "Moon Ga-young Korean actress"},
    {"name": "Han So-hee", "slug": "han-so-hee", "search": "Han So-hee Korean actress"},
    {"name": "Kim Yoo-jung", "slug": "kim-yoo-jung", "search": "Kim Yoo-jung Korean actress"},
    {"name": "Shin Min-a", "slug": "shin-min-a", "search": "Shin Min-a Korean actress"},
    {"name": "Son Ye-jin", "slug": "son-ye-jin", "search": "Son Ye-jin Korean actress"},
    {"name": "Kim Tae-ri", "slug": "kim-tae-ri", "search": "Kim Tae-ri Korean actress"},
    {"name": "Jeon Yeo-been", "slug": "jeon-yeo-been", "search": "Jeon Yeo-been Korean actress"},
    {"name": "Lim Ji-yeon", "slug": "lim-ji-yeon", "search": "Lim Ji-yeon Korean actress"},
    {"name": "Go Min-si", "slug": "go-min-si", "search": "Go Min-si Korean actress"},
    {"name": "Park Bo-young", "slug": "park-bo-young", "search": "Park Bo-young Korean actress"},
    {"name": "Seo Ye-ji", "slug": "seo-ye-ji", "search": "Seo Ye-ji Korean actress"},
    {"name": "Nam Ji-hyun", "slug": "nam-ji-hyun", "search": "Nam Ji-hyun Korean actress 4minute"},
    {"name": "Kim Se-jeong", "slug": "kim-se-jeong", "search": "Kim Se-jeong Korean actress singer"},
    {"name": "Park Min-young", "slug": "park-min-young", "search": "Park Min-young Korean actress"},
    {"name": "Shin Hye-sun", "slug": "shin-hye-sun", "search": "Shin Hye-sun Korean actress"},
    {"name": "Kim Go-eun", "slug": "kim-go-eun", "search": "Kim Go-eun Korean actress"},
    {"name": "Lee Sung-kyung", "slug": "lee-sung-kyung", "search": "Lee Sung-kyung Korean actress model"},
    {"name": "Jung So-min", "slug": "jung-so-min", "search": "Jung So-min Korean actress"},
    {"name": "Chun Woo-hee", "slug": "chun-woo-hee", "search": "Chun Woo-hee Korean actress"},
    {"name": "Lee Se-young", "slug": "lee-se-young", "search": "Lee Se-young Korean actress"},
    {"name": "Moon Chae-won", "slug": "moon-chae-won", "search": "Moon Chae-won Korean actress"},
    {"name": "Kim Da-mi", "slug": "kim-da-mi", "search": "Kim Da-mi Korean actress"},
    {"name": "Hwang Jung-eum", "slug": "hwang-jung-eum", "search": "Hwang Jung-eum Korean actress"},
    {"name": "Kim Hye-yoon", "slug": "kim-hye-yoon", "search": "Kim Hye-yoon Korean actress"},
    {"name": "Lee Bo-young", "slug": "lee-bo-young", "search": "Lee Bo-young Korean actress"},
    {"name": "Gong Hyo-jin", "slug": "gong-hyo-jin", "search": "Gong Hyo-jin Korean actress"},
    {"name": "Ha Ji-won", "slug": "ha-ji-won", "search": "Ha Ji-won Korean actress"},
    {"name": "Jang Na-ra", "slug": "jang-na-ra", "search": "Jang Na-ra Korean actress singer"},
    {"name": "Seo Hyun-jin", "slug": "seo-hyun-jin", "search": "Seo Hyun-jin Korean actress"},
]


def is_valid_image(filepath: str) -> bool:
    """Check if image is large enough and is a real photo."""
    try:
        size = os.path.getsize(filepath)
        if size < MIN_FILE_SIZE:
            return False
        with Image.open(filepath) as img:
            w, h = img.size
            if w < MIN_WIDTH or h < MIN_HEIGHT:
                return False
        return True
    except Exception:
        return False


def download_photos(actress: dict) -> list[str]:
    """Download portrait photos for one actress. Returns list of valid filenames."""
    slug = actress["slug"]
    search = actress["search"]
    out_dir = GALLERY_DIR / slug
    temp_dir = GALLERY_DIR / f"_temp_{slug}"

    # Download to temp dir first
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir(parents=True, exist_ok=True)

    # Download more than needed to account for filtering
    crawler = BingImageCrawler(
        storage={"root_dir": str(temp_dir)},
        log_level=40,  # ERROR only
    )
    crawler.crawl(
        keyword=search,
        max_num=20,
        filters={"type": "photo", "size": "large"},
    )

    # Filter valid images
    valid_files = []
    for f in sorted(os.listdir(temp_dir)):
        filepath = temp_dir / f
        if is_valid_image(str(filepath)):
            valid_files.append(f)
        if len(valid_files) >= TARGET:
            break

    # Move valid files to final directory
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    final_files = []
    for i, f in enumerate(valid_files, 1):
        ext = Path(f).suffix or ".jpg"
        new_name = f"{i:02d}{ext}"
        shutil.move(str(temp_dir / f), str(out_dir / new_name))
        final_files.append(new_name)

    # Cleanup temp
    shutil.rmtree(temp_dir, ignore_errors=True)

    return final_files


def main():
    GALLERY_DIR.mkdir(parents=True, exist_ok=True)

    mongo = MongoClient(MONGO_URI)
    db = mongo["kdrama_ranking"]
    col = db["actresses"]

    results = []

    for actress in ACTRESSES:
        name = actress["name"]
        slug = actress["slug"]
        print(f"\n  {name}...", end=" ", flush=True)

        files = download_photos(actress)
        print(f"{len(files)} photos")

        # Build gallery URLs (relative paths served by FastAPI)
        gallery_urls = [f"{BASE_URL}/{slug}/{f}" for f in files]

        # Update MongoDB
        col.update_one(
            {"name": name},
            {"$set": {"gallery": gallery_urls}},
        )

        results.append((name, len(files)))

    # Summary
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    short = [(name, count) for name, count in results if count < TARGET]
    ok = [(name, count) for name, count in results if count >= TARGET]
    print(f"  OK: {len(ok)}/{len(results)} actresses have {TARGET}+ photos")
    if short:
        print(f"\n  Short:")
        for name, count in short:
            print(f"    {name}: {count}/{TARGET}")

    mongo.close()


if __name__ == "__main__":
    main()

"""
Re-scrape all 36 actresses with 'kdrama actress' in search query
to reduce wrong-person matches. Deduplicates by content hash.
Uploads to Cloudinary and stores URLs in MongoDB.
"""

import os
import sys
import io
import shutil
import hashlib
from pathlib import Path
from PIL import Image
from icrawler.builtin import BingImageCrawler
from dotenv import load_dotenv
from pymongo import MongoClient
import cloudinary
import cloudinary.uploader

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
load_dotenv()

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True,
)

MONGO_URI = os.getenv("MONGODB_URI")
GALLERY_DIR = Path(__file__).parent / "static" / "gallery"
TARGET = 10
MIN_SIZE = 15_000
MIN_W = 200
MIN_H = 250

ACTRESSES = [
    {"name": "Kim Ji-won", "slug": "kim-ji-won", "search": "Kim Ji-won kdrama actress"},
    {"name": "Jun Ji-hyun", "slug": "jun-ji-hyun", "search": "Jun Ji-hyun Gianna kdrama actress"},
    {"name": "Song Hye-kyo", "slug": "song-hye-kyo", "search": "Song Hye-kyo kdrama actress"},
    {"name": "Park Shin-hye", "slug": "park-shin-hye", "search": "Park Shin-hye kdrama actress"},
    {"name": "Bae Suzy", "slug": "bae-suzy", "search": "Bae Suzy kdrama actress"},
    {"name": "IU (Lee Ji-eun)", "slug": "iu", "search": "IU Lee Ji-eun kdrama actress singer"},
    {"name": "Kim So-hyun", "slug": "kim-so-hyun", "search": "Kim So-hyun kdrama actress"},
    {"name": "Moon Ga-young", "slug": "moon-ga-young", "search": "Moon Ga-young kdrama actress"},
    {"name": "Han So-hee", "slug": "han-so-hee", "search": "Han So-hee kdrama actress"},
    {"name": "Kim Yoo-jung", "slug": "kim-yoo-jung", "search": "Kim Yoo-jung kdrama actress"},
    {"name": "Shin Min-a", "slug": "shin-min-a", "search": "Shin Min-a kdrama actress"},
    {"name": "Son Ye-jin", "slug": "son-ye-jin", "search": "Son Ye-jin kdrama actress"},
    {"name": "Kim Tae-ri", "slug": "kim-tae-ri", "search": "Kim Tae-ri kdrama actress"},
    {"name": "Jeon Yeo-been", "slug": "jeon-yeo-been", "search": "Jeon Yeo-been kdrama actress"},
    {"name": "Lim Ji-yeon", "slug": "lim-ji-yeon", "search": "Lim Ji-yeon kdrama actress"},
    {"name": "Go Min-si", "slug": "go-min-si", "search": "Go Min-si kdrama actress"},
    {"name": "Park Bo-young", "slug": "park-bo-young", "search": "Park Bo-young kdrama actress"},
    {"name": "Seo Ye-ji", "slug": "seo-ye-ji", "search": "Seo Ye-ji kdrama actress"},
    {"name": "Nam Ji-hyun", "slug": "nam-ji-hyun", "search": "Nam Ji-hyun kdrama actress"},
    {"name": "Kim Se-jeong", "slug": "kim-se-jeong", "search": "Kim Se-jeong kdrama actress"},
    {"name": "Park Min-young", "slug": "park-min-young", "search": "Park Min-young kdrama actress"},
    {"name": "Shin Hye-sun", "slug": "shin-hye-sun", "search": "Shin Hye-sun kdrama actress"},
    {"name": "Kim Go-eun", "slug": "kim-go-eun", "search": "Kim Go-eun kdrama actress"},
    {"name": "Lee Sung-kyung", "slug": "lee-sung-kyung", "search": "Lee Sung-kyung kdrama actress model"},
    {"name": "Jung So-min", "slug": "jung-so-min", "search": "Jung So-min kdrama actress"},
    {"name": "Chun Woo-hee", "slug": "chun-woo-hee", "search": "Chun Woo-hee kdrama actress"},
    {"name": "Lee Se-young", "slug": "lee-se-young", "search": "Lee Se-young kdrama actress"},
    {"name": "Moon Chae-won", "slug": "moon-chae-won", "search": "Moon Chae-won kdrama actress"},
    {"name": "Kim Da-mi", "slug": "kim-da-mi", "search": "Kim Da-mi kdrama actress"},
    {"name": "Hwang Jung-eum", "slug": "hwang-jung-eum", "search": "Hwang Jung-eum kdrama actress"},
    {"name": "Kim Hye-yoon", "slug": "kim-hye-yoon", "search": "Kim Hye-yoon kdrama actress"},
    {"name": "Lee Bo-young", "slug": "lee-bo-young", "search": "Lee Bo-young kdrama actress"},
    {"name": "Gong Hyo-jin", "slug": "gong-hyo-jin", "search": "Gong Hyo-jin kdrama actress"},
    {"name": "Ha Ji-won", "slug": "ha-ji-won", "search": "Ha Ji-won kdrama actress"},
    {"name": "Jang Na-ra", "slug": "jang-na-ra", "search": "Jang Na-ra kdrama actress singer"},
    {"name": "Seo Hyun-jin", "slug": "seo-hyun-jin", "search": "Seo Hyun-jin kdrama actress"},
]


def file_hash(path):
    with open(path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


def is_valid(path):
    try:
        if os.path.getsize(path) < MIN_SIZE:
            return False
        with Image.open(path) as img:
            w, h = img.size
            return w >= MIN_W and h >= MIN_H
    except:
        return False


def upload_to_cloudinary(filepath, slug, index):
    result = cloudinary.uploader.upload(
        str(filepath),
        folder=f"kdrama-gallery/{slug}",
        public_id=f"{index:02d}",
        overwrite=True,
        resource_type="image",
        transformation=[{"quality": "auto", "fetch_format": "auto"}],
    )
    return result["secure_url"]


def process_actress(actress):
    slug = actress["slug"]
    name = actress["name"]
    search = actress["search"]
    temp_dir = GALLERY_DIR / f"_temp_{slug}"

    # Download fresh
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir(parents=True, exist_ok=True)

    crawler = BingImageCrawler(storage={"root_dir": str(temp_dir)}, log_level=40)
    crawler.crawl(keyword=search, max_num=25, filters={"type": "photo", "size": "large"})

    # Collect valid, unique photos
    seen = set()
    valid = []
    for f in sorted(os.listdir(temp_dir)):
        fp = temp_dir / f
        if not is_valid(str(fp)):
            continue
        h = file_hash(fp)
        if h in seen:
            continue
        seen.add(h)
        valid.append(fp)
        if len(valid) >= TARGET:
            break

    # Upload to Cloudinary
    urls = []
    for i, fp in enumerate(valid, 1):
        try:
            url = upload_to_cloudinary(fp, slug, i)
            urls.append(url)
        except Exception as e:
            print(f"\n    FAILED photo {i}: {e}", end="")

    shutil.rmtree(temp_dir, ignore_errors=True)
    return name, urls


def main():
    mongo = MongoClient(MONGO_URI)
    col = mongo["kdrama_ranking"]["actresses"]

    short = []
    for actress in ACTRESSES:
        print(f"  {actress['name']}...", end=" ", flush=True)
        name, gallery = process_actress(actress)
        col.update_one({"name": name}, {"$set": {"gallery": gallery}})
        print(f"{len(gallery)} unique photos")
        if len(gallery) < TARGET:
            short.append((name, len(gallery)))

    print("\n" + "=" * 50)
    if short:
        print(f"{len(short)} short:")
        for n, c in short:
            print(f"  {n}: {c}/{TARGET}")
    else:
        print(f"All {len(ACTRESSES)} actresses have {TARGET} unique photos!")
    mongo.close()


if __name__ == "__main__":
    main()

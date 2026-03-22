"""Fetch actress profile photos from TMDB and store in gallery."""
import urllib.request
import urllib.parse
import json
import time
from database import actresses_collection

TMDB_API_KEY = "017bbf31bbe1016f0dca8bdd9be21ba4"
TMDB_IMG_BASE = "https://image.tmdb.org/t/p/w500"
PHOTOS_PER_ACTRESS = 10


def tmdb_get(path: str, params: dict) -> dict:
    params["api_key"] = TMDB_API_KEY
    url = f"https://api.themoviedb.org/3{path}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def find_person_id(name: str) -> int | None:
    """Search TMDB for a Korean actress and return their person ID."""
    data = tmdb_get("/search/person", {"query": name, "language": "en-US"})
    for p in data.get("results", []):
        if p.get("known_for_department") != "Acting":
            continue
        # Prefer someone with Korean credits
        for kf in p.get("known_for", []):
            if kf.get("original_language") == "ko":
                return p["id"]
        # Fallback: first actor result
        return p["id"]
    return None


def fetch_person_images(person_id: int) -> list[str]:
    """Fetch profile images for a person from TMDB."""
    data = tmdb_get(f"/person/{person_id}/images", {})
    profiles = data.get("profiles", [])
    # Sort by vote_average descending for best quality
    profiles.sort(key=lambda p: p.get("vote_average", 0), reverse=True)
    urls = []
    for p in profiles:
        path = p.get("file_path")
        if path:
            urls.append(f"{TMDB_IMG_BASE}{path}")
        if len(urls) >= PHOTOS_PER_ACTRESS:
            break
    return urls


def fetch_all():
    """Fetch gallery photos for all actresses."""
    actresses = list(actresses_collection.find({}))
    print(f"Processing {len(actresses)} actresses...")

    updated = 0
    cache = {}

    for i, doc in enumerate(actresses):
        name = doc["name"]
        existing = doc.get("gallery", [])
        # Filter out any drama poster URLs from existing gallery
        if len(existing) >= PHOTOS_PER_ACTRESS:
            print(f"  [{i+1}/{len(actresses)}] {name} — already has {len(existing)} photos, skipping")
            continue

        print(f"  [{i+1}/{len(actresses)}] {name}...", end=" ", flush=True)

        if name in cache:
            person_id = cache[name]
        else:
            person_id = find_person_id(name)
            cache[name] = person_id
            time.sleep(0.25)

        if not person_id:
            print("not found on TMDB")
            continue

        images = fetch_person_images(person_id)
        time.sleep(0.25)

        if not images:
            print("no images found")
            continue

        actresses_collection.update_one(
            {"_id": doc["_id"]},
            {"$set": {"gallery": images}},
        )
        updated += 1
        print(f"{len(images)} photos")

    print(f"\nUpdated galleries for {updated}/{len(actresses)} actresses.")


if __name__ == "__main__":
    fetch_all()

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


def fetch_person_images(person_id: int, name: str) -> list[str]:
    """Fetch profile + tagged images for a person from TMDB and Wikipedia."""
    urls: list[str] = []
    seen: set[str] = set()

    def add(url: str):
        if url not in seen and len(urls) < PHOTOS_PER_ACTRESS:
            seen.add(url)
            urls.append(url)

    # TMDB profiles
    try:
        data = tmdb_get(f"/person/{person_id}/images", {})
        profiles = data.get("profiles", [])
        profiles.sort(key=lambda p: p.get("vote_average", 0), reverse=True)
        for p in profiles:
            if p.get("file_path"):
                add(f"{TMDB_IMG_BASE}{p['file_path']}")
    except Exception:
        pass

    # TMDB tagged images (stills, not posters)
    if len(urls) < PHOTOS_PER_ACTRESS:
        try:
            tagged = tmdb_get(f"/person/{person_id}/tagged_images", {"page": 1})
            stills = [t for t in tagged.get("results", [])
                      if t.get("media_type") == "tv" and t.get("image_type") == "backdrop"
                      and t.get("file_path")]
            stills.sort(key=lambda t: t.get("vote_average", 0), reverse=True)
            for t in stills:
                add(f"{TMDB_IMG_BASE}{t['file_path']}")
        except Exception:
            pass

    # Wikipedia
    if len(urls) < PHOTOS_PER_ACTRESS:
        try:
            wiki_name = name.replace(" ", "_")
            wiki_url = f"https://en.wikipedia.org/api/rest_v1/page/media-list/{urllib.parse.quote(wiki_name)}"
            req = urllib.request.Request(wiki_url, headers={
                "Accept": "application/json",
                "User-Agent": "KDramaRanking/1.0",
            })
            with urllib.request.urlopen(req, timeout=10) as resp:
                wiki_data = json.loads(resp.read())
            for item in wiki_data.get("items", []):
                src = item.get("srcset", [{}])[0].get("src", "") if item.get("srcset") else ""
                if not src:
                    src = item.get("original", {}).get("source", "")
                if not src:
                    continue
                if not src.startswith("http"):
                    src = "https:" + src
                lower = src.lower()
                if any(skip in lower for skip in [".svg", "icon", "logo", "flag", "commons-logo", "wiki"]):
                    continue
                add(src)
        except Exception:
            pass

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

        images = fetch_person_images(person_id, name)
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

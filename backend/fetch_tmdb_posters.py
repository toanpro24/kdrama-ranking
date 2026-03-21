"""Fetch drama poster images from TMDB and update the database."""
import urllib.request
import urllib.parse
import json
import time
from database import actresses_collection

TMDB_API_KEY = "017bbf31bbe1016f0dca8bdd9be21ba4"
TMDB_IMG_BASE = "https://image.tmdb.org/t/p/w500"


def search_drama(title: str, year: int | None = None) -> str | None:
    """Search TMDB for a Korean drama and return its poster URL."""
    params = urllib.parse.urlencode({
        "api_key": TMDB_API_KEY,
        "query": title,
        "language": "en-US",
    })
    url = f"https://api.themoviedb.org/3/search/tv?{params}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            results = data.get("results", [])
            # Prefer Korean dramas
            for r in results:
                lang = r.get("original_language", "")
                poster = r.get("poster_path")
                if lang == "ko" and poster:
                    return f"{TMDB_IMG_BASE}{poster}"
            # Fallback: any result with a poster
            for r in results:
                poster = r.get("poster_path")
                if poster:
                    return f"{TMDB_IMG_BASE}{poster}"
    except Exception as e:
        print(f"    error: {e}")
    return None


def search_movie(title: str) -> str | None:
    """Search TMDB movies (for films like Night in Paradise)."""
    params = urllib.parse.urlencode({
        "api_key": TMDB_API_KEY,
        "query": title,
        "language": "en-US",
    })
    url = f"https://api.themoviedb.org/3/search/movie?{params}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            results = data.get("results", [])
            for r in results:
                lang = r.get("original_language", "")
                poster = r.get("poster_path")
                if lang == "ko" and poster:
                    return f"{TMDB_IMG_BASE}{poster}"
            for r in results:
                poster = r.get("poster_path")
                if poster:
                    return f"{TMDB_IMG_BASE}{poster}"
    except Exception:
        pass
    return None


def fetch_all():
    """Fetch posters for all dramas from TMDB."""
    # Collect all unique dramas
    all_dramas: dict[str, int | None] = {}
    for doc in actresses_collection.find({}):
        for d in doc.get("dramas", []):
            t = d["title"]
            if t not in all_dramas:
                all_dramas[t] = d.get("year")

    print(f"Found {len(all_dramas)} unique dramas. Fetching from TMDB...")

    poster_map: dict[str, str] = {}
    not_found = []

    for i, (title, year) in enumerate(sorted(all_dramas.items())):
        print(f"  [{i+1}/{len(all_dramas)}] {title}...", end=" ", flush=True)
        img = search_drama(title, year)
        if not img:
            # Try as movie
            img = search_movie(title)
        if img:
            poster_map[title] = img
            print("OK")
        else:
            not_found.append(title)
            print("not found")
        time.sleep(0.25)  # TMDB rate limit: ~4 req/s

    print(f"\nFound posters for {len(poster_map)}/{len(all_dramas)} dramas.")
    if not_found:
        print(f"Missing: {', '.join(not_found)}")

    # Update each actress's dramas with poster URLs
    updated = 0
    for doc in actresses_collection.find({}):
        dramas = doc.get("dramas", [])
        changed = False
        for d in dramas:
            if d["title"] in poster_map:
                d["poster"] = poster_map[d["title"]]
                changed = True
        if changed:
            actresses_collection.update_one(
                {"_id": doc["_id"]},
                {"$set": {"dramas": dramas}},
            )
            updated += 1

    print(f"Updated dramas for {updated} actresses.")

    # Save cache
    with open("poster_cache.json", "w", encoding="utf-8") as f:
        json.dump(poster_map, f, ensure_ascii=False, indent=2)
    print("Saved poster cache to poster_cache.json")


if __name__ == "__main__":
    fetch_all()

"""Fetch drama poster images from Wikipedia and update the database."""
import urllib.request
import urllib.parse
import json
import time
from database import actresses_collection


def fetch_wiki_image(title: str) -> str | None:
    """Try to fetch the main image for a drama from Wikipedia."""
    # Try common Wikipedia article name patterns
    candidates = [
        f"{title} (TV series)",
        f"{title} (South Korean TV series)",
        title,
        f"{title} (drama)",
    ]
    for candidate in candidates:
        encoded = urllib.parse.quote(candidate.replace(" ", "_"))
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{encoded}"
        req = urllib.request.Request(url, headers={
            "User-Agent": "KDramaRanking/1.0 (educational project)",
            "Accept": "application/json",
        })
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
                thumb = data.get("thumbnail", {}).get("source")
                if thumb:
                    # Get a larger version (400px wide)
                    thumb = thumb.rsplit("/", 1)
                    if len(thumb) == 2:
                        return thumb[0] + "/400px-" + thumb[1].split("px-", 1)[-1]
                    return thumb[0]
        except Exception:
            continue
        time.sleep(0.1)  # Be nice to Wikipedia
    return None


def update_posters():
    """Fetch posters for all dramas and update the database."""
    # Collect all unique dramas
    all_dramas: dict[str, list[str]] = {}  # title -> [actress_ids]
    for doc in actresses_collection.find({}):
        for d in doc.get("dramas", []):
            t = d["title"]
            if t not in all_dramas:
                all_dramas[t] = []
            all_dramas[t].append(str(doc["_id"]))

    print(f"Found {len(all_dramas)} unique dramas. Fetching posters...")

    poster_map: dict[str, str] = {}
    for i, title in enumerate(sorted(all_dramas.keys())):
        print(f"  [{i+1}/{len(all_dramas)}] {title}...", end=" ", flush=True)
        img = fetch_wiki_image(title)
        if img:
            poster_map[title] = img
            print("OK")
        else:
            print("not found")
        time.sleep(0.2)  # Rate limiting

    print(f"\nFound posters for {len(poster_map)}/{len(all_dramas)} dramas.")

    # Update each actress's dramas with poster URLs
    updated = 0
    for doc in actresses_collection.find({}):
        dramas = doc.get("dramas", [])
        changed = False
        for d in dramas:
            if not d.get("poster") and d["title"] in poster_map:
                d["poster"] = poster_map[d["title"]]
                changed = True
        if changed:
            actresses_collection.update_one(
                {"_id": doc["_id"]},
                {"$set": {"dramas": dramas}},
            )
            updated += 1

    print(f"Updated dramas for {updated} actresses.")

    # Save the mapping for future use
    with open("poster_cache.json", "w", encoding="utf-8") as f:
        json.dump(poster_map, f, ensure_ascii=False, indent=2)
    print(f"Saved poster cache to poster_cache.json")


if __name__ == "__main__":
    update_posters()

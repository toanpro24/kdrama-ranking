"""Apply drama poster images to the database from cached poster data."""
import json
import os
from database import actresses_collection

POSTER_CACHE = os.path.join(os.path.dirname(__file__), "poster_cache.json")


def load_posters() -> dict[str, str]:
    """Load poster URL mapping from cache file."""
    if not os.path.exists(POSTER_CACHE):
        return {}
    with open(POSTER_CACHE, "r", encoding="utf-8") as f:
        return json.load(f)


def update():
    """Apply poster images to all dramas in the database."""
    poster_map = load_posters()
    if not poster_map:
        print("No poster cache found. Run fetch_posters.py first.")
        return

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

    print(f"Applied posters for {updated} actresses.")


if __name__ == "__main__":
    update()

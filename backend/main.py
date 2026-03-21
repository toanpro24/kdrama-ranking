from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from bson import ObjectId
from database import actresses_collection
from models import ActressCreate, ActressResponse, TierUpdate
from seed import seed
from drama_metadata import DRAMA_META

app = FastAPI(title="K-Drama Actress Ranking API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    if actresses_collection.count_documents({}) == 0:
        seed()


# ── GET all actresses ──
@app.get("/api/actresses")
def get_actresses(genre: str | None = None, search: str | None = None):
    query = {}
    if genre and genre != "All":
        query["genre"] = genre
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"known": {"$regex": search, "$options": "i"}},
        ]
    docs = list(actresses_collection.find(query))
    for d in docs:
        d["_id"] = str(d["_id"])
    return docs


# ── GET single actress ──
@app.get("/api/actresses/{actress_id}")
def get_actress(actress_id: str):
    doc = actresses_collection.find_one({"_id": actress_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Actress not found")
    doc["_id"] = str(doc["_id"])
    return doc


# ── POST create actress ──
@app.post("/api/actresses", status_code=201)
def create_actress(actress: ActressCreate):
    last = actresses_collection.find_one(sort=[("_id", -1)])
    next_id = str(int(last["_id"]) + 1) if last else "1"
    doc = {"_id": next_id, **actress.model_dump(), "tier": None}
    actresses_collection.insert_one(doc)
    doc["_id"] = str(doc["_id"])
    return doc


# ── PATCH update tier ──
@app.patch("/api/actresses/{actress_id}/tier")
def update_tier(actress_id: str, update: TierUpdate):
    result = actresses_collection.update_one(
        {"_id": actress_id},
        {"$set": {"tier": update.tier}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Actress not found")
    return {"id": actress_id, "tier": update.tier}


# ── PATCH bulk update tiers ──
@app.patch("/api/actresses/bulk-tier")
def bulk_update_tiers(updates: list[dict]):
    for u in updates:
        actresses_collection.update_one(
            {"_id": u["id"]},
            {"$set": {"tier": u.get("tier")}},
        )
    return {"updated": len(updates)}


# ── PATCH rate a drama ──
@app.patch("/api/actresses/{actress_id}/dramas/{drama_title}/rating")
def rate_drama(actress_id: str, drama_title: str, body: dict):
    import urllib.parse
    decoded = urllib.parse.unquote(drama_title)
    rating = body.get("rating")
    if rating is not None and (rating < 1 or rating > 10):
        raise HTTPException(status_code=400, detail="Rating must be 1-10")
    doc = actresses_collection.find_one({"_id": actress_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Actress not found")
    dramas = doc.get("dramas", [])
    found = False
    for d in dramas:
        if d["title"] == decoded:
            d["rating"] = rating
            found = True
            break
    if not found:
        raise HTTPException(status_code=404, detail="Drama not found")
    actresses_collection.update_one({"_id": actress_id}, {"$set": {"dramas": dramas}})
    return {"actressId": actress_id, "drama": decoded, "rating": rating}


# ── DELETE actress ──
@app.delete("/api/actresses/{actress_id}")
def delete_actress(actress_id: str):
    result = actresses_collection.delete_one({"_id": actress_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Actress not found")
    return {"deleted": actress_id}


# ── GET stats ──
@app.get("/api/stats")
def get_stats():
    pipeline = [
        {"$group": {"_id": "$genre", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    genre_counts = {doc["_id"]: doc["count"] for doc in actresses_collection.aggregate(pipeline)}

    tier_pipeline = [
        {"$match": {"tier": {"$ne": None}}},
        {"$group": {"_id": "$tier", "count": {"$sum": 1}}},
    ]
    tier_counts = {doc["_id"]: doc["count"] for doc in actresses_collection.aggregate(tier_pipeline)}

    total = actresses_collection.count_documents({})
    ranked = actresses_collection.count_documents({"tier": {"$ne": None}})

    return {
        "total": total,
        "ranked": ranked,
        "unranked": total - ranked,
        "genreCounts": genre_counts,
        "tierCounts": tier_counts,
    }


# ── GET drama detail by title ──
@app.get("/api/dramas/{title}")
def get_drama(title: str):
    """Aggregate drama info from all actresses who appeared in it."""
    import urllib.parse
    decoded = urllib.parse.unquote(title)
    cast = []
    drama_info = None
    for doc in actresses_collection.find({}):
        for d in doc.get("dramas", []):
            if d["title"] == decoded:
                cast.append({
                    "actressId": str(doc["_id"]),
                    "actressName": doc["name"],
                    "actressImage": doc.get("image"),
                    "role": d.get("role", ""),
                })
                if not drama_info:
                    drama_info = {
                        "title": d["title"],
                        "year": d["year"],
                        "poster": d.get("poster"),
                    }
    if not drama_info:
        raise HTTPException(status_code=404, detail="Drama not found")
    drama_info["cast"] = cast
    # Merge extra metadata if available
    meta = DRAMA_META.get(decoded, {})
    drama_info["network"] = meta.get("network")
    drama_info["episodes"] = meta.get("episodes")
    drama_info["runtime"] = meta.get("runtime")
    drama_info["genre"] = meta.get("genre")
    drama_info["synopsis"] = meta.get("synopsis")
    return drama_info


# ── GET search dramas ──
@app.get("/api/dramas")
def search_dramas():
    """Return all unique dramas across all actresses."""
    dramas = {}
    for doc in actresses_collection.find({}):
        for d in doc.get("dramas", []):
            t = d["title"]
            if t not in dramas:
                dramas[t] = {"title": t, "year": d["year"], "poster": d.get("poster"), "cast": []}
            dramas[t]["cast"].append({
                "actressId": str(doc["_id"]),
                "actressName": doc["name"],
                "role": d.get("role", ""),
            })
    return list(dramas.values())


# ── POST reset (re-seed) ──
@app.post("/api/reset")
def reset_data():
    seed()
    return {"message": "Data reset to defaults"}

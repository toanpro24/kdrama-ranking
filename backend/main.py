import os
import urllib.parse
from contextlib import asynccontextmanager

from bson import ObjectId
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from database import actresses_collection
from drama_metadata import DRAMA_META
from models import ActressCreate, TierUpdate
from seed import seed

load_dotenv()
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "")


def _require_admin(x_api_key: str = Header(default="")):
    """Dependency: reject if no ADMIN_API_KEY is set or key doesn't match."""
    if not ADMIN_API_KEY:
        return  # no key configured = open (dev mode)
    if x_api_key != ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid or missing API key")


# ── Helper: resolve actress ID (string → ObjectId) ──
def _oid(actress_id: str) -> ObjectId:
    try:
        return ObjectId(actress_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid actress ID")


# ── Helper: atomic drama field update (no read-modify-write race) ──
def _update_drama_field(actress_id: str, drama_title: str, field: str, value):
    decoded = urllib.parse.unquote(drama_title)
    result = actresses_collection.update_one(
        {"_id": _oid(actress_id), "dramas.title": decoded},
        {"$set": {f"dramas.$.{field}": value}},
    )
    if result.matched_count == 0:
        # Distinguish: actress not found vs drama not found
        if not actresses_collection.find_one({"_id": _oid(actress_id)}):
            raise HTTPException(status_code=404, detail="Actress not found")
        raise HTTPException(status_code=404, detail="Drama not found")
    return {"actressId": actress_id, "drama": decoded, field: value}


# ── Lifespan (replaces deprecated @app.on_event) ──
@asynccontextmanager
async def lifespan(app: FastAPI):
    if actresses_collection.count_documents({}) == 0:
        seed()
    yield


app = FastAPI(title="K-Drama Actress Ranking API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    doc = actresses_collection.find_one({"_id": _oid(actress_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Actress not found")
    doc["_id"] = str(doc["_id"])
    return doc


# ── POST create actress (ObjectId = concurrent-safe, no race condition) ──
@app.post("/api/actresses", status_code=201)
def create_actress(actress: ActressCreate):
    doc = {**actress.model_dump(), "tier": None}
    result = actresses_collection.insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    return doc


# ── PATCH update tier ──
@app.patch("/api/actresses/{actress_id}/tier")
def update_tier(actress_id: str, update: TierUpdate):
    result = actresses_collection.update_one(
        {"_id": _oid(actress_id)},
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
            {"_id": _oid(u["id"])},
            {"$set": {"tier": u.get("tier")}},
        )
    return {"updated": len(updates)}


# ── PATCH rate a drama (atomic — no read-modify-write) ──
@app.patch("/api/actresses/{actress_id}/dramas/{drama_title}/rating")
def rate_drama(actress_id: str, drama_title: str, body: dict):
    rating = body.get("rating")
    if rating is not None and (rating < 1 or rating > 10):
        raise HTTPException(status_code=400, detail="Rating must be 1-10")
    return _update_drama_field(actress_id, drama_title, "rating", rating)


# ── PATCH watchlist status (atomic — no read-modify-write) ──
@app.patch("/api/actresses/{actress_id}/dramas/{drama_title}/watch-status")
def update_watch_status(actress_id: str, drama_title: str, body: dict):
    status = body.get("watchStatus")
    valid = [None, "watched", "watching", "plan_to_watch", "dropped"]
    if status not in valid:
        raise HTTPException(status_code=400, detail=f"Status must be one of {valid}")
    return _update_drama_field(actress_id, drama_title, "watchStatus", status)


# ── DELETE actress (admin-protected) ──
@app.delete("/api/actresses/{actress_id}", dependencies=[Depends(_require_admin)])
def delete_actress(actress_id: str):
    result = actresses_collection.delete_one({"_id": _oid(actress_id)})
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


# ── GET drama detail (aggregation pipeline instead of full scan) ──
@app.get("/api/dramas/{title}")
def get_drama(title: str):
    decoded = urllib.parse.unquote(title)
    pipeline = [
        {"$unwind": "$dramas"},
        {"$match": {"dramas.title": decoded}},
        {"$project": {
            "actressId": {"$toString": "$_id"},
            "actressName": "$name",
            "actressImage": "$image",
            "role": "$dramas.role",
            "year": "$dramas.year",
            "poster": "$dramas.poster",
        }},
    ]
    results = list(actresses_collection.aggregate(pipeline))
    if not results:
        raise HTTPException(status_code=404, detail="Drama not found")
    first = results[0]
    drama_info = {
        "title": decoded,
        "year": first["year"],
        "poster": first.get("poster"),
        "cast": [
            {
                "actressId": r["actressId"],
                "actressName": r["actressName"],
                "actressImage": r.get("actressImage"),
                "role": r.get("role", ""),
            }
            for r in results
        ],
    }
    meta = DRAMA_META.get(decoded, {})
    drama_info["network"] = meta.get("network")
    drama_info["episodes"] = meta.get("episodes")
    drama_info["runtime"] = meta.get("runtime")
    drama_info["genre"] = meta.get("genre")
    drama_info["synopsis"] = meta.get("synopsis")
    return drama_info


# ── GET all dramas (aggregation pipeline) ──
@app.get("/api/dramas")
def search_dramas():
    pipeline = [
        {"$unwind": "$dramas"},
        {"$group": {
            "_id": "$dramas.title",
            "year": {"$first": "$dramas.year"},
            "poster": {"$first": "$dramas.poster"},
            "cast": {"$push": {
                "actressId": {"$toString": "$_id"},
                "actressName": "$name",
                "role": "$dramas.role",
            }},
        }},
        {"$project": {
            "_id": 0,
            "title": "$_id",
            "year": 1,
            "poster": 1,
            "cast": 1,
        }},
    ]
    return list(actresses_collection.aggregate(pipeline))


# ── POST reset (re-seed, admin-protected) ──
@app.post("/api/reset", dependencies=[Depends(_require_admin)])
def reset_data():
    seed()
    return {"message": "Data reset to defaults"}

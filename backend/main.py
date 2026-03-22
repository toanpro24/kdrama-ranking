import json
import os
import urllib.parse
from contextlib import asynccontextmanager

import anthropic
from bson import ObjectId
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from auth import get_current_user, require_user
from database import actresses_collection, user_rankings_collection, user_drama_status_collection
from drama_metadata import DRAMA_META
from models import ActressCreate, TierUpdate
from seed import seed

load_dotenv()
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")


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


# ── Helper: merge per-user data into actress documents ──
def _merge_user_data(docs: list[dict], user_id: str | None) -> list[dict]:
    """Overlay user-specific tier/rating/watchStatus onto shared actress docs."""
    if not user_id:
        # Guest: no personal data, set defaults
        for d in docs:
            d["tier"] = None
            for drama in d.get("dramas", []):
                drama["rating"] = None
                drama["watchStatus"] = None
        return docs

    actress_ids = [d["_id"] for d in docs]
    # Fetch user rankings for these actresses
    rankings = {
        r["actressId"]: r["tier"]
        for r in user_rankings_collection.find({"userId": user_id, "actressId": {"$in": actress_ids}})
    }
    # Fetch user drama statuses
    statuses_cursor = user_drama_status_collection.find({"userId": user_id, "actressId": {"$in": actress_ids}})
    statuses = {}
    for s in statuses_cursor:
        statuses[(s["actressId"], s["dramaTitle"])] = s

    for d in docs:
        aid = d["_id"]
        d["tier"] = rankings.get(aid)
        for drama in d.get("dramas", []):
            key = (aid, drama["title"])
            if key in statuses:
                drama["rating"] = statuses[key].get("rating")
                drama["watchStatus"] = statuses[key].get("watchStatus")
            else:
                drama["rating"] = None
                drama["watchStatus"] = None
    return docs


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
def get_actresses(genre: str | None = None, search: str | None = None, user=Depends(get_current_user)):
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
    _merge_user_data(docs, user["uid"] if user else None)
    return docs


# ── GET single actress ──
@app.get("/api/actresses/{actress_id}")
def get_actress(actress_id: str, user=Depends(get_current_user)):
    doc = actresses_collection.find_one({"_id": _oid(actress_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Actress not found")
    doc["_id"] = str(doc["_id"])
    _merge_user_data([doc], user["uid"] if user else None)
    return doc


# ── POST create actress (ObjectId = concurrent-safe, no race condition) ──
@app.post("/api/actresses", status_code=201)
def create_actress(actress: ActressCreate):
    doc = actress.model_dump()
    result = actresses_collection.insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    doc["tier"] = None
    return doc


# ── PATCH update tier (per-user) ──
@app.patch("/api/actresses/{actress_id}/tier")
def update_tier(actress_id: str, update: TierUpdate, user=Depends(require_user)):
    # Verify actress exists
    if not actresses_collection.find_one({"_id": _oid(actress_id)}):
        raise HTTPException(status_code=404, detail="Actress not found")
    if update.tier:
        user_rankings_collection.update_one(
            {"userId": user["uid"], "actressId": actress_id},
            {"$set": {"tier": update.tier}},
            upsert=True,
        )
    else:
        user_rankings_collection.delete_one({"userId": user["uid"], "actressId": actress_id})
    return {"id": actress_id, "tier": update.tier}


# ── PATCH bulk update tiers (per-user) ──
@app.patch("/api/actresses/bulk-tier")
def bulk_update_tiers(updates: list[dict], user=Depends(require_user)):
    for u in updates:
        tier = u.get("tier")
        if tier:
            user_rankings_collection.update_one(
                {"userId": user["uid"], "actressId": u["id"]},
                {"$set": {"tier": tier}},
                upsert=True,
            )
        else:
            user_rankings_collection.delete_one({"userId": user["uid"], "actressId": u["id"]})
    return {"updated": len(updates)}


# ── PATCH rate a drama (per-user) ──
@app.patch("/api/actresses/{actress_id}/dramas/{drama_title}/rating")
def rate_drama(actress_id: str, drama_title: str, body: dict, user=Depends(require_user)):
    decoded = urllib.parse.unquote(drama_title)
    rating = body.get("rating")
    if rating is not None and (rating < 1 or rating > 10):
        raise HTTPException(status_code=400, detail="Rating must be 1-10")
    # Verify actress and drama exist
    if not actresses_collection.find_one({"_id": _oid(actress_id), "dramas.title": decoded}):
        raise HTTPException(status_code=404, detail="Actress or drama not found")
    user_drama_status_collection.update_one(
        {"userId": user["uid"], "actressId": actress_id, "dramaTitle": decoded},
        {"$set": {"rating": rating}},
        upsert=True,
    )
    return {"actressId": actress_id, "drama": decoded, "rating": rating}


# ── PATCH watchlist status (per-user) ──
@app.patch("/api/actresses/{actress_id}/dramas/{drama_title}/watch-status")
def update_watch_status(actress_id: str, drama_title: str, body: dict, user=Depends(require_user)):
    decoded = urllib.parse.unquote(drama_title)
    status = body.get("watchStatus")
    valid = [None, "watched", "watching", "plan_to_watch", "dropped"]
    if status not in valid:
        raise HTTPException(status_code=400, detail=f"Status must be one of {valid}")
    # Verify actress and drama exist
    if not actresses_collection.find_one({"_id": _oid(actress_id), "dramas.title": decoded}):
        raise HTTPException(status_code=404, detail="Actress or drama not found")
    user_drama_status_collection.update_one(
        {"userId": user["uid"], "actressId": actress_id, "dramaTitle": decoded},
        {"$set": {"watchStatus": status}},
        upsert=True,
    )
    return {"actressId": actress_id, "drama": decoded, "watchStatus": status}


# ── DELETE actress (admin-protected) ──
@app.delete("/api/actresses/{actress_id}", dependencies=[Depends(_require_admin)])
def delete_actress(actress_id: str):
    result = actresses_collection.delete_one({"_id": _oid(actress_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Actress not found")
    return {"deleted": actress_id}


# ── GET stats (per-user when logged in) ──
@app.get("/api/stats")
def get_stats(user=Depends(get_current_user)):
    pipeline = [
        {"$group": {"_id": "$genre", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    genre_counts = {doc["_id"]: doc["count"] for doc in actresses_collection.aggregate(pipeline)}
    total = actresses_collection.count_documents({})

    if user:
        tier_pipeline = [
            {"$group": {"_id": "$tier", "count": {"$sum": 1}}},
        ]
        tier_counts = {doc["_id"]: doc["count"] for doc in user_rankings_collection.aggregate(
            [{"$match": {"userId": user["uid"]}}, *tier_pipeline]
        )}
        ranked = sum(tier_counts.values())
    else:
        tier_counts = {}
        ranked = 0

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


# ── POST chat (AI recommendations via Claude Haiku, SSE streaming) ──
def _build_system_prompt(user_id: str | None) -> str:
    docs = list(actresses_collection.find())
    for d in docs:
        d["_id"] = str(d["_id"])
    _merge_user_data(docs, user_id)

    lines = ["You are a K-Drama recommendation assistant. You know every K-Drama ever made.",
             "The user has a tier-ranked list of K-Drama actresses and their dramas.",
             "Use this data to give personalized recommendations.",
             "Be enthusiastic but concise. Use drama titles in quotes.",
             "If asked about something unrelated to K-Dramas, politely steer back.",
             "", "=== USER'S ACTRESS RANKINGS & DRAMAS ==="]
    for doc in docs:
        tier = doc.get("tier") or "Unranked"
        name = doc["name"]
        genre = doc.get("genre", "")
        lines.append(f"\n{name} (Tier: {tier}, Genre: {genre})")
        for d in doc.get("dramas", []):
            rating = d.get("rating")
            watch = d.get("watchStatus")
            meta = DRAMA_META.get(d["title"], {})
            parts = [f'  - "{d["title"]}" ({d.get("year", "?")})']
            if d.get("role"):
                parts.append(f'role: {d["role"]}')
            if rating:
                parts.append(f"rating: {rating}/10")
            if watch:
                parts.append(f"status: {watch}")
            if meta.get("genre"):
                parts.append(f"genre: {meta['genre']}")
            lines.append(", ".join(parts))
    return "\n".join(lines)


@app.post("/api/chat")
async def chat(request: Request, user=Depends(get_current_user)):
    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=503, detail="AI chat is not configured")

    body = await request.json()
    messages = body.get("messages", [])
    if not messages:
        raise HTTPException(status_code=400, detail="Messages are required")

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    system_prompt = _build_system_prompt(user["uid"] if user else None)

    def generate():
        with client.messages.stream(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=system_prompt,
            messages=messages,
        ) as stream:
            for text in stream.text_stream:
                yield f"data: {json.dumps({'text': text})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")

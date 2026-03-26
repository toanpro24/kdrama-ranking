"""Actress CRUD, tier management, and TMDB search routes."""

import asyncio
import os
import urllib.parse

from fastapi import APIRouter, Depends, HTTPException, Request

from auth import get_current_user, require_user
from rate_limit import limiter
from database import (
    actresses_collection,
    user_rankings_collection,
    user_drama_status_collection,
    user_actresses_collection,
)
from helpers import _oid, _merge_user_data, _ensure_user_list
from models import ActressCreate, TierUpdate, VALID_TIERS
from tmdb import (
    TMDB_IMG,
    _tmdb_get,
    _classify_category,
    _fetch_gallery_photos,
)

router = APIRouter(prefix="/api")


# ── GET all actresses ──
@router.get("/actresses")
def get_actresses(genre: str | None = None, search: str | None = None, user=Depends(get_current_user)):
    query = {}

    # Filter to user's personal list if logged in, or default actresses for guests
    if user:
        _ensure_user_list(user["uid"])
        user_actress_ids = [
            d["actressId"] for d in user_actresses_collection.find({"userId": user["uid"]}, {"actressId": 1})
        ]
        query["_id"] = {"$in": [_oid(aid) for aid in user_actress_ids]}
    else:
        query["default"] = True

    if genre and genre != "All":
        query["genre"] = genre
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"known": {"$regex": search, "$options": "i"}},
        ]
    # Exclude gallery from list endpoint (base64 images are large)
    docs = list(actresses_collection.find(query, {"gallery": 0}))
    for d in docs:
        d["_id"] = str(d["_id"])
    _merge_user_data(docs, user["uid"] if user else None)
    return docs


# ── GET single actress ──
@router.get("/actresses/{actress_id}")
def get_actress(actress_id: str, user=Depends(get_current_user)):
    doc = actresses_collection.find_one({"_id": _oid(actress_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Actress not found")
    doc["_id"] = str(doc["_id"])
    _merge_user_data([doc], user["uid"] if user else None)
    return doc


# ── POST create actress ──
@router.post("/actresses", status_code=201)
@limiter.limit("10/minute")
def create_actress(request: Request, actress: ActressCreate, user=Depends(get_current_user)):
    # Check for duplicate by name (case-insensitive)
    existing = actresses_collection.find_one({"name": {"$regex": f"^{actress.name}$", "$options": "i"}})
    if existing:
        # Actress already exists in shared pool — just add to user's list if logged in
        actress_id = str(existing["_id"])
        if user:
            user_actresses_collection.update_one(
                {"userId": user["uid"], "actressId": actress_id},
                {"$set": {"userId": user["uid"], "actressId": actress_id}},
                upsert=True,
            )
            existing["_id"] = actress_id
            _merge_user_data([existing], user["uid"])
            return existing
        raise HTTPException(status_code=409, detail=f"{actress.name} is already in the database")
    doc = actress.model_dump()
    doc["default"] = False  # User-added, not part of the default seed set
    result = actresses_collection.insert_one(doc)
    actress_id = str(result.inserted_id)
    doc["_id"] = actress_id
    doc["tier"] = None
    # Add to user's personal list
    if user:
        user_actresses_collection.update_one(
            {"userId": user["uid"], "actressId": actress_id},
            {"$set": {"userId": user["uid"], "actressId": actress_id}},
            upsert=True,
        )
    return doc


# ── PATCH update tier (per-user) ──
@router.patch("/actresses/{actress_id}/tier")
@limiter.limit("60/minute")
def update_tier(request: Request, actress_id: str, update: TierUpdate, user=Depends(require_user)):
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
@router.patch("/actresses/bulk-tier")
@limiter.limit("20/minute")
def bulk_update_tiers(request: Request, updates: list[dict], user=Depends(require_user)):
    for u in updates:
        tier = u.get("tier")
        if tier and tier not in VALID_TIERS:
            raise HTTPException(400, f"Invalid tier '{tier}'")
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
@router.patch("/actresses/{actress_id}/dramas/{drama_title}/rating")
def rate_drama(actress_id: str, drama_title: str, body: dict, user=Depends(require_user)):
    decoded = urllib.parse.unquote(drama_title)
    rating = body.get("rating")
    if rating is not None and (not isinstance(rating, (int, float)) or rating < 1 or rating > 10):
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 10")
    doc = actresses_collection.find_one({"_id": _oid(actress_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Actress not found")
    # Verify drama exists on this actress
    if not any(d["title"] == decoded for d in doc.get("dramas", [])):
        raise HTTPException(status_code=404, detail="Drama not found on this actress")
    user_drama_status_collection.update_one(
        {"userId": user["uid"], "actressId": actress_id, "dramaTitle": decoded},
        {"$set": {"rating": rating}},
        upsert=True,
    )
    return {"actressId": actress_id, "dramaTitle": decoded, "rating": rating}


# ── PATCH watchlist status (per-user) ──
@router.patch("/actresses/{actress_id}/dramas/{drama_title}/watch-status")
def update_watch_status(actress_id: str, drama_title: str, body: dict, user=Depends(require_user)):
    decoded = urllib.parse.unquote(drama_title)
    status = body.get("watchStatus")
    valid_statuses = {None, "watching", "watched", "plan_to_watch", "dropped"}
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid watch status: {status}")
    doc = actresses_collection.find_one({"_id": _oid(actress_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Actress not found")
    if not any(d["title"] == decoded for d in doc.get("dramas", [])):
        raise HTTPException(status_code=404, detail="Drama not found on this actress")
    user_drama_status_collection.update_one(
        {"userId": user["uid"], "actressId": actress_id, "dramaTitle": decoded},
        {"$set": {"watchStatus": status}},
        upsert=True,
    )
    return {"actressId": actress_id, "dramaTitle": decoded, "watchStatus": status}


# ── DELETE actress from user's list (per-user) ──
@router.delete("/actresses/{actress_id}")
@limiter.limit("20/minute")
def delete_actress(request: Request, actress_id: str, user=Depends(require_user)):
    result = user_actresses_collection.delete_one({"userId": user["uid"], "actressId": actress_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Actress not in your list")
    user_rankings_collection.delete_one({"userId": user["uid"], "actressId": actress_id})
    user_drama_status_collection.delete_many({"userId": user["uid"], "actressId": actress_id})
    return {"deleted": actress_id}


# ── TMDB search ──
@router.get("/search-actress")
@limiter.limit("30/minute")
async def search_actress_online(request: Request, q: str):
    """Search TMDB for a Korean actress and return structured data."""
    if not q or len(q) < 2:
        return []
    data = await _tmdb_get("/search/person", {"query": q, "language": "en-US"})
    results = []
    for p in data.get("results", [])[:8]:
        if p.get("known_for_department") != "Acting":
            continue
        profile = f"{TMDB_IMG}{p['profile_path']}" if p.get("profile_path") else None
        # Get known_for titles
        known_for = ""
        for kf in p.get("known_for", []):
            title = kf.get("name") or kf.get("title", "")
            lang = kf.get("original_language", "")
            if lang == "ko" and title:
                known_for = title
                break
        if not known_for:
            for kf in p.get("known_for", []):
                title = kf.get("name") or kf.get("title", "")
                if title:
                    known_for = title
                    break
        results.append({
            "tmdbId": p["id"],
            "name": p["name"],
            "image": profile,
            "knownFor": known_for,
        })
    return results


@router.get("/search-actress/{tmdb_id}")
@limiter.limit("30/minute")
async def get_actress_details_from_tmdb(request: Request, tmdb_id: int):
    """Fetch full actress details + Korean drama credits from TMDB."""
    person = await _tmdb_get(f"/person/{tmdb_id}", {"language": "en-US"})
    credits = await _tmdb_get(f"/person/{tmdb_id}/tv_credits", {"language": "en-US"})

    image = f"{TMDB_IMG}{person['profile_path']}" if person.get("profile_path") else None
    birth_date = person.get("birthday")
    birth_place = person.get("place_of_birth")

    # Filter Korean credits and classify as drama vs show
    dramas = []
    seen_titles = set()
    for c in credits.get("cast", []):
        if c.get("original_language") != "ko":
            continue
        title = c.get("name", "")
        if not title or title in seen_titles:
            continue
        seen_titles.add(title)
        year_str = c.get("first_air_date", "")
        year = int(year_str[:4]) if year_str and len(year_str) >= 4 else 0
        poster = f"{TMDB_IMG}{c['poster_path']}" if c.get("poster_path") else None
        role = c.get("character", "")
        category = _classify_category(c.get("genre_ids", []))
        dramas.append({"title": title, "year": year, "role": role, "poster": poster, "category": category})

    dramas.sort(key=lambda d: d["year"], reverse=True)

    # Determine known-for (most popular Korean drama)
    known = dramas[0]["title"] if dramas else "\u2014"

    # Guess genre from most common genre in their Korean credits
    genre_ids = []
    for c in credits.get("cast", []):
        if c.get("original_language") == "ko":
            genre_ids.extend(c.get("genre_ids", []))
    # TMDB genre mapping (common ones)
    tmdb_genres = {18: "Drama", 35: "Comedy", 10759: "Action", 10765: "Sci-Fi",
                   9648: "Mystery", 80: "Crime", 10768: "War", 10751: "Family",
                   16: "Animation", 10762: "Kids", 37: "Western", 99: "Documentary"}
    genre_counts: dict[str, int] = {}
    for gid in genre_ids:
        g = tmdb_genres.get(gid, "Drama")
        genre_counts[g] = genre_counts.get(g, 0) + 1
    # Map to our genres: Romance, Drama, Thriller, Comedy, Action, Sci-Fi
    top_genre = "Romance"
    if genre_counts:
        top = max(genre_counts, key=lambda k: genre_counts[k])
        our_genres = {"Drama": "Romance", "Comedy": "Comedy", "Action": "Action",
                      "Sci-Fi": "Sci-Fi", "Mystery": "Thriller", "Crime": "Thriller"}
        top_genre = our_genres.get(top, "Romance")

    # Fetch gallery photos from multiple sources
    gallery = await _fetch_gallery_photos(tmdb_id, person.get("name", ""))

    return {
        "name": person.get("name", ""),
        "image": image,
        "known": known,
        "genre": top_genre,
        "year": dramas[0]["year"] if dramas else 2024,
        "birthDate": birth_date,
        "birthPlace": birth_place,
        "dramas": dramas[:20],
        "gallery": gallery,
    }


# ── GET stats (per-user when logged in) ──
@router.get("/stats")
def get_stats(user=Depends(get_current_user)):
    if user:
        _ensure_user_list(user["uid"])
        user_actress_ids = [
            _oid(d["actressId"]) for d in user_actresses_collection.find({"userId": user["uid"]}, {"actressId": 1})
        ]
        match_filter = {"_id": {"$in": user_actress_ids}}
    else:
        match_filter = {}

    pipeline = [
        {"$match": match_filter},
        {"$group": {"_id": "$genre", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    genre_counts = {doc["_id"]: doc["count"] for doc in actresses_collection.aggregate(pipeline)}
    total = actresses_collection.count_documents(match_filter)

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

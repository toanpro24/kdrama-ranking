"""Drama detail, drama search, and watchlist routes."""

import urllib.parse

from fastapi import APIRouter, Depends, HTTPException

from auth import get_current_user, require_user
from database import (
    actresses_collection,
    user_drama_status_collection,
)
from drama_metadata import DRAMA_META
from helpers import _oid, _ensure_user_list
from tmdb import _tmdb_get

router = APIRouter(prefix="/api")


# ── GET drama detail ──
@router.get("/dramas/{title}")
async def get_drama(title: str, user=Depends(get_current_user)):
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

    # Look up per-user watch status for this drama
    user_watch_status = None
    user_rating = None
    user_actress_id = None
    if user:
        user_id = user["uid"]
        status_doc = user_drama_status_collection.find_one(
            {"userId": user_id, "dramaTitle": decoded}
        )
        if status_doc:
            user_watch_status = status_doc.get("watchStatus")
            user_rating = status_doc.get("rating")
            user_actress_id = status_doc.get("actressId")
    if not user_actress_id and results:
        user_actress_id = results[0]["actressId"]

    drama_info = {
        "title": decoded,
        "year": first["year"],
        "poster": first.get("poster"),
        "watchStatus": user_watch_status,
        "rating": user_rating,
        "actressId": user_actress_id,
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
    if meta:
        drama_info["network"] = meta.get("network")
        drama_info["episodes"] = meta.get("episodes")
        drama_info["runtime"] = meta.get("runtime")
        drama_info["genre"] = meta.get("genre")
        drama_info["synopsis"] = meta.get("synopsis")
    else:
        # Fetch from TMDB dynamically
        try:
            tmdb_data = await _tmdb_get("/search/tv", {"query": decoded, "language": "en-US"})
            tmdb_match = None
            for r in tmdb_data.get("results", []):
                if r.get("original_language") == "ko":
                    tmdb_match = r
                    break
            if not tmdb_match:
                for r in tmdb_data.get("results", []):
                    tmdb_match = r
                    break

            if tmdb_match:
                tv_id = tmdb_match["id"]
                detail = await _tmdb_get(f"/tv/{tv_id}", {"language": "en-US"})
                networks = [n["name"] for n in detail.get("networks", [])]
                genres = [g["name"] for g in detail.get("genres", [])]
                episodes = detail.get("number_of_episodes")
                runtimes = detail.get("episode_run_time", [])
                runtime = runtimes[0] if runtimes else None
                # Fallback: get runtime from last episode
                if not runtime:
                    last_ep = detail.get("last_episode_to_air") or {}
                    runtime = last_ep.get("runtime")
                # Fallback: get runtime from first season episode list
                if not runtime and detail.get("seasons"):
                    try:
                        s1_id = detail["seasons"][0].get("season_number", 1)
                        s1 = await _tmdb_get(f"/tv/{tv_id}/season/{s1_id}", {"language": "en-US"})
                        ep_runtimes = [e.get("runtime") for e in s1.get("episodes", []) if e.get("runtime")]
                        if ep_runtimes:
                            runtime = round(sum(ep_runtimes) / len(ep_runtimes))
                    except Exception:
                        pass
                synopsis = detail.get("overview") or None

                drama_info["network"] = networks[0] if networks else None
                drama_info["episodes"] = episodes
                drama_info["runtime"] = runtime
                drama_info["genre"] = ", ".join(genres) if genres else None
                drama_info["synopsis"] = synopsis
            else:
                drama_info["network"] = None
                drama_info["episodes"] = None
                drama_info["runtime"] = None
                drama_info["genre"] = None
                drama_info["synopsis"] = None
        except Exception:
            drama_info["network"] = None
            drama_info["episodes"] = None
            drama_info["runtime"] = None
            drama_info["genre"] = None
            drama_info["synopsis"] = None
    return drama_info


# ── GET all dramas ──
@router.get("/dramas")
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


# ── GET user's watchlist ──
@router.get("/watchlist")
def get_watchlist(user=Depends(require_user)):
    user_id = user["uid"]
    statuses = list(user_drama_status_collection.find({"userId": user_id, "watchStatus": {"$ne": None}}))
    if not statuses:
        return []

    drama_titles = list({s["dramaTitle"] for s in statuses})
    pipeline = [
        {"$unwind": "$dramas"},
        {"$match": {"dramas.title": {"$in": drama_titles}}},
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
    ]
    dramas_by_title = {d["_id"]: d for d in actresses_collection.aggregate(pipeline)}

    result = []
    for s in statuses:
        drama = dramas_by_title.get(s["dramaTitle"])
        if not drama:
            continue
        result.append({
            "title": s["dramaTitle"],
            "year": drama["year"],
            "poster": drama.get("poster"),
            "watchStatus": s["watchStatus"],
            "rating": s.get("rating"),
            "actressId": s["actressId"],
            "cast": drama.get("cast", []),
        })
    return result

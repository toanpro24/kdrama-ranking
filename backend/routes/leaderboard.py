"""Leaderboard, trending, community stats, and compare routes."""

import threading
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from auth import get_current_user
from database import (
    actresses_collection,
    user_rankings_collection,
    user_actresses_collection,
    user_profiles_collection,
    leaderboard_cache_collection,
)
from helpers import _oid, _merge_user_data, TIER_WEIGHT

router = APIRouter(prefix="/api")


# ── Leaderboard cache with stampede protection ──
_leaderboard_lock = threading.Lock()


def invalidate_leaderboard_cache():
    """Clear the cached leaderboard so the next request rebuilds from fresh data.

    Call this whenever ranking inputs change: profile visibility flips, tier updates.
    """
    leaderboard_cache_collection.delete_many({})


def _build_leaderboard():
    """Aggregate actress rankings across all public users into a leaderboard.

    Returns (entries, totalUsers) tuple. Uses a lock to prevent cache stampede.
    """
    # Check cache first (no lock needed for reads)
    cached = leaderboard_cache_collection.find_one(sort=[("cachedAt", -1)])
    if cached:
        return cached["entries"], cached.get("totalUsers", 0)

    # Acquire lock so only one thread rebuilds the cache
    with _leaderboard_lock:
        # Double-check after acquiring lock — another thread may have rebuilt
        cached = leaderboard_cache_collection.find_one(sort=[("cachedAt", -1)])
        if cached:
            return cached["entries"], cached.get("totalUsers", 0)

        # Get public user IDs
        public_uids = [
            p["userId"] for p in user_profiles_collection.find(
                {"tierListVisibility": "public"}, {"userId": 1}
            )
        ]
        if not public_uids:
            return [], 0

        # Get all rankings from public users
        rankings = list(user_rankings_collection.find({"userId": {"$in": public_uids}}))

        # Aggregate per actress
        actress_stats: dict = {}
        for r in rankings:
            aid = r["actressId"]
            tier = r.get("tier")
            if not tier or tier not in TIER_WEIGHT:
                continue
            if aid not in actress_stats:
                actress_stats[aid] = {"totalLists": 0, "tierSum": 0, "tierCounts": {}, "topTierCount": 0}
            stats = actress_stats[aid]
            stats["totalLists"] += 1
            stats["tierSum"] += TIER_WEIGHT[tier]
            stats["tierCounts"][tier] = stats["tierCounts"].get(tier, 0) + 1
            if tier in ("splus", "s", "a"):
                stats["topTierCount"] += 1

        if not actress_stats:
            return [], len(public_uids)

        # Fetch actress info
        actress_ids = list(actress_stats.keys())
        actress_docs = {
            str(d["_id"]): d
            for d in actresses_collection.find({"_id": {"$in": [_oid(a) for a in actress_ids]}}, {"gallery": 0})
        }

        # Build leaderboard entries
        entries = []
        for aid, stats in actress_stats.items():
            doc = actress_docs.get(aid)
            if not doc:
                continue
            avg_score = stats["tierSum"] / stats["totalLists"] if stats["totalLists"] > 0 else 0
            entries.append({
                "actressId": aid,
                "name": doc.get("name", ""),
                "image": doc.get("image"),
                "known": doc.get("known", ""),
                "genre": doc.get("genre", ""),
                "totalLists": stats["totalLists"],
                "avgScore": round(avg_score, 2),
                "topTierCount": stats["topTierCount"],
                "tierCounts": stats["tierCounts"],
            })

        entries.sort(key=lambda e: (-e["avgScore"], -e["totalLists"]))
        for i, e in enumerate(entries):
            e["rank"] = i + 1

        total_users = len(public_uids)

        # Cache results
        leaderboard_cache_collection.insert_one({
            "entries": entries,
            "totalUsers": total_users,
            "cachedAt": datetime.now(timezone.utc),
        })

        return entries, total_users


@router.get("/leaderboard")
def get_leaderboard(sort: str = "score", genre: str | None = None,
                    page: int = 1, pageSize: int = 50):
    """Get the global actress leaderboard with pagination."""
    entries, total_users = _build_leaderboard()

    if genre and genre != "All":
        entries = [e for e in entries if e["genre"] == genre]

    if sort == "lists":
        entries = sorted(entries, key=lambda e: (-e["totalLists"], -e["avgScore"]))
    elif sort == "top":
        entries = sorted(entries, key=lambda e: (-e["topTierCount"], -e["avgScore"]))
    # default: by avgScore (already sorted)

    # Re-rank after filtering
    for i, e in enumerate(entries):
        e["rank"] = i + 1

    total = len(entries)
    page = max(1, page)
    pageSize = max(1, min(pageSize, 100))
    start = (page - 1) * pageSize
    paged = entries[start:start + pageSize]

    return {"entries": paged, "totalUsers": total_users, "total": total,
            "page": page, "pageSize": pageSize}


# ── Per-actress community stats ──
@router.get("/actresses/{actress_id}/community")
def get_actress_community_stats(actress_id: str):
    """Get community ranking stats for a specific actress."""
    # Get public user IDs
    public_uids = [
        p["userId"] for p in user_profiles_collection.find(
            {"tierListVisibility": "public"}, {"userId": 1}
        )
    ]
    if not public_uids:
        return {"totalLists": 0, "avgScore": 0, "tierCounts": {}, "topTierCount": 0, "rank": None}

    # Get all rankings for this actress from public users
    rankings = list(user_rankings_collection.find({
        "userId": {"$in": public_uids},
        "actressId": actress_id,
        "tier": {"$exists": True, "$ne": None},
    }))

    tier_counts: dict = {}
    tier_sum = 0
    top_tier_count = 0
    for r in rankings:
        tier = r.get("tier")
        if not tier or tier not in TIER_WEIGHT:
            continue
        tier_counts[tier] = tier_counts.get(tier, 0) + 1
        tier_sum += TIER_WEIGHT[tier]
        if tier in ("splus", "s", "a"):
            top_tier_count += 1

    total = len(rankings)
    avg_score = round(tier_sum / total, 1) if total > 0 else 0

    # Get rank from leaderboard
    lb_entries, _ = _build_leaderboard()
    rank = None
    for e in lb_entries:
        if e["actressId"] == actress_id:
            rank = e["rank"]
            break

    return {
        "totalLists": total,
        "avgScore": avg_score,
        "tierCounts": tier_counts,
        "topTierCount": top_tier_count,
        "rank": rank,
    }


# ── Compare tier lists ──
@router.get("/compare/{slug1}/{slug2}")
def compare_tier_lists(slug1: str, slug2: str):
    """Compare two users' tier lists side-by-side."""
    profiles = []
    for slug in (slug1, slug2):
        profile = user_profiles_collection.find_one({"shareSlug": slug})
        if not profile:
            raise HTTPException(404, f"Tier list '{slug}' not found")
        if profile["tierListVisibility"] == "private":
            raise HTTPException(403, f"Tier list '{slug}' is private")
        profiles.append(profile)

    results = []
    for profile in profiles:
        uid = profile["userId"]
        user_actress_ids = [
            d["actressId"] for d in user_actresses_collection.find({"userId": uid}, {"actressId": 1})
        ]
        query = {"_id": {"$in": [_oid(aid) for aid in user_actress_ids]}}
        docs = list(actresses_collection.find(query, {"name": 1, "image": 1, "known": 1, "genre": 1}))
        for d in docs:
            d["_id"] = str(d["_id"])
        _merge_user_data(docs, uid)
        results.append({
            "displayName": profile.get("displayName", ""),
            "picture": profile.get("picture", ""),
            "shareSlug": profile.get("shareSlug", ""),
            "actresses": docs,
        })

    # Compute agreement stats
    tiers1 = {a["_id"]: a.get("tier") for a in results[0]["actresses"] if a.get("tier")}
    tiers2 = {a["_id"]: a.get("tier") for a in results[1]["actresses"] if a.get("tier")}
    common = set(tiers1.keys()) & set(tiers2.keys())
    exact_match = sum(1 for aid in common if tiers1[aid] == tiers2[aid])
    agreement_pct = round(exact_match / len(common) * 100) if common else 0

    return {
        "users": results,
        "stats": {
            "commonActresses": len(common),
            "exactMatches": exact_match,
            "agreementPct": agreement_pct,
        },
    }


# ── Trending Leaderboard ──
@router.get("/trending")
def get_trending():
    """Get trending actresses based on ranking activity."""
    # Get all public user IDs
    public_uids = [
        p["userId"] for p in user_profiles_collection.find(
            {"tierListVisibility": "public"}, {"userId": 1}
        )
    ]
    if not public_uids:
        return {"entries": [], "totalUsers": 0}

    # Get all rankings from public users
    all_rankings = list(user_rankings_collection.find({"userId": {"$in": public_uids}}))

    # Count how many public users ranked each actress (popularity signal)
    actress_data: dict = {}
    for r in all_rankings:
        aid = r["actressId"]
        tier = r.get("tier")
        if not tier or tier not in TIER_WEIGHT:
            continue
        if aid not in actress_data:
            actress_data[aid] = {"userCount": 0, "tierSum": 0, "topTierCount": 0}
        actress_data[aid]["userCount"] += 1
        actress_data[aid]["tierSum"] += TIER_WEIGHT[tier]
        if tier in ("splus", "s"):
            actress_data[aid]["topTierCount"] += 1

    if not actress_data:
        return {"entries": [], "totalUsers": len(public_uids)}

    # Trending score: combines popularity (user count) with quality (avg tier)
    for aid, data in actress_data.items():
        avg = data["tierSum"] / data["userCount"] if data["userCount"] > 0 else 0
        data["trendScore"] = round(data["userCount"] * avg, 2)
        data["avgScore"] = round(avg, 2)

    # Fetch actress info
    actress_ids = list(actress_data.keys())
    actress_docs = {
        str(d["_id"]): d
        for d in actresses_collection.find({"_id": {"$in": [_oid(a) for a in actress_ids]}}, {"gallery": 0})
    }

    entries = []
    for aid, data in actress_data.items():
        doc = actress_docs.get(aid)
        if not doc:
            continue
        entries.append({
            "actressId": aid,
            "name": doc.get("name", ""),
            "image": doc.get("image"),
            "known": doc.get("known", ""),
            "genre": doc.get("genre", ""),
            "userCount": data["userCount"],
            "avgScore": data["avgScore"],
            "topTierCount": data["topTierCount"],
            "trendScore": data["trendScore"],
        })

    entries.sort(key=lambda e: (-e["trendScore"], -e["avgScore"]))
    for i, e in enumerate(entries):
        e["rank"] = i + 1

    return {"entries": entries[:50], "totalUsers": len(public_uids)}

"""Shared helper functions used across route modules."""

import re
import threading

from bson import ObjectId
from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from database import (
    actresses_collection,
    user_rankings_collection,
    user_drama_status_collection,
    user_actresses_collection,
    user_profiles_collection,
    user_follows_collection,
)


# ── Tier scoring weights ──
TIER_WEIGHT = {"splus": 10, "s": 8, "a": 5, "b": 3, "c": 2, "d": 1}


def _oid(actress_id: str) -> ObjectId:
    """Convert string to ObjectId, raising 400 on invalid input."""
    try:
        return ObjectId(actress_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid actress ID")


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


def _ensure_user_list(uid: str):
    """Seed a user's actress list on first visit (copy only default/seed actresses)."""
    if user_actresses_collection.find_one({"userId": uid}, {"_id": 1}):
        return
    # Only seed with the original default actresses, not user-added ones
    default_ids = [str(d["_id"]) for d in actresses_collection.find({"default": True}, {"_id": 1})]
    if default_ids:
        user_actresses_collection.insert_many(
            [{"userId": uid, "actressId": aid} for aid in default_ids]
        )


def _get_or_create_profile(user: dict) -> dict:
    """Get existing profile or create a default one."""
    profile = user_profiles_collection.find_one({"userId": user["uid"]})
    if profile:
        profile["_id"] = str(profile["_id"])
        return profile
    # Create default profile from Firebase user info
    base_slug = re.sub(r"[^a-z0-9]+", "-", (user.get("name") or "user").lower()).strip("-")
    slug = base_slug
    counter = 1
    for _ in range(20):  # bounded retry to prevent infinite loop
        try:
            doc = {
                "userId": user["uid"],
                "displayName": user.get("name", ""),
                "bio": "",
                "shareSlug": slug,
                "tierListVisibility": "private",
                "picture": user.get("picture", ""),
            }
            result = user_profiles_collection.insert_one(doc)
            doc["_id"] = str(result.inserted_id)
            return doc
        except DuplicateKeyError:
            # Either slug or userId collision — re-check if our profile was created concurrently
            profile = user_profiles_collection.find_one({"userId": user["uid"]})
            if profile:
                profile["_id"] = str(profile["_id"])
                return profile
            # Slug taken by another user — try next slug
            slug = f"{base_slug}-{counter}"
            counter += 1
    raise HTTPException(status_code=500, detail="Could not generate unique profile slug")

"""User profile and shared tier list routes."""

import re

from fastapi import APIRouter, Depends, HTTPException, Request
from pymongo.errors import DuplicateKeyError

from auth import require_user
from rate_limit import limiter
from database import (
    actresses_collection,
    user_actresses_collection,
    user_profiles_collection,
    user_follows_collection,
)
from helpers import _oid, _merge_user_data, _get_or_create_profile
from models import ProfileUpdate
from routes.leaderboard import invalidate_leaderboard_cache

router = APIRouter(prefix="/api")


@router.get("/profile")
def get_profile(user=Depends(require_user)):
    """Get the current user's profile."""
    profile = _get_or_create_profile(user)
    return profile


@router.put("/profile")
@limiter.limit("10/minute")
def update_profile(request: Request, data: ProfileUpdate, user=Depends(require_user)):
    """Update the current user's profile."""
    _get_or_create_profile(user)  # ensure exists
    updates = {}
    if data.displayName is not None:
        name = data.displayName.strip()
        if not name or len(name) > 50:
            raise HTTPException(400, "Display name must be 1-50 characters")
        updates["displayName"] = name
    if data.bio is not None:
        if len(data.bio) > 200:
            raise HTTPException(400, "Bio must be 200 characters or less")
        updates["bio"] = data.bio.strip()
    if data.shareSlug is not None:
        slug = re.sub(r"[^a-z0-9]+", "-", data.shareSlug.lower()).strip("-")
        if not slug or len(slug) < 3 or len(slug) > 30:
            raise HTTPException(400, "Share slug must be 3-30 characters (letters, numbers, hyphens)")
        existing = user_profiles_collection.find_one({"shareSlug": slug, "userId": {"$ne": user["uid"]}})
        if existing:
            raise HTTPException(409, "This share link is already taken")
        updates["shareSlug"] = slug
    if data.tierListVisibility is not None:
        if data.tierListVisibility not in ("private", "link_only", "public"):
            raise HTTPException(400, "Visibility must be private, link_only, or public")
        updates["tierListVisibility"] = data.tierListVisibility
    if not updates:
        raise HTTPException(400, "No fields to update")
    try:
        user_profiles_collection.update_one({"userId": user["uid"]}, {"$set": updates})
    except DuplicateKeyError:
        raise HTTPException(409, "This share link is already taken")
    # When going private, remove all followers to prevent data leaks
    if updates.get("tierListVisibility") == "private":
        user_follows_collection.delete_many({"followingId": user["uid"]})
    # Visibility change affects which users contribute to the leaderboard
    if "tierListVisibility" in updates:
        invalidate_leaderboard_cache()
    return _get_or_create_profile(user)


@router.get("/shared/{slug}")
def get_shared_tier_list(slug: str):
    """View a public/link_only tier list by share slug."""
    profile = user_profiles_collection.find_one({"shareSlug": slug})
    if not profile:
        raise HTTPException(status_code=404, detail="Tier list not found")
    if profile["tierListVisibility"] == "private":
        raise HTTPException(status_code=403, detail="This tier list is private")
    uid = profile["userId"]
    user_actress_ids = [
        d["actressId"] for d in user_actresses_collection.find({"userId": uid}, {"actressId": 1})
    ]
    query = {"_id": {"$in": [_oid(aid) for aid in user_actress_ids]}}
    docs = list(actresses_collection.find(query, {"gallery": 0}))
    for d in docs:
        d["_id"] = str(d["_id"])
    _merge_user_data(docs, uid)
    return {
        "displayName": profile.get("displayName", ""),
        "bio": profile.get("bio", ""),
        "picture": profile.get("picture", ""),
        "actresses": docs,
    }

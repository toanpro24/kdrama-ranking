"""Follow system routes — follow, unfollow, following list, follower counts."""

from fastapi import APIRouter, Depends, HTTPException
from pymongo.errors import DuplicateKeyError

from auth import require_user
from database import (
    user_profiles_collection,
    user_follows_collection,
)

router = APIRouter(prefix="/api")


@router.post("/follow/{slug}")
def follow_user(slug: str, user=Depends(require_user)):
    """Follow a user by their share slug."""
    target = user_profiles_collection.find_one({"shareSlug": slug})
    if not target:
        raise HTTPException(404, "User not found")
    if target["userId"] == user["uid"]:
        raise HTTPException(400, "Cannot follow yourself")
    if target["tierListVisibility"] == "private":
        raise HTTPException(403, "This user's tier list is private")
    try:
        user_follows_collection.insert_one({
            "followerId": user["uid"],
            "followingId": target["userId"],
        })
    except DuplicateKeyError:
        pass  # Already following
    return {"ok": True}


@router.delete("/follow/{slug}")
def unfollow_user(slug: str, user=Depends(require_user)):
    """Unfollow a user by their share slug."""
    target = user_profiles_collection.find_one({"shareSlug": slug})
    if not target:
        raise HTTPException(404, "User not found")
    user_follows_collection.delete_one({
        "followerId": user["uid"],
        "followingId": target["userId"],
    })
    return {"ok": True}


@router.get("/following")
def get_following(user=Depends(require_user)):
    """Get the list of users the current user is following."""
    follows = list(user_follows_collection.find({"followerId": user["uid"]}))
    following_ids = [f["followingId"] for f in follows]
    if not following_ids:
        return []

    result = []
    for uid in following_ids:
        profile = user_profiles_collection.find_one({"userId": uid})
        if not profile:
            continue
        # Skip users who have since gone private (safety net)
        if profile.get("tierListVisibility") == "private":
            continue
        result.append({
            "userId": uid,
            "displayName": profile.get("displayName", ""),
            "picture": profile.get("picture", ""),
            "shareSlug": profile.get("shareSlug", ""),
            "bio": profile.get("bio", ""),
            "rankedCount": 0,  # Could be enriched later
        })
    return result


@router.get("/followers/count")
def get_follower_count(user=Depends(require_user)):
    """Get follower and following counts for the current user."""
    followers = user_follows_collection.count_documents({"followingId": user["uid"]})
    following = user_follows_collection.count_documents({"followerId": user["uid"]})
    return {"followers": followers, "following": following}


@router.get("/is-following/{slug}")
def is_following(slug: str, user=Depends(require_user)):
    """Check if the current user is following a given user."""
    target = user_profiles_collection.find_one({"shareSlug": slug})
    if not target:
        return {"following": False}
    doc = user_follows_collection.find_one({
        "followerId": user["uid"],
        "followingId": target["userId"],
    })
    return {"following": doc is not None}

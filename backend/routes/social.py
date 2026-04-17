"""Follow system routes — follow, unfollow, following list, follower counts."""

from fastapi import APIRouter, Depends, HTTPException, Request
from pymongo.errors import DuplicateKeyError

from auth import get_current_user, require_user
from rate_limit import limiter
from database import (
    user_profiles_collection,
    user_follows_collection,
    user_rankings_collection,
)

router = APIRouter(prefix="/api")


@router.post("/follow/{slug}")
@limiter.limit("20/minute")
def follow_user(request: Request, slug: str, user=Depends(require_user)):
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
@limiter.limit("20/minute")
def unfollow_user(request: Request, slug: str, user=Depends(require_user)):
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


@router.get("/users/public")
def list_public_users(user=Depends(get_current_user)):
    """List users with public tier lists for discovery. Excludes the current user."""
    query = {"tierListVisibility": "public"}
    profiles = list(user_profiles_collection.find(query))
    if not profiles:
        return []

    current_uid = user["uid"] if user else None
    profiles = [p for p in profiles if p.get("userId") != current_uid and p.get("shareSlug")]

    uids = [p["userId"] for p in profiles]
    ranked_counts: dict = {}
    if uids:
        pipeline = [
            {"$match": {"userId": {"$in": uids}, "tier": {"$exists": True, "$ne": None}}},
            {"$group": {"_id": "$userId", "count": {"$sum": 1}}},
        ]
        for row in user_rankings_collection.aggregate(pipeline):
            ranked_counts[row["_id"]] = row["count"]

    followed_ids: set = set()
    if current_uid:
        followed_ids = {
            f["followingId"] for f in user_follows_collection.find(
                {"followerId": current_uid}, {"followingId": 1}
            )
        }

    result = []
    for p in profiles:
        uid = p["userId"]
        result.append({
            "userId": uid,
            "displayName": p.get("displayName", ""),
            "picture": p.get("picture", ""),
            "shareSlug": p["shareSlug"],
            "bio": p.get("bio", ""),
            "rankedCount": ranked_counts.get(uid, 0),
            "isFollowing": uid in followed_ids,
        })
    result.sort(key=lambda u: (-u["rankedCount"], u["displayName"].lower()))
    return result


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

"""Admin-only routes — reset, clear tiers, refresh data, admin delete."""

import asyncio
import os

from fastapi import APIRouter, Depends, Header, HTTPException, Request

from auth import require_user
from database import (
    actresses_collection,
    user_rankings_collection,
    user_drama_status_collection,
    user_actresses_collection,
)
from helpers import _oid, _ensure_user_list
from tmdb import (
    TMDB_IMG,
    _tmdb_get,
    _find_tmdb_person,
    _fetch_tmdb_dramas,
    _fetch_gallery_photos,
)

ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "")


def _require_admin(x_api_key: str = Header(default="")):
    """Dependency: reject if API key doesn't match."""
    if not ADMIN_API_KEY:
        raise HTTPException(status_code=503, detail="ADMIN_API_KEY not configured")
    if x_api_key != ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid or missing API key")


router = APIRouter(prefix="/api")


# ── POST reset (back to 36 defaults, per-user) ──
@router.post("/reset")
def reset_data(user=Depends(require_user)):
    """Reset user's list back to the 36 default actresses, all unranked."""
    uid = user["uid"]
    # Clear user's actress list, tiers, and drama statuses
    user_actresses_collection.delete_many({"userId": uid})
    user_rankings_collection.delete_many({"userId": uid})
    user_drama_status_collection.delete_many({"userId": uid})
    # Re-seed with defaults
    _ensure_user_list(uid)
    return {"message": "List reset to 36 default actresses"}


# ── POST clear tiers (move all to unranked, per-user) ──
@router.post("/clear-tiers")
def clear_tiers(user=Depends(require_user)):
    """Move all of the user's actresses back to the unranked pool (keep the full list)."""
    uid = user["uid"]
    result = user_rankings_collection.delete_many({"userId": uid})
    return {"message": f"Cleared {result.deleted_count} tier assignments"}


# ── DELETE actress permanently (admin-protected) ──
@router.delete("/actresses/{actress_id}/admin", dependencies=[Depends(_require_admin)])
def admin_delete_actress(actress_id: str):
    """Permanently remove an actress from the global pool (admin only)."""
    oid = _oid(actress_id)
    result = actresses_collection.delete_one({"_id": oid})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Actress not found")
    # Clean up all user references
    user_actresses_collection.delete_many({"actressId": actress_id})
    user_rankings_collection.delete_many({"actressId": actress_id})
    user_drama_status_collection.delete_many({"actressId": actress_id})
    return {"deleted": actress_id}


# ── POST refresh all actress data from TMDB (admin-protected) ──
@router.post("/refresh-all", dependencies=[Depends(_require_admin)])
async def refresh_all_data(request: Request):
    """Re-fetch dramas, gallery photos, and profile images for all actresses from TMDB."""
    actresses = list(actresses_collection.find({}))
    results = {"total": len(actresses), "updated": 0, "failed": []}

    for doc in actresses:
        name = doc["name"]
        known_drama = doc.get("known", "")
        try:
            person_id = await _find_tmdb_person(name, known_drama=known_drama)
            if not person_id:
                results["failed"].append(f"{name}: not found on TMDB")
                continue

            # Fetch fresh data
            person = await _tmdb_get(f"/person/{person_id}", {"language": "en-US"})
            dramas = await _fetch_tmdb_dramas(person_id)
            gallery = await _fetch_gallery_photos(person_id, name)
            image = f"{TMDB_IMG}{person['profile_path']}" if person.get("profile_path") else doc.get("image")

            update_fields: dict = {
                "dramas": dramas,
                "gallery": gallery,
                "image": image,
            }
            # Update birth info if available and not already set
            if person.get("birthday"):
                update_fields["birthDate"] = person["birthday"]
            if person.get("place_of_birth"):
                update_fields["birthPlace"] = person["place_of_birth"]

            actresses_collection.update_one(
                {"_id": doc["_id"]},
                {"$set": update_fields},
            )
            results["updated"] += 1
            await asyncio.sleep(0.4)
        except Exception as e:
            results["failed"].append(f"{name}: {str(e)}")

    return results

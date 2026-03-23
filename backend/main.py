import asyncio
import json
import os
import time
import urllib.parse
from contextlib import asynccontextmanager

import anthropic
import httpx
from bson import ObjectId
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from auth import get_current_user, require_user
from database import actresses_collection, user_rankings_collection, user_drama_status_collection, user_actresses_collection
from drama_metadata import DRAMA_META
from models import ActressCreate, TierUpdate
from seed import seed

load_dotenv()
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",") if o.strip()]


def _require_admin(x_api_key: str = Header(default="")):
    """Dependency: reject if API key doesn't match."""
    if not ADMIN_API_KEY:
        raise HTTPException(status_code=503, detail="ADMIN_API_KEY not configured")
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
POSTER_FIXES = {
    "Eve": "https://image.tmdb.org/t/p/w500/6xvIRR50lDzFRWLFCAwSzEkoEu3.jpg",
}


def _apply_poster_fixes():
    """Fix any known incorrect drama posters."""
    for title, correct_url in POSTER_FIXES.items():
        actresses_collection.update_many(
            {"dramas.title": title},
            {"$set": {"dramas.$[d].poster": correct_url}},
            array_filters=[{"d.title": title}],
        )


async def _fetch_gallery_photos(person_id: int, name: str, target: int = 10) -> list[str]:
    """Gather photos from multiple sources: TMDB profiles, TMDB tagged images, Wikipedia."""
    gallery: list[str] = []
    seen: set[str] = set()
    client = _get_http_client()

    def _add(url: str):
        if url not in seen and len(gallery) < target:
            seen.add(url)
            gallery.append(url)

    # Source 1: TMDB profile photos
    try:
        images_data = await _tmdb_get(f"/person/{person_id}/images", {})
        profiles = images_data.get("profiles", [])
        profiles.sort(key=lambda p: p.get("vote_average", 0), reverse=True)
        for p in profiles:
            if p.get("file_path"):
                _add(f"{TMDB_IMG}{p['file_path']}")
    except Exception:
        pass

    # Source 2: TMDB tagged images (stills from shows, not posters)
    if len(gallery) < target:
        try:
            tagged = await _tmdb_get(f"/person/{person_id}/tagged_images", {"page": 1})
            stills = [t for t in tagged.get("results", [])
                      if t.get("media_type") == "tv" and t.get("image_type") == "backdrop"
                      and t.get("file_path")]
            stills.sort(key=lambda t: t.get("vote_average", 0), reverse=True)
            for t in stills:
                _add(f"{TMDB_IMG}{t['file_path']}")
        except Exception:
            pass

    # Source 3: Wikipedia page images
    if len(gallery) < target:
        try:
            wiki_name = name.replace(" ", "_")
            wiki_url = f"https://en.wikipedia.org/api/rest_v1/page/media-list/{urllib.parse.quote(wiki_name)}"
            resp = await client.get(wiki_url, headers={
                "Accept": "application/json",
                "User-Agent": "KDramaRanking/1.0",
            })
            wiki_data = resp.json()
            for item in wiki_data.get("items", []):
                src = item.get("srcset", [{}])[0].get("src", "") if item.get("srcset") else ""
                if not src:
                    src = item.get("original", {}).get("source", "")
                if not src:
                    continue
                if not src.startswith("http"):
                    src = "https:" + src
                lower = src.lower()
                if any(skip in lower for skip in [".svg", "icon", "logo", "flag", "commons-logo", "wiki"]):
                    continue
                _add(src)
        except Exception:
            pass

    # Source 4: Wikimedia Commons search
    if len(gallery) < target:
        try:
            commons_params = urllib.parse.urlencode({
                "action": "query", "format": "json",
                "generator": "search", "gsrnamespace": "6",
                "gsrsearch": f"{name} actress", "gsrlimit": "15",
                "prop": "imageinfo", "iiprop": "url|size",
                "iiurlwidth": "500",
            })
            commons_url = f"https://commons.wikimedia.org/w/api.php?{commons_params}"
            resp = await client.get(commons_url, headers={"User-Agent": "KDramaRanking/1.0"})
            commons_data = resp.json()
            pages = commons_data.get("query", {}).get("pages", {})
            for page in pages.values():
                info = (page.get("imageinfo") or [{}])[0]
                url = info.get("thumburl") or info.get("url", "")
                if not url:
                    continue
                lower = url.lower()
                if any(skip in lower for skip in [".svg", "icon", "logo", "flag", "map", "emblem"]):
                    continue
                width = info.get("width", 0)
                if width < 200:
                    continue
                _add(url)
        except Exception:
            pass

    # Source 5: Google Custom Search Images (if configured)
    if len(gallery) < target and GOOGLE_API_KEY and GOOGLE_CSE_ID:
        try:
            needed = target - len(gallery)
            gparams = urllib.parse.urlencode({
                "key": GOOGLE_API_KEY, "cx": GOOGLE_CSE_ID,
                "q": f"{name} korean actress", "searchType": "image",
                "num": min(needed, 10), "imgSize": "large",
                "safe": "active",
            })
            gurl = f"https://www.googleapis.com/customsearch/v1?{gparams}"
            resp = await client.get(gurl, headers={"Accept": "application/json"})
            gdata = resp.json()
            for item in gdata.get("items", []):
                link = item.get("link", "")
                if link:
                    _add(link)
        except Exception:
            pass

    return gallery


async def _backfill_galleries():
    """Fetch gallery photos for actresses with fewer than 10."""
    missing = list(actresses_collection.find({
        "$or": [
            {"gallery": {"$exists": False}},
            {"gallery": {"$size": 0}},
            {"$expr": {"$lt": [{"$size": {"$ifNull": ["$gallery", []]}}, 10]}},
        ]
    }))
    if not missing:
        return
    print(f"Backfilling gallery photos for {len(missing)} actresses...")
    for doc in missing:
        name = doc["name"]
        known_drama = doc.get("known", "")
        try:
            person_id = await _find_tmdb_person(name, known_drama=known_drama)
            if not person_id:
                continue
            gallery = await _fetch_gallery_photos(person_id, name)
            if gallery:
                actresses_collection.update_one({"_id": doc["_id"]}, {"$set": {"gallery": gallery}})
                print(f"  {name}: {len(gallery)} photos")
            await asyncio.sleep(0.3)
        except Exception as e:
            print(f"  Error fetching gallery for {name}: {e}")


_http_client: httpx.AsyncClient | None = None


def _get_http_client() -> httpx.AsyncClient:
    if _http_client is None:
        raise RuntimeError("HTTP client not initialized")
    return _http_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _http_client
    _http_client = httpx.AsyncClient(timeout=15, follow_redirects=True)
    if actresses_collection.count_documents({}) == 0:
        seed()
    # One-time migration: mark existing actresses as default if not already tagged
    if actresses_collection.count_documents({"default": True}) == 0:
        from seed import SEED_DATA
        seed_names = [a["name"] for a in SEED_DATA]
        actresses_collection.update_many(
            {"name": {"$in": seed_names}},
            {"$set": {"default": True}},
        )
    _apply_poster_fixes()
    await _backfill_galleries()
    yield
    await _http_client.aclose()
    _http_client = None


limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="K-Drama Actress Ranking API", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)


def _ensure_user_list(uid: str):
    """Seed a user's actress list on first visit (copy only default/seed actresses)."""
    if user_actresses_collection.count_documents({"userId": uid}) > 0:
        return
    # Only seed with the original default actresses, not user-added ones
    default_ids = [str(d["_id"]) for d in actresses_collection.find({"default": True}, {"_id": 1})]
    if default_ids:
        user_actresses_collection.insert_many(
            [{"userId": uid, "actressId": aid} for aid in default_ids]
        )


# ── GET all actresses ──
@app.get("/api/actresses")
def get_actresses(genre: str | None = None, search: str | None = None, user=Depends(get_current_user)):
    query = {}

    # Filter to user's personal list if logged in
    if user:
        _ensure_user_list(user["uid"])
        user_actress_ids = [
            d["actressId"] for d in user_actresses_collection.find({"userId": user["uid"]}, {"actressId": 1})
        ]
        query["_id"] = {"$in": [_oid(aid) for aid in user_actress_ids]}

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


TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")
TMDB_IMG = "https://image.tmdb.org/t/p/w500"
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID", "")


_tmdb_cache: dict[str, tuple[float, dict]] = {}
_TMDB_CACHE_TTL = 600  # 10 minutes


async def _tmdb_get(path: str, params: dict) -> dict:
    if not TMDB_API_KEY:
        raise HTTPException(status_code=503, detail="TMDB_API_KEY not configured")
    cache_key = f"{path}:{json.dumps(params, sort_keys=True)}"
    now = time.monotonic()
    cached = _tmdb_cache.get(cache_key)
    if cached and now - cached[0] < _TMDB_CACHE_TTL:
        return cached[1]
    params["api_key"] = TMDB_API_KEY
    url = f"https://api.themoviedb.org/3{path}?{urllib.parse.urlencode(params)}"
    client = _get_http_client()
    resp = await client.get(url, headers={"Accept": "application/json"})
    resp.raise_for_status()
    data = resp.json()
    _tmdb_cache[cache_key] = (now, data)
    # Evict old entries if cache grows too large
    if len(_tmdb_cache) > 500:
        cutoff = now - _TMDB_CACHE_TTL
        expired = [k for k, (t, _) in _tmdb_cache.items() if t < cutoff]
        for k in expired:
            del _tmdb_cache[k]
    return data


@app.get("/api/search-actress")
@limiter.limit("15/minute")
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


@app.get("/api/search-actress/{tmdb_id}")
@limiter.limit("10/minute")
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
    known = dramas[0]["title"] if dramas else "—"

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


# ── POST create actress (ObjectId = concurrent-safe, no race condition) ──
@app.post("/api/actresses", status_code=201)
def create_actress(actress: ActressCreate, user=Depends(get_current_user)):
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


# ── DELETE actress from user's list (per-user) ──
@app.delete("/api/actresses/{actress_id}")
def delete_actress(actress_id: str, user=Depends(require_user)):
    # Remove from user's personal list only
    result = user_actresses_collection.delete_one({"userId": user["uid"], "actressId": actress_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Actress not found in your list")
    # Also clean up user's tier and drama status for this actress
    user_rankings_collection.delete_many({"userId": user["uid"], "actressId": actress_id})
    user_drama_status_collection.delete_many({"userId": user["uid"], "actressId": actress_id})
    return {"deleted": actress_id}


# ── DELETE actress permanently (admin-protected) ──
@app.delete("/api/actresses/{actress_id}/admin", dependencies=[Depends(_require_admin)])
def admin_delete_actress(actress_id: str):
    result = actresses_collection.delete_one({"_id": _oid(actress_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Actress not found")
    # Clean up all user data for this actress
    user_actresses_collection.delete_many({"actressId": actress_id})
    user_rankings_collection.delete_many({"actressId": actress_id})
    user_drama_status_collection.delete_many({"actressId": actress_id})
    return {"deleted": actress_id}


# ── GET stats (per-user when logged in) ──
@app.get("/api/stats")
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


# ── GET drama detail (aggregation pipeline instead of full scan) ──
@app.get("/api/dramas/{title}")
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


# ── GET user's watchlist ──
@app.get("/api/watchlist")
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


# ── POST reset (re-seed, admin-protected) ──
@app.post("/api/reset", dependencies=[Depends(_require_admin)])
def reset_data():
    seed()
    return {"message": "Data reset to defaults"}


async def _find_tmdb_person(name: str, known_drama: str | None = None) -> int | None:
    """Search TMDB for a Korean actress by name.

    If known_drama is provided, cross-reference against each result's known_for
    credits to pick the correct person (avoids wrong matches for common names).
    """
    data = await _tmdb_get("/search/person", {"query": name, "language": "en-US"})
    actors = [p for p in data.get("results", []) if p.get("known_for_department") == "Acting"]

    if not actors:
        return None

    # If we have a known drama, try to match against known_for titles
    if known_drama:
        known_lower = known_drama.lower()
        for p in actors:
            kf_titles = []
            for kf in p.get("known_for", []):
                kf_titles.append(kf.get("name", "").lower())
                kf_titles.append(kf.get("original_name", "").lower())
                kf_titles.append(kf.get("title", "").lower())
                kf_titles.append(kf.get("original_title", "").lower())
            if known_lower in kf_titles:
                return p["id"]

        # Fuzzy: check if known drama is a substring of any known_for title
        for p in actors:
            for kf in p.get("known_for", []):
                for field in ("name", "original_name", "title", "original_title"):
                    val = kf.get(field, "").lower()
                    if val and (known_lower in val or val in known_lower):
                        return p["id"]

        # Still no match — try fetching TV credits for each candidate (up to 3)
        for p in actors[:3]:
            try:
                credits = await _tmdb_get(f"/person/{p['id']}/tv_credits", {"language": "en-US"})
                credit_titles = set()
                for c in credits.get("cast", []):
                    credit_titles.add(c.get("name", "").lower())
                    credit_titles.add(c.get("original_name", "").lower())
                if known_lower in credit_titles:
                    return p["id"]
                await asyncio.sleep(0.2)
            except Exception:
                continue

    # Fallback: first actor with Korean credits
    for p in actors:
        for kf in p.get("known_for", []):
            if kf.get("original_language") == "ko":
                return p["id"]

    # Last resort: first actor result
    return actors[0]["id"]


# TMDB genre IDs for non-drama TV (variety, reality, talk, game shows)
_SHOW_GENRE_IDS = {10764, 10767, 10766, 10763}  # Reality, Talk, Game Show, News


def _classify_category(genre_ids: list[int]) -> str:
    """Return 'show' for variety/reality/talk/game shows, 'drama' otherwise."""
    if any(gid in _SHOW_GENRE_IDS for gid in genre_ids):
        return "show"
    return "drama"


async def _fetch_tmdb_dramas(person_id: int) -> list[dict]:
    """Fetch Korean TV credits for a person from TMDB, classified as drama or show."""
    credits = await _tmdb_get(f"/person/{person_id}/tv_credits", {"language": "en-US"})
    dramas = []
    seen = set()
    for c in credits.get("cast", []):
        if c.get("original_language") != "ko":
            continue
        title = c.get("name", "")
        if not title or title in seen:
            continue
        seen.add(title)
        year_str = c.get("first_air_date", "")
        year = int(year_str[:4]) if year_str and len(year_str) >= 4 else 0
        poster = f"{TMDB_IMG}{c['poster_path']}" if c.get("poster_path") else None
        role = c.get("character", "")
        category = _classify_category(c.get("genre_ids", []))
        dramas.append({"title": title, "year": year, "role": role, "poster": poster, "category": category})
    dramas.sort(key=lambda d: d["year"], reverse=True)
    return dramas


# ── POST refresh all actress data from TMDB (admin-protected) ──
@app.post("/api/refresh-all", dependencies=[Depends(_require_admin)])
@limiter.limit("2/hour")
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


# ── POST chat (AI recommendations via Claude Haiku, SSE streaming) ──
def _build_system_prompt(user_id: str | None) -> str:
    query = {}
    if user_id:
        _ensure_user_list(user_id)
        user_actress_ids = [
            _oid(d["actressId"]) for d in user_actresses_collection.find({"userId": user_id}, {"actressId": 1})
        ]
        query["_id"] = {"$in": user_actress_ids}
    docs = list(actresses_collection.find(query))
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
@limiter.limit("15/minute")
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

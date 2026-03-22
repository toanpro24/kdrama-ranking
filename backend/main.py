import json
import os
import urllib.parse
import urllib.request
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


def _fetch_gallery_photos(person_id: int, name: str, target: int = 10) -> list[str]:
    """Gather photos from multiple sources: TMDB profiles, TMDB tagged images, Wikipedia."""
    gallery: list[str] = []
    seen: set[str] = set()

    def _add(url: str):
        if url not in seen and len(gallery) < target:
            seen.add(url)
            gallery.append(url)

    # Source 1: TMDB profile photos
    try:
        images_data = _tmdb_get(f"/person/{person_id}/images", {})
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
            tagged = _tmdb_get(f"/person/{person_id}/tagged_images", {"page": 1})
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
            req = urllib.request.Request(wiki_url, headers={
                "Accept": "application/json",
                "User-Agent": "KDramaRanking/1.0",
            })
            with urllib.request.urlopen(req, timeout=10) as resp:
                wiki_data = json.loads(resp.read())
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
            req = urllib.request.Request(commons_url, headers={
                "User-Agent": "KDramaRanking/1.0",
            })
            with urllib.request.urlopen(req, timeout=10) as resp:
                commons_data = json.loads(resp.read())
            pages = commons_data.get("query", {}).get("pages", {})
            for page in pages.values():
                info = (page.get("imageinfo") or [{}])[0]
                url = info.get("thumburl") or info.get("url", "")
                if not url:
                    continue
                lower = url.lower()
                if any(skip in lower for skip in [".svg", "icon", "logo", "flag", "map", "emblem"]):
                    continue
                # Only keep reasonably sized images
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
            req = urllib.request.Request(gurl, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                gdata = json.loads(resp.read())
            for item in gdata.get("items", []):
                link = item.get("link", "")
                if link:
                    _add(link)
        except Exception:
            pass

    return gallery


def _backfill_galleries():
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
    import time
    print(f"Backfilling gallery photos for {len(missing)} actresses...")
    for doc in missing:
        name = doc["name"]
        known_drama = doc.get("known", "")
        try:
            person_id = _find_tmdb_person(name, known_drama=known_drama)
            if not person_id:
                continue
            gallery = _fetch_gallery_photos(person_id, name)
            if gallery:
                actresses_collection.update_one({"_id": doc["_id"]}, {"$set": {"gallery": gallery}})
                print(f"  {name}: {len(gallery)} photos")
            time.sleep(0.3)
        except Exception as e:
            print(f"  Error fetching gallery for {name}: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if actresses_collection.count_documents({}) == 0:
        seed()
    _apply_poster_fixes()
    _backfill_galleries()
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


TMDB_API_KEY = os.getenv("TMDB_API_KEY", "017bbf31bbe1016f0dca8bdd9be21ba4")
TMDB_IMG = "https://image.tmdb.org/t/p/w500"
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID", "")


def _tmdb_get(path: str, params: dict) -> dict:
    params["api_key"] = TMDB_API_KEY
    url = f"https://api.themoviedb.org/3{path}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


@app.get("/api/search-actress")
def search_actress_online(q: str):
    """Search TMDB for a Korean actress and return structured data."""
    if not q or len(q) < 2:
        return []
    data = _tmdb_get("/search/person", {"query": q, "language": "en-US"})
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
def get_actress_details_from_tmdb(tmdb_id: int):
    """Fetch full actress details + Korean drama credits from TMDB."""
    person = _tmdb_get(f"/person/{tmdb_id}", {"language": "en-US"})
    credits = _tmdb_get(f"/person/{tmdb_id}/tv_credits", {"language": "en-US"})

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
    gallery = _fetch_gallery_photos(tmdb_id, person.get("name", ""))

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
def create_actress(actress: ActressCreate):
    # Check for duplicate by name (case-insensitive)
    existing = actresses_collection.find_one({"name": {"$regex": f"^{actress.name}$", "$options": "i"}})
    if existing:
        raise HTTPException(status_code=409, detail=f"{actress.name} is already in the database")
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
def get_drama(title: str, user=Depends(get_current_user)):
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
    user_actress_id = None
    if user:
        user_id = user["uid"]
        status_doc = user_drama_status_collection.find_one(
            {"userId": user_id, "dramaTitle": decoded}
        )
        if status_doc:
            user_watch_status = status_doc.get("watchStatus")
            user_actress_id = status_doc.get("actressId")
    if not user_actress_id and results:
        user_actress_id = results[0]["actressId"]

    drama_info = {
        "title": decoded,
        "year": first["year"],
        "poster": first.get("poster"),
        "watchStatus": user_watch_status,
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
            tmdb_data = _tmdb_get("/search/tv", {"query": decoded, "language": "en-US"})
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
                detail = _tmdb_get(f"/tv/{tv_id}", {"language": "en-US"})
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
                        s1 = _tmdb_get(f"/tv/{tv_id}/season/{s1_id}", {"language": "en-US"})
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
            "actressId": s["actressId"],
            "cast": drama.get("cast", []),
        })
    return result


# ── POST reset (re-seed, admin-protected) ──
@app.post("/api/reset", dependencies=[Depends(_require_admin)])
def reset_data():
    seed()
    return {"message": "Data reset to defaults"}


def _find_tmdb_person(name: str, known_drama: str | None = None) -> int | None:
    """Search TMDB for a Korean actress by name.

    If known_drama is provided, cross-reference against each result's known_for
    credits to pick the correct person (avoids wrong matches for common names).
    """
    data = _tmdb_get("/search/person", {"query": name, "language": "en-US"})
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
        # and check if their credits include the known drama
        import time
        for p in actors[:3]:
            try:
                credits = _tmdb_get(f"/person/{p['id']}/tv_credits", {"language": "en-US"})
                credit_titles = set()
                for c in credits.get("cast", []):
                    credit_titles.add(c.get("name", "").lower())
                    credit_titles.add(c.get("original_name", "").lower())
                if known_lower in credit_titles:
                    return p["id"]
                time.sleep(0.2)
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


def _fetch_tmdb_dramas(person_id: int) -> list[dict]:
    """Fetch Korean TV credits for a person from TMDB, classified as drama or show."""
    credits = _tmdb_get(f"/person/{person_id}/tv_credits", {"language": "en-US"})
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
def refresh_all_data():
    """Re-fetch dramas, gallery photos, and profile images for all actresses from TMDB."""
    import time
    actresses = list(actresses_collection.find({}))
    results = {"total": len(actresses), "updated": 0, "failed": []}

    for doc in actresses:
        name = doc["name"]
        known_drama = doc.get("known", "")
        try:
            person_id = _find_tmdb_person(name, known_drama=known_drama)
            if not person_id:
                results["failed"].append(f"{name}: not found on TMDB")
                continue

            # Fetch fresh data
            person = _tmdb_get(f"/person/{person_id}", {"language": "en-US"})
            dramas = _fetch_tmdb_dramas(person_id)
            gallery = _fetch_gallery_photos(person_id, name)
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
            time.sleep(0.4)
        except Exception as e:
            results["failed"].append(f"{name}: {str(e)}")

    return results


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

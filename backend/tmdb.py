"""TMDB API integration — search, fetch details, gallery photos."""

import asyncio
import json
import os
import time
import urllib.parse

import httpx
from fastapi import HTTPException


TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")
TMDB_IMG = "https://image.tmdb.org/t/p/w500"
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID", "")


# ── HTTP client (initialized in lifespan) ──
_http_client: httpx.AsyncClient | None = None


def set_http_client(client: httpx.AsyncClient | None):
    global _http_client
    _http_client = client


def _get_http_client() -> httpx.AsyncClient:
    if _http_client is None:
        raise RuntimeError("HTTP client not initialized")
    return _http_client


# ── TMDB response cache ──
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


# TMDB genre IDs for non-drama TV (variety, reality, talk, game shows)
_SHOW_GENRE_IDS = {10764, 10767, 10766, 10763}  # Reality, Talk, Game Show, News


def _classify_category(genre_ids: list[int]) -> str:
    """Return 'show' for variety/reality/talk/game shows, 'drama' otherwise."""
    if any(gid in _SHOW_GENRE_IDS for gid in genre_ids):
        return "show"
    return "drama"


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

    # Source 5: TMDB drama stills (scene screenshots from Korean dramas)
    if len(gallery) < target:
        try:
            credits = await _tmdb_get(f"/person/{person_id}/tv_credits", {"language": "en-US"})
            for c in credits.get("cast", []):
                if len(gallery) >= target:
                    break
                if c.get("original_language") != "ko":
                    continue
                tv_id = c.get("id")
                if not tv_id:
                    continue
                try:
                    imgs_data = await _tmdb_get(f"/tv/{tv_id}/images", {})
                    backdrops = imgs_data.get("backdrops", [])
                    backdrops.sort(key=lambda b: b.get("vote_average", 0), reverse=True)
                    for b in backdrops[:2]:
                        if b.get("file_path"):
                            _add(f"{TMDB_IMG}{b['file_path']}")
                except Exception:
                    pass
                await asyncio.sleep(0.2)
        except Exception:
            pass

    return gallery


async def _backfill_galleries():
    """Fetch gallery photos for actresses with fewer than 10."""
    from database import actresses_collection

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

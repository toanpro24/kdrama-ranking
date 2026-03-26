"""K-Drama Actress Ranking API — application entry point.

This module creates the FastAPI app, registers middleware, and includes
all route modules. Helper functions and route handlers live in their
respective modules under routes/ and helpers.py.
"""

import os
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from rate_limit import limiter

from database import actresses_collection
from seed import seed
from tmdb import set_http_client, _backfill_galleries, _tmdb_cache

# Import route modules
from routes.actresses import router as actresses_router
from routes.dramas import router as dramas_router
from routes.profiles import router as profiles_router
from routes.social import router as social_router
from routes.leaderboard import router as leaderboard_router
from routes.chat import router as chat_router
from routes.admin import router as admin_router

# ── Re-exports for backward compatibility (tests import from main) ──
from helpers import _oid, _merge_user_data, _ensure_user_list, _get_or_create_profile, TIER_WEIGHT  # noqa: F401
from tmdb import _classify_category, _SHOW_GENRE_IDS, _tmdb_get, _find_tmdb_person  # noqa: F401
from tmdb import _get_http_client, _fetch_gallery_photos, _fetch_tmdb_dramas  # noqa: F401
from tmdb import TMDB_IMG, TMDB_API_KEY  # noqa: F401
from tmdb import _http_client  # noqa: F401
from routes.admin import _require_admin, ADMIN_API_KEY  # noqa: F401

# ── Environment ──
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",") if o.strip()]


# ── Poster fixes (one-time corrections) ──
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


# ── Lifespan ──
@asynccontextmanager
async def lifespan(app: FastAPI):
    client = httpx.AsyncClient(timeout=15, follow_redirects=True)
    set_http_client(client)
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
    await client.aclose()
    set_http_client(None)


# ── App creation ──
app = FastAPI(title="K-Drama Actress Ranking API", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Serve gallery photos as static files
_static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(_static_dir):
    app.mount("/static", StaticFiles(directory=_static_dir), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# ── Include routers ──
app.include_router(actresses_router)
app.include_router(dramas_router)
app.include_router(profiles_router)
app.include_router(social_router)
app.include_router(leaderboard_router)
app.include_router(chat_router)
app.include_router(admin_router)

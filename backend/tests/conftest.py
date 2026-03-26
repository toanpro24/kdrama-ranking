"""Shared fixtures for K-Drama Ranking backend tests."""

import sys
import os
from unittest.mock import MagicMock, patch

import pytest
import httpx
import respx
from bson import ObjectId

# Ensure backend package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ---------------------------------------------------------------------------
# Set env vars BEFORE any app modules are imported
# ---------------------------------------------------------------------------
os.environ.setdefault("FIREBASE_PROJECT_ID", "")
os.environ.setdefault("FIREBASE_CLIENT_EMAIL", "")
os.environ.setdefault("FIREBASE_PRIVATE_KEY", "")
os.environ.setdefault("ADMIN_API_KEY", "test-admin-key")
os.environ.setdefault("TMDB_API_KEY", "fake-tmdb-key")
os.environ.setdefault("MONGODB_URI", "mongodb://localhost:27017")

# ---------------------------------------------------------------------------
# Mock pymongo.MongoClient BEFORE database.py is imported.
# This prevents real DB connections.  database.py does:
#   client = MongoClient(...)
#   db = client[DB_NAME]
#   actresses_collection = db["actresses"]
# With MongoClient mocked, all those are MagicMocks.
# ---------------------------------------------------------------------------
_mock_mongo_client_instance = MagicMock(name="MongoClientInstance")
_mock_db = MagicMock(name="db")
_mock_mongo_client_instance.__getitem__ = MagicMock(return_value=_mock_db)

_mock_actresses = MagicMock(name="actresses_collection")
_mock_rankings = MagicMock(name="user_rankings_collection")
_mock_drama_status = MagicMock(name="user_drama_status_collection")
_mock_user_actresses = MagicMock(name="user_actresses_collection")

# Map collection names to our mocks
def _mock_getitem(name):
    return {
        "actresses": _mock_actresses,
        "user_rankings": _mock_rankings,
        "user_drama_status": _mock_drama_status,
        "user_actresses": _mock_user_actresses,
    }.get(name, MagicMock())

_mock_db.__getitem__ = MagicMock(side_effect=_mock_getitem)

_mongo_patch = patch("pymongo.MongoClient", return_value=_mock_mongo_client_instance)
_mongo_patch.start()

# Now import the app — database.py will use our mock MongoClient
from main import app, _oid, _classify_category, _merge_user_data, _SHOW_GENRE_IDS  # noqa: E402
import main as main_module  # noqa: E402
import tmdb as tmdb_module  # noqa: E402
import helpers as helpers_module  # noqa: E402
import routes.actresses as actresses_route  # noqa: E402
import routes.dramas as dramas_route  # noqa: E402
import routes.profiles as profiles_route  # noqa: E402
import routes.social as social_route  # noqa: E402
import routes.leaderboard as leaderboard_route  # noqa: E402
import routes.chat as chat_route  # noqa: E402
import routes.admin as admin_route  # noqa: E402

# Disable rate limiter for tests so we don't hit rate limits.
# slowapi's Limiter stores this as ._enabled (set via constructor's enabled param).
app.state.limiter.enabled = False

# Patch collection references on ALL modules that imported them.
# pymongo.MongoClient is mocked, so these are already MagicMocks via database.py,
# but we force-assign for safety in case of import ordering issues.
import database as db_module  # noqa: E402
_all_modules_with_collections = [
    db_module, main_module, helpers_module,
    actresses_route, dramas_route, profiles_route, social_route,
    leaderboard_route, chat_route, admin_route,
]
for mod in _all_modules_with_collections:
    if hasattr(mod, "actresses_collection"):
        mod.actresses_collection = _mock_actresses
    if hasattr(mod, "user_rankings_collection"):
        mod.user_rankings_collection = _mock_rankings
    if hasattr(mod, "user_drama_status_collection"):
        mod.user_drama_status_collection = _mock_drama_status
    if hasattr(mod, "user_actresses_collection"):
        mod.user_actresses_collection = _mock_user_actresses

# Also need to mock profiles and follows collections for social/profile routes
_mock_profiles = MagicMock(name="user_profiles_collection")
_mock_follows = MagicMock(name="user_follows_collection")
_mock_leaderboard_cache = MagicMock(name="leaderboard_cache_collection")

for mod in _all_modules_with_collections:
    if hasattr(mod, "user_profiles_collection"):
        mod.user_profiles_collection = _mock_profiles
    if hasattr(mod, "user_follows_collection"):
        mod.user_follows_collection = _mock_follows
    if hasattr(mod, "leaderboard_cache_collection"):
        mod.leaderboard_cache_collection = _mock_leaderboard_cache

db_module.user_profiles_collection = _mock_profiles
db_module.user_follows_collection = _mock_follows
db_module.leaderboard_cache_collection = _mock_leaderboard_cache

# And in seed module
import seed as seed_module  # noqa: E402
seed_module.actresses_collection = _mock_actresses


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MOCK_USER = {
    "uid": "user123",
    "email": "test@example.com",
    "name": "Test User",
    "picture": "https://example.com/photo.jpg",
}

SAMPLE_ACTRESS_ID = str(ObjectId())

SAMPLE_ACTRESS_DOC = {
    "_id": SAMPLE_ACTRESS_ID,
    "name": "Kim Yoo-jung",
    "known": "Love in the Moonlight",
    "genre": "Romance",
    "year": 2016,
    "tier": None,
    "image": "https://example.com/image.jpg",
    "birthDate": "1999-09-22",
    "birthPlace": "Seoul, South Korea",
    "agency": "SidusHQ",
    "dramas": [
        {
            "title": "Love in the Moonlight",
            "year": 2016,
            "role": "Hong Ra-on",
            "poster": "https://example.com/poster.jpg",
            "category": "drama",
        },
        {
            "title": "Backstreet Rookie",
            "year": 2020,
            "role": "Jung Saet-byul",
            "poster": None,
            "category": "drama",
        },
    ],
    "awards": ["Baeksang Arts Award"],
    "gallery": ["https://example.com/g1.jpg"],
}


def _make_doc(doc: dict | None = None) -> dict:
    """Return a fresh copy of a sample doc so tests don't mutate shared state."""
    base = doc or SAMPLE_ACTRESS_DOC
    return {**base, "dramas": [d.copy() for d in base["dramas"]]}


@pytest.fixture(autouse=True)
def _reset_mocks():
    """Reset all collection mocks and TMDB cache before each test."""
    for m in (_mock_actresses, _mock_rankings, _mock_drama_status,
              _mock_user_actresses, _mock_profiles, _mock_follows,
              _mock_leaderboard_cache):
        m.reset_mock(return_value=True, side_effect=True)
    tmdb_module._tmdb_cache.clear()
    # Re-apply defaults that client_authed expects
    _mock_user_actresses.find_one.return_value = {"_id": "existing"}
    _mock_user_actresses.find.return_value = [{"actressId": SAMPLE_ACTRESS_ID}]
    yield


@pytest.fixture()
def actresses_col():
    return _mock_actresses


@pytest.fixture()
def rankings_col():
    return _mock_rankings


@pytest.fixture()
def drama_status_col():
    return _mock_drama_status


@pytest.fixture()
def user_actresses_col():
    return _mock_user_actresses


@pytest.fixture()
def profiles_col():
    return _mock_profiles


@pytest.fixture()
def follows_col():
    return _mock_follows


@pytest.fixture()
def leaderboard_cache_col():
    return _mock_leaderboard_cache


@pytest.fixture()
def mock_user():
    return {**MOCK_USER}


@pytest.fixture()
def sample_actress():
    return _make_doc(SAMPLE_ACTRESS_DOC)


@pytest.fixture()
def sample_actress_id():
    return SAMPLE_ACTRESS_ID


def _override_get_current_user_authed():
    """Dependency override returning an authenticated user."""
    return {**MOCK_USER}


def _override_get_current_user_guest():
    """Dependency override returning None (guest)."""
    return None


def _override_require_user():
    """Dependency override returning an authenticated user."""
    return {**MOCK_USER}


def _override_require_user_denied():
    """Dependency override that raises 401."""
    from fastapi import HTTPException
    raise HTTPException(status_code=401, detail="Authentication required")


@pytest.fixture()
def tmdb_mock():
    """A respx Router that tests can register TMDB mocks on."""
    return respx.Router(assert_all_mocked=False)


@pytest.fixture()
async def client_authed(tmdb_mock):
    """Async test client with authenticated user."""
    from auth import get_current_user, require_user

    app.dependency_overrides[get_current_user] = _override_get_current_user_authed
    app.dependency_overrides[require_user] = _override_require_user

    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def _test_lifespan(a):
        yield

    original_lifespan = app.router.lifespan_context
    app.router.lifespan_context = _test_lifespan

    # Use the tmdb_mock router as the transport so all outgoing requests are intercepted
    tmdb_module.set_http_client(httpx.AsyncClient(
        transport=httpx.MockTransport(tmdb_mock.async_handler),
        timeout=5,
    ))
    # Default: user already has a seeded list (find_one returns a doc)
    _mock_user_actresses.find_one.return_value = {"_id": "existing"}
    # Default: return the actress IDs the user has
    _mock_user_actresses.find.return_value = [{"actressId": SAMPLE_ACTRESS_ID}]
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    await tmdb_module._http_client.aclose()
    tmdb_module.set_http_client(None)

    app.router.lifespan_context = original_lifespan
    app.dependency_overrides.clear()


@pytest.fixture()
async def client_guest(tmdb_mock):
    """Async test client with guest (unauthenticated) user."""
    from auth import get_current_user, require_user

    app.dependency_overrides[get_current_user] = _override_get_current_user_guest
    app.dependency_overrides[require_user] = _override_require_user_denied

    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def _test_lifespan(a):
        yield

    original_lifespan = app.router.lifespan_context
    app.router.lifespan_context = _test_lifespan

    tmdb_module.set_http_client(httpx.AsyncClient(
        transport=httpx.MockTransport(tmdb_mock.async_handler),
        timeout=5,
    ))
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    await tmdb_module._http_client.aclose()
    tmdb_module.set_http_client(None)

    app.router.lifespan_context = original_lifespan
    app.dependency_overrides.clear()


@pytest.fixture()
def mock_tmdb_search_response():
    """Sample TMDB person search response."""
    return {
        "results": [
            {
                "id": 12345,
                "name": "Kim Yoo-jung",
                "known_for_department": "Acting",
                "profile_path": "/abc123.jpg",
                "known_for": [
                    {
                        "media_type": "tv",
                        "name": "Love in the Moonlight",
                        "original_language": "ko",
                    }
                ],
            },
            {
                "id": 99999,
                "name": "Kim Director",
                "known_for_department": "Directing",
                "profile_path": None,
                "known_for": [],
            },
        ]
    }


@pytest.fixture()
def mock_tmdb_person_response():
    """Sample TMDB person detail response."""
    return {
        "id": 12345,
        "name": "Kim Yoo-jung",
        "profile_path": "/abc123.jpg",
        "birthday": "1999-09-22",
        "place_of_birth": "Seoul, South Korea",
    }


@pytest.fixture()
def mock_tmdb_credits_response():
    """Sample TMDB TV credits response."""
    return {
        "cast": [
            {
                "name": "Love in the Moonlight",
                "original_language": "ko",
                "first_air_date": "2016-08-22",
                "poster_path": "/poster1.jpg",
                "character": "Hong Ra-on",
                "genre_ids": [18],
            },
            {
                "name": "Running Man",
                "original_language": "ko",
                "first_air_date": "2010-07-11",
                "poster_path": "/poster2.jpg",
                "character": "Guest",
                "genre_ids": [10764],
            },
            {
                "name": "Non-Korean Show",
                "original_language": "en",
                "first_air_date": "2020-01-01",
                "poster_path": None,
                "character": "Some Role",
                "genre_ids": [18],
            },
        ]
    }


@pytest.fixture()
def mock_tmdb_images_response():
    """Sample TMDB person images response."""
    return {
        "profiles": [
            {"file_path": "/photo1.jpg", "vote_average": 5.5},
            {"file_path": "/photo2.jpg", "vote_average": 4.0},
        ]
    }

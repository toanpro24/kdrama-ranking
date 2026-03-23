"""Integration tests for API endpoints."""

import pytest
from unittest.mock import MagicMock, patch
from bson import ObjectId

from tests.conftest import (
    _mock_actresses,
    _mock_rankings,
    _mock_drama_status,
    _mock_user_actresses,
    SAMPLE_ACTRESS_DOC,
    MOCK_USER,
)


def _make_doc(base=None):
    """Fresh copy of sample actress doc."""
    doc = dict(base or SAMPLE_ACTRESS_DOC)
    doc["dramas"] = [d.copy() for d in doc["dramas"]]
    return doc


# ── GET /api/actresses ──


class TestGetActresses:
    @pytest.mark.anyio
    async def test_returns_list(self, client_authed, actresses_col):
        doc = _make_doc()
        actresses_col.find.return_value = [doc]
        _mock_rankings.find.return_value = []
        _mock_drama_status.find.return_value = []

        resp = await client_authed.get("/api/actresses")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["name"] == "Kim Yoo-jung"

    @pytest.mark.anyio
    async def test_genre_filter(self, client_authed, actresses_col):
        actresses_col.find.return_value = []
        _mock_rankings.find.return_value = []
        _mock_drama_status.find.return_value = []

        resp = await client_authed.get("/api/actresses", params={"genre": "Comedy"})
        assert resp.status_code == 200
        # Verify find was called with genre filter
        call_args = actresses_col.find.call_args[0][0]
        assert call_args["genre"] == "Comedy"

    @pytest.mark.anyio
    async def test_search_filter(self, client_authed, actresses_col):
        actresses_col.find.return_value = []
        _mock_rankings.find.return_value = []
        _mock_drama_status.find.return_value = []

        resp = await client_authed.get("/api/actresses", params={"search": "Kim"})
        assert resp.status_code == 200
        call_args = actresses_col.find.call_args[0][0]
        assert "$or" in call_args

    @pytest.mark.anyio
    async def test_empty_result(self, client_authed, actresses_col):
        actresses_col.find.return_value = []
        _mock_rankings.find.return_value = []
        _mock_drama_status.find.return_value = []

        resp = await client_authed.get("/api/actresses")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.anyio
    async def test_guest_access(self, client_guest, actresses_col):
        doc = _make_doc()
        actresses_col.find.return_value = [doc]

        resp = await client_guest.get("/api/actresses")
        assert resp.status_code == 200
        data = resp.json()
        # Guest: tier should be None
        assert data[0]["tier"] is None


# ── GET /api/actresses/{id} ──


class TestGetActressById:
    @pytest.mark.anyio
    async def test_found(self, client_authed, actresses_col, sample_actress_id):
        doc = _make_doc()
        doc["_id"] = ObjectId(sample_actress_id)
        actresses_col.find_one.return_value = doc
        _mock_rankings.find.return_value = []
        _mock_drama_status.find.return_value = []

        resp = await client_authed.get(f"/api/actresses/{sample_actress_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Kim Yoo-jung"

    @pytest.mark.anyio
    async def test_not_found(self, client_authed, actresses_col, sample_actress_id):
        actresses_col.find_one.return_value = None

        resp = await client_authed.get(f"/api/actresses/{sample_actress_id}")
        assert resp.status_code == 404

    @pytest.mark.anyio
    async def test_invalid_id(self, client_authed):
        resp = await client_authed.get("/api/actresses/bad-id")
        assert resp.status_code == 400


# ── POST /api/actresses ──


class TestCreateActress:
    @pytest.mark.anyio
    async def test_create_new(self, client_authed, actresses_col):
        actresses_col.find_one.return_value = None  # no duplicate
        mock_result = MagicMock()
        mock_result.inserted_id = ObjectId()
        actresses_col.insert_one.return_value = mock_result

        payload = {"name": "Shin Hye-sun", "genre": "Romance", "year": 2020}
        resp = await client_authed.post("/api/actresses", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Shin Hye-sun"
        assert data["tier"] is None

    @pytest.mark.anyio
    async def test_duplicate_name_adds_to_user_list(self, client_authed, actresses_col):
        """When an actress already exists, logged-in user gets her added to their list."""
        existing_id = ObjectId()
        existing_doc = {
            "_id": existing_id, "name": "Shin Hye-sun", "known": "Mr. Queen",
            "genre": "Romance", "year": 2021, "dramas": [], "awards": [], "gallery": [],
        }
        actresses_col.find_one.return_value = existing_doc

        payload = {"name": "Shin Hye-sun"}
        resp = await client_authed.post("/api/actresses", json=payload)
        assert resp.status_code == 201
        assert resp.json()["name"] == "Shin Hye-sun"
        _mock_user_actresses.update_one.assert_called_once()

    @pytest.mark.anyio
    async def test_duplicate_name_409_guest(self, client_guest, actresses_col):
        """Guests still get 409 for duplicates."""
        actresses_col.find_one.return_value = {"_id": ObjectId(), "name": "Shin Hye-sun"}

        payload = {"name": "Shin Hye-sun"}
        resp = await client_guest.post("/api/actresses", json=payload)
        assert resp.status_code == 409


# ── PATCH /api/actresses/{id}/tier ──


class TestUpdateTier:
    @pytest.mark.anyio
    async def test_update_tier(self, client_authed, actresses_col, sample_actress_id):
        actresses_col.find_one.return_value = {"_id": ObjectId(sample_actress_id)}

        resp = await client_authed.patch(
            f"/api/actresses/{sample_actress_id}/tier",
            json={"tier": "s"},
        )
        assert resp.status_code == 200
        assert resp.json()["tier"] == "s"
        _mock_rankings.update_one.assert_called_once()

    @pytest.mark.anyio
    async def test_remove_tier(self, client_authed, actresses_col, sample_actress_id):
        actresses_col.find_one.return_value = {"_id": ObjectId(sample_actress_id)}

        resp = await client_authed.patch(
            f"/api/actresses/{sample_actress_id}/tier",
            json={"tier": None},
        )
        assert resp.status_code == 200
        _mock_rankings.delete_one.assert_called_once()

    @pytest.mark.anyio
    async def test_tier_requires_auth(self, client_guest, sample_actress_id):
        resp = await client_guest.patch(
            f"/api/actresses/{sample_actress_id}/tier",
            json={"tier": "a"},
        )
        assert resp.status_code == 401


# ── PATCH /api/actresses/{id}/dramas/{title}/rating ──


class TestRateDrama:
    @pytest.mark.anyio
    async def test_rate_drama_authenticated(self, client_authed, actresses_col, sample_actress_id):
        actresses_col.find_one.return_value = {
            "_id": ObjectId(sample_actress_id),
            "dramas": [{"title": "Love in the Moonlight"}],
        }

        resp = await client_authed.patch(
            f"/api/actresses/{sample_actress_id}/dramas/Love%20in%20the%20Moonlight/rating",
            json={"rating": 9},
        )
        assert resp.status_code == 200
        assert resp.json()["rating"] == 9
        _mock_drama_status.update_one.assert_called_once()

    @pytest.mark.anyio
    async def test_rate_drama_unauthenticated(self, client_guest, sample_actress_id):
        resp = await client_guest.patch(
            f"/api/actresses/{sample_actress_id}/dramas/Love%20in%20the%20Moonlight/rating",
            json={"rating": 9},
        )
        assert resp.status_code == 401

    @pytest.mark.anyio
    async def test_rate_drama_invalid_rating(self, client_authed, actresses_col, sample_actress_id):
        actresses_col.find_one.return_value = {
            "_id": ObjectId(sample_actress_id),
            "dramas": [{"title": "Love in the Moonlight"}],
        }

        resp = await client_authed.patch(
            f"/api/actresses/{sample_actress_id}/dramas/Love%20in%20the%20Moonlight/rating",
            json={"rating": 15},
        )
        assert resp.status_code == 400


# ── PATCH /api/actresses/{id}/dramas/{title}/watch-status ──


class TestUpdateWatchStatus:
    @pytest.mark.anyio
    async def test_update_watch_status(self, client_authed, actresses_col, sample_actress_id):
        actresses_col.find_one.return_value = {
            "_id": ObjectId(sample_actress_id),
            "dramas": [{"title": "Love in the Moonlight"}],
        }

        resp = await client_authed.patch(
            f"/api/actresses/{sample_actress_id}/dramas/Love%20in%20the%20Moonlight/watch-status",
            json={"watchStatus": "watched"},
        )
        assert resp.status_code == 200
        assert resp.json()["watchStatus"] == "watched"

    @pytest.mark.anyio
    async def test_invalid_watch_status(self, client_authed, actresses_col, sample_actress_id):
        actresses_col.find_one.return_value = {
            "_id": ObjectId(sample_actress_id),
            "dramas": [{"title": "Love in the Moonlight"}],
        }

        resp = await client_authed.patch(
            f"/api/actresses/{sample_actress_id}/dramas/Love%20in%20the%20Moonlight/watch-status",
            json={"watchStatus": "invalid_status"},
        )
        assert resp.status_code == 400

    @pytest.mark.anyio
    async def test_watch_status_requires_auth(self, client_guest, sample_actress_id):
        resp = await client_guest.patch(
            f"/api/actresses/{sample_actress_id}/dramas/Love%20in%20the%20Moonlight/watch-status",
            json={"watchStatus": "watched"},
        )
        assert resp.status_code == 401


# ── DELETE /api/actresses/{id} ──


class TestDeleteActress:
    @pytest.mark.anyio
    async def test_delete_removes_from_user_list(self, client_authed, sample_actress_id):
        """Authenticated user can remove actress from their personal list."""
        mock_result = MagicMock()
        mock_result.deleted_count = 1
        _mock_user_actresses.delete_one.return_value = mock_result

        resp = await client_authed.delete(f"/api/actresses/{sample_actress_id}")
        assert resp.status_code == 200
        assert resp.json()["deleted"] == sample_actress_id
        _mock_user_actresses.delete_one.assert_called_once()

    @pytest.mark.anyio
    async def test_delete_not_in_list_404(self, client_authed, sample_actress_id):
        """Returns 404 if actress not in user's list."""
        mock_result = MagicMock()
        mock_result.deleted_count = 0
        _mock_user_actresses.delete_one.return_value = mock_result

        resp = await client_authed.delete(f"/api/actresses/{sample_actress_id}")
        assert resp.status_code == 404

    @pytest.mark.anyio
    async def test_delete_guest_401(self, client_guest, sample_actress_id):
        """Guests cannot delete actresses."""
        resp = await client_guest.delete(f"/api/actresses/{sample_actress_id}")
        assert resp.status_code == 401


# ── GET /api/stats ──


class TestGetStats:
    @pytest.mark.anyio
    async def test_stats_returns_object(self, client_authed, actresses_col):
        actresses_col.aggregate.return_value = [
            {"_id": "Romance", "count": 5},
            {"_id": "Thriller", "count": 2},
        ]
        actresses_col.count_documents.return_value = 7
        _mock_rankings.aggregate.return_value = [
            {"_id": "s", "count": 3},
            {"_id": "a", "count": 2},
        ]

        resp = await client_authed.get("/api/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "ranked" in data
        assert "genreCounts" in data
        assert "tierCounts" in data
        assert data["total"] == 7

    @pytest.mark.anyio
    async def test_stats_guest(self, client_guest, actresses_col):
        actresses_col.aggregate.return_value = [{"_id": "Romance", "count": 3}]
        actresses_col.count_documents.return_value = 3

        resp = await client_guest.get("/api/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ranked"] == 0
        assert data["tierCounts"] == {}


# ── GET /api/watchlist ──


class TestGetWatchlist:
    @pytest.mark.anyio
    async def test_watchlist_requires_auth(self, client_guest):
        resp = await client_guest.get("/api/watchlist")
        assert resp.status_code == 401

    @pytest.mark.anyio
    async def test_watchlist_empty(self, client_authed):
        _mock_drama_status.find.return_value = []

        resp = await client_authed.get("/api/watchlist")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.anyio
    async def test_watchlist_with_data(self, client_authed, actresses_col):
        _mock_drama_status.find.return_value = [
            {
                "userId": "user123",
                "actressId": "a1",
                "dramaTitle": "Love in the Moonlight",
                "watchStatus": "watched",
            }
        ]
        actresses_col.aggregate.return_value = [
            {
                "_id": "Love in the Moonlight",
                "year": 2016,
                "poster": "https://example.com/poster.jpg",
                "cast": [{"actressId": "a1", "actressName": "Kim Yoo-jung", "role": "Hong Ra-on"}],
            }
        ]

        resp = await client_authed.get("/api/watchlist")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["title"] == "Love in the Moonlight"
        assert data[0]["watchStatus"] == "watched"


# ── POST /api/reset ──


class TestReset:
    @pytest.mark.anyio
    async def test_reset_requires_auth(self, client_guest):
        resp = await client_guest.post("/api/reset")
        assert resp.status_code == 401

    @pytest.mark.anyio
    async def test_reset_clears_user_data(self, client_authed):
        resp = await client_authed.post("/api/reset")
        assert resp.status_code == 200
        assert resp.json()["message"] == "List reset to 36 default actresses"
        _mock_user_actresses.delete_many.assert_called()
        _mock_rankings.delete_many.assert_called()


class TestClearTiers:
    @pytest.mark.anyio
    async def test_clear_tiers_requires_auth(self, client_guest):
        resp = await client_guest.post("/api/clear-tiers")
        assert resp.status_code == 401

    @pytest.mark.anyio
    async def test_clear_tiers_authenticated(self, client_authed):
        mock_result = MagicMock()
        mock_result.deleted_count = 5
        _mock_rankings.delete_many.return_value = mock_result

        resp = await client_authed.post("/api/clear-tiers")
        assert resp.status_code == 200
        assert "Cleared" in resp.json()["message"]

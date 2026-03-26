"""Tests for leaderboard, trending, community stats, and compare endpoints."""

import pytest
from unittest.mock import MagicMock
from bson import ObjectId

from tests.conftest import (
    _mock_profiles,
    _mock_rankings,
    _mock_actresses,
    _mock_user_actresses,
    _mock_drama_status,
    _mock_leaderboard_cache,
    MOCK_USER,
)


ACTRESS_ID_1 = str(ObjectId())
ACTRESS_ID_2 = str(ObjectId())


class TestLeaderboard:
    @pytest.mark.anyio
    async def test_leaderboard_from_cache(self, client_authed):
        cached_entries = [
            {"actressId": ACTRESS_ID_1, "name": "Test", "avgScore": 8.0, "rank": 1,
             "totalLists": 5, "topTierCount": 3, "genre": "Romance", "tierCounts": {}},
        ]
        _mock_leaderboard_cache.find_one.return_value = {
            "entries": cached_entries,
            "totalUsers": 10,
        }

        resp = await client_authed.get("/api/leaderboard")
        assert resp.status_code == 200
        data = resp.json()
        assert "entries" in data
        assert "totalUsers" in data
        assert data["totalUsers"] == 10
        assert len(data["entries"]) == 1

    @pytest.mark.anyio
    async def test_leaderboard_builds_from_db(self, client_authed, profiles_col):
        _mock_leaderboard_cache.find_one.return_value = None
        profiles_col.find.return_value = [{"userId": "u1"}]
        _mock_rankings.find.return_value = [
            {"userId": "u1", "actressId": ACTRESS_ID_1, "tier": "s"},
        ]
        _mock_actresses.find.return_value = [{
            "_id": ObjectId(ACTRESS_ID_1), "name": "Test Actress",
            "image": None, "known": "Drama", "genre": "Romance",
        }]

        resp = await client_authed.get("/api/leaderboard")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["entries"]) == 1
        assert data["entries"][0]["name"] == "Test Actress"
        assert data["entries"][0]["avgScore"] == 8.0
        _mock_leaderboard_cache.insert_one.assert_called_once()

    @pytest.mark.anyio
    async def test_leaderboard_empty(self, client_authed, profiles_col):
        _mock_leaderboard_cache.find_one.return_value = None
        profiles_col.find.return_value = []

        resp = await client_authed.get("/api/leaderboard")
        assert resp.status_code == 200
        data = resp.json()
        assert data["entries"] == []
        assert data["totalUsers"] == 0

    @pytest.mark.anyio
    async def test_leaderboard_genre_filter(self, client_authed):
        _mock_leaderboard_cache.find_one.return_value = {
            "entries": [
                {"actressId": "1", "name": "A", "avgScore": 8.0, "rank": 1,
                 "totalLists": 5, "topTierCount": 3, "genre": "Romance", "tierCounts": {}},
                {"actressId": "2", "name": "B", "avgScore": 7.0, "rank": 2,
                 "totalLists": 3, "topTierCount": 1, "genre": "Thriller", "tierCounts": {}},
            ],
            "totalUsers": 10,
        }

        resp = await client_authed.get("/api/leaderboard", params={"genre": "Romance"})
        data = resp.json()
        assert len(data["entries"]) == 1
        assert data["entries"][0]["genre"] == "Romance"

    @pytest.mark.anyio
    async def test_leaderboard_sort_by_lists(self, client_authed):
        _mock_leaderboard_cache.find_one.return_value = {
            "entries": [
                {"actressId": "1", "name": "A", "avgScore": 10.0, "rank": 1,
                 "totalLists": 1, "topTierCount": 1, "genre": "Romance", "tierCounts": {}},
                {"actressId": "2", "name": "B", "avgScore": 5.0, "rank": 2,
                 "totalLists": 10, "topTierCount": 5, "genre": "Romance", "tierCounts": {}},
            ],
            "totalUsers": 10,
        }

        resp = await client_authed.get("/api/leaderboard", params={"sort": "lists"})
        data = resp.json()
        assert data["entries"][0]["name"] == "B"  # More lists


class TestLeaderboardPagination:
    @pytest.mark.anyio
    async def test_pagination_metadata(self, client_authed):
        _mock_leaderboard_cache.find_one.return_value = {
            "entries": [
                {"actressId": str(ObjectId()), "name": f"A{i}", "avgScore": 10 - i, "rank": i + 1,
                 "totalLists": 5, "topTierCount": 3, "genre": "Romance", "tierCounts": {}}
                for i in range(5)
            ],
            "totalUsers": 10,
        }

        resp = await client_authed.get("/api/leaderboard", params={"page": 1, "pageSize": 2})
        data = resp.json()
        assert data["total"] == 5
        assert data["page"] == 1
        assert data["pageSize"] == 2
        assert len(data["entries"]) == 2

    @pytest.mark.anyio
    async def test_pagination_page_2(self, client_authed):
        _mock_leaderboard_cache.find_one.return_value = {
            "entries": [
                {"actressId": str(ObjectId()), "name": f"A{i}", "avgScore": 10 - i, "rank": i + 1,
                 "totalLists": 5, "topTierCount": 3, "genre": "Romance", "tierCounts": {}}
                for i in range(5)
            ],
            "totalUsers": 10,
        }

        resp = await client_authed.get("/api/leaderboard", params={"page": 2, "pageSize": 2})
        data = resp.json()
        assert len(data["entries"]) == 2
        assert data["entries"][0]["name"] == "A2"

    @pytest.mark.anyio
    async def test_pagination_last_page(self, client_authed):
        _mock_leaderboard_cache.find_one.return_value = {
            "entries": [
                {"actressId": str(ObjectId()), "name": f"A{i}", "avgScore": 10 - i, "rank": i + 1,
                 "totalLists": 5, "topTierCount": 3, "genre": "Romance", "tierCounts": {}}
                for i in range(5)
            ],
            "totalUsers": 10,
        }

        resp = await client_authed.get("/api/leaderboard", params={"page": 3, "pageSize": 2})
        data = resp.json()
        assert len(data["entries"]) == 1  # Only 1 left on page 3

    @pytest.mark.anyio
    async def test_pagination_clamps_page_size(self, client_authed):
        _mock_leaderboard_cache.find_one.return_value = {
            "entries": [], "totalUsers": 0,
        }

        resp = await client_authed.get("/api/leaderboard", params={"pageSize": 999})
        data = resp.json()
        assert data["pageSize"] == 100  # Clamped to max


class TestCommunityStats:
    @pytest.mark.anyio
    async def test_community_stats(self, client_authed, profiles_col):
        profiles_col.find.return_value = [{"userId": "u1"}]
        _mock_rankings.find.return_value = [
            {"userId": "u1", "actressId": ACTRESS_ID_1, "tier": "s"},
        ]
        # Leaderboard cache
        _mock_leaderboard_cache.find_one.return_value = {
            "entries": [{"actressId": ACTRESS_ID_1, "rank": 1}],
            "totalUsers": 1,
        }

        resp = await client_authed.get(f"/api/actresses/{ACTRESS_ID_1}/community")
        assert resp.status_code == 200
        data = resp.json()
        assert data["totalLists"] == 1
        assert data["avgScore"] > 0
        assert data["rank"] == 1

    @pytest.mark.anyio
    async def test_community_stats_no_public_users(self, client_authed, profiles_col):
        profiles_col.find.return_value = []

        resp = await client_authed.get(f"/api/actresses/{ACTRESS_ID_1}/community")
        assert resp.status_code == 200
        data = resp.json()
        assert data["totalLists"] == 0
        assert data["rank"] is None


class TestCompare:
    @pytest.mark.anyio
    async def test_compare_two_users(self, client_authed, profiles_col, actresses_col):
        profile1 = {
            "_id": ObjectId(), "userId": "u1", "displayName": "Alice",
            "shareSlug": "alice", "tierListVisibility": "public", "picture": "",
        }
        profile2 = {
            "_id": ObjectId(), "userId": "u2", "displayName": "Bob",
            "shareSlug": "bob", "tierListVisibility": "public", "picture": "",
        }
        profiles_col.find_one.side_effect = [profile1, profile2]
        _mock_user_actresses.find.return_value = [{"actressId": ACTRESS_ID_1}]
        actresses_col.find.return_value = [{
            "_id": ACTRESS_ID_1, "name": "Test", "image": None,
            "known": "Drama", "genre": "Romance",
        }]
        _mock_rankings.find.return_value = [
            {"actressId": ACTRESS_ID_1, "tier": "s"},
        ]
        _mock_drama_status.find.return_value = []

        resp = await client_authed.get("/api/compare/alice/bob")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["users"]) == 2
        assert "stats" in data
        assert "commonActresses" in data["stats"]

    @pytest.mark.anyio
    async def test_compare_nonexistent_user(self, client_authed, profiles_col):
        profiles_col.find_one.return_value = None

        resp = await client_authed.get("/api/compare/alice/nobody")
        assert resp.status_code == 404

    @pytest.mark.anyio
    async def test_compare_private_user(self, client_authed, profiles_col):
        profiles_col.find_one.return_value = {
            "_id": ObjectId(), "userId": "u1", "displayName": "Alice",
            "shareSlug": "alice", "tierListVisibility": "private", "picture": "",
        }

        resp = await client_authed.get("/api/compare/alice/bob")
        assert resp.status_code == 403


class TestTrending:
    @pytest.mark.anyio
    async def test_trending(self, client_authed, profiles_col):
        profiles_col.find.return_value = [{"userId": "u1"}]
        _mock_rankings.find.return_value = [
            {"userId": "u1", "actressId": ACTRESS_ID_1, "tier": "splus"},
        ]
        _mock_actresses.find.return_value = [{
            "_id": ObjectId(ACTRESS_ID_1), "name": "Trending Actress",
            "image": None, "known": "Drama", "genre": "Romance",
        }]

        resp = await client_authed.get("/api/trending")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["entries"]) == 1
        assert data["entries"][0]["name"] == "Trending Actress"
        assert data["entries"][0]["trendScore"] > 0
        assert data["totalUsers"] == 1

    @pytest.mark.anyio
    async def test_trending_empty(self, client_authed, profiles_col):
        profiles_col.find.return_value = []

        resp = await client_authed.get("/api/trending")
        assert resp.status_code == 200
        data = resp.json()
        assert data["entries"] == []
        assert data["totalUsers"] == 0

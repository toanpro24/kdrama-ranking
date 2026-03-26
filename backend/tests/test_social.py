"""Tests for follow system endpoints."""

import pytest
from unittest.mock import MagicMock
from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from tests.conftest import (
    _mock_profiles,
    _mock_follows,
    MOCK_USER,
)


TARGET_PROFILE = {
    "_id": ObjectId(),
    "userId": "target-user-456",
    "displayName": "Target User",
    "shareSlug": "target",
    "tierListVisibility": "public",
    "picture": "",
    "bio": "Drama lover",
}


class TestFollowUser:
    @pytest.mark.anyio
    async def test_follow_success(self, client_authed, profiles_col):
        profiles_col.find_one.return_value = {**TARGET_PROFILE}

        resp = await client_authed.post("/api/follow/target")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
        _mock_follows.insert_one.assert_called_once()

    @pytest.mark.anyio
    async def test_follow_nonexistent_user(self, client_authed, profiles_col):
        profiles_col.find_one.return_value = None

        resp = await client_authed.post("/api/follow/nobody")
        assert resp.status_code == 404

    @pytest.mark.anyio
    async def test_follow_self(self, client_authed, profiles_col):
        # Target profile has the same userId as MOCK_USER
        profiles_col.find_one.return_value = {**TARGET_PROFILE, "userId": "user123"}

        resp = await client_authed.post("/api/follow/myself")
        assert resp.status_code == 400

    @pytest.mark.anyio
    async def test_follow_private_user(self, client_authed, profiles_col):
        profiles_col.find_one.return_value = {**TARGET_PROFILE, "tierListVisibility": "private"}

        resp = await client_authed.post("/api/follow/target")
        assert resp.status_code == 403

    @pytest.mark.anyio
    async def test_follow_already_following(self, client_authed, profiles_col):
        profiles_col.find_one.return_value = {**TARGET_PROFILE}
        _mock_follows.insert_one.side_effect = DuplicateKeyError("duplicate")

        resp = await client_authed.post("/api/follow/target")
        assert resp.status_code == 200  # Idempotent

    @pytest.mark.anyio
    async def test_follow_requires_auth(self, client_guest):
        resp = await client_guest.post("/api/follow/target")
        assert resp.status_code == 401


class TestUnfollowUser:
    @pytest.mark.anyio
    async def test_unfollow_success(self, client_authed, profiles_col):
        profiles_col.find_one.return_value = {**TARGET_PROFILE}

        resp = await client_authed.delete("/api/follow/target")
        assert resp.status_code == 200
        _mock_follows.delete_one.assert_called_once()

    @pytest.mark.anyio
    async def test_unfollow_nonexistent_user(self, client_authed, profiles_col):
        profiles_col.find_one.return_value = None

        resp = await client_authed.delete("/api/follow/nobody")
        assert resp.status_code == 404

    @pytest.mark.anyio
    async def test_unfollow_requires_auth(self, client_guest):
        resp = await client_guest.delete("/api/follow/target")
        assert resp.status_code == 401


class TestGetFollowing:
    @pytest.mark.anyio
    async def test_following_list(self, client_authed, profiles_col):
        _mock_follows.find.return_value = [
            {"followerId": "user123", "followingId": "target-user-456"},
        ]
        profiles_col.find_one.return_value = {**TARGET_PROFILE}

        resp = await client_authed.get("/api/following")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["displayName"] == "Target User"
        assert data[0]["shareSlug"] == "target"

    @pytest.mark.anyio
    async def test_following_empty(self, client_authed):
        _mock_follows.find.return_value = []

        resp = await client_authed.get("/api/following")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.anyio
    async def test_following_skips_private_users(self, client_authed, profiles_col):
        _mock_follows.find.return_value = [
            {"followerId": "user123", "followingId": "private-user"},
        ]
        profiles_col.find_one.return_value = {**TARGET_PROFILE, "tierListVisibility": "private"}

        resp = await client_authed.get("/api/following")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.anyio
    async def test_following_requires_auth(self, client_guest):
        resp = await client_guest.get("/api/following")
        assert resp.status_code == 401


class TestFollowerCount:
    @pytest.mark.anyio
    async def test_counts(self, client_authed):
        _mock_follows.count_documents.side_effect = lambda q: {
            "followingId": 5,
            "followerId": 3,
        }.get(list(q.keys())[0], 0)

        resp = await client_authed.get("/api/followers/count")
        assert resp.status_code == 200
        data = resp.json()
        assert "followers" in data
        assert "following" in data

    @pytest.mark.anyio
    async def test_counts_requires_auth(self, client_guest):
        resp = await client_guest.get("/api/followers/count")
        assert resp.status_code == 401


class TestIsFollowing:
    @pytest.mark.anyio
    async def test_is_following_true(self, client_authed, profiles_col):
        profiles_col.find_one.return_value = {**TARGET_PROFILE}
        _mock_follows.find_one.return_value = {"_id": ObjectId()}

        resp = await client_authed.get("/api/is-following/target")
        assert resp.status_code == 200
        assert resp.json()["following"] is True

    @pytest.mark.anyio
    async def test_is_following_false(self, client_authed, profiles_col):
        profiles_col.find_one.return_value = {**TARGET_PROFILE}
        _mock_follows.find_one.return_value = None

        resp = await client_authed.get("/api/is-following/target")
        assert resp.status_code == 200
        assert resp.json()["following"] is False

    @pytest.mark.anyio
    async def test_is_following_nonexistent_user(self, client_authed, profiles_col):
        profiles_col.find_one.return_value = None

        resp = await client_authed.get("/api/is-following/nobody")
        assert resp.status_code == 200
        assert resp.json()["following"] is False

    @pytest.mark.anyio
    async def test_is_following_requires_auth(self, client_guest):
        resp = await client_guest.get("/api/is-following/target")
        assert resp.status_code == 401

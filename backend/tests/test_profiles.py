"""Tests for profile and shared tier list endpoints."""

import pytest
from unittest.mock import MagicMock
from bson import ObjectId

from tests.conftest import (
    _mock_profiles,
    _mock_user_actresses,
    _mock_actresses,
    _mock_rankings,
    _mock_drama_status,
    _mock_follows,
    MOCK_USER,
    SAMPLE_ACTRESS_ID,
)


SAMPLE_PROFILE = {
    "_id": ObjectId(),
    "userId": "user123",
    "displayName": "Test User",
    "bio": "I love K-dramas",
    "shareSlug": "test-user",
    "tierListVisibility": "public",
    "picture": "https://example.com/photo.jpg",
}


def _make_profile(overrides=None):
    p = {**SAMPLE_PROFILE, "_id": ObjectId()}
    if overrides:
        p.update(overrides)
    return p


class TestGetProfile:
    @pytest.mark.anyio
    async def test_get_existing_profile(self, client_authed, profiles_col):
        profile = _make_profile()
        profiles_col.find_one.return_value = profile

        resp = await client_authed.get("/api/profile")
        assert resp.status_code == 200
        data = resp.json()
        assert data["displayName"] == "Test User"
        assert data["shareSlug"] == "test-user"

    @pytest.mark.anyio
    async def test_get_profile_creates_default(self, client_authed, profiles_col):
        # First call returns None (no profile), then insert_one creates one
        profiles_col.find_one.return_value = None
        mock_result = MagicMock()
        mock_result.inserted_id = ObjectId()
        profiles_col.insert_one.return_value = mock_result

        resp = await client_authed.get("/api/profile")
        assert resp.status_code == 200
        profiles_col.insert_one.assert_called_once()

    @pytest.mark.anyio
    async def test_get_profile_requires_auth(self, client_guest):
        resp = await client_guest.get("/api/profile")
        assert resp.status_code == 401


class TestUpdateProfile:
    @pytest.mark.anyio
    async def test_update_display_name(self, client_authed, profiles_col):
        profiles_col.find_one.return_value = _make_profile()

        resp = await client_authed.put("/api/profile", json={"displayName": "New Name"})
        assert resp.status_code == 200
        profiles_col.update_one.assert_called_once()

    @pytest.mark.anyio
    async def test_update_bio(self, client_authed, profiles_col):
        profiles_col.find_one.return_value = _make_profile()

        resp = await client_authed.put("/api/profile", json={"bio": "K-drama enthusiast"})
        assert resp.status_code == 200

    @pytest.mark.anyio
    async def test_update_slug(self, client_authed, profiles_col):
        profiles_col.find_one.side_effect = [
            _make_profile(),  # _get_or_create_profile
            None,             # slug uniqueness check
            _make_profile(),  # return updated profile
        ]

        resp = await client_authed.put("/api/profile", json={"shareSlug": "my-slug"})
        assert resp.status_code == 200

    @pytest.mark.anyio
    async def test_update_slug_taken(self, client_authed, profiles_col):
        profiles_col.find_one.side_effect = [
            _make_profile(),  # _get_or_create_profile
            _make_profile({"userId": "other-user"}),  # slug taken by someone else
        ]

        resp = await client_authed.put("/api/profile", json={"shareSlug": "taken-slug"})
        assert resp.status_code == 409

    @pytest.mark.anyio
    async def test_update_visibility_to_private_removes_followers(self, client_authed, profiles_col):
        profiles_col.find_one.side_effect = [
            _make_profile(),  # _get_or_create_profile
            _make_profile(),  # return updated
        ]

        resp = await client_authed.put("/api/profile", json={"tierListVisibility": "private"})
        assert resp.status_code == 200
        _mock_follows.delete_many.assert_called_once()

    @pytest.mark.anyio
    async def test_update_invalid_visibility(self, client_authed, profiles_col):
        profiles_col.find_one.return_value = _make_profile()

        resp = await client_authed.put("/api/profile", json={"tierListVisibility": "invalid"})
        assert resp.status_code == 400

    @pytest.mark.anyio
    async def test_update_name_too_long(self, client_authed, profiles_col):
        profiles_col.find_one.return_value = _make_profile()

        resp = await client_authed.put("/api/profile", json={"displayName": "x" * 51})
        assert resp.status_code == 400

    @pytest.mark.anyio
    async def test_update_empty_body(self, client_authed, profiles_col):
        profiles_col.find_one.return_value = _make_profile()

        resp = await client_authed.put("/api/profile", json={})
        assert resp.status_code == 400

    @pytest.mark.anyio
    async def test_update_requires_auth(self, client_guest):
        resp = await client_guest.put("/api/profile", json={"displayName": "Test"})
        assert resp.status_code == 401


class TestSharedTierList:
    @pytest.mark.anyio
    async def test_get_public_tier_list(self, client_authed, profiles_col, actresses_col):
        profiles_col.find_one.return_value = _make_profile({"tierListVisibility": "public"})
        _mock_user_actresses.find.return_value = [{"actressId": SAMPLE_ACTRESS_ID}]
        actresses_col.find.return_value = [{
            "_id": SAMPLE_ACTRESS_ID, "name": "Test Actress", "known": "Drama",
            "genre": "Romance", "dramas": [],
        }]
        _mock_rankings.find.return_value = []
        _mock_drama_status.find.return_value = []

        resp = await client_authed.get("/api/shared/test-user")
        assert resp.status_code == 200
        data = resp.json()
        assert data["displayName"] == "Test User"
        assert isinstance(data["actresses"], list)

    @pytest.mark.anyio
    async def test_get_private_tier_list_403(self, client_authed, profiles_col):
        profiles_col.find_one.return_value = _make_profile({"tierListVisibility": "private"})

        resp = await client_authed.get("/api/shared/test-user")
        assert resp.status_code == 403

    @pytest.mark.anyio
    async def test_get_nonexistent_tier_list_404(self, client_authed, profiles_col):
        profiles_col.find_one.return_value = None

        resp = await client_authed.get("/api/shared/nobody")
        assert resp.status_code == 404

    @pytest.mark.anyio
    async def test_link_only_tier_list(self, client_authed, profiles_col, actresses_col):
        profiles_col.find_one.return_value = _make_profile({"tierListVisibility": "link_only"})
        _mock_user_actresses.find.return_value = []
        actresses_col.find.return_value = []
        _mock_rankings.find.return_value = []
        _mock_drama_status.find.return_value = []

        resp = await client_authed.get("/api/shared/test-user")
        assert resp.status_code == 200

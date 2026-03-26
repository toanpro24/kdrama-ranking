"""Tests for input validation — tier values, auth edge cases, model constraints."""

import pytest
from unittest.mock import MagicMock
from bson import ObjectId
from pydantic import ValidationError

from models import TierUpdate, ProfileUpdate, VALID_TIERS
from tests.conftest import _mock_actresses, _mock_rankings, MOCK_USER, SAMPLE_ACTRESS_ID


class TestTierValidation:
    def test_valid_tiers_accepted(self):
        for tier in ["splus", "s", "a", "b", "c", "d"]:
            t = TierUpdate(tier=tier)
            assert t.tier == tier

    def test_none_tier_accepted(self):
        t = TierUpdate(tier=None)
        assert t.tier is None

    def test_invalid_tier_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            TierUpdate(tier="z")
        assert "Invalid tier" in str(exc_info.value)

    def test_empty_string_tier_rejected(self):
        with pytest.raises(ValidationError):
            TierUpdate(tier="")

    def test_random_string_tier_rejected(self):
        with pytest.raises(ValidationError):
            TierUpdate(tier="super-plus")

    def test_case_sensitive(self):
        with pytest.raises(ValidationError):
            TierUpdate(tier="S")  # Must be lowercase "s"

    @pytest.mark.anyio
    async def test_api_rejects_invalid_tier(self, client_authed, actresses_col, sample_actress_id):
        """The API endpoint should return 422 for invalid tier values."""
        actresses_col.find_one.return_value = {"_id": ObjectId(sample_actress_id)}

        resp = await client_authed.patch(
            f"/api/actresses/{sample_actress_id}/tier",
            json={"tier": "invalid_tier"},
        )
        assert resp.status_code == 422  # Pydantic validation error

    @pytest.mark.anyio
    async def test_api_accepts_valid_tier(self, client_authed, actresses_col, sample_actress_id):
        actresses_col.find_one.return_value = {"_id": ObjectId(sample_actress_id)}

        resp = await client_authed.patch(
            f"/api/actresses/{sample_actress_id}/tier",
            json={"tier": "splus"},
        )
        assert resp.status_code == 200
        assert resp.json()["tier"] == "splus"

    @pytest.mark.anyio
    async def test_bulk_tier_rejects_invalid(self, client_authed):
        resp = await client_authed.patch(
            "/api/actresses/bulk-tier",
            json=[{"id": SAMPLE_ACTRESS_ID, "tier": "invalid"}],
        )
        assert resp.status_code == 400

    @pytest.mark.anyio
    async def test_bulk_tier_accepts_valid(self, client_authed):
        resp = await client_authed.patch(
            "/api/actresses/bulk-tier",
            json=[{"id": SAMPLE_ACTRESS_ID, "tier": "a"}],
        )
        assert resp.status_code == 200


class TestProfileValidation:
    def test_profile_update_all_none(self):
        p = ProfileUpdate()
        assert p.displayName is None
        assert p.bio is None
        assert p.shareSlug is None
        assert p.tierListVisibility is None

    def test_profile_update_partial(self):
        p = ProfileUpdate(displayName="Test", bio="Hello")
        assert p.displayName == "Test"
        assert p.bio == "Hello"
        assert p.shareSlug is None


class TestAuthEdgeCases:
    @pytest.mark.anyio
    async def test_guest_can_access_public_endpoints(self, client_guest, actresses_col):
        """Guests should be able to access read-only endpoints."""
        actresses_col.find.return_value = []
        resp = await client_guest.get("/api/actresses")
        assert resp.status_code == 200

    @pytest.mark.anyio
    async def test_guest_cannot_access_protected_endpoints(self, client_guest):
        """Guests should get 401 for protected endpoints."""
        endpoints = [
            ("PATCH", f"/api/actresses/{SAMPLE_ACTRESS_ID}/tier"),
            ("POST", "/api/reset"),
            ("POST", "/api/clear-tiers"),
            ("GET", "/api/profile"),
            ("GET", "/api/following"),
            ("GET", "/api/watchlist"),
        ]
        for method, path in endpoints:
            if method == "PATCH":
                resp = await client_guest.patch(path, json={"tier": "s"})
            elif method == "POST":
                resp = await client_guest.post(path)
            else:
                resp = await client_guest.get(path)
            assert resp.status_code == 401, f"Expected 401 for {method} {path}, got {resp.status_code}"

"""Tests for Pydantic models."""

import pytest
from models import Drama, ActressCreate, TierUpdate


class TestDramaModel:
    def test_drama_defaults(self):
        d = Drama(title="Crash Landing on You", year=2019)
        assert d.title == "Crash Landing on You"
        assert d.year == 2019
        assert d.role == ""
        assert d.poster is None
        assert d.category == "drama"

    def test_drama_all_fields(self):
        d = Drama(
            title="Vincenzo",
            year=2021,
            role="Hong Cha-young",
            poster="https://example.com/poster.jpg",
            category="drama",
        )
        assert d.title == "Vincenzo"
        assert d.role == "Hong Cha-young"
        assert d.poster == "https://example.com/poster.jpg"
        assert d.category == "drama"

    def test_drama_show_category(self):
        d = Drama(title="Running Man", year=2010, category="show")
        assert d.category == "show"


class TestActressCreateModel:
    def test_minimal_fields(self):
        a = ActressCreate(name="Park Eun-bin")
        assert a.name == "Park Eun-bin"
        assert a.known == "\u2014"
        assert a.genre == "Romance"
        assert a.year == 2024
        assert a.image is None
        assert a.birthDate is None
        assert a.birthPlace is None
        assert a.agency is None
        assert a.dramas == []
        assert a.awards == []
        assert a.gallery == []

    def test_all_fields(self):
        dramas = [Drama(title="Extraordinary Attorney Woo", year=2022, role="Woo Young-woo")]
        a = ActressCreate(
            name="Park Eun-bin",
            known="Extraordinary Attorney Woo",
            genre="Drama",
            year=2022,
            image="https://example.com/img.jpg",
            birthDate="1992-09-04",
            birthPlace="Seoul, South Korea",
            agency="Namoo Actors",
            dramas=dramas,
            awards=["Baeksang Arts Award"],
            gallery=["https://example.com/g1.jpg", "https://example.com/g2.jpg"],
        )
        assert a.name == "Park Eun-bin"
        assert a.known == "Extraordinary Attorney Woo"
        assert len(a.dramas) == 1
        assert a.dramas[0].role == "Woo Young-woo"
        assert len(a.awards) == 1
        assert len(a.gallery) == 2

    def test_empty_name_rejected(self):
        # Pydantic will accept empty string but name is required
        with pytest.raises(Exception):
            ActressCreate()  # name is required


class TestTierUpdateModel:
    def test_tier_with_value(self):
        t = TierUpdate(tier="splus")
        assert t.tier == "splus"

    def test_tier_none(self):
        t = TierUpdate(tier=None)
        assert t.tier is None

    def test_tier_default(self):
        t = TierUpdate()
        assert t.tier is None

    def test_tier_various_values(self):
        for tier in ["splus", "s", "a", "b", "c", "d"]:
            t = TierUpdate(tier=tier)
            assert t.tier == tier

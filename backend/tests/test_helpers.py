"""Tests for helper functions in main.py."""

import pytest
from unittest.mock import MagicMock
from bson import ObjectId
from fastapi import HTTPException

from tests.conftest import _mock_rankings, _mock_drama_status
from main import _oid, _classify_category, _merge_user_data, _SHOW_GENRE_IDS


class TestOid:
    def test_valid_object_id(self):
        valid = str(ObjectId())
        result = _oid(valid)
        assert isinstance(result, ObjectId)
        assert str(result) == valid

    def test_another_valid_id(self):
        oid = ObjectId()
        result = _oid(str(oid))
        assert result == oid

    def test_invalid_string_raises_400(self):
        with pytest.raises(HTTPException) as exc_info:
            _oid("not-a-valid-id")
        assert exc_info.value.status_code == 400
        assert "Invalid actress ID" in exc_info.value.detail

    def test_empty_string_raises_400(self):
        with pytest.raises(HTTPException) as exc_info:
            _oid("")
        assert exc_info.value.status_code == 400

    def test_short_hex_raises_400(self):
        with pytest.raises(HTTPException) as exc_info:
            _oid("abc123")
        assert exc_info.value.status_code == 400


class TestClassifyCategory:
    def test_drama_genre_ids(self):
        # Genre 18 = Drama on TMDB
        assert _classify_category([18]) == "drama"
        assert _classify_category([18, 35]) == "drama"

    def test_reality_show(self):
        assert _classify_category([10764]) == "show"

    def test_talk_show(self):
        assert _classify_category([10767]) == "show"

    def test_game_show(self):
        assert _classify_category([10766]) == "show"

    def test_news_show(self):
        assert _classify_category([10763]) == "show"

    def test_mixed_with_show_genre(self):
        # If any show genre is present, it's a show
        assert _classify_category([18, 10764]) == "show"

    def test_empty_list(self):
        assert _classify_category([]) == "drama"

    def test_unknown_genre_defaults_to_drama(self):
        assert _classify_category([99999]) == "drama"


class TestMergeUserData:
    def test_guest_no_user_id(self):
        docs = [
            {
                "_id": "abc123",
                "name": "Test",
                "dramas": [
                    {"title": "Drama A", "year": 2020},
                    {"title": "Drama B", "year": 2021},
                ],
            }
        ]
        result = _merge_user_data(docs, None)
        assert result[0]["tier"] is None
        assert result[0]["dramas"][0]["rating"] is None
        assert result[0]["dramas"][0]["watchStatus"] is None
        assert result[0]["dramas"][1]["rating"] is None

    def test_guest_multiple_docs(self):
        docs = [
            {"_id": "a", "name": "A", "dramas": [{"title": "D1"}]},
            {"_id": "b", "name": "B", "dramas": []},
        ]
        result = _merge_user_data(docs, None)
        assert all(d["tier"] is None for d in result)

    def test_authenticated_user_with_rankings(self):
        docs = [
            {
                "_id": "actress1",
                "name": "Test",
                "dramas": [{"title": "My Drama", "year": 2022}],
            }
        ]
        # Mock rankings query
        _mock_rankings.find.return_value = [
            {"actressId": "actress1", "tier": "s"}
        ]
        # Mock drama status query
        _mock_drama_status.find.return_value = [
            {
                "actressId": "actress1",
                "dramaTitle": "My Drama",
                "rating": 9,
                "watchStatus": "watched",
            }
        ]

        result = _merge_user_data(docs, "user123")
        assert result[0]["tier"] == "s"
        assert result[0]["dramas"][0]["rating"] == 9
        assert result[0]["dramas"][0]["watchStatus"] == "watched"

    def test_authenticated_user_no_rankings(self):
        docs = [
            {
                "_id": "actress1",
                "name": "Test",
                "dramas": [{"title": "Some Drama"}],
            }
        ]
        _mock_rankings.find.return_value = []
        _mock_drama_status.find.return_value = []

        result = _merge_user_data(docs, "user123")
        assert result[0]["tier"] is None
        assert result[0]["dramas"][0]["rating"] is None
        assert result[0]["dramas"][0]["watchStatus"] is None

    def test_authenticated_user_partial_data(self):
        docs = [
            {
                "_id": "actress1",
                "name": "Test",
                "dramas": [
                    {"title": "Drama A"},
                    {"title": "Drama B"},
                ],
            }
        ]
        _mock_rankings.find.return_value = [
            {"actressId": "actress1", "tier": "a"}
        ]
        # Only Drama A has status
        _mock_drama_status.find.return_value = [
            {
                "actressId": "actress1",
                "dramaTitle": "Drama A",
                "rating": 8,
                "watchStatus": "watched",
            }
        ]

        result = _merge_user_data(docs, "user123")
        assert result[0]["tier"] == "a"
        assert result[0]["dramas"][0]["rating"] == 8
        assert result[0]["dramas"][1]["rating"] is None
        assert result[0]["dramas"][1]["watchStatus"] is None

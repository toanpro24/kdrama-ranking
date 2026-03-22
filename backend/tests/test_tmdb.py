"""Tests for TMDB-related endpoints and helpers."""

import pytest
from httpx import Response

from tests.conftest import _mock_actresses, _mock_rankings, _mock_drama_status


TMDB_BASE = "https://api.themoviedb.org/3"
TMDB_IMG = "https://image.tmdb.org/t/p/w500"
WIKI_BASE = "https://en.wikipedia.org/api/rest_v1"
COMMONS_BASE = "https://commons.wikimedia.org/w/api.php"


def _mock_gallery_sources(router, tmdb_id, images_resp=None):
    """Register mocks for all gallery-related external endpoints."""
    if images_resp is None:
        images_resp = {"profiles": []}
    router.get(url__regex=rf".*/person/{tmdb_id}/images.*").mock(
        return_value=Response(200, json=images_resp)
    )
    router.get(url__regex=rf".*/person/{tmdb_id}/tagged_images.*").mock(
        return_value=Response(200, json={"results": []})
    )
    router.get(url__startswith=WIKI_BASE).mock(
        return_value=Response(200, json={"items": []})
    )
    router.get(url__startswith=COMMONS_BASE).mock(
        return_value=Response(200, json={"query": {"pages": {}}})
    )


class TestSearchActressOnline:
    @pytest.mark.anyio
    async def test_search_returns_results(self, tmdb_mock, client_authed, mock_tmdb_search_response):
        tmdb_mock.get(url__regex=r".*/search/person.*").mock(
            return_value=Response(200, json=mock_tmdb_search_response)
        )

        resp = await client_authed.get("/api/search-actress", params={"q": "Kim Yoo-jung"})
        assert resp.status_code == 200
        data = resp.json()
        # Should filter out non-Acting (Director)
        assert len(data) == 1
        assert data[0]["name"] == "Kim Yoo-jung"
        assert data[0]["tmdbId"] == 12345
        assert data[0]["knownFor"] == "Love in the Moonlight"
        assert TMDB_IMG in data[0]["image"]

    @pytest.mark.anyio
    async def test_search_short_query(self, client_authed):
        resp = await client_authed.get("/api/search-actress", params={"q": "K"})
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.anyio
    async def test_search_empty_results(self, tmdb_mock, client_authed):
        tmdb_mock.get(url__regex=r".*/search/person.*").mock(
            return_value=Response(200, json={"results": []})
        )

        resp = await client_authed.get("/api/search-actress", params={"q": "Nonexistent Person"})
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.anyio
    async def test_search_no_profile_path(self, tmdb_mock, client_authed):
        tmdb_resp = {
            "results": [
                {
                    "id": 111,
                    "name": "Unknown",
                    "known_for_department": "Acting",
                    "profile_path": None,
                    "known_for": [],
                }
            ]
        }
        tmdb_mock.get(url__regex=r".*/search/person.*").mock(
            return_value=Response(200, json=tmdb_resp)
        )

        resp = await client_authed.get("/api/search-actress", params={"q": "Unknown"})
        data = resp.json()
        assert data[0]["image"] is None


class TestGetActressDetailsFromTmdb:
    @pytest.mark.anyio
    async def test_full_details(
        self,
        tmdb_mock,
        client_authed,
        mock_tmdb_person_response,
        mock_tmdb_credits_response,
        mock_tmdb_images_response,
    ):
        tmdb_id = 12345

        tmdb_mock.get(url__regex=rf".*/person/{tmdb_id}\?.*").mock(
            return_value=Response(200, json=mock_tmdb_person_response)
        )
        tmdb_mock.get(url__regex=rf".*/person/{tmdb_id}/tv_credits.*").mock(
            return_value=Response(200, json=mock_tmdb_credits_response)
        )
        _mock_gallery_sources(tmdb_mock, tmdb_id, mock_tmdb_images_response)

        resp = await client_authed.get(f"/api/search-actress/{tmdb_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Kim Yoo-jung"
        assert data["birthDate"] == "1999-09-22"
        assert data["birthPlace"] == "Seoul, South Korea"
        assert data["image"] is not None
        # Should have Korean dramas only (not Non-Korean Show)
        drama_titles = [d["title"] for d in data["dramas"]]
        assert "Love in the Moonlight" in drama_titles
        assert "Running Man" in drama_titles  # Korean show
        assert "Non-Korean Show" not in drama_titles

    @pytest.mark.anyio
    async def test_drama_classification(
        self,
        tmdb_mock,
        client_authed,
        mock_tmdb_person_response,
        mock_tmdb_credits_response,
        mock_tmdb_images_response,
    ):
        tmdb_id = 12345

        tmdb_mock.get(url__regex=rf".*/person/{tmdb_id}\?.*").mock(
            return_value=Response(200, json=mock_tmdb_person_response)
        )
        tmdb_mock.get(url__regex=rf".*/person/{tmdb_id}/tv_credits.*").mock(
            return_value=Response(200, json=mock_tmdb_credits_response)
        )
        _mock_gallery_sources(tmdb_mock, tmdb_id, mock_tmdb_images_response)

        resp = await client_authed.get(f"/api/search-actress/{tmdb_id}")
        data = resp.json()
        dramas_by_title = {d["title"]: d for d in data["dramas"]}
        # Love in the Moonlight has genre_ids [18] -> drama
        assert dramas_by_title["Love in the Moonlight"]["category"] == "drama"
        # Running Man has genre_ids [10764] -> show
        assert dramas_by_title["Running Man"]["category"] == "show"

    @pytest.mark.anyio
    async def test_gallery_photos(
        self,
        tmdb_mock,
        client_authed,
        mock_tmdb_person_response,
        mock_tmdb_credits_response,
    ):
        tmdb_id = 12345

        tmdb_mock.get(url__regex=rf".*/person/{tmdb_id}\?.*").mock(
            return_value=Response(200, json=mock_tmdb_person_response)
        )
        tmdb_mock.get(url__regex=rf".*/person/{tmdb_id}/tv_credits.*").mock(
            return_value=Response(200, json=mock_tmdb_credits_response)
        )
        images_resp = {
            "profiles": [
                {"file_path": "/g1.jpg", "vote_average": 8.0},
                {"file_path": "/g2.jpg", "vote_average": 6.0},
                {"file_path": "/g3.jpg", "vote_average": 4.0},
            ]
        }
        _mock_gallery_sources(tmdb_mock, tmdb_id, images_resp)

        resp = await client_authed.get(f"/api/search-actress/{tmdb_id}")
        data = resp.json()
        assert len(data["gallery"]) == 3
        # Should be sorted by vote_average descending
        assert "/g1.jpg" in data["gallery"][0]


class TestFindTmdbPerson:
    """Test the _find_tmdb_person helper via the search endpoint behavior."""

    @pytest.mark.anyio
    async def test_known_drama_matching(self, tmdb_mock, client_authed):
        """When known_drama is provided, picks the result whose known_for matches."""
        tmdb_resp = {
            "results": [
                {
                    "id": 111,
                    "name": "Kim Yoo-jung",
                    "known_for_department": "Acting",
                    "profile_path": "/a.jpg",
                    "known_for": [
                        {"name": "Wrong Drama", "original_language": "ko", "media_type": "tv"},
                    ],
                },
                {
                    "id": 222,
                    "name": "Kim Yoo-jung",
                    "known_for_department": "Acting",
                    "profile_path": "/b.jpg",
                    "known_for": [
                        {"name": "Love in the Moonlight", "original_language": "ko", "media_type": "tv"},
                    ],
                },
            ]
        }
        tmdb_mock.get(url__regex=r".*/search/person.*").mock(
            return_value=Response(200, json=tmdb_resp)
        )

        resp = await client_authed.get("/api/search-actress", params={"q": "Kim Yoo-jung"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2  # Both are actors
        assert any(r["knownFor"] == "Love in the Moonlight" for r in data)


class TestFetchTmdbDramas:
    """Test the _fetch_tmdb_dramas helper indirectly through the details endpoint."""

    @pytest.mark.anyio
    async def test_classification_drama_vs_show(self, tmdb_mock, client_authed, mock_tmdb_person_response):
        tmdb_id = 12345
        credits_resp = {
            "cast": [
                {
                    "name": "My Mister",
                    "original_language": "ko",
                    "first_air_date": "2018-03-21",
                    "poster_path": "/my_mister.jpg",
                    "character": "Lee Ji-an",
                    "genre_ids": [18],
                },
                {
                    "name": "Knowing Bros",
                    "original_language": "ko",
                    "first_air_date": "2015-12-05",
                    "poster_path": "/knowing.jpg",
                    "character": "Guest",
                    "genre_ids": [10767, 35],
                },
                {
                    "name": "I Live Alone",
                    "original_language": "ko",
                    "first_air_date": "2013-03-22",
                    "poster_path": "/alone.jpg",
                    "character": "Cast",
                    "genre_ids": [10764],
                },
            ]
        }

        tmdb_mock.get(url__regex=rf".*/person/{tmdb_id}\?.*").mock(
            return_value=Response(200, json=mock_tmdb_person_response)
        )
        tmdb_mock.get(url__regex=rf".*/person/{tmdb_id}/tv_credits.*").mock(
            return_value=Response(200, json=credits_resp)
        )
        _mock_gallery_sources(tmdb_mock, tmdb_id)

        resp = await client_authed.get(f"/api/search-actress/{tmdb_id}")
        assert resp.status_code == 200
        data = resp.json()
        dramas_by_title = {d["title"]: d for d in data["dramas"]}

        assert dramas_by_title["My Mister"]["category"] == "drama"
        assert dramas_by_title["Knowing Bros"]["category"] == "show"
        assert dramas_by_title["I Live Alone"]["category"] == "show"

    @pytest.mark.anyio
    async def test_non_korean_filtered_out(self, tmdb_mock, client_authed, mock_tmdb_person_response):
        tmdb_id = 12345
        credits_resp = {
            "cast": [
                {
                    "name": "Korean Drama",
                    "original_language": "ko",
                    "first_air_date": "2020-01-01",
                    "poster_path": "/kr.jpg",
                    "character": "Lead",
                    "genre_ids": [18],
                },
                {
                    "name": "American Show",
                    "original_language": "en",
                    "first_air_date": "2020-06-01",
                    "poster_path": "/us.jpg",
                    "character": "Guest",
                    "genre_ids": [18],
                },
                {
                    "name": "Japanese Drama",
                    "original_language": "ja",
                    "first_air_date": "2019-04-01",
                    "poster_path": "/jp.jpg",
                    "character": "Cameo",
                    "genre_ids": [18],
                },
            ]
        }

        tmdb_mock.get(url__regex=rf".*/person/{tmdb_id}\?.*").mock(
            return_value=Response(200, json=mock_tmdb_person_response)
        )
        tmdb_mock.get(url__regex=rf".*/person/{tmdb_id}/tv_credits.*").mock(
            return_value=Response(200, json=credits_resp)
        )
        _mock_gallery_sources(tmdb_mock, tmdb_id)

        resp = await client_authed.get(f"/api/search-actress/{tmdb_id}")
        data = resp.json()
        titles = [d["title"] for d in data["dramas"]]
        assert "Korean Drama" in titles
        assert "American Show" not in titles
        assert "Japanese Drama" not in titles

    @pytest.mark.anyio
    async def test_duplicate_titles_deduplicated(self, tmdb_mock, client_authed, mock_tmdb_person_response):
        tmdb_id = 12345
        credits_resp = {
            "cast": [
                {
                    "name": "Same Drama",
                    "original_language": "ko",
                    "first_air_date": "2020-01-01",
                    "poster_path": "/a.jpg",
                    "character": "Role A",
                    "genre_ids": [18],
                },
                {
                    "name": "Same Drama",
                    "original_language": "ko",
                    "first_air_date": "2020-01-01",
                    "poster_path": "/b.jpg",
                    "character": "Role B",
                    "genre_ids": [18],
                },
            ]
        }

        tmdb_mock.get(url__regex=rf".*/person/{tmdb_id}\?.*").mock(
            return_value=Response(200, json=mock_tmdb_person_response)
        )
        tmdb_mock.get(url__regex=rf".*/person/{tmdb_id}/tv_credits.*").mock(
            return_value=Response(200, json=credits_resp)
        )
        _mock_gallery_sources(tmdb_mock, tmdb_id)

        resp = await client_authed.get(f"/api/search-actress/{tmdb_id}")
        data = resp.json()
        assert len(data["dramas"]) == 1  # Deduplication

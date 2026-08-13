import pytest

from anicli_multi.kinds import (
    ANIME,
    CATEGORY_TO_KIND,
    KNOWN_CATEGORIES,
    category_from_url,
    resolve_kind,
)

FILM_URL = "https://hdrezka-home.tv/films/fiction/2259-interstellar-2014.html"
SERIES_URL = "https://hdrezka-home.tv/series/thriller/646-vo-vse-tyazhkie-2008-latest.html"
ANIME_URL = "https://hdrezka-home.tv/animation/adventures/24686-armitazh.html"
CARTOON_URL = "https://hdrezka-home.tv/cartoons/comedy/91389-medvedi-2026.html"
ANIMEGO_URL = "https://animego.me/anime/naruto-123"


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        (FILM_URL, "films"),
        (SERIES_URL, "series"),
        (ANIME_URL, "animation"),
        (CARTOON_URL, "cartoons"),
        (ANIMEGO_URL, "anime"),
    ],
)
def test_category_from_url(url, expected):
    assert category_from_url(url) == expected


@pytest.mark.parametrize("url", ["", "https://hdrezka-home.tv", "https://hdrezka-home.tv/"])
def test_category_from_url_without_path(url):
    assert category_from_url(url) == ""


def test_category_from_url_does_not_raise_on_broken_url():
    assert category_from_url("http://[") == ""


@pytest.mark.parametrize("url", ["не url", "http://[", "", "///", "?a=b"])
def test_garbage_url_never_yields_a_wrong_kind(url):
    """Важна не сама категория из мусора, а то, что тип из неё не выведется."""
    assert resolve_kind("hdrezka", url) == ANIME


def test_all_five_categories_are_known():
    assert sorted(KNOWN_CATEGORIES) == ["animation", "cartoons", "films", "series", "show"]


def test_category_to_kind_values():
    assert CATEGORY_TO_KIND["films"] == "фильм"
    assert CATEGORY_TO_KIND["series"] == "сериал"
    assert CATEGORY_TO_KIND["cartoons"] == "мультфильм"
    assert CATEGORY_TO_KIND["show"] == "шоу"
    assert CATEGORY_TO_KIND["animation"] == ANIME


def test_resolve_kind_for_hdrezka_uses_url():
    assert resolve_kind("hdrezka", FILM_URL) == "фильм"
    assert resolve_kind("hdrezka", SERIES_URL) == "сериал"
    assert resolve_kind("hdrezka", ANIME_URL) == ANIME


def test_resolve_kind_for_anime_sources_is_always_anime():
    """У аниме-источников свои схемы путей; разбирать их URL нельзя."""
    for source in ("animego", "anilibria", "yummy-anime", "animevost"):
        assert resolve_kind(source, ANIMEGO_URL) == ANIME
        assert resolve_kind(source, FILM_URL) == ANIME


def test_resolve_kind_falls_back_to_anime_on_unknown_category():
    assert resolve_kind("hdrezka", "https://hdrezka-home.tv/чтотоновое/x.html") == ANIME


def test_resolve_kind_handles_empty_url():
    assert resolve_kind("hdrezka", "") == ANIME

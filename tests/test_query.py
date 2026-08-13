import pytest

from anicli_multi.kinds import ANIME, CARTOON, MOVIE, SERIES, SHOW
from anicli_multi.query import parse_query


def test_type_word_at_end_becomes_filter():
    """Ровно тот случай, с которого началась задача."""
    parsed = parse_query("жизнь по вызову сериал")
    assert parsed.text == "жизнь по вызову"
    assert parsed.kind == SERIES


def test_type_word_at_start_becomes_filter():
    parsed = parse_query("сериал жизнь по вызову")
    assert parsed.text == "жизнь по вызову"
    assert parsed.kind == SERIES


def test_type_word_in_the_middle_is_left_alone():
    parsed = parse_query("наруто фильм последний")
    assert parsed.text == "наруто фильм последний"
    assert parsed.kind is None


def test_single_type_word_is_a_query_not_a_filter():
    """«аниме» — это запрос, а не фильтр по пустоте."""
    parsed = parse_query("аниме")
    assert parsed.text == "аниме"
    assert parsed.kind is None


def test_query_without_type_word():
    parsed = parse_query("интерстеллар")
    assert parsed.text == "интерстеллар"
    assert parsed.kind is None


@pytest.mark.parametrize(
    ("word", "expected"),
    [
        ("сериал", SERIES),
        ("сериалы", SERIES),
        ("сериала", SERIES),
        ("фильм", MOVIE),
        ("фильмы", MOVIE),
        ("фильма", MOVIE),
        ("кино", MOVIE),
        ("аниме", ANIME),
        ("мультфильм", CARTOON),
        ("мультфильмы", CARTOON),
        ("мультик", CARTOON),
        ("мультики", CARTOON),
        ("мультсериал", CARTOON),
        ("шоу", SHOW),
    ],
)
def test_all_synonyms(word, expected):
    parsed = parse_query(f"тайтл {word}")
    assert parsed.text == "тайтл"
    assert parsed.kind == expected


def test_case_is_ignored():
    parsed = parse_query("жизнь по вызову СЕРИАЛ")
    assert parsed.text == "жизнь по вызову"
    assert parsed.kind == SERIES


def test_only_one_type_word_is_stripped():
    """Два слова типа подряд — снимаем одно, второе остаётся текстом."""
    parsed = parse_query("тайтл фильм сериал")
    assert parsed.kind == SERIES
    assert parsed.text == "тайтл фильм"


def test_extra_whitespace_is_collapsed():
    parsed = parse_query("  жизнь   по вызову   сериал  ")
    assert parsed.text == "жизнь по вызову"
    assert parsed.kind == SERIES


def test_raw_is_preserved_for_display():
    parsed = parse_query("жизнь по вызову сериал")
    assert parsed.raw == "жизнь по вызову сериал"


def test_empty_query():
    parsed = parse_query("   ")
    assert parsed.text == ""
    assert parsed.kind is None

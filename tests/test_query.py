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


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Re zero 1 сезон", "Re zero"),
        ("наруто 2 сезон", "наруто"),
        ("наруто сезон 2", "наруто"),
        ("наруто 5 серия", "наруто"),
        ("наруто серия 5", "наруто"),
        ("наруто 12 эпизод", "наруто"),
        ("наруто смотреть онлайн", "наруто"),
        ("наруто бесплатно", "наруто"),
        ("наруто hd", "наруто"),
        ("во все тяжкие 1 сезон смотреть", "во все тяжкие"),
    ],
)
def test_qualifiers_are_stripped(raw, expected):
    assert parse_query(raw).text == expected


@pytest.mark.parametrize("raw", ["Сезон охоты", "Наруто 2", "Власть книжного червя 2"])
def test_real_titles_are_not_damaged(raw):
    """«Сезон охоты» — настоящее название, голое число — часть названия."""
    assert parse_query(raw).text == raw


def test_qualifier_and_kind_together():
    """Сначала уточнение, потом тип."""
    parsed = parse_query("жизнь по вызову сериал 1 сезон")
    assert parsed.text == "жизнь по вызову"
    assert parsed.kind == SERIES


def test_kind_after_qualifier_removal():
    parsed = parse_query("жизнь по вызову 1 сезон сериал")
    assert parsed.text == "жизнь по вызову"
    assert parsed.kind == SERIES


def test_query_that_is_only_qualifiers_survives():
    """Не должны вычистить запрос в пустоту."""
    parsed = parse_query("1 сезон")
    assert parsed.text

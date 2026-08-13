import pytest

from anicli_multi.normalize import normalize_title


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Наруто", "наруто"),
        ("  Наруто  ", "наруто"),
        ("НАРУТО", "наруто"),
        ("Ёжик", "ежик"),
        ("Наруто / Naruto [1-220 из 220]", "наруто"),
        ("Наруто OVA-1 / Naruto OVA-1 [1 из 1]", "наруто ova 1"),
        ("Наруто: Ураганные хроники", "наруто ураганные хроники"),
        ("Наруто Ураганные хроники", "наруто ураганные хроники"),
        ("Наруто [OVA-8] / Пылающий Экзамен", "наруто ova 8"),
    ],
)
def test_normalize_title(raw, expected):
    assert normalize_title(raw) == expected


def test_same_title_different_sources_merge():
    """Одинаковый тайтл с разных источников даёт один ключ."""
    animevost = "Наруто / Naruto [1-220 из 220]"
    hdrezka = "Наруто "
    assert normalize_title(animevost) == normalize_title(hdrezka)


@pytest.mark.parametrize(
    ("left", "right"),
    [
        ("Наруто", "Наруто: Ураганные хроники"),
        ("Наруто [OVA-8] / Пылающий Экзамен", "Наруто [OVA-5] / Пересечение путей"),
        ("Наруто", "Боруто: Новое поколение Наруто"),
        ("Наруто OVA-1 / Naruto OVA-1 [1 из 1]", "Наруто OVA-2 / Naruto OVA-2 [1 из 1]"),
    ],
)
def test_different_titles_do_not_merge(left, right):
    """Главная защита от «каши»: разные тайтлы должны давать разные ключи."""
    assert normalize_title(left) != normalize_title(right)


def test_empty_and_garbage_input():
    assert normalize_title("") == ""
    assert normalize_title("   ") == ""
    assert normalize_title("!!!") == ""

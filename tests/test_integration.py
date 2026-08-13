import pytest

from anicli_multi.aggregate import search_all
from anicli_multi.commands import build_extractors
from anicli_multi.config import DEFAULT_SOURCES
from anicli_multi.grouping import group_results
from anicli_multi.normalize import normalize_title
from anicli_multi.query import parse_query
from anicli_multi.refine import refine

pytestmark = pytest.mark.network


async def _search(raw_query, max_results=30):
    """Полный путь запроса так, как его проходит команда поиска."""
    parsed = parse_query(raw_query)
    extractors = build_extractors(DEFAULT_SOURCES)
    per_source, _ = await search_all(extractors, parsed.text, timeout=15)
    groups = group_results(per_source, priority=DEFAULT_SOURCES, query=parsed.text)
    return refine(groups, normalize_title(parsed.text), parsed.kind, max_results)


async def test_type_word_in_query_finds_the_series():
    """Тот самый запрос, с которого началась задача."""
    result = await _search("жизнь по вызову сериал")
    assert result.groups, "сериал не найден"
    assert result.groups[0].kind == "сериал"
    assert "жизнь по вызову" in result.groups[0].title.lower()


async def test_noise_is_cut_off():
    result = await _search("жизнь по вызову")
    assert len(result.groups) <= 10, f"слишком много строк: {[g.title for g in result.groups]}"
    assert result.hidden_irrelevant > 0


async def test_type_word_that_is_part_of_the_title_falls_back():
    """«наруто последний фильм»: фильм лежит в разделе аниме, фильтр должен откатиться."""
    result = await _search("наруто последний фильм")
    assert result.groups
    assert any("последний" in g.title.lower() for g in result.groups)


async def test_result_never_exceeds_limit():
    result = await _search("наруто", max_results=10)
    assert len(result.groups) == 10
    assert result.total > 10


async def test_real_search_returns_grouped_results():
    extractors = build_extractors(DEFAULT_SOURCES)
    per_source, failures = await search_all(extractors, "наруто", timeout=15)
    assert per_source, f"ни один источник не ответил: {failures}"

    groups = group_results(per_source, priority=DEFAULT_SOURCES)
    assert groups

    keys = [g.key for g in groups]
    assert len(keys) == len(set(keys)), "в выдаче есть дубли групп"


async def test_multi_source_title_is_grouped_once():
    """«Наруто» есть минимум на двух источниках — должна быть одна строка."""
    extractors = build_extractors(DEFAULT_SOURCES)
    per_source, _ = await search_all(extractors, "наруто", timeout=15)
    groups = group_results(per_source, priority=DEFAULT_SOURCES)

    multi = [g for g in groups if len(g.sources) > 1]
    assert multi, "ожидалась хотя бы одна группа с несколькими источниками"
    for group in multi:
        assert len(group.sources) == len(set(group.sources))


async def test_real_search_finds_a_movie():
    extractors = build_extractors(DEFAULT_SOURCES)
    per_source, failures = await search_all(extractors, "интерстеллар", timeout=15)
    assert per_source, f"ни один источник не ответил: {failures}"

    groups = group_results(per_source, priority=DEFAULT_SOURCES)
    films = [g for g in groups if g.kind == "фильм"]
    assert films, f"фильм не найден, типы в выдаче: {sorted({g.kind for g in groups})}"


async def test_real_search_finds_a_series():
    extractors = build_extractors(DEFAULT_SOURCES)
    per_source, failures = await search_all(extractors, "во все тяжкие", timeout=15)
    assert per_source, f"ни один источник не ответил: {failures}"

    groups = group_results(per_source, priority=DEFAULT_SOURCES)
    series = [g for g in groups if g.kind == "сериал"]
    assert series, f"сериал не найден, типы в выдаче: {sorted({g.kind for g in groups})}"


async def test_anime_search_still_groups_across_sources():
    """Регрессия: добавление типа в ключ не должно разбить склейку аниме."""
    extractors = build_extractors(DEFAULT_SOURCES)
    per_source, _ = await search_all(extractors, "наруто", timeout=15)
    groups = group_results(per_source, priority=DEFAULT_SOURCES)

    multi = [g for g in groups if len(g.sources) > 1]
    assert multi, "ожидалась хотя бы одна группа с несколькими источниками"


async def test_group_entries_carry_their_own_source():
    """Каждая запись в группе помнит свой источник — от этого зависит история просмотров."""
    extractors = build_extractors(DEFAULT_SOURCES)
    per_source, _ = await search_all(extractors, "наруто", timeout=15)
    groups = group_results(per_source, priority=DEFAULT_SOURCES)

    for group in groups:
        for source, result in group.entries:
            assert source in DEFAULT_SOURCES
            assert hasattr(result, "a_get_anime")

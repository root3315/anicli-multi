from anicli_multi.grouping import TitleGroup
from anicli_multi.kinds import ANIME, MOVIE, SERIES
from anicli_multi.refine import refine


def group(title: str, kind: str = ANIME, sources=("animego",)) -> TitleGroup:
    from anicli_multi.normalize import normalize_title

    return TitleGroup(
        key=(kind, normalize_title(title)),
        title=title,
        kind=kind,
        entries=[(s, object()) for s in sources],
    )


def test_irrelevant_groups_are_dropped():
    groups = [
        group("Жизнь по вызову", SERIES),
        group("Жизнь без оружия"),
        group("Дисквалифицирован по жизни"),
    ]
    result = refine(groups, "жизнь по вызову", kind=None, max_results=30)
    assert [g.title for g in result.groups] == ["Жизнь по вызову"]
    assert result.hidden_irrelevant == 2


def test_everything_shown_when_nothing_is_relevant():
    """Пустой экран хуже неточного."""
    groups = [group("Жизнь без оружия"), group("Наруто")]
    result = refine(groups, "чегототакогонет", kind=None, max_results=30)
    assert len(result.groups) == 2
    assert result.hidden_irrelevant == 0


def test_kind_filter_applied():
    groups = [
        group("Жизнь по вызову", SERIES),
        group("Жизнь по вызову. Док", MOVIE),
    ]
    result = refine(groups, "жизнь по вызову", kind=SERIES, max_results=30)
    assert [g.title for g in result.groups] == ["Жизнь по вызову"]
    assert result.kind_filter_dropped is False


def test_kind_filter_softly_falls_back_when_empty():
    """«наруто последний фильм»: слово типа — часть названия, фильтр не должен обнулять."""
    groups = [group("Наруто 10: Последний фильм", ANIME)]
    result = refine(groups, "наруто последний", kind=MOVIE, max_results=30)
    assert [g.title for g in result.groups] == ["Наруто 10: Последний фильм"]
    assert result.kind_filter_dropped is True


def test_no_kind_filter_means_no_drop_flag():
    groups = [group("Наруто")]
    result = refine(groups, "наруто", kind=None, max_results=30)
    assert result.kind_filter_dropped is False


def test_limit_truncates_and_total_reports_full_size():
    groups = [group(f"Наруто {i}") for i in range(50)]
    result = refine(groups, "наруто", kind=None, max_results=10)
    assert len(result.groups) == 10
    assert result.total == 50


def test_total_equals_shown_when_under_limit():
    groups = [group("Наруто"), group("Наруто 2")]
    result = refine(groups, "наруто", kind=None, max_results=30)
    assert result.total == 2
    assert len(result.groups) == 2


def test_limit_below_one_is_ignored():
    groups = [group("Наруто"), group("Наруто 2")]
    result = refine(groups, "наруто", kind=None, max_results=0)
    assert len(result.groups) == 2


def test_empty_input():
    result = refine([], "наруто", kind=None, max_results=30)
    assert result.groups == []
    assert result.total == 0
    assert result.hidden_irrelevant == 0


def test_kind_filter_runs_after_relevance_cutoff():
    """Фильтр по типу не должен воскрешать отсечённое нерелевантное."""
    groups = [
        group("Жизнь по вызову", SERIES),
        group("Совсем другое", SERIES),
    ]
    result = refine(groups, "жизнь по вызову", kind=SERIES, max_results=30)
    assert [g.title for g in result.groups] == ["Жизнь по вызову"]


def test_empty_query_key_keeps_everything():
    groups = [group("Наруто"), group("Боруто")]
    result = refine(groups, "", kind=None, max_results=30)
    assert len(result.groups) == 2

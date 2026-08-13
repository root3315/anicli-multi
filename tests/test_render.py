from anicli_multi.grouping import TitleGroup
from anicli_multi.kinds import ANIME, SERIES
from anicli_multi.normalize import normalize_title
from anicli_multi.refine import RefineResult
from anicli_multi.render import render_groups, summary_line


def group(title: str, kind: str = ANIME) -> TitleGroup:
    return TitleGroup(
        key=(kind, normalize_title(title)),
        title=title,
        kind=kind,
        entries=[("animego", object())],
    )


def test_every_group_gets_a_row(capsys):
    """Главное отличие от anicli-ru: строки не прячутся в середине таблицы."""
    groups = [group(f"Тайтл {i}") for i in range(40)]
    render_groups("Результаты", groups)
    out = capsys.readouterr().out
    assert "more" not in out
    for i in (1, 20, 40):
        assert f"Тайтл {i - 1}" in out


def test_numbering_starts_at_one(capsys):
    render_groups("Результаты", [group("Первый"), group("Второй")])
    out = capsys.readouterr().out
    assert "1" in out
    assert "Первый" in out


def test_empty_groups_render_without_crash(capsys):
    render_groups("Результаты", [])
    assert capsys.readouterr().out is not None


def test_summary_reports_truncation():
    result = RefineResult(groups=[group("х")] * 30, total=57)
    assert "30 из 57" in summary_line(result)


def test_summary_reports_hidden_irrelevant():
    result = RefineResult(groups=[group("х")], total=1, hidden_irrelevant=68)
    assert "68" in summary_line(result)


def test_summary_reports_dropped_kind_filter():
    result = RefineResult(groups=[group("х")], total=1, kind_filter_dropped=True)
    assert summary_line(result)


def test_summary_is_empty_when_nothing_to_say():
    result = RefineResult(groups=[group("х")], total=1)
    assert summary_line(result) == ""


def test_summary_combines_parts():
    result = RefineResult(groups=[group("х")] * 30, total=57, hidden_irrelevant=68)
    line = summary_line(result)
    assert "30 из 57" in line
    assert "68" in line


def test_badge_visible_in_rendered_table(capsys):
    render_groups("Результаты", [group("Жизнь по вызову", SERIES)])
    assert "[сериал]" in capsys.readouterr().out

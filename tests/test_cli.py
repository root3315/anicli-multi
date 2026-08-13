from anicli_multi.cli import build_upstream_argv, split_own_args


def test_split_own_args_extracts_sources():
    sources, rest = split_own_args(["--sources", "animego,hdrezka", "наруто"])
    assert sources == "animego,hdrezka"
    assert rest == ["наруто"]


def test_split_own_args_supports_equals_form():
    sources, rest = split_own_args(["--sources=animego", "наруто"])
    assert sources == "animego"
    assert rest == ["наруто"]


def test_split_own_args_without_flag():
    sources, rest = split_own_args(["наруто"])
    assert sources is None
    assert rest == ["наруто"]


def test_build_upstream_argv_no_args_starts_repl():
    assert build_upstream_argv([], "animego") == ["cli", "-s", "animego"]


def test_build_upstream_argv_bare_query_becomes_search():
    argv = build_upstream_argv(["наруто"], "animego")
    assert argv == ["cli", "-s", "animego", "--search", "наруто"]


def test_build_upstream_argv_multiword_query_joined():
    argv = build_upstream_argv(["атака", "титанов"], "animego")
    assert argv == ["cli", "-s", "animego", "--search", "атака титанов"]


def test_build_upstream_argv_passes_through_flags():
    argv = build_upstream_argv(["-q", "1080", "--proxy", "http://x"], "animego")
    assert argv == ["cli", "-s", "animego", "-q", "1080", "--proxy", "http://x"]


def test_build_upstream_argv_flags_with_query():
    argv = build_upstream_argv(["-q", "1080", "наруто"], "animego")
    assert argv[:3] == ["cli", "-s", "animego"]
    assert "--search" in argv
    assert argv[-1] == "наруто"


def test_boolean_flag_does_not_swallow_query():
    """`ani --ongoing` — булев флаг, следующее слово это запрос, а не его значение."""
    argv = build_upstream_argv(["--ongoing"], "animego")
    assert argv == ["cli", "-s", "animego", "--ongoing"]


def test_boolean_flag_followed_by_word_keeps_word_as_query():
    argv = build_upstream_argv(["--ongoing", "наруто"], "animego")
    assert argv == ["cli", "-s", "animego", "--ongoing", "--search", "наруто"]


def test_build_upstream_argv_respects_explicit_source():
    argv = build_upstream_argv(["-s", "hdrezka"], "animego")
    assert argv.count("-s") == 1
    assert "hdrezka" in argv
    assert "animego" not in argv


def test_proxy_from_config_is_injected():
    argv = build_upstream_argv([], "animego", proxy="socks5://127.0.0.1:1080")
    assert argv == ["cli", "-s", "animego", "--proxy", "socks5://127.0.0.1:1080"]


def test_explicit_proxy_wins_over_config():
    argv = build_upstream_argv(["--proxy", "http://mine"], "animego", proxy="socks5://from-config")
    assert argv.count("--proxy") == 1
    assert "http://mine" in argv
    assert "socks5://from-config" not in argv


def test_explicit_proxy_equals_form_wins():
    argv = build_upstream_argv(["--proxy=http://mine"], "animego", proxy="socks5://from-config")
    assert "socks5://from-config" not in argv


def test_no_proxy_when_config_empty():
    argv = build_upstream_argv([], "animego", proxy=None)
    assert "--proxy" not in argv


def test_build_upstream_argv_respects_long_source_flag():
    argv = build_upstream_argv(["--source", "hdrezka"], "animego")
    assert "animego" not in argv
    assert argv == ["cli", "--source", "hdrezka"]


def test_build_upstream_argv_respects_source_equals_form():
    argv = build_upstream_argv(["--source=hdrezka"], "animego")
    assert "animego" not in argv
    assert argv == ["cli", "--source=hdrezka"]

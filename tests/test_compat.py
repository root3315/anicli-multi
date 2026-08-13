import pytest

from anicli_multi.compat import (
    REQUIRED_CONTEXT_KEYS,
    CompatError,
    assert_compat,
    check_compat,
)


def test_installed_anicli_is_compatible():
    """Smoke: фактически установленный anicli-ru предоставляет ожидаемый контракт."""
    problems = check_compat()
    assert problems == [], "контракт anicli-ru изменился: " + "; ".join(problems)


def test_assert_compat_passes_on_current_install():
    assert_compat()


def test_required_context_keys_are_declared():
    for key in ("results", "anime", "episodes", "extractor_name", "result_num"):
        assert key in REQUIRED_CONTEXT_KEYS


def test_compat_error_is_runtime_error():
    assert issubclass(CompatError, RuntimeError)


def test_assert_compat_raises_when_problems(monkeypatch):
    monkeypatch.setattr("anicli_multi.compat.check_compat", lambda: ["всё сломалось"])
    with pytest.raises(CompatError) as exc:
        assert_compat()
    assert "всё сломалось" in str(exc.value)

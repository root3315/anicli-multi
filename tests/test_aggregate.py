import asyncio

from anicli_multi.aggregate import SourceFailure, search_all


class FakeResult:
    def __init__(self, title: str):
        self.title = title


class FakeExtractor:
    def __init__(self, titles=None, *, delay=0.0, error=None):
        self._titles = titles or []
        self._delay = delay
        self._error = error

    async def a_search(self, query):
        if self._delay:
            await asyncio.sleep(self._delay)
        if self._error:
            raise self._error
        return [FakeResult(t) for t in self._titles]


async def test_collects_results_from_all_sources():
    extractors = {
        "animego": FakeExtractor(["Наруто"]),
        "hdrezka": FakeExtractor(["Наруто", "Боруто"]),
    }
    per_source, failures = await search_all(extractors, "наруто", timeout=5)
    assert failures == []
    assert [name for name, _ in per_source] == ["animego", "hdrezka"]
    assert len(dict(per_source)["hdrezka"]) == 2


async def test_slow_source_times_out_without_killing_others():
    extractors = {
        "animego": FakeExtractor(["Наруто"]),
        "hdrezka": FakeExtractor(["Боруто"], delay=5),
    }
    per_source, failures = await search_all(extractors, "наруто", timeout=0.1)
    assert dict(per_source).keys() == {"animego"}
    assert len(failures) == 1
    assert failures[0].source == "hdrezka"
    assert "таймаут" in failures[0].reason.lower()


async def test_failing_source_is_reported_not_raised():
    extractors = {
        "animego": FakeExtractor(["Наруто"]),
        "hdrezka": FakeExtractor(error=RuntimeError("500 Server Error")),
    }
    per_source, failures = await search_all(extractors, "наруто", timeout=5)
    assert dict(per_source).keys() == {"animego"}
    assert len(failures) == 1
    assert failures[0].source == "hdrezka"
    assert "500 Server Error" in failures[0].reason


async def test_all_sources_fail_returns_empty_without_raising():
    extractors = {
        "animego": FakeExtractor(error=RuntimeError("boom")),
        "hdrezka": FakeExtractor(error=RuntimeError("boom")),
    }
    per_source, failures = await search_all(extractors, "наруто", timeout=5)
    assert per_source == []
    assert len(failures) == 2


async def test_empty_result_is_not_a_failure():
    extractors = {"animego": FakeExtractor([])}
    per_source, failures = await search_all(extractors, "нет такого", timeout=5)
    assert per_source == []
    assert failures == []


async def test_searches_run_concurrently_not_sequentially():
    extractors = {
        "a": FakeExtractor(["x"], delay=0.2),
        "b": FakeExtractor(["y"], delay=0.2),
        "c": FakeExtractor(["z"], delay=0.2),
    }
    loop = asyncio.get_running_loop()
    started = loop.time()
    per_source, _failures = await search_all(extractors, "q", timeout=5)
    elapsed = loop.time() - started
    assert len(per_source) == 3
    assert elapsed < 0.5, f"источники опрашивались последовательно: {elapsed:.2f}s"


def test_source_failure_fields():
    failure = SourceFailure(source="hdrezka", reason="таймаут")
    assert failure.source == "hdrezka"
    assert failure.reason == "таймаут"


async def test_no_extractors_returns_empty():
    per_source, failures = await search_all({}, "наруто", timeout=5)
    assert per_source == []
    assert failures == []

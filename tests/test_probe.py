import httpx
import pytest

from anicli_multi.probe import is_reachable, pick_playable


class FakeVideo:
    def __init__(self, url="https://example.test/v.m3u8", quality=720, headers=None):
        self.url = url
        self.quality = quality
        self.type = "m3u8"
        self.headers = headers or {}


class FakeSource:
    def __init__(self, title, videos, error=None):
        self.title = title
        self._videos = videos
        self._error = error

    async def a_get_videos(self):
        if self._error:
            raise self._error
        return self._videos


async def test_reachable_when_server_answers(monkeypatch):
    async def fake_get(self, url, **kwargs):
        return httpx.Response(200, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    assert await is_reachable("https://example.test/v.m3u8", {}, timeout=1) is True


async def test_not_reachable_on_connect_error(monkeypatch):
    async def fake_get(self, url, **kwargs):
        raise httpx.ConnectTimeout("blocked")

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    assert await is_reachable("https://blocked.test/v.m3u8", {}, timeout=1) is False


async def test_not_reachable_on_server_error(monkeypatch):
    async def fake_get(self, url, **kwargs):
        return httpx.Response(503, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    assert await is_reachable("https://example.test/v.m3u8", {}, timeout=1) is False


async def test_pick_playable_returns_first_working(monkeypatch):
    """Первая озвучка мертва — берём следующую, не спрашивая пользователя."""
    calls = []

    async def fake_reachable(url, headers, timeout):
        calls.append(url)
        return "ok" in url

    monkeypatch.setattr("anicli_multi.probe.is_reachable", fake_reachable)

    sources = [
        FakeSource("мертвая", [FakeVideo("https://dead.test/a")]),
        FakeSource("рабочая", [FakeVideo("https://ok.test/b")]),
    ]
    result = await pick_playable(sources, quality=720, timeout=1)
    assert result is not None
    assert result.source.title == "рабочая"
    assert len(calls) == 2


async def test_pick_playable_returns_none_when_all_dead(monkeypatch):
    async def fake_reachable(url, headers, timeout):
        return False

    monkeypatch.setattr("anicli_multi.probe.is_reachable", fake_reachable)

    sources = [FakeSource("а", [FakeVideo()]), FakeSource("б", [FakeVideo()])]
    assert await pick_playable(sources, quality=720, timeout=1) is None


async def test_pick_playable_skips_source_that_raises(monkeypatch):
    async def fake_reachable(url, headers, timeout):
        return True

    monkeypatch.setattr("anicli_multi.probe.is_reachable", fake_reachable)

    sources = [
        FakeSource("битая", [], error=RuntimeError("boom")),
        FakeSource("рабочая", [FakeVideo()]),
    ]
    result = await pick_playable(sources, quality=720, timeout=1)
    assert result.source.title == "рабочая"


async def test_pick_playable_skips_source_without_videos(monkeypatch):
    async def fake_reachable(url, headers, timeout):
        return True

    monkeypatch.setattr("anicli_multi.probe.is_reachable", fake_reachable)

    sources = [FakeSource("пустая", []), FakeSource("рабочая", [FakeVideo()])]
    result = await pick_playable(sources, quality=720, timeout=1)
    assert result.source.title == "рабочая"


async def test_pick_playable_empty_input():
    assert await pick_playable([], quality=720, timeout=1) is None


async def test_result_carries_video_and_index(monkeypatch):
    async def fake_reachable(url, headers, timeout):
        return True

    monkeypatch.setattr("anicli_multi.probe.is_reachable", fake_reachable)

    sources = [FakeSource("первая", [FakeVideo("https://ok.test/x")])]
    result = await pick_playable(sources, quality=720, timeout=1)
    assert result.index == 0
    assert str(result.video.url) == "https://ok.test/x"


@pytest.mark.parametrize("status", [200, 206, 302])
async def test_various_success_statuses(monkeypatch, status):
    async def fake_get(self, url, **kwargs):
        return httpx.Response(status, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    assert await is_reachable("https://example.test/v", {}, timeout=1) is True

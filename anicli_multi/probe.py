"""Проверка доступности видео перед запуском плеера.

CDN, с которых раздаётся видео, периодически перестают отвечать у отдельных
провайдеров. Замер 2026-08-13 на одной сети: voidboost и solodcdn не отвечали,
libria.fun работал — причём solodcdn до этого играл нормально. Список меняется,
поэтому ловить это вручную бессмысленно: проверяем перед запуском и молча берём
следующую озвучку.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Optional

import httpx
from anicli_api.tools.helpers import get_video_by_quality

DEFAULT_PROBE_TIMEOUT = 6.0


@dataclass
class Playable:
    """Озвучка, видео которой реально отдаётся сервером."""

    index: int
    source: Any
    video: Any


async def is_reachable(url: str, headers: dict, timeout: float = DEFAULT_PROBE_TIMEOUT) -> bool:
    """Отвечает ли сервер по ссылке.

    HEAD не используем: часть CDN на него отвечает 405, хотя видео отдаёт.
    """
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
            response = await client.get(url, headers=headers or {})
    except Exception:  # noqa: BLE001 — недоступность это ожидаемый исход, не ошибка
        return False
    return response.status_code < 400


async def pick_playable(
    sources: Sequence[Any],
    quality: int,
    timeout: float = DEFAULT_PROBE_TIMEOUT,
    preferred_index: int = 0,
) -> Optional[Playable]:
    """Найти первую озвучку, видео которой отдаётся.

    Проверка начинается с выбранной пользователем и идёт по остальным по порядку.
    Источник без видео или упавший на запросе просто пропускается.
    """
    if not sources:
        return None

    order = [preferred_index] + [i for i in range(len(sources)) if i != preferred_index]
    for index in order:
        if index >= len(sources):
            continue
        source = sources[index]
        try:
            videos = await source.a_get_videos()
        except Exception:  # noqa: BLE001 — битая озвучка не должна ронять перебор
            continue
        if not videos:
            continue
        video = get_video_by_quality(videos, quality)
        if video is None:
            continue
        headers = dict(getattr(video, "headers", {}) or {})
        if await is_reachable(str(video.url), headers, timeout=timeout):
            return Playable(index=index, source=source, video=video)
    return None

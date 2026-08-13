"""Пользовательский конфиг в платформенной директории. Формат — JSON (см. спеку §8)."""

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

from platformdirs import user_config_dir

from .kinds import KNOWN_CATEGORIES

APP_NAME = "anicli-multi"

DEFAULT_SOURCES: list[str] = ["animego", "hdrezka", "yummy-anime", "anilibria"]
DEFAULT_TIMEOUT = 10.0
# Разделы каталога hdrezka, по которым идёт поиск. ["animation"] вернёт прежнее
# поведение — только аниме.
DEFAULT_HDREZKA_CATEGORIES: list[str] = ["animation", "films", "series", "cartoons", "show"]
# Сколько строк показывать. Скрытые строки не выбираются — в FSM уходит только
# показанный срез, поэтому лимит честный, а не косметический.
DEFAULT_MAX_RESULTS = 30


@dataclass
class MultiConfig:
    sources: list[str] = field(default_factory=lambda: list(DEFAULT_SOURCES))
    timeout: float = DEFAULT_TIMEOUT
    bare_text_search: bool = True
    hdrezka_categories: list[str] = field(default_factory=lambda: list(DEFAULT_HDREZKA_CATEGORIES))
    max_results: int = DEFAULT_MAX_RESULTS


def config_path() -> Path:
    return Path(user_config_dir(APP_NAME, appauthor=False)) / "config.json"


def load_config(path: Optional[Path] = None) -> MultiConfig:
    """Прочитать конфиг. Отсутствие или поломка файла — не ошибка, берутся дефолты."""
    target = path or config_path()
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return MultiConfig()
    if not isinstance(raw, dict):
        return MultiConfig()

    config = MultiConfig()
    sources = raw.get("sources")
    if isinstance(sources, list) and sources:
        config.sources = [str(s) for s in sources]
    timeout = raw.get("timeout")
    if isinstance(timeout, (int, float)) and timeout > 0:
        config.timeout = float(timeout)
    bare = raw.get("bare_text_search")
    if isinstance(bare, bool):
        config.bare_text_search = bare
    categories = raw.get("hdrezka_categories")
    if isinstance(categories, list):
        # неизвестные категории отбрасываем; если не осталось ничего — дефолт
        known = [str(c) for c in categories if str(c) in KNOWN_CATEGORIES]
        if known:
            config.hdrezka_categories = known
    max_results = raw.get("max_results")
    if isinstance(max_results, int) and not isinstance(max_results, bool) and max_results >= 1:
        config.max_results = max_results
    return config


def save_config(config: MultiConfig, path: Optional[Path] = None) -> None:
    target = path or config_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(asdict(config), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

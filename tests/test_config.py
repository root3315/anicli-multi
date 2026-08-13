import json

from anicli_multi.config import (
    DEFAULT_SOURCES,
    MultiConfig,
    config_path,
    load_config,
    save_config,
)


def test_defaults_when_file_missing(tmp_path):
    config = load_config(tmp_path / "нет.json")
    assert config.sources == DEFAULT_SOURCES
    assert config.timeout == 10.0
    assert config.bare_text_search is True


def test_default_sources_exact_order():
    assert DEFAULT_SOURCES == ["animego", "hdrezka", "yummy-anime", "anilibria"]


def test_roundtrip(tmp_path):
    path = tmp_path / "config.json"
    save_config(MultiConfig(sources=["animego"], timeout=3.5, bare_text_search=False), path)
    loaded = load_config(path)
    assert loaded.sources == ["animego"]
    assert loaded.timeout == 3.5
    assert loaded.bare_text_search is False


def test_partial_config_fills_defaults(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"timeout": 2}), encoding="utf-8")
    config = load_config(path)
    assert config.timeout == 2
    assert config.sources == DEFAULT_SOURCES


def test_broken_json_falls_back_to_defaults(tmp_path):
    path = tmp_path / "config.json"
    path.write_text("{ это не json", encoding="utf-8")
    config = load_config(path)
    assert config.sources == DEFAULT_SOURCES


def test_unknown_keys_ignored(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"такого_поля_нет": 1}), encoding="utf-8")
    assert load_config(path).sources == DEFAULT_SOURCES


def test_save_creates_parent_directory(tmp_path):
    path = tmp_path / "вложено" / "config.json"
    save_config(MultiConfig(), path)
    assert path.exists()


def test_config_path_mentions_app_name():
    assert "anicli-multi" in str(config_path())


def test_default_instances_do_not_share_sources_list():
    """default_factory обязателен: иначе правка одного конфига поменяла бы все."""
    first = MultiConfig()
    second = MultiConfig()
    first.sources.append("hdrezka")
    assert second.sources == DEFAULT_SOURCES


def test_saved_file_is_readable_utf8(tmp_path):
    path = tmp_path / "config.json"
    save_config(MultiConfig(sources=["животные"]), path)
    assert "животные" in path.read_text(encoding="utf-8")

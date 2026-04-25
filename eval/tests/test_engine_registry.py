"""Unit tests for EngineRegistry."""

import os
import textwrap
from pathlib import Path

import pytest
import yaml

from evaluator.engine_registry import EngineConfig, EngineRegistry, REQUIRED_FIELDS


# ------------------------------------------------------------------ #
#  EngineConfig.from_dict                                              #
# ------------------------------------------------------------------ #

VALID_DATA = {
    "engine_id": "test_engine",
    "engine_name": "Test Engine",
    "strategy_name": "Test Strategy",
    "owner": "Tester",
    "uci_command": "echo dummy",
    "language": "Python",
}


def test_from_dict_valid():
    ec = EngineConfig.from_dict(VALID_DATA)
    assert ec.engine_id == "test_engine"
    assert ec.enabled is True
    assert ec.frameworks == []


def test_from_dict_optional_defaults():
    ec = EngineConfig.from_dict(VALID_DATA)
    assert ec.stockfish_derived is False
    assert ec.requires_gpu is False
    assert ec.repo_path is None


@pytest.mark.parametrize("missing_field", list(REQUIRED_FIELDS))
def test_from_dict_missing_required(missing_field):
    data = dict(VALID_DATA)
    del data[missing_field]
    with pytest.raises(ValueError, match="missing required fields"):
        EngineConfig.from_dict(data)


def test_enabled_flag_respected():
    data = {**VALID_DATA, "enabled": False}
    ec = EngineConfig.from_dict(data)
    assert ec.enabled is False


# ------------------------------------------------------------------ #
#  EngineRegistry loading                                              #
# ------------------------------------------------------------------ #

def _write_engines_yaml(tmp_path: Path, engines: list) -> Path:
    config = tmp_path / "engines.yaml"
    config.write_text(yaml.dump({"engines": engines}))
    return config


def test_registry_loads_from_yaml(tmp_path):
    cfg = _write_engines_yaml(tmp_path, [VALID_DATA])
    registry = EngineRegistry.from_yaml(str(cfg))
    assert len(registry) == 1
    assert registry.get("test_engine").engine_name == "Test Engine"


def test_registry_enabled_engines_filter(tmp_path):
    e1 = {**VALID_DATA, "engine_id": "e1", "enabled": True}
    e2 = {**VALID_DATA, "engine_id": "e2", "enabled": False}
    cfg = _write_engines_yaml(tmp_path, [e1, e2])
    registry = EngineRegistry.from_yaml(str(cfg))
    enabled = registry.enabled_engines()
    assert len(enabled) == 1
    assert enabled[0].engine_id == "e1"


def test_registry_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        EngineRegistry.from_yaml("/nonexistent/engines.yaml")


def test_registry_invalid_engine_raises(tmp_path):
    bad_data = {"engine_id": "bad", "engine_name": "Bad"}  # missing fields
    cfg = _write_engines_yaml(tmp_path, [bad_data])
    with pytest.raises(ValueError, match="missing required fields"):
        EngineRegistry.from_yaml(str(cfg))


def test_registry_get_unknown_raises(tmp_path):
    cfg = _write_engines_yaml(tmp_path, [VALID_DATA])
    registry = EngineRegistry.from_yaml(str(cfg))
    with pytest.raises(KeyError):
        registry.get("no_such_engine")


def test_registry_scans_engine_subdirectories(tmp_path):
    """engine.yaml files in an engines/ subdirectory are auto-discovered."""
    engines_dir = tmp_path / "engines" / "mybot"
    engines_dir.mkdir(parents=True)
    sub_engine = {**VALID_DATA, "engine_id": "mybot"}
    (engines_dir / "engine.yaml").write_text(yaml.dump(sub_engine))

    # Central config lives one level up from engines/ (i.e. tmp_path/configs/)
    configs_dir = tmp_path / "configs"
    configs_dir.mkdir(parents=True)
    cfg = configs_dir / "engines.yaml"
    cfg.write_text(yaml.dump({"engines": []}))

    registry = EngineRegistry.from_yaml(str(cfg))
    assert registry.get("mybot").engine_id == "mybot"


def test_registry_central_config_takes_precedence(tmp_path):
    """If the same engine_id appears in both central config and engine.yaml, central wins."""
    engines_dir = tmp_path / "engines" / "test_engine"
    engines_dir.mkdir(parents=True)
    sub_data = {**VALID_DATA, "engine_id": "test_engine", "engine_name": "SubName"}
    (engines_dir / "engine.yaml").write_text(yaml.dump(sub_data))

    central_data = {**VALID_DATA, "engine_id": "test_engine", "engine_name": "CentralName"}
    cfg = tmp_path / "configs" / "engines.yaml"
    cfg.parent.mkdir(exist_ok=True)
    cfg.write_text(yaml.dump({"engines": [central_data]}))

    registry = EngineRegistry.from_yaml(str(cfg))
    assert registry.get("test_engine").engine_name == "CentralName"

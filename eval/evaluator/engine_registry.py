"""
Engine Registry — loads and validates engine configs from YAML files.

An engine config can live either in a central engines.yaml list or as a
standalone engine.yaml inside each engine's directory.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

import yaml


REQUIRED_FIELDS = {
    "engine_id",
    "engine_name",
    "strategy_name",
    "owner",
    "uci_command",
    "language",
}


@dataclass
class EngineConfig:
    engine_id: str
    engine_name: str
    strategy_name: str
    owner: str
    uci_command: str
    language: str
    frameworks: List[str] = field(default_factory=list)
    created_from_existing_foundation: bool = False
    stockfish_derived: bool = False
    enabled: bool = True
    notes: str = ""
    # optional fields
    repo_path: Optional[str] = None
    build_command: Optional[str] = None
    test_command: Optional[str] = None
    license_notes: Optional[str] = None
    requires_gpu: bool = False
    requires_network: bool = False
    # UCI setoption key-value pairs sent after handshake
    uci_options: dict = field(default_factory=dict)
    # If set, the engine uses "go depth N" instead of "go movetime/wtime/btime"
    max_search_depth: Optional[int] = None
    # If set, the engine process is launched with this as its working directory
    working_directory: Optional[str] = None

    # ------------------------------------------------------------------ #
    #  UCI health check                                                    #
    # ------------------------------------------------------------------ #

    def health_check(self, timeout: float = 5.0) -> Tuple[bool, str]:
        """
        Launch the engine process and verify the UCI handshake.

        Returns (success, message).
        """
        try:
            proc = subprocess.Popen(
                self.uci_command,
                shell=True,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=self.working_directory or None,
            )
        except Exception as exc:
            return False, f"Failed to launch process: {exc}"

        try:
            stdout, _ = proc.communicate(input="uci\nquit\n", timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            return False, "Engine did not respond within timeout"

        if "uciok" in stdout:
            return True, "uciok received"
        return False, f"uciok not found in output: {stdout[:200]!r}"

    # ------------------------------------------------------------------ #
    #  Serialisation                                                       #
    # ------------------------------------------------------------------ #

    def to_dict(self) -> dict:
        return {
            "engine_id": self.engine_id,
            "engine_name": self.engine_name,
            "strategy_name": self.strategy_name,
            "owner": self.owner,
            "uci_command": self.uci_command,
            "language": self.language,
            "frameworks": self.frameworks,
            "created_from_existing_foundation": self.created_from_existing_foundation,
            "stockfish_derived": self.stockfish_derived,
            "enabled": self.enabled,
            "notes": self.notes,
        }

    # ------------------------------------------------------------------ #
    #  Factory                                                             #
    # ------------------------------------------------------------------ #

    @classmethod
    def from_dict(cls, data: dict) -> "EngineConfig":
        missing = REQUIRED_FIELDS - set(data.keys())
        if missing:
            raise ValueError(
                f"Engine config missing required fields: {sorted(missing)}"
            )
        return cls(
            engine_id=data["engine_id"],
            engine_name=data["engine_name"],
            strategy_name=data["strategy_name"],
            owner=data["owner"],
            uci_command=data["uci_command"],
            language=data["language"],
            frameworks=data.get("frameworks", []),
            created_from_existing_foundation=data.get(
                "created_from_existing_foundation", False
            ),
            stockfish_derived=data.get("stockfish_derived", False),
            enabled=data.get("enabled", True),
            notes=data.get("notes", ""),
            repo_path=data.get("repo_path"),
            build_command=data.get("build_command"),
            test_command=data.get("test_command"),
            license_notes=data.get("license_notes"),
            requires_gpu=data.get("requires_gpu", False),
            requires_network=data.get("requires_network", False),
            uci_options=data.get("uci_options", {}),
            max_search_depth=data.get("max_search_depth"),
            working_directory=data.get("working_directory"),
        )


class EngineRegistry:
    """Holds all registered engine configs."""

    def __init__(self, engines: List[EngineConfig]):
        self._engines: dict[str, EngineConfig] = {e.engine_id: e for e in engines}

    # ------------------------------------------------------------------ #
    #  Accessors                                                           #
    # ------------------------------------------------------------------ #

    def all_engines(self) -> List[EngineConfig]:
        return list(self._engines.values())

    def enabled_engines(self) -> List[EngineConfig]:
        return [e for e in self._engines.values() if e.enabled]

    def get(self, engine_id: str) -> EngineConfig:
        if engine_id not in self._engines:
            raise KeyError(f"Engine '{engine_id}' not found in registry")
        return self._engines[engine_id]

    def __len__(self) -> int:
        return len(self._engines)

    # ------------------------------------------------------------------ #
    #  Loaders                                                             #
    # ------------------------------------------------------------------ #

    @classmethod
    def from_yaml(cls, path: str) -> "EngineRegistry":
        """
        Load engines from a central YAML config file.

        The file is expected to have the shape::

            engines:
              - engine_id: ...
                ...

        Individual engine subdirectories are also scanned for engine.yaml
        files relative to the directory that contains the config file.
        """
        config_path = Path(path)
        if not config_path.exists():
            raise FileNotFoundError(f"Engine config not found: {path}")

        with open(config_path) as f:
            data = yaml.safe_load(f)

        engine_list = data.get("engines", []) if data else []
        engines: List[EngineConfig] = []
        for entry in engine_list:
            try:
                engines.append(EngineConfig.from_dict(entry))
            except ValueError as exc:
                raise ValueError(
                    f"Invalid engine config in {path}: {exc}"
                ) from exc

        # also scan engines/ subdirectory next to the config for engine.yaml files
        engines_dir = config_path.parent.parent / "engines"
        if engines_dir.is_dir():
            for engine_yaml in sorted(engines_dir.glob("*/engine.yaml")):
                with open(engine_yaml) as f:
                    sub_data = yaml.safe_load(f)
                if sub_data:
                    try:
                        ec = EngineConfig.from_dict(sub_data)
                        # avoid duplicates — central config takes precedence
                        if ec.engine_id not in {e.engine_id for e in engines}:
                            engines.append(ec)
                    except ValueError as exc:
                        raise ValueError(
                            f"Invalid engine.yaml at {engine_yaml}: {exc}"
                        ) from exc

        return cls(engines)

    @classmethod
    def from_directory(cls, engines_dir: str) -> "EngineRegistry":
        """Load engines by scanning a directory for engine.yaml files."""
        base = Path(engines_dir)
        engines: List[EngineConfig] = []
        for engine_yaml in sorted(base.glob("*/engine.yaml")):
            with open(engine_yaml) as f:
                data = yaml.safe_load(f)
            if data:
                try:
                    engines.append(EngineConfig.from_dict(data))
                except ValueError as exc:
                    raise ValueError(
                        f"Invalid engine.yaml at {engine_yaml}: {exc}"
                    ) from exc
        return cls(engines)

import hashlib
from pathlib import Path

PATCHABLE_FILES = {
    "evaluation.py",
    "search.py",
    "transposition_table.py",
    "time_manager.py",
}


def _resolve_target(engine_dir: str, filename: str) -> Path:
    if filename not in PATCHABLE_FILES:
        raise ValueError(f"filename is not patchable: {filename}")
    return Path(engine_dir) / filename


def snapshot_engine_code(engine_dir: str) -> dict[str, str]:
    snapshot = {}
    for filename in sorted(PATCHABLE_FILES):
        target = _resolve_target(engine_dir, filename)
        snapshot[filename] = target.read_text(encoding="utf-8")
    return snapshot


def snapshot_fingerprint(snapshot: dict[str, str]) -> str:
    digest = hashlib.sha256()
    for filename in sorted(PATCHABLE_FILES):
        source = snapshot.get(filename, "")
        digest.update(filename.encode("utf-8"))
        digest.update(b"\0")
        digest.update(source.encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()


def engine_fingerprint(engine_dir: str) -> str:
    return snapshot_fingerprint(snapshot_engine_code(engine_dir))


def apply_patches(engine_dir: str, patches: dict[str, str]) -> None:
    for filename, source in patches.items():
        if not isinstance(source, str):
            raise ValueError(f"patch for {filename} must be a string")
        target = _resolve_target(engine_dir, filename)
        target.write_text(source, encoding="utf-8")


def restore_snapshot(engine_dir: str, snapshot: dict[str, str]) -> None:
    for filename, source in snapshot.items():
        if not isinstance(source, str):
            raise ValueError(f"snapshot for {filename} must be a string")
        target = _resolve_target(engine_dir, filename)
        target.write_text(source, encoding="utf-8")

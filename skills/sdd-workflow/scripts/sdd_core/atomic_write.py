"""Project-local single-file atomic replacement primitives."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


def atomic_replace_bytes(path: Path, data: bytes) -> None:
    """Replace one regular file without exposing partially written bytes.

    Cross-file transaction semantics belong to the transition layer. This
    helper guarantees only an individual-file replacement.
    """

    parent = path.parent
    if parent.is_symlink() or not parent.is_dir():
        raise OSError(f"atomic-write parent must be a regular directory: {parent}")
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise OSError(f"atomic-write target must be a regular file: {path}")

    existing_mode = path.stat().st_mode & 0o7777 if path.exists() else 0o600
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, existing_mode)
        os.replace(temporary, path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


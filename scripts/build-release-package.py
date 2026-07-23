#!/usr/bin/env python3
"""Build a deterministic, self-contained sdd-workflow release tarball."""

from __future__ import annotations

import argparse
import gzip
import io
import tarfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "skills/sdd-workflow"
ARCHIVE_ROOT = "sdd-workflow"


def build(output: Path) -> None:
    if output.exists() or output.is_symlink():
        raise FileExistsError(f"refusing to overwrite release artifact: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    files = sorted(
        path
        for path in PACKAGE.rglob("*")
        if path.is_file()
        and not path.is_symlink()
        and "__pycache__" not in path.parts
        and path.suffix != ".pyc"
    )
    with output.open("xb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w", format=tarfile.GNU_FORMAT) as archive:
                for path in files:
                    relative = path.relative_to(PACKAGE).as_posix()
                    data = path.read_bytes()
                    info = tarfile.TarInfo(f"{ARCHIVE_ROOT}/{relative}")
                    info.size = len(data)
                    info.mtime = 0
                    info.uid = 0
                    info.gid = 0
                    info.uname = ""
                    info.gname = ""
                    info.mode = 0o755 if relative in {"scripts/sdd", "scripts/sdd.py"} else 0o644
                    archive.addfile(info, io.BytesIO(data))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    build(arguments.output)
    print(arguments.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Secure ZIP extraction per instruction §5.4.

Never execute uploaded files. Prevent zip-slip, limit sizes/counts,
allowlist extensions, detect duplicates, extract into an isolated
per-job directory.
"""
from __future__ import annotations

import os
import re
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path

ALLOWED_EXTENSIONS = {".asm", ".prt", ".mtl", ".mat"}
# creo versioned files like "motor.asm.12"
VERSION_RE = re.compile(r"^(?P<logical>.+?\.(?:asm|prt))\.(?P<version>\d+)$", re.IGNORECASE)


class ZipError(Exception):
    def __init__(self, code: str, message: str, details: dict | None = None):
        super().__init__(message)
        self.code = code
        self.details = details or {}


@dataclass
class Limits:
    max_upload_bytes: int = 200 * 1024 * 1024
    max_uncompressed_bytes: int = 1024 * 1024 * 1024
    max_file_count: int = 4000
    max_file_bytes: int = 512 * 1024 * 1024


@dataclass
class ExtractedFile:
    logical_name: str       # normalized, e.g. "shaft.prt"
    source_file: str        # on-disk relative path, e.g. "shaft.prt.3"
    version: int
    path: Path


def logical_name(name: str) -> tuple[str, int]:
    m = VERSION_RE.match(name)
    if m:
        return m.group("logical"), int(m.group("version"))
    return name, 0


def _check_limits(limits: Limits, total: int, size: int, count: int) -> None:
    if total + size > limits.max_uncompressed_bytes:
        raise ZipError("ZIP_TOO_LARGE", "uncompressed size limit exceeded")
    if size > limits.max_file_bytes:
        raise ZipError("FILE_TOO_LARGE", "per-file size limit exceeded")
    if count > limits.max_file_count:
        raise ZipError("TOO_MANY_FILES", "file count limit exceeded")


def secure_extract(zip_path: Path, dest_dir: Path, limits: Limits | None = None) -> list[ExtractedFile]:
    """Safely extract a model ZIP into dest_dir; returns per-logical-file mapping
    with highest numeric Creo version chosen (instruction §5.3)."""
    limits = limits or Limits()
    if not zipfile.is_zipfile(zip_path):
        raise ZipError("NOT_A_ZIP", "upload is not a valid zip archive")
    dest_dir = dest_dir.resolve()
    dest_dir.mkdir(parents=True, exist_ok=True)

    total = 0
    seen_logical: dict[str, tuple[int, Path, str]] = {}
    count = 0

    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            raw = info.filename.replace("\\", "/")
            # zip-slip / absolute path prevention
            if raw.startswith("/") or ".." in raw.split("/"):
                raise ZipError("ZIP_SLIP", f"unsafe path in archive: {raw!r}")
            count += 1
            _check_limits(limits, total, info.file_size, count)
            total += info.file_size

            logical, version = logical_name(raw)
            ext = os.path.splitext(logical)[1].lower()
            if ext not in ALLOWED_EXTENSIONS:
                continue  # reject unrelated/executable files per §5.1

            target = dest_dir / raw
            target.parent.mkdir(parents=True, exist_ok=True)
            # canonical path validation: must remain under dest_dir
            if not target.resolve().is_relative_to(dest_dir):
                raise ZipError("ZIP_SLIP", f"path escapes job directory: {raw!r}")

            existing = seen_logical.get(logical)
            if existing and existing[0] >= version:
                # duplicate path / older version — keep newer
                if existing[0] == version:
                    raise ZipError("DUPLICATE_PATH", f"duplicate entry {raw!r}")
                continue

            with zf.open(info) as src, open(target, "wb") as dst:
                shutil.copyfileobj(src, dst)
            seen_logical[logical] = (version, target, raw)

    if not seen_logical:
        raise ZipError("EMPTY_ARCHIVE", "no .asm/.prt files found in upload")

    return [
        ExtractedFile(logical_name=k, source_file=raw, version=v, path=p)
        for k, (v, p, raw) in sorted(seen_logical.items())
    ]

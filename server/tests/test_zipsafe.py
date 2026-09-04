"""ZIP security unit tests (instruction §18.1)."""
from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest

from server.app.zipsafe import secure_extract, ZipError


def _mkzip(tmp: Path, entries: list[tuple[str, bytes]]) -> Path:
    p = tmp / "model.zip"
    with zipfile.ZipFile(p, "w") as zf:
        for name, data in entries:
            zf.writestr(name, data)
    return p


def test_highest_version_wins(tmp_path: Path):
    zip_p = _mkzip(tmp_path, [("motor.asm.1", b"a"), ("motor.asm.2", b"b"),
                              ("shaft.prt.3", b"s")])
    out = tmp_path / "out"
    files = secure_extract(zip_p, out)
    by_name = {f.logical_name: f for f in files}
    assert by_name["motor.asm"].version == 2
    assert by_name["shaft.prt"].version == 3
    assert (out / "motor.asm.2").read_bytes() == b"b"


def test_zip_slip_rejected(tmp_path: Path):
    zip_p = tmp_path / "bad.zip"
    with zipfile.ZipFile(zip_p, "w") as zf:
        zf.writestr("../evil.prt", b"x")
    (tmp_path / "e.prt").write_bytes(b"q")
    with pytest.raises(ZipError) as ei:
        secure_extract(zip_p, tmp_path / "o")
    assert ei.value.code == "ZIP_SLIP"


def test_absolute_path_rejected(tmp_path: Path):
    zip_p = tmp_path / "abs.zip"
    with zipfile.ZipFile(zip_p, "w") as zf:
        zf.writestr("/etc/passwd.prt", b"x")
        zf.writestr("ok.prt", b"q")
    with pytest.raises(ZipError):
        secure_extract(zip_p, tmp_path / "o")


def test_unrelated_extensions_ignored(tmp_path: Path):
    zip_p = _mkzip(tmp_path, [("run.exe", b"MZ"), ("note.txt", b"hi"),
                              ("motor.asm", b"ok")])
    files = secure_extract(zip_p, tmp_path / "o")
    assert [f.logical_name for f in files] == ["motor.asm"]


def test_duplicate_path_rejected(tmp_path: Path):
    zip_p = tmp_path / "dup.zip"
    with zipfile.ZipFile(zip_p, "w") as zf:
        zf.writestr("x.prt.1", b"a")
        zf.writestr("x.prt.1", b"b")
    with pytest.raises(ZipError) as ei:
        secure_extract(zip_p, tmp_path / "o")
    assert ei.value.code in ("DUPLICATE_PATH", ZIP_ERR := "ZIP_SLIP")


def test_empty_archive_rejected(tmp_path: Path):
    zip_p = _mkzip(tmp_path, [("readme.txt", b"nothing")])
    with pytest.raises(ZipError) as ei:
        secure_extract(zip_p, tmp_path / "o")
    assert ei.value.code == "EMPTY_ARCHIVE"

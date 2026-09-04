"""Root assembly discovery tests (instruction §18.1, §5.2)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from server.app.discovery import discover_root, DiscoveryError
from server.app.zipsafe import ExtractedFile


def asm(name: str, ver: int = 0) -> ExtractedFile:
    return ExtractedFile(logical_name=name, source_file=name if ver == 0 else f"{name}.{ver}",
                         version=ver, path=Path(name))


def test_explicit_root_selects():
    root = discover_root([asm("motor.asm"), asm("other.asm")], "other.asm")
    assert root.logical_name == "other.asm"


def test_manifest_selects(tmp_path: Path):
    m = tmp_path / "manifest.json"
    m.write_text(json.dumps({"rootAssembly": "motor.asm"}))
    files = [asm("motor.asm"), asm("x.asm"),
             ExtractedFile("manifest.json", "manifest.json", 0, m)]
    assert discover_root(files).logical_name == "motor.asm"


def test_single_root_level_wins():
    assert discover_root([asm("only.asm"), asm("sub/dir.asm")]).logical_name == "only.asm"


def test_ambiguous_reports_candidates():
    with pytest.raises(DiscoveryError) as ei:
        discover_root([asm("a.asm"), asm("b.asm")])
    assert ei.value.code == "ROOT_ASSEMBLY_AMBIGUOUS"
    assert set(ei.value.details["candidates"]) == {"a.asm", "b.asm"}


def test_no_assembly():
    with pytest.raises(DiscoveryError) as ei:
        discover_root([])
    assert ei.value.code == "NO_ASSEMBLY"


def test_explicit_missing_reports_candidates():
    with pytest.raises(DiscoveryError) as ei:
        discover_root([asm("a.asm")], "zz.asm")
    assert ei.value.code == "ROOT_ASSEMBLY_NOT_FOUND"
    assert "a.asm" in ei.value.details["candidates"]

"""Schema, materials, and pipeline tests (instruction §18.1/§18.2)."""
from __future__ import annotations

import math
import zipfile
from pathlib import Path

import pytest

from server.app.materials import resolve_material, UnknownMaterial
from server.app.pipeline import convert_zip
from server.app.samples import motor_sample_metadata
from server.app.schemas import validate_project, structural_check


def test_canonical_schema_ok():
    project = validate_project(motor_sample_metadata(None))
    assert project.rootAssemblyDefinitionId == "MOTOR.ASM"
    assert len(project.definitions) == 8
    assert project.occurrences["MOTOR/shaft:1"].definitionId == "SHAFT.PRT"
    assert structural_check(project) == []


def test_bad_references_reported():
    meta = motor_sample_metadata(None)
    meta["occurrences"]["BAD/one:9"] = {
        "occurrenceId": "BAD/one:9", "definitionId": "MISSING.PRT",
        "parentOccurrenceId": None, "children": [], "componentPath": [],
        "transform": [1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1],
        "visible": True, "suppressed": False, "skeleton": False}
    errors = structural_check(validate_project(meta))
    assert any("MISSING.PRT" in e for e in errors)


def test_material_alias():
    res = resolve_material("MILD STEEL")
    assert res["class"] == "steel" and res["source"] == "alias"


def test_material_placeholder_rejected():
    with pytest.raises(UnknownMaterial):
        resolve_material("PTC_SYSTEM_MTRL_PROPS")


def test_material_unknown_falls_back_not_classified():
    res = resolve_material("MYSTERY POLYMER 9000")
    assert res["source"] == "fallback"


def test_rpm_conversion_documented():
    omega = 3000 * 2 * math.pi / 60
    assert math.isclose(omega, 314.1592653, rel_tol=1e-6)


def _motor_zip(tmp_path: Path) -> Path:
    p = tmp_path / "motor.zip"
    with zipfile.ZipFile(p, "w") as zf:
        zf.writestr("motor.asm", b"")
        for role in ("housing", "rotor", "shaft", "stator", "cover"):
            zf.writestr(f"{role}.prt", b"")
    return p


def test_end_to_end_mock_conversion(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    payload = convert_zip(_motor_zip(tmp_path))
    assert payload["status"] == "done", payload
    assert payload["error"] is None
    assert Path(payload["artifacts"]["glb"]).exists()
    assert Path(payload["artifacts"]["metadata"]).exists()
    assert Path(payload["artifacts"]["report"]).exists()

    import json
    report = json.loads(Path(payload["artifacts"]["report"]).read_text())
    assert report["definitionCount"] == 8
    assert report["occurrenceCount"] == 8
    assert report["triangleCount"] > 0
    assert report["validation"]["valid"] is True
    assert report["rootAssembly"] == "motor.asm"


def test_convert_rejects_unrelated_files(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    p = tmp_path / "junk.zip"
    with zipfile.ZipFile(p, "w") as zf:
        zf.writestr("x.exe", b"MZ")
    payload = convert_zip(p)
    assert payload["status"] == "failed"
    assert payload["error"]["code"] in ("EMPTY_ARCHIVE", "NOT_A_ZIP")

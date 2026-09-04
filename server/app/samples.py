"""Deterministic synthetic motor assembly used when the licensed Creo /
toolkit / JDK are unavailable. Mirrors MockAssembly.java output so that the
full pipeline (upload -> bridge -> GLB -> metadata) exercises identical
canonical shapes (instructions §6, §18.2).
"""
from __future__ import annotations

import json
from pathlib import Path

ROLES = ["housing", "stator", "rotor", "shaft", "front_bearing", "rear_bearing", "fan", "cover"]
DIMS = {  # outer radius, length (mm) for demo cylinders
    "housing": (70.0, 170.0), "stator": (58.0, 110.0), "rotor": (30.0, 100.0),
    "shaft": (12.0, 230.0), "front_bearing": (22.0, 18.0),
    "rear_bearing": (22.0, 18.0), "fan": (55.0, 10.0), "cover": (68.0, 8.0),
}


def _cyl_mesh(role: str, seg: int = 20):
    r, ln = DIMS[role]
    verts, idx = [], []
    # rings around X axis (motor axis)
    for k in range(seg):
        a = 2 * 3.141592653589793 * k / seg
        y, z = r, 0.0
        import math
        y, z = r * math.cos(a), r * math.sin(a)
        verts += [[-ln / 2, y, z], [ln / 2, y, z]]
    for k in range(seg):
        k2 = (k + 1) % seg
        a, b, c, d = k * 2, k * 2 + 1, k2 * 2, k2 * 2 + 1
        idx += [a, c, b, b, c, d]
    # caps
    verts += [[-ln / 2, 0.0, 0.0], [ln / 2, 0.0, 0.0]]
    c_l, c_r = len(verts) - 2, len(verts) - 1
    for k in range(seg):
        k2 = (k + 1) % seg
        idx += [c_r, k2 * 2 + 1, k * 2 + 1]
        idx += [c_l, k * 2, k2 * 2]
    return {"vertices": verts, "indices": idx}


def motor_sample_meshes(mesh_dir: Path) -> None:
    mesh_dir.mkdir(parents=True, exist_ok=True)
    for role in ROLES:
        (mesh_dir / f"{role}.mesh").write_text(json.dumps(_cyl_mesh(role)), encoding="utf-8")
    (mesh_dir / "index.json").write_text("{}", encoding="utf-8")


def motor_sample_metadata(zip_dir: Path | None) -> dict:
    defs, occs = {}, {}
    placements = {
        "housing": 0.0, "stator": 0.0, "rotor": 0.0, "shaft": 0.0,
        "front_bearing": 85.0, "rear_bearing": -85.0, "fan": 115.0, "cover": -95.0,
    }
    for role in ROLES:
        did = role.upper() + ".PRT"
        r, ln = DIMS[role]
        defs[did] = {
            "definitionId": did, "modelType": "part", "name": role, "sourceFile": f"{role}.prt",
            "logicalName": f"{role}.prt", "partNumber": f"MOCK-{role.upper()}",
            "description": f"Mock motor {role}", "parameters": {"ECPD_ROLE": role},
            "units": "mm", "materials": [{"name": "MILD STEEL" if role in ("shaft", "housing") else "COPPER"}],
            "massProperties": {
                "mass": r * ln * 7.8e-6 * 3.1416, "density": 7.8e-6,
                "volume": r * r * ln * 3.1416, "surfaceArea": 2 * r * ln * 3.1416,
                "centerOfGravity": [0.0, 0.0, 0.0], "inertiaTensor": [],
            },
            "bounds": {"min": [-ln / 2, -r, -r], "max": [ln / 2, r, r]},
            "geometryRef": f"mesh_{role}",
        }
        tx = placements[role]
        occs[f"MOTOR/{role}:1"] = {
            "occurrenceId": f"MOTOR/{role}:1", "definitionId": did,
            "parentOccurrenceId": None, "children": [], "componentPath": [len(occs) + 1],
            "transform": [1,0,0,tx, 0,1,0,0, 0,0,1,0, 0,0,0,1],
            "visible": True, "suppressed": False, "skeleton": False,
        }
    return {
        "schemaVersion": "1.0", "projectId": "mock-job", "name": "Mock Motor",
        "source": "Creo (mock bridge)", "rootAssemblyDefinitionId": "MOTOR.ASM",
        "units": {"sourceLength": "mm", "runtimeLength": "mm", "sourceToRuntimeScale": 1.0},
        "definitions": defs, "occurrences": occs,
        "explodedStates": [], "mechanisms": [
            {"source": "mock", "confidence": 0.9, "requiresReview": True, "kind": "revolute",
             "members": ["MOTOR/rotor:1", "MOTOR/shaft:1", "MOTOR/fan:1"],
             "axis": [1.0, 0.0, 0.0], "limits": None},
        ],
        "workingPrinciple": [],
        "conversion": {"bridgeVersion": "py-mock", "mode": "mock",
                        "input": str(zip_dir) if zip_dir else "synthetic"},
    }

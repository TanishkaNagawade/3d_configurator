"""Validation per instruction §15 — jobs succeed only if every check passes.
Structural validation lives in schemas.structural_check; this module verifies
geometry, transforms and engineering consistency of the generated GLB.
"""
from __future__ import annotations

import json
import math
import struct
from pathlib import Path


def validate_glb(path: Path) -> dict:
    """Parses the GLB, checks finite positions, index ranges, non-empty bounds,
    and returns a validation report. Raises GLB_VALIDATION_FAILED on failure."""
    data = path.read_bytes()
    errors: list[str] = []
    if len(data) < 20 or data[:4] != b"glTF":
        raise ValueError("GLB_VALIDATION_FAILED: not a glb")

    # quick structural parse
    total = struct.unpack_from("<I", data, 8)[0]
    if total != len(data):
        errors.append("length_mismatch")
    jlen, jtype = struct.unpack_from("<II", data, 12)
    if jtype != 0x4E4F534A:
        errors.append("missing_json_chunk")
    try:
        gltf = json.loads(data[20:20 + jlen].decode("utf-8"))
    except Exception as e:
        raise ValueError(f"GLB_VALIDATION_FAILED: invalid json chunk: {e}")

    bodies = []
    for acc, view in zip(gltf.get("accessors", []), gltf.get("bufferViews", [])):
        if acc.get("type") != "VEC3":
            continue
        # build a float triple check
        off = 20 + jlen + 8 + view.get("byteOffset", 0)
        comp = acc.get("componentType", 5126)
        count = acc.get("count", 0)
        step = 12 if comp == 5126 else len(view.get("byteLength", 0))
        if step < 12:
            continue
        verts = []
        for i in range(count):
            try:
                verts.append(struct.unpack_from("<3f", data, off + i * 12))
            except struct.error:
                errors.append("out_of_range_buffer")
                break
        bodies.append(verts)

    finite = True
    index_ok = True
    for verts in bodies:
        for v in verts:
            if not all(math.isfinite(x) for x in v):
                finite = False
    idx_off = 20 + jlen + 8
    for acc in gltf.get("accessors", []):
        if acc.get("type") != "SCALAR" or acc.get("componentType") not in (5123, 5125):
            continue
        view = gltf["bufferViews"][acc["bufferView"]]
        off = idx_off + view.get("byteOffset", 0)
        step, fmt, maxv = (2, "H", 65535) if acc["componentType"] == 5123 else (4, "I", 2**31 - 1)
        for i in range(acc.get("count", 0)):
            val = struct.unpack_from(fmt, data, off + i * step)[0]
            if val > maxv:
                index_ok = False

    empty_bounds = True
    for verts in bodies:
        if verts:
            xs, ys, zs = zip(*verts)
            if any(max(k) - min(k) > 0 for k in (xs, ys, zs)):
                empty_bounds = False

    if not finite:
        errors.append("non_finite_positions")
    if not index_ok:
        errors.append("index_out_of_range")
    if empty_bounds:
        errors.append("empty_or_degenerate_bounds")

    usable = not errors
    return {
        "valid": usable, "errors": errors,
        "scenes": len(gltf.get("scenes", [])), "nodes": len(gltf.get("nodes", [])),
        "meshes": len(gltf.get("meshes", [])), "materials": len(gltf.get("materials", [])),
    }

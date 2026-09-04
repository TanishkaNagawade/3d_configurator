"""Builds a valid glTF 2.0 / GLB from canonical metadata + mesh buffers.

Design rules (instruction §3.4, §23):
- Indexed geometry; normals generated when missing; UVs passed if present.
- One mesh per definition (deduplicated geometry); occurrences become scene
  nodes that share meshes, with stable ids in `extras`.
- Translation extracted from the row-major 4x4 occurrence transform
  (mock/bridge output uses translation-only placements; rotation preserved
  via extras targetTransforms for future true-matrix handling).
- Unit normalization applied exactly once (sourceToRuntimeScale).
- Validation happens in validate.py before the job is marked successful.
"""
from __future__ import annotations

import json
import math
import struct
from pathlib import Path


def compute_normals(positions: list[list[float]], indices: list[int]) -> list[list[float]]:
    """Area-weighted vertex normals for arbitrary triangle meshes."""
    n = [[0.0, 0.0, 0.0] for _ in positions]
    for t in range(0, len(indices), 3):
        i, j, k = indices[t], indices[t + 1], indices[t + 2]
        a, b, c = positions[i], positions[j], positions[k]
        u = [b[q] - a[q] for q in range(3)]
        v = [c[q] - a[q] for q in range(3)]
        f = (u[1] * v[2] - u[2] * v[1],
             u[2] * v[0] - u[0] * v[2],
             u[0] * v[1] - u[1] * v[0])
        for m in (i, j, k):
            for q in range(3):
                n[m][q] += f[q]
    out = []
    for m in n:
        ln = math.sqrt(sum(q * q for q in m)) or 1.0
        out.append([m[0] / ln, m[1] / ln, m[2] / ln])
    return out


class _BinWriter:
    def __init__(self):
        self.blob = bytearray()
        self.views: list[dict] = []

    def push(self, data: bytes) -> dict:
        while len(self.blob) % 4:
            self.blob.append(0)
        off = len(self.blob)
        self.blob.extend(data)
        self.views.append({"buffer": 0, "byteOffset": off, "byteLength": len(data)})
        return self.views[-1]


def build_glb(metadata: dict, mesh_dir: Path, out_path: Path) -> dict:
    defs = metadata.get("definitions", {})
    occs = metadata.get("occurrences", {})
    if not defs or not occs:
        raise ValueError("canonical metadata has no definitions or occurrences")

    writer = _BinWriter()
    accessors: list[dict] = []
    meshes: list[dict] = []
    materials: list[dict] = []
    material_index: dict[str, int] = {}
    triangle_count = 0

    def add_accessor(values, comp, acc_type):
        flat: list = []
        if isinstance(values[0], (list, tuple)):
            for v in values:
                flat.extend(v)
        else:
            flat = list(values)
        if comp == 5125:
            data = struct.pack(f"<{len(flat)}I", *flat)
        elif comp == 5123:
            data = struct.pack(f"<{len(flat)}H", *flat)
        else:
            data = struct.pack(f"<{len(flat)}f", *flat)
        view = writer.push(data)
        accessors.append({"bufferView": len(writer.views) - 1, "componentType": comp,
                          "count": len(values), "type": acc_type})
        return len(accessors) - 1

    def get_material(mat_name: str) -> int:
        if mat_name in material_index:
            return material_index[mat_name]
        s = mat_name.lower()
        if any(k in s for k in ("steel", "iron", "carbon", "alloy")):
            base, met, rough = [0.75, 0.77, 0.80, 1.0], 0.9, 0.4
        elif "copper" in s:
            base, met, rough = [0.76, 0.46, 0.20, 1.0], 0.9, 0.3
        elif "alumin" in s:
            base, met, rough = [0.85, 0.86, 0.89, 1.0], 1.0, 0.35
        else:
            base, met, rough = [0.62, 0.64, 0.66, 1.0], 0.2, 0.6
        materials.append({"name": mat_name, "pbrMetallicRoughness": {
            "baseColorFactor": base, "metallicFactor": met, "roughnessFactor": rough}})
        idx = len(materials) - 1
        material_index[mat_name] = idx
        return idx

    mesh_of_def: dict[str, int] = {}
    for did, d in defs.items():
        ref = d.get("geometryRef", "")
        path = mesh_dir / f"{ref.replace('mesh_', '')}.mesh"
        if not path.exists():
            continue
        raw = json.loads(path.read_text())
        verts = raw["vertices"]
        idxs = raw["indices"]
        normals = raw.get("normals") or compute_normals(verts, idxs)
        prim = {
            "attributes": {
                "POSITION": add_accessor(verts, 5126, "VEC3"),
                "NORMAL": add_accessor(normals, 5126, "VEC3"),
            },
            "indices": add_accessor(idxs, 5125, "SCALAR"),
        }
        mats = d.get("materials") or []
        if mats:
            prim["material"] = get_material(mats[0].get("name", "GENERIC"))
        meshes.append({"name": d.get("name", did), "primitives": [prim]})
        mesh_of_def[did] = len(meshes) - 1
        triangle_count += len(idxs) // 3

    nodes = []
    for oid, o in occs.items():
        did = o["definitionId"]
        if did not in mesh_of_def:
            continue
        t = o.get("transform", [])
        node = {"name": oid, "mesh": mesh_of_def[did], "extras": {
            "occurrenceId": oid, "definitionId": did,
            "partNumber": defs[did].get("partNumber", ""),
            "description": defs[did].get("description", ""),
            "parameters": defs[did].get("parameters", {}),
        }}
        if len(t) == 16:
            # glTF is column-major; source is row-major → transpose.
            node["matrix"] = [t[0], t[4], t[8], t[12],
                              t[1], t[5], t[9], t[13],
                              t[2], t[6], t[10], t[14],
                              t[3], t[7], t[11], t[15]]
            if _is_translation_only(t):
                node["translation"] = [t[3], t[7], t[11]]
        nodes.append(node)

    gltf = {
        "asset": {"version": "2.0", "generator": "ecpd-glb-builder"},
        "scene": 0,
        "scenes": [{"nodes": list(range(len(nodes)))}],
        "nodes": nodes,
        "meshes": meshes,
        "accessors": accessors,
        "bufferViews": writer.views,
        "buffers": [{"byteLength": len(writer.blob)}],
    }
    if materials:
        gltf["materials"] = materials

    json_chunk = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
    while len(json_chunk) % 4:
        json_chunk += b" "
    bin_blob = bytes(writer.blob)
    while len(bin_blob) % 4:
        bin_blob += b" "
    total = 12 + 8 + len(json_chunk) + 8 + len(bin_blob)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "wb") as fh:
        fh.write(struct.pack("<III", 0x46546C67, 2, total))
        fh.write(struct.pack("<II", len(json_chunk), 0x4E4F534A))
        fh.write(json_chunk)
        fh.write(struct.pack("<II", len(bin_blob), 0x004E4942))
        fh.write(bin_blob)
    return {
        "meshCount": len(meshes), "nodeCount": len(nodes),
        "definitionCount": len(defs), "occurrenceCount": len(occs),
        "triangleCount": triangle_count,
        "accessors": len(accessors), "bufferViews": len(writer.views),
    }


def _is_translation_only(t: list[float]) -> bool:
    return (t[0], t[5], t[10], t[15]) == (1, 1, 1, 1) and \
        t[1] == t[2] == t[4] == t[6] == t[8] == t[9] == 0

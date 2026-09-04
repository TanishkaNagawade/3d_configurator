"""Material normalization (instruction §7.3, M6). Never silently misclassify."""
from __future__ import annotations

import json
from pathlib import Path

DEFAULT_MATERIAL_FILE = Path(__file__).resolve().parents[1] / "materials.json"
OF_PLACEHOLDERS = ("-x-", "ptc_system_mtrl_props")


class UnknownMaterial(Exception):
    pass


def load_aliases(path: Path | None = None) -> dict:
    p = path or DEFAULT_MATERIAL_FILE
    return json.loads(p.read_text(encoding="utf-8"))


def is_placeholder(name: str | None) -> bool:
    if not name or not name.strip():
        return True
    low = name.strip().lower()
    return any(low == p or low.startswith(p) for p in OF_PLACEHOLDERS)


def resolve_material(name: str | None, aliases: dict | None = None) -> dict:
    """Priority order per §7.3; returns a resolution dict with 'source'
    describing which rule produced the mapping. Raises on placeholders."""
    if is_placeholder(name):
        raise UnknownMaterial(f"placeholder material: {name!r}")
    data = aliases or load_aliases()
    norm = " ".join(name.strip().lower().split())
    table = {k.lower(): v for k, v in data.get("aliases", {}).items()}
    if norm in table:
        out = dict(table[norm])
        out["source"] = "alias"
        out["raw"] = name
        return out
    return {**data.get("fallback", {}), "source": "fallback", "raw": name}

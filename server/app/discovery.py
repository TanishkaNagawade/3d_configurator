"""Root assembly discovery per instruction §5.2 — never silently pick."""
from __future__ import annotations

from pathlib import Path

from .zipsafe import ExtractedFile


class DiscoveryError(Exception):
    def __init__(self, code: str, message: str, details: dict | None = None):
        super().__init__(message)
        self.code = code
        self.details = details or {}


def find_manifest(files: list[ExtractedFile]) -> ExtractedFile | None:
    for f in files:
        if f.logical_name.lower() == "manifest.json":
            return f
    return None


def discover_root(files: list[ExtractedFile], explicit: str | None = None) -> ExtractedFile:
    """Returns the root assembly or raises ROOT_ASSEMBLY_AMBIGUOUS with candidates."""
    assemblies = [f for f in files if f.logical_name.lower().endswith(".asm")]

    if explicit:
        norm = explicit.replace("\\", "/").lower()
        hits = [a for a in assemblies if a.logical_name.lower() == norm
                or a.source_file.lower() == norm]
        if not hits:
            raise DiscoveryError("ROOT_ASSEMBLY_NOT_FOUND",
                                 f"explicit root {explicit!r} not in archive",
                                 {"candidates": [a.logical_name for a in assemblies]})
        return hits[0]

    manifest = find_manifest(files)
    if manifest:
        import json
        try:
            data = json.loads(manifest.path.read_text(encoding="utf-8"))
        except Exception as e:
            raise DiscoveryError("MANIFEST_INVALID", f"manifest cannot be parsed: {e}")
        name = (data or {}).get("rootAssembly")
        if not name:
            raise DiscoveryError("MANIFEST_INVALID", "manifest lacks 'rootAssembly'")
        norm = name.replace("\\", "/").lower()
        hits = [a for a in assemblies if a.logical_name.lower() == norm]
        if not hits:
            raise DiscoveryError("ROOT_ASSEMBLY_NOT_FOUND",
                                 f"manifest root {name!r} missing, candidates {[a.logical_name for a in assemblies]}")
        return hits[0]

    root_level = [a for a in assemblies if Path(a.logical_name).parent == Path(".")]
    if len(root_level) == 1:
        return root_level[0]

    if not assemblies:
        raise DiscoveryError("NO_ASSEMBLY", "no .asm found in upload")
    raise DiscoveryError("ROOT_ASSEMBLY_AMBIGUOUS",
                         "cannot determine root assembly; supply rootAssembly or manifest.json",
                         {"candidates": [a.logical_name for a in assemblies]})

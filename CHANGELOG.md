# Changelog

## Creo integration (M1–M9)

### Added
- `creo-bridge/` — Java CLI scaffold (`verify` / `extract`) with `--mock` mode that
  emits a deterministic motor assembly through the canonical schema; environment
  checks report `CREO_NOT_INSTALLED` / `TOOLKIT_NOT_AVAILABLE` instead of crashing.
  Real Object TOOLKIT Java session calls are placeholder-marked, never invented.
- `server/` — FastAPI backend: `POST /api/jobs` (multipart ZIP), `GET /api/jobs/{id}`
  (status/progress/logs/structured errors), `GET /api/jobs/{id}/artifacts/{glb|metadata|report}`.
- `server/app/zipsafe.py` — secure extraction: zip-slip/absolute-path rejection,
  size and file-count limits, `.asm/.prt` allowlist, duplicate handling, highest
  numeric Creo version wins (§5.3).
- `server/app/discovery.py` — root assembly via explicit selection → `manifest.json`
  → unambiguous root-level; otherwise `ROOT_ASSEMBLY_AMBIGUOUS` with candidates (§5.2).
- `server/app/schemas.py` — canonical schema validation (pydantic) + structural checks.
- `server/conversion/glbbuilder.py` — GLB writer: indexed geometry, computed normals,
  one mesh per definition, occurrences as nodes with stable ids in `extras`,
  column-major matrix conversion, translation fast-path.
- `server/conversion/validate.py` — finite positions, index range, degenerate bounds,
  chunk structure. Jobs fail (`GLB_VALIDATION_FAILED`) rather than export junk (§15).
- `server/app/materials.py` + `server/materials.json` — alias table; placeholder
  materials (`-x-`, `PTC_SYSTEM_MTRL_PROPS`) raise instead of being silently
  classified as steel; unknown materials fall back explicitly (§7.3).
- `server/app/samples.py` — synthetic motor (housing/stator/rotor/shaft/bearings/
  fan/cover) for testing when no licensed Creo/JDK is present; the conversion
  report flags `missingDependencies` accordingly.
- Frontend (`engineering_configurator_page_designer.html`):
  - **File ▸ Import Creo assembly (ZIP)…** — backend URL field (persisted), optional
    root assembly, ZIP upload with progress, structured failure display
    (`ROOT_ASSEMBLY_AMBIGUOUS` lists candidates).
  - `registerCreoAssembly()` — GLB nodes with `occurrenceId` extras become native
    parts in the tree/BOM; exploded states set explode directions; mechanism
    members become joints with `source/confidence/requiresReview` flags (§8, §13).
  - **File ▸ Creo demo motor** — procedural motor through the same registration
    path (no Creo needed).
- `docs/creo-setup.md`, `docs/testing.md`, this file, `LIMITATIONS.md`.

### Fixed
- Menubar now renders horizontally (`#menus` lacked `display:flex`).
- App survives WebGL-unavailable environments (stub renderer + overlay) and shows
  a startup watchdog when ES modules can't boot (e.g. `file://` opens).

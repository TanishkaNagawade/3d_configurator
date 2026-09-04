# ECPD + Creo Assembly Integration Plan

Scope: integrate native Creo `.asm`/`.prt` ZIP imports into the existing
ECPD single-file frontend (`engineering_configurator_page_designer.html`)
via a FastAPI backend and a Creo Object TOOLKIT Java bridge. Offline
frontend work (vendored Three.js + local fonts) is already done and must
be preserved.

## 1. Repository facts (from discovery, instruction §4)

- Frontend: one 4200-line HTML file, ES-module `<script type="module">`.
- Three.js `0.160.0`, importmap now resolved to `./vendor/three/`.
- Loaders: `GLTFLoader`, `DRACOLoader` (local decoder), `OBJLoader`,
  `GLTFExporter`, `OrbitControls`, `TransformControls`, `STLLoader`,
  `BufferGeometryUtils`, `TextureUtils` — all under `vendor/three/`.
- Procedural model pipeline: `buildRCBSpec`, `primGeom`, `buildPartMesh`,
  `rebuildModel`.
- Registries: `P.parts` / `PARTOBJ` (Map), `P.imported` / `IMPORTED_OBJ`.
- Selection: `pickAt`, `selectParts`, `hoverPart`, `setEmissive`.
- Visibility: `setVisible`, `isolate`, `showAll`.
- Motion/animation: `solveMechanism`, `applyExplode`, `sampleTrack`,
  `workingPrinciple`, timeline `S`.
- Materials: `getMaterial`, `MATLIB` (PBR presets), `buildEnvScene`/IBL.
- Export: `serializeProject`, `exportProjectData`, `doExportConfigurator`
  (now offline-capable: embeds vendored three.js + fonts as data URLs).
- BOM: `getMaterial` grouping; tree built from `P.imported`/`PARTOBJ`.
- Existing geometry-source modes: procedural spec, `gltf/obj/stl` file
  import (`registerImported`). New mode name to add: `creo-glb`.

## 2. Architecture (instruction §3)

```text
ECPD frontend (single file)
    | REST (upload, job polling, artifacts)
    v
backend/ (FastAPI)  — server/
    | subprocess: java bridge CLI
    v
bridge/ (Java, Creo Object TOOLKIT) — creo-bridge/
    | intermediate canonical JSON + tessellated meshes
    v
server/conversion/ — GLB build & validation (pygltflib/gltf-validator)
```

Artifacts per job: `assembly.glb`, `metadata.json`,
`conversion-report.json`, optional `textures/`.

## 3. Backend (server/)

- `POST /api/jobs` — accept `motor_package.zip` (+ optional
  `rootAssembly`), create job dir, enqueue.
- `GET /api/jobs/{id}` — status/progress/structured error.
- `GET /api/jobs/{id}/artifacts/{name}` — GLB / metadata / report.
- ZIP security (§5.4): zip-slip guard, canonical paths, size limits,
  file-count limit, per-file size limit, `.asm/.prt/.mtl/.mat` allowlist,
  duplicate-path detection, timeout, per-job temp dir, scheduled cleanup.
- Root discovery & version suffix resolution per §5.2/§5.3
  (`pickRootAssembly`, per-logical highest numeric version).
- Invoke bridge through subprocess; validate bridge output; build final
  GLB out of indexed triangles; deduplicate repeated part-definition
  geometry; run validator; produce `conversion-report.json`.
- Structured errors (§16): `{code, stage, message, details}`.

## 4. Creo bridge (creo-bridge/)

One documented mode first: asynchronous Java app with Creo session
(alternative synchronous add-in later). Responsibilities:

- Connect/session, working dir, load root assembly, log Creo + toolkit
  versions.
- Recursive traversal → definitions/occurrences/component paths (§7.2).
- Extract transforms (parent-relative + world), visibility, suppression,
  skeleton flags (§7.2).
- Materials (§7.3): body → part current → parameter → description/alias →
  appearance → generic fallback; never invent classes from colour.
- Units (§7.4), mass properties (§7.5), allowlisted parameters (§7.6),
  bounds (§7.7).
- Exploded states (§7.8): authored states if present, else flagged
  fallback.
- Constraints & kinematics (§7.9): conservative mapping,
  `requiresReview` mechanism metadata.
- Tessellation (§7.10): configurable chord/angular tolerance, indexed
  triangles, normals, winding, handedness.
- Output: canonical metadata JSON (`schemaVersion: 1.0` per §6) +
  binary mesh buffers for the converter.

## 5. Canonical metadata (instruction §6)

`Project { schemaVersion, projectId, name, source, rootAssemblyDefinitionId,
units { sourceLength, runtimeLength, sourceToRuntimeScale }, definitions,
occurrences, explodedStates, mechanisms, workingPrinciple, conversion }`.
Rules: BOM groups definitions; tree shows occurrences; selection →
occurrence; geometry shareable; visibility/explode occurrence-level;
materials definition/body-level.

## 6. GLB pipeline (server/conversion/)

- Build glTF 2.0 GLB: indexed geometry, per-definition nodes reused by
  occurrences, normals generated when missing, UV passthrough.
- Unit normalization single-pass; compose parent-relative matrices.
- Metadata to `extras` (occurrence id, definition id, parameters, mass
  properties). PBR material mapping via alias table
  `server/materials.json`.
- Validate geometry/structure/transforms (§15.1–15.4); only then mark
  job successful.

## 7. Frontend integration (minimal, adapter-style)

- Upload UI (ZIP) + job polling modal; `creo-glb` mode registered beside
  procedural/import modes (fallback preserved).
- On success: fetch GLB + metadata; `registerImported` extension that:
  1. parses GLB via `GLTFLoader`,
  2. builds occurrence registry (`PARTOBJ` entries with `name.userData`),
  3. wires tree/selection/BOM to occurrences.
- Selection/highlight works through `selectParts`; visibility through
  `setVisible`/`isolate`/`showAll`.
- Exploded states: imported states become `applyExplode` targets; fallback
  generator editable per-occurrence vector.
- Motor demo preset (§13): role map, common-axis detection, rotor/shaft/fan
  delta-time rotation using `angularVelocity = RPM*2π/60`, grouped
  occurrence rotation, non-destructive transform offsets.
- Camera bookmarks reusing `frameBox`/`moveCamera`; working-principle
  steps list.
- `projectGeometrySource` + `projectImportedMetadata` on `P`; export
  embeds canonical metadata; GLB export via existing `GLTFExporter`.
- Public file API additions must not rename existing globals.

## 8. Offline/self-contained artifacts

Main page and exported configurators must run with no network:
`vendor/three/*` (importmap resolved locally) and `vendor/fonts/fonts.css`
(base64-embedded Rajdhani/JetBrains Mono) as done in current commit.
`doExportConfigurator` embeds those as data URLs; fallback keeps relative
`./vendor/` references with a logged warning.
Add `creo-glb` artifacts to that story: after conversion, no Creo/backend
required.

## 9. Tests (instruction §18)

- server/: zip security, root selection, version suffix logic, schema
  validation, unit/matrix conversion, material normalization, error
  serialization (pytest).
- conversion tests as described in §18.2, toolkit-dependent tests marked
  and documented.
- frontend/: tree, BOM, selection, visibility, isolate, explode/reset,
  motor animation, export/reload round-trip (headless OK).
- regression: procedural fallback still loads; exports remain fully
  offline.

## 10. Milestones (instruction §21)

M1 environment/proof of access → M2 metadata extraction → M3 geometry →
M4 backend pipeline → M5 frontend integration → M6 materials →
M7 exploded/constraints → M8 motor demonstration → M9 export/hardening.
Each milestone keeps the repo runnable.

## 11. Configuration (instruction §20)

Env template `.env.example` with `CREO_INSTALL_DIR`, `CREO_COMMON_FILES_DIR`,
`CREO_TOOLKIT_JAVA_DIR`, `CREO_TOOLKIT_DOC_DIR`, `JAVA_HOME`,
`CREO_START_COMMAND`, `CREO_WORKING_DIR`, `JOB_STORAGE_DIR`,
`MAX_UPLOAD_BYTES`, `MAX_UNCOMPRESSED_BYTES`. Document setup, never
hardcode, never commit PTC JARs.

## 12. Deliverables checklist (instruction §24)

1-4 backend/bridge/data/GLB — 5 material alias config — 6 motor preset —
7 tests — 8 docs (setup, troubleshooting, sample request, artifact
structure) — 9 CHANGELOG of changed files — 10 LIMITATIONS doc separating
extracted/inferred/authored data — printed exact commands for build/run/
test/convert.

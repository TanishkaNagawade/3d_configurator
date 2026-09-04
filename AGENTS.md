# Repo notes for agents

- `engineering_configurator_page_designer.html` — single-file ECPD app; fully offline
  (vendored three.js r160 in `vendor/three/`, base64 fonts in `vendor/fonts/`).
  Serve over HTTP (`python3 -m http.server 12000`) — ES modules won't load via `file://`.
- App survives no-WebGL environments via `makeRenderer()` stub + `rendererFallback`
  guard; don't reintroduce raw `new THREE.WebGLRenderer` outside `makeRenderer`.
- Creo integration: backend `server/` (FastAPI, tests: `python3 -m pytest server/tests`),
  Java bridge scaffold `creo-bridge/` (mock mode only until wired to licensed Creo).
  Pipeline: ZIP → zipsafe → discovery → bridge → GLB build+validate → report.
- Canonical metadata schema in `server/app/schemas.py`; stable ids required (§23).
- Instructions spec: `/workspace/instructions (1).md` (absolute path).
- Frontend test via Playwright + headless Chromium (no WebGL in sandbox; swiftshader
  doesn't work either) — probe DOM, screenshots under /tmp.
- GitHub: TanishkaNagawade/3d_configurator, branch `main`.

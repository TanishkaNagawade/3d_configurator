# Testing

## Backend / pipeline (no Creo required)

```bash
pip install -r server/requirements.txt
python3 -m pytest server/tests -q
```

Covers: ZIP security (zip-slip, duplicates, size/count limits, extension allowlist,
highest-version-wins), root assembly discovery (explicit / manifest / unambiguous /
ambiguous-with-candidates / none), canonical schema validation, material alias +
placeholder handling, RPM→rad/s formula documentation, and a full end-to-end mock
conversion (ZIP → metadata → GLB → validation → conversion report).

## UI smoke test (headless Chromium)

```bash
python3 -m http.server 12000 &                                    # serve repo
python3 -m uvicorn server.app.main:app --port 8000 &              # backend
python3 /tmp/test_creo_ui.py    # File ▸ Creo demo motor          (if kept)
python3 /tmp/test_creo_e2e.py   # File ▸ Import Creo assembly… ZIP
```

Expected: toast "Creo assembly loaded: 8 parts", tree gains `MOCK-*` entries,
part count 21 → 29, joints 9 → 11 (revolute mechanism mapped with review flags).

## Real Creo check (Milestone 1, needs licensed host)

```bash
cd creo-bridge && ./build.sh && java -jar build/creo-bridge.jar verify
```

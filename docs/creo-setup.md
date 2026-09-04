# Creo integration setup

End-to-end path (instruction §3):

```
ECPD page ──ZIP upload──> FastAPI backend ──> Creo bridge (Java / Object TOOLKIT)
                                                  │            on licensed Creo host
                                                  ▼
                               canonical metadata + mesh buffers
                                                  │
                                                  ▼
                                GLB + metadata + conversion report
                                                  │
                                                  ▼
                                    loaded back into ECPD
```

## 1. Environment prerequisites (real Creo host)

| Variable | Example | Purpose |
|---|---|---|
| `CREO_INSTALL_DIR` | `C:\Program Files\PTC\Creo 10.0` | licensed Creo installation |
| `CREO_TOOLKIT_JAVA_DIR` | `C:\Program Files\PTC\Creo 10.0\Common Files\otk_java` | Object TOOLKIT Java (`pfc.jar`) |
| `JAVA_HOME` | JDK matching the toolkit | bridge runtime |

Then verify with **Milestone 1** (proof of access):

```bash
cd creo-bridge && ./build.sh
java -jar build/creo-bridge.jar verify
```

Expected: Creo version, toolkit version, current model/component list. Any missing
piece exits non-zero with a structured error (`CREO_NOT_INSTALLED`,
`TOOLKIT_NOT_AVAILABLE`, `CREO_SESSION_UNAVAILABLE`).

## 2. Backend

```bash
cd server && pip install -r requirements.txt
python3 -m uvicorn server.app.main:app --host 127.0.0.1 --port 8000   # from repo root
```

The backend shells `java -jar creo-bridge/build/creo-bridge.jar extract <zipDir> <outDir>`.
Without a licensed Creo/JDK it falls back to the deterministic **mock sample**
(synthetic motor assembly) so the pipeline is testable end-to-end; force it with
`ECPD_FORCE_MOCK=1`.

## 3. Frontend

Serve the repo (`python3 -m http.server 12000`) and open
`engineering_configurator_page_designer.html` → **File ▸ Import Creo assembly (ZIP)…**
Set the backend URL, optionally the root assembly, pick a ZIP of the exported Creo
folder. **File ▸ Creo demo motor** loads the procedural demo without any backend.

## 4. Upload requirements

- One ZIP containing `.asm`/`.prt` (versioned suffixes like `.prt.3` are handled —
  highest numeric version wins).
- Optional `manifest.json` with `{"rootAssembly": "motor.asm"}` when several
  top-level assemblies exist; otherwise pass `rootAssembly` in the dialog.
- Limits: 200 MB upload, 1 GB uncompressed, 4000 files (see `server/app/zipsafe.py`).

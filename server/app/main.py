"""FastAPI surface (instruction §3.2). Run: `uvicorn server.app.main:app`."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from .jobs import STORE, JOB_ROOT
from .pipeline import run_pipeline

app = FastAPI(title="ECPD Creo Integration", version="0.1.0")
# Local tool: the ECPD page may be served from any port/file host.
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"],
                   allow_headers=["*"])
MAX_UPLOAD = int(os.environ.get("MAX_UPLOAD_BYTES", 200 * 1024 * 1024))


@app.post("/api/jobs")
async def create_job(upload: UploadFile = File(...), rootAssembly: str | None = Form(default=None)):
    if upload.filename is None or not upload.filename.lower().endswith(".zip"):
        raise HTTPException(400, {"code": "BAD_UPLOAD", "message": "expect a .zip file"})
    job = STORE.create()
    tmp = Path(tempfile.gettempdir()) / f"ecpd_upload_{job.id}.zip"
    uploaded = 0
    with open(tmp, "wb") as fh:
        while True:
            chunk = await upload.read(1 << 20)
            if not chunk:
                break
            uploaded += len(chunk)
            if uploaded > MAX_UPLOAD:
                fh.close(); tmp.unlink(missing_ok=True)
                STORE.fail(job, "UPLOAD_TOO_LARGE", "upload",
                           f"upload exceeds {MAX_UPLOAD} bytes")
                return {"jobId": job.id, "status": "failed",
                        "error": {"code": "UPLOAD_TOO_LARGE"}}
            fh.write(chunk)
    STORE.run_async(job, lambda j: run_pipeline(j, tmp, rootAssembly))
    return {"jobId": job.id, "status": job.status}


@app.get("/api/jobs/{jid}")
def job_status(jid: str):
    job = STORE.get(jid)
    if job is None:
        raise HTTPException(404, {"code": "NOT_FOUND", "message": "job not found"})
    return {"jobId": job.id, "status": job.status, "progress": job.progress,
            "stage": job.stage, "error": job.error, "logs": job.logs[-25:]}


@app.get("/api/jobs/{jid}/artifacts/{name}")
def artifact(jid: str, name: str):
    job = STORE.get(jid)
    if job is None:
        raise HTTPException(404, "job not found")
    path = job.artifacts.get(name)
    if not path or not Path(path).exists():
        raise HTTPException(404, "artifact not found")
    return FileResponse(path, filename=f"{job.id}-{name.split('/')[-1]}")


@app.get("/api/health")
def health():
    return {"ok": True, "jobs": len(list(JOB_ROOT.iterdir())) if JOB_ROOT.exists() else 0}

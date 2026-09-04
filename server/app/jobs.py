"""Job lifecycle management (instruction §3.2, §17)."""
from __future__ import annotations

import json
import shutil
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

JOB_ROOT = Path("jobs")
JOB_ROOT.mkdir(exist_ok=True)


def new_job_id() -> str:
    return uuid.uuid4().hex[:12]


@dataclass
class Job:
    id: str
    status: str = "queued"
    progress: int = 0
    stage: str = ""
    logs: list[str] = field(default_factory=list)
    error: dict | None = None
    artifacts: dict[str, str] = field(default_factory=dict)
    created: float = field(default_factory=time.time)

    def log(self, msg: str) -> None:
        self.logs.append(msg)


class JobStore:
    def __init__(self):
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()

    def create(self) -> Job:
        with self._lock:
            jid = new_job_id()
            job = Job(id=jid)
            self._jobs[jid] = job
        return job

    def get(self, jid: str) -> Job | None:
        return self._jobs.get(jid)

    def run_async(self, job: Job, fn) -> None:
        t = threading.Thread(target=fn, args=(job,), daemon=True)
        t.start()

    def fail(self, job: Job, code: str, stage: str, message: str, details: dict | None = None):
        job.status = "failed"
        job.error = {"code": code, "stage": stage, "message": message,
                     "details": details or {}}
        job.log(f"ERROR[{code}] {message}")

    def succeed(self, job: Job, artifacts: dict[str, str]):
        job.status = "done"
        job.progress = 100
        job.artifacts = artifacts

    def write_report(self, job: Job, payload: dict) -> Path:
        report = JOB_ROOT / job.id / "conversion-report.json"
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps({
            "jobId": payload.get("jobId", job.id),
            "rootAssembly": payload.get("rootAssembly", ""),
            "creoVersion": payload.get("creoVersion", ""),
            "toolkitVersion": payload.get("toolkitVersion", ""),
            "qualityPreset": payload.get("qualityPreset", "high"),
            "definitionCount": payload.get("definitionCount", 0),
            "occurrenceCount": payload.get("occurrenceCount", 0),
            "triangleCount": payload.get("triangleCount", 0),
            "materialSummary": payload.get("materialSummary", {}),
            "unitSummary": payload.get("unitSummary", {}),
            "missingDependencies": payload.get("missingDependencies", []),
            "warnings": payload.get("warnings", job.logs[-10:]),
            "validation": payload.get("validation", {}),
            "timings": payload.get("timings", {}),
            "logs": job.logs,
        }, indent=1), encoding="utf-8")
        return report

    def cleanup_old(self, retention_hours: float = 24.0) -> None:
        cutoff = time.time() - retention_hours * 3600
        for d in JOB_ROOT.iterdir():
            if (JOB_ROOT / d.name).is_dir() and d.stat().st_mtime < cutoff:
                shutil.rmtree(d, ignore_errors=True)


STORE = JobStore()

"""End-to-end conversion pipeline (instruction §3, §5, §15, §16)."""
from __future__ import annotations

import json
import os
import time
import zipfile
from pathlib import Path

from .bridge import run_bridge, BridgeError
from .discovery import discover_root, DiscoveryError
from .jobs import STORE, JOB_ROOT
from .materials import resolve_material, UnknownMaterial
from .schemas import validate_project, structural_check
from .zipsafe import secure_extract, ZipError, ALLOWED_EXTENSIONS
from ..conversion.glbbuilder import build_glb
from ..conversion.validate import validate_glb

REPO_ROOT = Path(__file__).resolve().parents[2]


def run_pipeline(job, zip_path: Path, root_assembly: str | None):
    t0 = time.time()
    job_dir = JOB_ROOT / job.id
    job_dir.mkdir(parents=True, exist_ok=True)
    work = job_dir / "extract"
    out = job_dir / "out"
    try:
        job.status = "running"; job.stage = "upload"; job.progress = 5
        job.log(f"secure-extract {zip_path.name}")
        files = secure_extract(zip_path, work)
        job.stage = "discovery"; job.progress = 15
        root = discover_root(files, root_assembly or os.environ.get("ROOT_ASSEMBLY"))
        job.log(f"root assembly: {root.logical_name}")
        job.stage = "bridge"; job.progress = 30
        result = run_bridge(work, out, REPO_ROOT, use_mock=os.environ.get("ECPD_FORCE_MOCK") == "1",
                            log=job.log)

        job.stage = "canonicalize"; job.progress = 50
        meta = validate_project(result.metadata)
        errors = structural_check(meta)
        if errors:
            raise BridgeError("METADATA_INVALID", "canonicalize",
                              " ; ".join(errors))
        job.stage = "glb"; job.progress = 70
        glb_path = job_dir / "assembly.glb"
        stats = build_glb(result.metadata, result.mesh_dir, glb_path)
        job.stage = "validate"; job.progress = 85
        validation = validate_glb(glb_path)
        if not validation["valid"]:
            raise BridgeError("GLB_VALIDATION_FAILED", "validate",
                              "GLB invalid: " + " ; ".join(validation["errors"]),
                              validation)

        job.stage = "finish"; job.progress = 95
        (job_dir / "metadata.json").write_text(
            json.dumps(result.metadata, indent=1), encoding="utf-8")
        material_summary = {}
        unresolved = []
        for did, d in result.metadata.get("definitions", {}).items():
            for m in d.get("materials", []) or []:
                nm = m.get("name", "") if isinstance(m, dict) else str(m)
                try:
                    res = resolve_material(nm)
                except UnknownMaterial:
                    unresolved.append({"definition": did, "raw": nm})
                    res = {"class": "unknown", "source": "placeholder"}
                material_summary.setdefault(res.get("class", "unknown"), 0)
                material_summary[res.get("class", "unknown")] += 1
        payload = {
            "jobId": job.id, "rootAssembly": root.logical_name,
            "definitionCount": stats["definitionCount"],
            "occurrenceCount": stats["occurrenceCount"],
            "triangleCount": stats["triangleCount"],
            "unitSummary": result.metadata.get("units", {}),
            "materialSummary": material_summary,
            "validation": validation,
            "missingDependencies": unresolved + ([] if not result.used_mock else
                [{"reason": "using mock bridge (no licensed Creo/JDK available)"}]),
            "warnings": job.logs[-10:],
            "timings": {"total": round(time.time() - t0, 3)},
        }
        report = STORE.write_report(job, payload)
        STORE.succeed(job, {
            "glb": str((job_dir / "assembly.glb").resolve()),
            "metadata": str((job_dir / "metadata.json").resolve()),
            "report": str(report.resolve()),
        })
    except (ZipError, DiscoveryError) as e:
        STORE.fail(job, e.code, job.stage, str(e), getattr(e, "details", {}))
    except BridgeError as e:
        STORE.fail(job, e.code, e.stage, str(e), e.details)
    except Exception as e:  # §16 structured error fallback
        STORE.fail(job, "CONVERSION_FAILED", job.stage, f"{type(e).__name__}: {e}",
                   {"zip": str(zip_path)})


def convert_zip(zip_path: Path, root_assembly: str | None = None) -> dict:
    """Synchronous convenience used by tests."""
    job = STORE.create()
    run_pipeline(job, zip_path, root_assembly)
    return store_payload(job)


def store_payload(job) -> dict:
    return {"id": job.id, "status": job.status, "progress": job.progress,
            "stage": job.stage, "logs": job.logs[-25:], "error": job.error,
            "artifacts": job.artifacts}

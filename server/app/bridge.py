"""Bridge invocation (instruction §3.2) — runs the Java bridge as a subprocess.

When the bridge jar is unavailable/not built (no JDK in this environment),
we fall back to a Python-emitted synthetic sample that matches the same
canonical schemas so the full pipeline remains testable end-to-end.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


class BridgeError(Exception):
    def __init__(self, code: str, stage: str, message: str, details: dict | None = None):
        super().__init__(message)
        self.code = code
        self.stage = stage
        self.details = details or {}


@dataclass
class BridgeResult:
    metadata: dict
    mesh_dir: Path
    used_mock: bool


def bridge_jar(repo_root: Path) -> Path | None:
    jar = repo_root / "creo-bridge" / "build" / "creo-bridge.jar"
    return jar if jar.exists() else None


def run_bridge(zip_dir: Path, out_dir: Path, repo_root: Path, use_mock: bool, log) -> BridgeResult:
    out_dir.mkdir(parents=True, exist_ok=True)
    jar = bridge_jar(repo_root)
    java = shutil.which("java") or (
        Path(os.environ.get("JAVA_HOME", "")) / "bin" / "java"
        if os.environ.get("JAVA_HOME") else None)

    if jar and java and not use_mock and _creo_env_present():
        cmd = [str(java), "-jar", str(jar), "extract", str(zip_dir), str(out_dir)]
        log(f"bridge: {' '.join(cmd)}")
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
        if proc.returncode != 0:
            err = proc.stderr.strip() or "bridge failed"
            try:
                payload = json.loads(err.splitlines()[-1]).get("error", {})
            except Exception:
                payload = {"code": "BRIDGE_FAILED", "message": err}
            raise BridgeError(payload.get("code", "BRIDGE_FAILED"), "creo-bridge",
                              payload.get("message", err), payload.get("details"))
        inter = out_dir / "intermediate.json"
        mesh_dir = out_dir / "meshes"
        if not inter.exists():
            raise BridgeError("BRIDGE_FAILED", "creo-bridge",
                              "intermediate.json not produced", {"stderr": proc.stderr[-2000:]})
        return BridgeResult(metadata=json.loads(inter.read_text()), mesh_dir=mesh_dir, used_mock=False)

    # fallback: synthetic sample through the same canonical shape (§ M1/M2 testability)
    log("bridge: using mock sample (no licensed Creo/JDK on this host)")
    from .samples import motor_sample_metadata, motor_sample_meshes
    meta = motor_sample_metadata(zip_dir)
    mesh_dir = out_dir / "meshes"
    mesh_dir.mkdir(parents=True, exist_ok=True)
    motor_sample_meshes(mesh_dir)
    (out_dir / "intermediate.json").write_text(json.dumps(meta), encoding="utf-8")
    return BridgeResult(metadata=meta, mesh_dir=mesh_dir, used_mock=True)


def _creo_env_present() -> bool:
    return bool(os.environ.get("CREO_INSTALL_DIR") and os.environ.get("JAVA_HOME"))

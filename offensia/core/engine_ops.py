"""Bring the engine stack up/down from the pinned manifest (deps/engines.yaml).

Docker engines start with `docker compose up -d`; pip engines start in a per-engine
virtualenv via their `startup_command`. Everything is best-effort and never raises:
a missing runtime or a failed start is reported, not fatal, so `install.sh` and the
CLI degrade gracefully (the adapters already return structured errors when an engine
is offline).
"""
from __future__ import annotations

import os
import shutil
import subprocess
import time
import urllib.error
import urllib.request

from offensia.core.config import Paths


def load_engines(paths: Paths) -> list[dict]:
    if not paths.engines_manifest.exists():
        return []
    import yaml

    data = yaml.safe_load(paths.engines_manifest.read_text(encoding="utf-8")) or {}
    return data.get("engines", [])


def url_ok(url: str, timeout: int = 3) -> bool:
    if not url:
        return False
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:  # nosec B310
            return 200 <= resp.status < 400
    except (urllib.error.URLError, OSError, ValueError):
        return False


def _docker_compose() -> list[str] | None:
    if shutil.which("docker"):
        return ["docker", "compose"]
    if shutil.which("docker-compose"):
        return ["docker-compose"]
    return None


def _is_docker(eng: dict) -> bool:
    return eng.get("required_runtime") == "docker" or eng.get("install_method") == "docker"


def _wait_health(url: str, seconds: int = 30) -> bool:
    if not url:
        return True
    deadline = time.time() + seconds
    while time.time() < deadline:
        if url_ok(url):
            return True
        time.sleep(2)
    return url_ok(url)


def start_engine(paths: Paths, eng: dict, wait: int = 30) -> dict:
    """Start one engine. Returns {name, status, detail}."""
    name = eng.get("name", "?")
    dest = paths.deps_dir / name
    hc = eng.get("healthcheck", "")
    if url_ok(hc):
        return {"name": name, "status": "already_up", "detail": hc}
    if not dest.exists():
        return {"name": name, "status": "not_provisioned", "detail": str(dest)}

    if _is_docker(eng):
        compose = _docker_compose()
        if compose is None:
            return {"name": name, "status": "skipped", "detail": "docker not found"}
        try:
            subprocess.run([*compose, "up", "-d"], cwd=str(dest), check=False,
                           capture_output=True, timeout=600)
        except (subprocess.SubprocessError, OSError) as exc:
            return {"name": name, "status": "error", "detail": str(exc)}
    else:
        # pip engine: isolated venv, install, then start detached.
        venv = dest / ".venv"
        py = venv / "bin" / "python"
        try:
            if not py.exists():
                subprocess.run(["python3", "-m", "venv", str(venv)], check=False,
                               capture_output=True, timeout=300)
            req = dest / "requirements.txt"
            if req.exists():
                subprocess.run([str(py), "-m", "pip", "install", "-q", "-r", str(req)],
                               check=False, capture_output=True, timeout=1800)
            startup = (eng.get("startup_command") or "").split()
            if startup and startup[0] in ("python", "python3"):
                startup[0] = str(py)
            if not startup:
                return {"name": name, "status": "no_startup", "detail": ""}
            log = paths.deps_dir / f"{name}.log"
            with open(log, "w", encoding="utf-8") as fh:
                proc = subprocess.Popen(startup, cwd=str(dest), stdout=fh,
                                        stderr=subprocess.STDOUT, start_new_session=True,
                                        env={**os.environ})
            (paths.deps_dir / f"{name}.pid").write_text(str(proc.pid), encoding="utf-8")
        except (subprocess.SubprocessError, OSError) as exc:
            return {"name": name, "status": "error", "detail": str(exc)}

    up = _wait_health(hc, wait)
    return {"name": name, "status": "up" if up else "unhealthy", "detail": hc}


def stop_engine(paths: Paths, eng: dict) -> dict:
    name = eng.get("name", "?")
    dest = paths.deps_dir / name
    if _is_docker(eng):
        compose = _docker_compose()
        if compose is None or not dest.exists():
            return {"name": name, "status": "skipped", "detail": "docker/dir missing"}
        subprocess.run([*compose, "down"], cwd=str(dest), check=False,
                       capture_output=True, timeout=300)
        return {"name": name, "status": "down", "detail": ""}
    pidfile = paths.deps_dir / f"{name}.pid"
    if pidfile.exists():
        try:
            os.kill(int(pidfile.read_text().strip()), 15)
        except (ProcessLookupError, ValueError, OSError):
            pass
        pidfile.unlink(missing_ok=True)
        return {"name": name, "status": "down", "detail": ""}
    return {"name": name, "status": "not_running", "detail": ""}


def up_all(paths: Paths, wait: int = 30, docker_only: bool = False) -> list[dict]:
    engines = load_engines(paths)
    if docker_only:
        engines = [e for e in engines if _is_docker(e)]
    return [start_engine(paths, eng, wait) for eng in engines]


def down_all(paths: Paths) -> list[dict]:
    return [stop_engine(paths, eng) for eng in load_engines(paths)]

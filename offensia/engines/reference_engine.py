"""Reference engine — a lightweight local backend for OffensIA (dev / self-test).

It satisfies the adapter HTTP contracts so the full OffensIA pipeline runs without
Docker or heavy security suites:

  execution (default :8888)
    GET  /health          -> {"status": "ok"}
    POST /api/command      {"command": "..."} -> {"success", "stdout", "return_code"}
  recon (default :11235)
    GET  /health          -> {"status": "ok"}
    POST /md               {"url": "..."} -> {"markdown": "..."}

This is NOT the production engine set. It runs real local commands (execution) and
real HTTP fetches (recon), bounded and bound to 127.0.0.1 only. In production,
provision the engines declared in deps/engines.yaml instead.

Run both:  python -m offensia.engines.reference_engine
Run one:   python -m offensia.engines.reference_engine --only exec
"""
from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST = "127.0.0.1"
EXEC_PORT = 8888
RECON_PORT = 11235
CMD_TIMEOUT = 60
MAX_OUT = 256 * 1024


def _strip_html(html: str) -> str:
    html = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", "", html)
    text = re.sub(r"(?s)<[^>]+>", " ", html)
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\n\s*\n+", "\n\n", text).strip()


class _Handler(BaseHTTPRequestHandler):
    role = "exec"

    def log_message(self, *a):  # quiet
        pass

    def _send(self, code: int, obj: dict):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.rstrip("/") == "/health":
            return self._send(200, {"status": "ok", "role": self.role})
        self._send(404, {"error": "not found"})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(raw or b"{}")
        except json.JSONDecodeError:
            return self._send(400, {"error": "bad json"})
        if self.role == "exec" and self.path.rstrip("/") == "/api/command":
            return self._exec(data)
        if self.role == "recon" and self.path.rstrip("/") == "/md":
            return self._md(data)
        self._send(404, {"error": "not found"})

    def _exec(self, data: dict):
        command = str(data.get("command", "")).strip()
        if not command:
            return self._send(400, {"error": "empty command"})
        try:
            proc = subprocess.run(shlex.split(command), capture_output=True,
                                  text=True, timeout=CMD_TIMEOUT)
            out = (proc.stdout + proc.stderr)[:MAX_OUT]
            self._send(200, {"success": proc.returncode == 0,
                             "stdout": out, "return_code": proc.returncode})
        except FileNotFoundError as exc:
            self._send(200, {"success": False, "stdout": str(exc), "return_code": 127})
        except subprocess.TimeoutExpired:
            self._send(200, {"success": False, "stdout": "timeout", "return_code": 124})

    def _md(self, data: dict):
        url = str(data.get("url", "")).strip()
        if not url:
            return self._send(400, {"error": "empty url"})
        try:
            import requests
            resp = requests.get(url, timeout=30)
            md = _strip_html(resp.text)[:MAX_OUT]
            self._send(200, {"markdown": md, "status_code": resp.status_code})
        except Exception as exc:  # noqa: BLE001
            self._send(200, {"markdown": "", "error": f"{type(exc).__name__}: {exc}"})


def _make_handler(role: str):
    return type(f"Handler_{role}", (_Handler,), {"role": role})


def serve(role: str, port: int) -> ThreadingHTTPServer:
    srv = ThreadingHTTPServer((HOST, port), _make_handler(role))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    print(f"[reference-engine] {role} listening on http://{HOST}:{port}")
    return srv


def main(argv=None):
    ap = argparse.ArgumentParser(description="OffensIA reference engine (dev/self-test)")
    ap.add_argument("--only", choices=["exec", "recon"], default=None)
    ap.add_argument("--exec-port", type=int, default=EXEC_PORT)
    ap.add_argument("--recon-port", type=int, default=RECON_PORT)
    args = ap.parse_args(argv)
    servers = []
    if args.only in (None, "exec"):
        servers.append(serve("exec", args.exec_port))
    if args.only in (None, "recon"):
        servers.append(serve("recon", args.recon_port))
    print("[reference-engine] ready. Ctrl-C to stop.")
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        for s in servers:
            s.shutdown()


if __name__ == "__main__":
    main()

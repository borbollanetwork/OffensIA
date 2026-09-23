from offensia.core import engine_ops
from offensia.core.config import get_paths


def test_load_engines_empty_when_no_manifest(tmp_path):
    paths = get_paths(str(tmp_path))
    assert engine_ops.load_engines(paths) == []


def test_up_all_empty_manifest_is_noop(tmp_path):
    paths = get_paths(str(tmp_path))
    assert engine_ops.up_all(paths, wait=0) == []


def test_url_ok_false_on_bad_url():
    assert engine_ops.url_ok("") is False
    assert engine_ops.url_ok("http://127.0.0.1:1/health", timeout=1) is False


def test_start_engine_not_provisioned(tmp_path):
    paths = get_paths(str(tmp_path))
    eng = {"name": "x", "healthcheck": "http://127.0.0.1:1/health",
           "required_runtime": "docker"}
    r = engine_ops.start_engine(paths, eng, wait=0)
    assert r["status"] in ("not_provisioned", "skipped")

from offensia.core.digest import summarize


def test_http_digest_extracts_status_title_tech_params_anomaly():
    raw = ("HTTP/1.1 500 Internal Server Error\r\n"
           "Server: nginx/1.25.1\r\nX-Powered-By: PHP/8.2\r\n\r\n"
           "<html><title>Login</title>"
           "<a href='/x?id=1&user=bob'>x</a>"
           "You have an error in your SQL syntax near</html>")
    d = summarize("http", raw)
    assert 500 in d["status_codes"]
    assert "Login" in d["titles"]
    assert any("nginx" in t for t in d["tech"]) and any("PHP" in t for t in d["tech"])
    assert "id" in d["params"] and "user" in d["params"]
    assert any("SQL" in a for a in d["anomalies"])


def test_nmap_digest_extracts_ports():
    raw = ("Nmap scan report for scanme.example\n"
           "80/tcp   open  http    nginx 1.25.1\n"
           "443/tcp  open  https\n"
           "22/tcp   closed ssh\n")
    d = summarize("port_scan", raw)
    assert any(p.startswith("80/tcp") for p in d["ports"])
    assert any(p.startswith("443/tcp") for p in d["ports"])
    assert not any(p.startswith("22/tcp") for p in d["ports"])   # closed excluded


def test_digest_is_bounded_and_never_raises_on_garbage():
    d = summarize("http", b"\x00\xff" * 100000)     # binary, huge
    assert isinstance(d, dict) and d["bytes"] == 200000
    for k, v in d.items():
        if isinstance(v, list):
            assert len(v) <= 20
    assert summarize("http", "") == {"kind": "http", "bytes": 0}


def test_digest_is_deterministic():
    raw = "HTTP/1.1 200 OK\r\n\r\n<title>A</title><title>A</title>"
    assert summarize("http", raw) == summarize("http", raw)

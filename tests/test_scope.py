import pytest
from offensia.core.scope import normalize, in_scope, add_entry, remove_entry, load_scope


@pytest.mark.parametrize("raw,host,port", [
    ("https://A.Example.com:8443/p?x=1", "a.example.com", 8443),
    ("user:pass@Host.TLD", "host.tld", None),
    ("http://10.0.0.5", "10.0.0.5", None),
    ("[2001:db8::1]:443", "2001:db8::1", 443),
])
def test_normalize(raw, host, port):
    nt = normalize(raw)
    assert nt.host == host and nt.port == port


def test_default_deny_missing_file(tmp_path):
    assert in_scope("example.com", tmp_path / "nope") is False


def test_comments_only_is_deny(tmp_path):
    f = tmp_path / "s"; f.write_text("# c\n\n")
    assert load_scope(f) == [] and in_scope("example.com", f) is False


def test_exact_glob_cidr_and_exclude(tmp_path):
    f = tmp_path / "s"
    f.write_text("example.com\n*.lab.internal\n10.0.0.0/24\n!secret.lab.internal\n")
    assert in_scope("https://example.com/x", f) is True
    assert in_scope("api.lab.internal", f) is True
    assert in_scope("10.0.0.7", f) is True
    assert in_scope("10.0.1.7", f) is False
    assert in_scope("secret.lab.internal", f) is False  # exclusion wins
    assert in_scope("evil.com", f) is False


def test_add_requires_auth_and_remove(tmp_path):
    f = tmp_path / "s"
    with pytest.raises(ValueError):
        add_entry("example.com", "", f)
    add_entry("example.com", "CONTRACT-1", f, engagement="ENG-9")
    assert in_scope("example.com", f) is True
    assert remove_entry("example.com", f) is True
    assert in_scope("example.com", f) is False

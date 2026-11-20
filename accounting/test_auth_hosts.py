#!/usr/bin/env python3
"""Local-access matrix for the dashboard token bypass.

Guards the defect found 20-nov-2026: the bypass compared the Host header against
three exact strings, so `http://<hostname>:8799` and `http://127.0.1.1:8799`
(a loopback address this machine resolves its own name to) returned 401 and the
browser asked for a token on a purely local visit.

Two directions must hold, and the second is the one that matters for security:
  - local visit  → no token (127.0.0.0/8 is loopback, the name too)
  - remote visit → token REQUIRED, even though it also arrives as 127.0.0.1
                   because the tunnel terminates locally. DNS rebinding (a remote
                   page pointing its own name at 127.0.0.1) must not slip through.

Run: python3 accounting/test_auth_hosts.py
"""
# OKF-METADATA
# ---
# type: Test
# title: "Guard de acceso local (Host de loopback)"
# description: "Verifica que una visita local no pide token y que una remota sí, incluido el caso de DNS rebinding."
# status: verified
# generated: 2026-11-20T02:25:00+01:00
# source:
#   - "accounting/web_dashboard.py::Handler._is_local_host"
# verified: 2026-11-20
# stale_after: 2027-06-30

import socket
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from web_dashboard import Handler

LOCAL = [
    "127.0.0.1:8799",
    "localhost:8799",
    "LOCALHOST:8799",
    "127.0.1.1:8799",          # this machine's own name (see /etc/hosts)
    "127.0.0.2:8799",          # any address in 127.0.0.0/8 is loopback
    "[::1]:8799",
    "::1",
    "127.0.0.1",               # no port
    f"{socket.gethostname()}:8799",       # uppercase-insensitive
]

REMOTE = [
    "192.168.2.20:8799",       # LAN address of this machine
    "evil.example",            # DNS rebinding: our own name pointed at 127.0.0.1
    "evil.example:8799",
    "10.0.0.5",
    "tcpGFwWCAFreLBrqfDWAOrdahM.tailcat",
    "example.com",
    "",
    "   ",
]


def test_loopback_visits_need_no_token():
    """A genuinely local visit must not be asked for a token."""
    bad = [h for h in LOCAL if not Handler._is_local_host(h)]
    assert not bad, f"local Host rejected by the bypass: {bad}"


def test_remote_visits_still_require_token():
    """Non-loopback Hosts must never take the bypass, rebinding included."""
    bad = [h for h in REMOTE if Handler._is_local_host(h)]
    assert not bad, f"non-local Host WRONGLY given the bypass: {bad}"


def test_hostname_alone_is_not_enough():
    """The bypass must also require a loopback peer, not just a local Host.

    tailcat terminates the tunnel on 127.0.0.1, so a remote visitor could present
    a loopback Host. The peer test in _authorized is what stops that; here we only
    pin the ordering assumption: _is_local_host is Host-only and _authorized ANDs
    it with the peer check.
    """
    src = (Path(__file__).resolve().parent / "web_dashboard.py").read_text()
    assert "and self._is_local_host(" in src, "peer check no longer ANDed with Host check"
    assert 'self.client_address[0] in ("127.0.0.1", "::1")' in src, \
        "peer loopback check disappeared — tunnel visitors would inherit the bypass"


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
            except AssertionError as exc:
                failures += 1
                print(f"FAIL {name}: {exc}")
    sys.exit(1 if failures else 0)

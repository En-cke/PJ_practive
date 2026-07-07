"""Shared pytest fixtures/paths for the top-down-labs test suite."""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LABS = os.path.join(ROOT, "labs")

# Make each lab package importable by its module name.
for sub in (
    "00-tcp-clientserver",
    "01-webserver",
    "02-udp-pinger",
    "03-smtp-mailclient",
    "04-http-proxy",
    "07-rdt",
    "08-distance-vector",
):
    path = os.path.join(LABS, sub)
    if path not in sys.path:
        sys.path.insert(0, path)


def free_port() -> int:
    """Ask the OS for an unused TCP port."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]

"""End-to-end tests for the socket-programming labs (0-4).

Each server runs in a background thread on an OS-assigned free port; the client
connects over real loopback sockets. These are genuine integration tests: actual
TCP/UDP traffic crosses the kernel network stack.
"""

import os
import threading
import time

import pytest

from conftest import free_port

import tcp_server
import tcp_client
import webserver
import udp_ping_server
import udp_ping_client
import smtp_client
import mock_smtp_server
import proxy_server
import proxy_client


def _spawn(target, **kwargs):
    t = threading.Thread(target=target, kwargs=kwargs, daemon=True)
    t.start()
    time.sleep(0.3)  # let the server bind
    return t


# ---- Lab 0: TCP client/server ------------------------------------------- #
def test_tcp_upper_echo():
    port = free_port()
    _spawn(tcp_server.serve, host="127.0.0.1", port=port, once=True)
    reply = tcp_client.request("127.0.0.1", port, "hello top-down")
    assert reply == "HELLO TOP-DOWN"


# ---- Lab 1: web server -------------------------------------------------- #
def test_webserver_200_and_404():
    port = free_port()
    root = os.path.join(os.path.dirname(webserver.__file__), "www")
    # 200 path
    _spawn(webserver.serve, host="127.0.0.1", port=port, root=root, once=True)
    resp = proxy_client.fetch_via_proxy  # reuse a raw HTTP fetch
    import socket
    def raw_get(target):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect(("127.0.0.1", port))
            s.sendall(f"GET {target} HTTP/1.1\r\nHost: localhost\r\n\r\n".encode())
            data = b""
            while True:
                chunk = s.recv(4096)
                if not chunk:
                    break
                data += chunk
            return data
    ok = raw_get("/HelloWorld.html")
    assert b"200 OK" in ok
    assert b"Hello, World!" in ok

    # 404 path (new server instance since serve(once=True) handled one request)
    _spawn(webserver.serve, host="127.0.0.1", port=port, root=root, once=True)
    missing = raw_get("/does-not-exist.html")
    assert b"404 Not Found" in missing


def test_webserver_handle_request_unit():
    root = os.path.join(os.path.dirname(webserver.__file__), "www")
    status, resp = webserver.handle_request(
        b"GET /HelloWorld.html HTTP/1.1\r\nHost: x\r\n\r\n", root
    )
    assert status == 200
    status, resp = webserver.handle_request(b"GET /nope HTTP/1.1\r\n\r\n", root)
    assert status == 404
    status, resp = webserver.handle_request(b"POST / HTTP/1.1\r\n\r\n", root)
    assert status == 400


# ---- Lab 2: UDP pinger -------------------------------------------------- #
def test_udp_pinger_no_loss():
    port = free_port()
    _spawn(udp_ping_server.serve, host="127.0.0.1", port=port,
           loss=0.0, count=10, seed=1)
    stats = udp_ping_client.ping("127.0.0.1", port, count=10, timeout=1.0)
    assert stats["received"] == 10
    assert stats["loss_pct"] == 0.0
    assert stats["avg_ms"] is not None


def test_udp_pinger_with_loss():
    port = free_port()
    # 50% loss, deterministic seed -> some packets dropped, client survives
    _spawn(udp_ping_server.serve, host="127.0.0.1", port=port,
           loss=0.5, count=0, seed=42)
    stats = udp_ping_client.ping("127.0.0.1", port, count=20, timeout=0.5)
    assert stats["sent"] == 20
    assert 0 < stats["received"] <= 20  # some got through, client did not hang


# ---- Lab 3: SMTP mail client ------------------------------------------- #
def test_smtp_client_delivers_message():
    port = free_port()
    captured = {}

    def run_server():
        captured.update(mock_smtp_server.serve("127.0.0.1", port, once=True))

    t = threading.Thread(target=run_server, daemon=True)
    t.start()
    time.sleep(0.3)

    logs = []
    smtp_client.send_mail(
        "127.0.0.1", port,
        mail_from="alice@example.com", mail_to="bob@example.com",
        subject="Lab3", body="hello via SMTP", log=logs.append,
    )
    t.join(timeout=2)
    assert captured["from"] == "<alice@example.com>"
    assert captured["to"] == "<bob@example.com>"
    assert "hello via SMTP" in captured["data"]
    assert any("message sent successfully" in line for line in logs)


# ---- Lab 4: caching HTTP proxy ----------------------------------------- #
def test_proxy_miss_then_hit():
    origin_port = free_port()
    proxy_port = free_port()
    root = os.path.join(os.path.dirname(webserver.__file__), "www")

    # Long-lived origin web server (serves many requests).
    threading.Thread(
        target=webserver.serve,
        kwargs=dict(host="127.0.0.1", port=origin_port, root=root, once=False),
        daemon=True,
    ).start()
    # Long-lived proxy with a fresh cache dir.
    cache_dir = os.path.join(os.path.dirname(proxy_server.__file__), "cache_test")
    import shutil
    shutil.rmtree(cache_dir, ignore_errors=True)
    threading.Thread(
        target=proxy_server.serve,
        kwargs=dict(host="127.0.0.1", port=proxy_port, cache_dir=cache_dir, once=False),
        daemon=True,
    ).start()
    time.sleep(0.4)

    url = f"http://127.0.0.1:{origin_port}/HelloWorld.html"
    first = proxy_client.fetch_via_proxy("127.0.0.1", proxy_port, url)
    second = proxy_client.fetch_via_proxy("127.0.0.1", proxy_port, url)

    assert b"X-Cache: MISS" in first
    assert b"Hello, World!" in first
    assert b"X-Cache: HIT" in second
    assert b"Hello, World!" in second
    shutil.rmtree(cache_dir, ignore_errors=True)

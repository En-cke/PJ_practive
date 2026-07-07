"""Lab 4 - HTTP Web Proxy Server (Kurose-Ross Programming Assignment 4).

A caching HTTP proxy. When a client requests a URL through the proxy the proxy:

  1. Checks its on-disk cache. On a hit it returns the cached object and marks
     the response with an `X-Cache: HIT` header.
  2. On a miss it opens a TCP connection to the origin server, forwards the GET
     request, streams the response back to the client, and stores it in the
     cache (`X-Cache: MISS`).

The proxy parses absolute-form request lines ("GET http://host/path HTTP/1.1")
as sent by a browser configured to use a proxy, and also accepts a bare path
with a Host header. Only GET is supported, matching the assignment scope.

Run:
    python proxy_server.py --port 8888
Configure your browser's HTTP proxy to 127.0.0.1:8888, or test with the
companion proxy_client.py.
"""

import argparse
import hashlib
import os
import socket
from urllib.parse import urlparse

DEFAULT_CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")


def cache_path(cache_dir: str, url: str) -> str:
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
    return os.path.join(cache_dir, digest)


def parse_request(raw: bytes):
    """Return (method, host, port, path) from a proxied HTTP request."""
    text = raw.decode("utf-8", errors="replace")
    lines = text.split("\r\n")
    method, target, _version = lines[0].split()

    host = None
    port = 80
    if target.startswith("http://") or target.startswith("https://"):
        parsed = urlparse(target)
        host = parsed.hostname
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        path = parsed.path or "/"
        if parsed.query:
            path += "?" + parsed.query
    else:
        path = target
        for line in lines[1:]:
            if line.lower().startswith("host:"):
                hostval = line.split(":", 1)[1].strip()
                if ":" in hostval:
                    host, port_s = hostval.split(":", 1)
                    port = int(port_s)
                else:
                    host = hostval
                break
    return method, host, port, path


def fetch_from_origin(host: str, port: int, path: str) -> bytes:
    request = (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: {host}\r\n"
        f"Connection: close\r\n"
        f"User-Agent: TopDownProxy/1.0\r\n"
        f"\r\n"
    )
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as origin:
        origin.settimeout(10)
        origin.connect((host, port))
        origin.sendall(request.encode("utf-8"))
        chunks = []
        while True:
            data = origin.recv(4096)
            if not data:
                break
            chunks.append(data)
    return b"".join(chunks)


def inject_cache_header(response: bytes, value: str) -> bytes:
    """Insert an X-Cache header right after the status line."""
    sep = b"\r\n"
    if sep not in response:
        return response
    status_line, rest = response.split(sep, 1)
    return status_line + sep + f"X-Cache: {value}\r\n".encode("utf-8") + rest


def handle_client(conn: socket.socket, cache_dir: str) -> str:
    raw = conn.recv(8192)
    if not raw:
        return "empty"
    method, host, port, path = parse_request(raw)
    if method != "GET" or not host:
        conn.sendall(b"HTTP/1.1 501 Not Implemented\r\nConnection: close\r\n\r\n")
        return "501"

    url = f"http://{host}:{port}{path}"
    cpath = cache_path(cache_dir, url)

    if os.path.exists(cpath):
        with open(cpath, "rb") as f:
            cached = f.read()
        conn.sendall(inject_cache_header(cached, "HIT"))
        return "HIT"

    response = fetch_from_origin(host, port, path)
    os.makedirs(cache_dir, exist_ok=True)
    with open(cpath, "wb") as f:
        f.write(response)
    conn.sendall(inject_cache_header(response, "MISS"))
    return "MISS"


def serve(host: str, port: int, cache_dir: str = DEFAULT_CACHE_DIR,
          once: bool = False) -> None:
    os.makedirs(cache_dir, exist_ok=True)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((host, port))
        server_socket.listen(5)
        print(f"[proxy] listening on {host}:{port}, cache={cache_dir}")
        while True:
            conn, addr = server_socket.accept()
            with conn:
                try:
                    result = handle_client(conn, cache_dir)
                    print(f"[proxy] {addr[0]} -> {result}")
                except Exception as exc:  # noqa: BLE001 - proxy must stay up
                    print(f"[proxy] error: {exc}")
                    try:
                        conn.sendall(
                            b"HTTP/1.1 502 Bad Gateway\r\nConnection: close\r\n\r\n"
                        )
                    except OSError:
                        pass
            if once:
                return


def main() -> None:
    parser = argparse.ArgumentParser(description="Caching HTTP proxy server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8888)
    parser.add_argument("--cache", default=DEFAULT_CACHE_DIR)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    serve(args.host, args.port, args.cache, once=args.once)


if __name__ == "__main__":
    main()

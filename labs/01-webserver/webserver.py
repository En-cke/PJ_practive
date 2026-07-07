"""Lab 1 - Web Server (Kurose-Ross Programming Assignment 1).

A minimal HTTP/1.1 server that handles one request at a time. It parses the
request line, opens the requested file relative to a document root, and returns
it with a "200 OK" status. If the file does not exist it returns "404 Not
Found". This mirrors the assignment's spec: any browser (or the companion
client) can fetch a served file, and a request for a missing file yields a 404.

Run:
    python webserver.py --root ./www --port 8080
Then browse to http://127.0.0.1:8080/HelloWorld.html
"""

import argparse
import os
import socket

STATUS_TEXT = {200: "OK", 404: "Not Found", 400: "Bad Request"}

CONTENT_TYPES = {
    ".html": "text/html",
    ".htm": "text/html",
    ".txt": "text/plain",
    ".css": "text/css",
    ".js": "application/javascript",
    ".json": "application/json",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".gif": "image/gif",
}


def guess_content_type(path: str) -> str:
    _, ext = os.path.splitext(path)
    return CONTENT_TYPES.get(ext.lower(), "application/octet-stream")


def build_response(status: int, body: bytes, content_type: str = "text/html") -> bytes:
    reason = STATUS_TEXT.get(status, "Unknown")
    header = (
        f"HTTP/1.1 {status} {reason}\r\n"
        f"Content-Type: {content_type}\r\n"
        f"Content-Length: {len(body)}\r\n"
        f"Connection: close\r\n"
        f"\r\n"
    )
    return header.encode("utf-8") + body


def handle_request(raw_request: bytes, root: str):
    """Return (status_code, response_bytes) for a raw HTTP request."""
    try:
        request_line = raw_request.split(b"\r\n", 1)[0].decode("utf-8")
        method, target, _version = request_line.split()
    except ValueError:
        body = b"<html><body><h1>400 Bad Request</h1></body></html>"
        return 400, build_response(400, body)

    if method != "GET":
        body = b"<html><body><h1>400 Bad Request</h1></body></html>"
        return 400, build_response(400, body)

    # Strip leading slash and any query string; normalise to prevent traversal.
    filename = target.split("?", 1)[0].lstrip("/")
    if filename == "":
        filename = "index.html"
    safe_path = os.path.normpath(os.path.join(root, filename))
    if not os.path.abspath(safe_path).startswith(os.path.abspath(root)):
        body = b"<html><body><h1>404 Not Found</h1></body></html>"
        return 404, build_response(404, body)

    try:
        with open(safe_path, "rb") as f:
            body = f.read()
        return 200, build_response(200, body, guess_content_type(safe_path))
    except (FileNotFoundError, IsADirectoryError):
        body = b"<html><body><h1>404 Not Found</h1></body></html>"
        return 404, build_response(404, body)


def serve(host: str, port: int, root: str, once: bool = False) -> None:
    root = os.path.abspath(root)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((host, port))
        server_socket.listen(5)
        print(f"[webserver] serving {root} on http://{host}:{port}")

        while True:
            connection_socket, addr = server_socket.accept()
            with connection_socket:
                raw = connection_socket.recv(4096)
                if not raw:
                    continue
                status, response = handle_request(raw, root)
                connection_socket.sendall(response)
                print(f"[webserver] {addr[0]} -> {status}")
            if once:
                return


def main() -> None:
    parser = argparse.ArgumentParser(description="Minimal HTTP web server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--root", default=os.path.join(os.path.dirname(__file__), "www"))
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    serve(args.host, args.port, args.root, once=args.once)


if __name__ == "__main__":
    main()

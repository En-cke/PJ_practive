"""Lab 0 - Simple TCP client/server (Kurose-Ross Section 2.7.2).

The server accepts one TCP connection at a time, reads a line of text from the
client, upper-cases it, and sends it back. It is the canonical "hello world" of
socket programming and the foundation every later lab builds on.

Run:
    python tcp_server.py [--host 127.0.0.1] [--port 12000]
"""

import argparse
import socket


def serve(host: str, port: int, once: bool = False) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        # Allow immediate reuse of the port after the server exits.
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((host, port))
        server_socket.listen(1)
        print(f"[tcp-server] listening on {host}:{port}")

        while True:
            connection_socket, addr = server_socket.accept()
            with connection_socket:
                data = connection_socket.recv(1024)
                if not data:
                    continue
                sentence = data.decode("utf-8")
                print(f"[tcp-server] from {addr}: {sentence!r}")
                connection_socket.sendall(sentence.upper().encode("utf-8"))
            if once:
                return


def main() -> None:
    parser = argparse.ArgumentParser(description="Simple TCP echo/upper server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=12000)
    parser.add_argument("--once", action="store_true", help="serve one request then exit")
    args = parser.parse_args()
    serve(args.host, args.port, once=args.once)


if __name__ == "__main__":
    main()

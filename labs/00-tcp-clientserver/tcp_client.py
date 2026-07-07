"""Lab 0 - TCP client counterpart to tcp_server.py.

Sends one line of text to the server and prints the (upper-cased) reply.

Run (server must be listening first):
    python tcp_client.py --message "hello world"
"""

import argparse
import socket


def request(host: str, port: int, message: str) -> str:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
        client_socket.connect((host, port))
        client_socket.sendall(message.encode("utf-8"))
        reply = client_socket.recv(1024).decode("utf-8")
    return reply


def main() -> None:
    parser = argparse.ArgumentParser(description="Simple TCP client")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=12000)
    parser.add_argument("--message", default="hello top-down world")
    args = parser.parse_args()
    reply = request(args.host, args.port, args.message)
    print(f"From server: {reply}")


if __name__ == "__main__":
    main()

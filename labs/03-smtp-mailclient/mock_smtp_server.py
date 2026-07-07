"""Lab 3 helper - a minimal RFC 5321 SMTP server for local verification.

The Kurose-Ross assignment targets a real mail server, but relying on an
external SMTP relay is neither reproducible nor network-safe. This tiny server
speaks just enough of SMTP to exercise the client's protocol handling
(HELO / MAIL FROM / RCPT TO / DATA / QUIT) and captures the delivered message so
tests can assert on it. It is a verification aid, not part of the assignment
proper.

Run:
    python mock_smtp_server.py --port 2525
"""

import argparse
import socket


def handle_client(conn: socket.socket) -> dict:
    """Drive one SMTP session; return the captured message dict."""
    captured = {"from": None, "to": None, "data": None}

    def send(line: str) -> None:
        conn.sendall((line + "\r\n").encode("utf-8"))

    def recv_line() -> str:
        return conn.recv(1024).decode("utf-8")

    send("220 mock.smtp.local Simple Mail Transfer Service Ready")
    in_data = False
    data_lines = []

    while True:
        chunk = recv_line()
        if not chunk:
            break
        for line in chunk.split("\r\n"):
            if line == "" and not in_data:
                continue
            if in_data:
                if line == ".":
                    captured["data"] = "\r\n".join(data_lines)
                    in_data = False
                    send("250 OK: message accepted for delivery")
                else:
                    data_lines.append(line)
                continue

            upper = line.upper()
            if upper.startswith("HELO") or upper.startswith("EHLO"):
                send("250 mock.smtp.local Hello")
            elif upper.startswith("MAIL FROM"):
                captured["from"] = line.split(":", 1)[1].strip()
                send("250 OK")
            elif upper.startswith("RCPT TO"):
                captured["to"] = line.split(":", 1)[1].strip()
                send("250 OK")
            elif upper.startswith("DATA"):
                in_data = True
                send("354 End data with <CR><LF>.<CR><LF>")
            elif upper.startswith("QUIT"):
                send("221 mock.smtp.local closing connection")
                return captured
            elif line == "":
                continue
            else:
                send("500 Command not recognized")
    return captured


def serve(host: str, port: int, once: bool = True) -> dict:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((host, port))
        server_socket.listen(1)
        print(f"[mock-smtp] listening on {host}:{port}")
        captured = {}
        while True:
            conn, _addr = server_socket.accept()
            with conn:
                captured = handle_client(conn)
                print(f"[mock-smtp] captured: {captured}")
            if once:
                return captured


def main() -> None:
    parser = argparse.ArgumentParser(description="Mock SMTP server for Lab 3")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=2525)
    parser.add_argument("--forever", action="store_true")
    args = parser.parse_args()
    serve(args.host, args.port, once=not args.forever)


if __name__ == "__main__":
    main()

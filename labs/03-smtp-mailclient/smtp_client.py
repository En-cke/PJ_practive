"""Lab 3 - SMTP Mail Client (Kurose-Ross Programming Assignment 3).

Implements the SMTP protocol directly over a TCP socket, following the exact
command sequence from RFC 5321 / the assignment handout:

    <connect>          -> expect 220
    HELO <host>        -> expect 250
    MAIL FROM:<addr>   -> expect 250
    RCPT TO:<addr>     -> expect 250
    DATA               -> expect 354
    <message> CRLF.CRLF-> expect 250
    QUIT               -> expect 221

At each step it checks the server's numeric reply code and aborts on anything
unexpected. This is the "speak the protocol by hand" assignment, so it does NOT
use Python's smtplib.

Run against a local test server:
    python smtp_client.py --server 127.0.0.1 --port 2525 \
        --from alice@example.com --to bob@example.com --subject Hi --body "hello"
"""

import argparse
import socket


class SMTPError(RuntimeError):
    pass


def _recv(sock: socket.socket) -> str:
    reply = sock.recv(1024).decode("utf-8")
    if not reply:
        raise SMTPError("connection closed by server")
    return reply


def _expect(reply: str, code: str, stage: str) -> None:
    if reply[:3] != code:
        raise SMTPError(f"{stage}: expected {code}, got {reply.strip()!r}")


def send_mail(server: str, port: int, mail_from: str, mail_to: str,
              subject: str, body: str, helo_name: str = "topdown.client",
              log=print) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
        client_socket.connect((server, port))

        greeting = _recv(client_socket)
        log(f"S: {greeting.strip()}")
        _expect(greeting, "220", "greeting")

        def command(line: str, expect_code: str, stage: str) -> str:
            log(f"C: {line.strip()}")
            client_socket.sendall((line + "\r\n").encode("utf-8"))
            reply = _recv(client_socket)
            log(f"S: {reply.strip()}")
            _expect(reply, expect_code, stage)
            return reply

        command(f"HELO {helo_name}", "250", "HELO")
        command(f"MAIL FROM:<{mail_from}>", "250", "MAIL FROM")
        command(f"RCPT TO:<{mail_to}>", "250", "RCPT TO")
        command("DATA", "354", "DATA")

        # Message body. The lone "." on its own line terminates the message.
        message = (
            f"From: {mail_from}\r\n"
            f"To: {mail_to}\r\n"
            f"Subject: {subject}\r\n"
            f"\r\n"
            f"{body}\r\n"
            f".\r\n"
        )
        log("C: <message body>")
        client_socket.sendall(message.encode("utf-8"))
        end_reply = _recv(client_socket)
        log(f"S: {end_reply.strip()}")
        _expect(end_reply, "250", "end-of-data")

        command("QUIT", "221", "QUIT")
        log("[smtp-client] message sent successfully")


def main() -> None:
    parser = argparse.ArgumentParser(description="Hand-rolled SMTP mail client")
    parser.add_argument("--server", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=2525)
    parser.add_argument("--from", dest="mail_from", default="alice@example.com")
    parser.add_argument("--to", dest="mail_to", default="bob@example.com")
    parser.add_argument("--subject", default="Top-Down Lab 3")
    parser.add_argument("--body", default="Hello from the SMTP lab client.")
    args = parser.parse_args()
    send_mail(args.server, args.port, args.mail_from, args.mail_to,
              args.subject, args.body)


if __name__ == "__main__":
    main()

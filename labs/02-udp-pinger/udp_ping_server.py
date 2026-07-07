"""Lab 2 - UDP Pinger, server side (Kurose-Ross Programming Assignment 2).

The server listens on a UDP port. For each datagram it receives it flips a coin:
with a configurable loss probability it silently drops the packet, otherwise it
capitalises the payload and echoes it back. This deliberately unreliable server
lets the client observe UDP packet loss and measure round-trip times.

Run:
    python udp_ping_server.py --port 12000 --loss 0.3
"""

import argparse
import random
import socket


def serve(host: str, port: int, loss: float, count: int = 0, seed=None) -> None:
    rng = random.Random(seed)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server_socket:
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((host, port))
        print(f"[udp-ping-server] listening on {host}:{port} (loss={loss})")

        served = 0
        while True:
            message, address = server_socket.recvfrom(1024)
            served += 1
            if rng.random() < loss:
                # Simulate a lost packet by not replying.
                continue
            server_socket.sendto(message.upper(), address)
            if count and served >= count:
                return


def main() -> None:
    parser = argparse.ArgumentParser(description="UDP pinger server with simulated loss")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=12000)
    parser.add_argument("--loss", type=float, default=0.3, help="packet loss probability [0,1]")
    parser.add_argument("--count", type=int, default=0, help="stop after N received (0 = forever)")
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()
    serve(args.host, args.port, args.loss, count=args.count, seed=args.seed)


if __name__ == "__main__":
    main()

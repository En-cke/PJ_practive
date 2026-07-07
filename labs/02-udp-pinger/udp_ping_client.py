"""Lab 2 - UDP Pinger, client side (Kurose-Ross Programming Assignment 2).

Sends 10 ping messages to the UDP server. Each ping carries a sequence number
and a timestamp. The client sets a 1-second socket timeout; if no reply arrives
it prints "Request timed out" (the packet was lost). Otherwise it prints the
measured round-trip time. At the end it reports summary statistics (min/max/avg
RTT and packet-loss rate), exactly like the real `ping` utility.

Run (server must be listening):
    python udp_ping_client.py --port 12000 --count 10
"""

import argparse
import socket
import time


def ping(host: str, port: int, count: int, timeout: float = 1.0):
    rtts = []
    received = 0
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client_socket:
        client_socket.settimeout(timeout)
        for seq in range(1, count + 1):
            send_time = time.time()
            message = f"Ping {seq} {send_time}"
            try:
                client_socket.sendto(message.encode("utf-8"), (host, port))
                _reply, _server = client_socket.recvfrom(1024)
                rtt = (time.time() - send_time) * 1000.0  # ms
                rtts.append(rtt)
                received += 1
                print(f"Reply from {host}: seq={seq} time={rtt:.3f} ms")
            except socket.timeout:
                print(f"Request timed out: seq={seq}")

    loss_pct = 100.0 * (count - received) / count if count else 0.0
    stats = {
        "sent": count,
        "received": received,
        "lost": count - received,
        "loss_pct": loss_pct,
        "min_ms": min(rtts) if rtts else None,
        "max_ms": max(rtts) if rtts else None,
        "avg_ms": (sum(rtts) / len(rtts)) if rtts else None,
    }
    return stats


def print_summary(stats: dict, host: str) -> None:
    print(f"\n--- {host} ping statistics ---")
    print(
        f"{stats['sent']} packets transmitted, {stats['received']} received, "
        f"{stats['loss_pct']:.1f}% packet loss"
    )
    if stats["received"]:
        print(
            f"rtt min/avg/max = {stats['min_ms']:.3f}/"
            f"{stats['avg_ms']:.3f}/{stats['max_ms']:.3f} ms"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="UDP pinger client")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=12000)
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--timeout", type=float, default=1.0)
    args = parser.parse_args()
    stats = ping(args.host, args.port, args.count, args.timeout)
    print_summary(stats, args.host)


if __name__ == "__main__":
    main()

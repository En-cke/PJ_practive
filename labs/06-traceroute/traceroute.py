"""Lab 6 - Traceroute (Kurose-Ross Programming Assignment 6).

Discovers the path to a destination by sending ICMP echo-requests with an
increasing IP TTL. Each router that decrements the TTL to zero replies with an
ICMP "Time Exceeded" (type 11) message revealing its address; the destination
itself replies with an echo-reply (type 0). This reproduces the classic Van
Jacobson traceroute using raw sockets, so it needs root/administrator rights.

Run:
    sudo python3 traceroute.py 8.8.8.8 --max-hops 30
"""

import argparse
import os
import select
import socket
import struct
import sys
import time

ICMP_ECHO_REQUEST = 8
ICMP_ECHO_REPLY = 0
ICMP_TIME_EXCEEDED = 11
ICMP_DEST_UNREACH = 3


def checksum(data: bytes) -> int:
    if len(data) % 2:
        data += b"\x00"
    total = 0
    for i in range(0, len(data), 2):
        total += (data[i] << 8) + data[i + 1]
    total = (total >> 16) + (total & 0xFFFF)
    total += total >> 16
    return ~total & 0xFFFF


def build_packet(identifier: int, sequence: int) -> bytes:
    header = struct.pack("!BBHHH", ICMP_ECHO_REQUEST, 0, 0, identifier, sequence)
    payload = struct.pack("!d", time.time())
    chk = checksum(header + payload)
    header = struct.pack("!BBHHH", ICMP_ECHO_REQUEST, 0, chk, identifier, sequence)
    return header + payload


def probe(dest_ip: str, ttl: int, identifier: int, seq: int, timeout: float):
    send_sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
    send_sock.setsockopt(socket.IPPROTO_IP, socket.IP_TTL, ttl)
    recv_sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
    recv_sock.settimeout(timeout)

    with send_sock, recv_sock:
        packet = build_packet(identifier, seq)
        send_time = time.time()
        send_sock.sendto(packet, (dest_ip, 0))

        ready = select.select([recv_sock], [], [], timeout)
        if not ready[0]:
            return {"addr": None, "rtt_ms": None, "final": False}
        recv_time = time.time()
        data, addr = recv_sock.recvfrom(1024)
        icmp_type = data[20]
        rtt = (recv_time - send_time) * 1000.0
        final = icmp_type == ICMP_ECHO_REPLY or addr[0] == dest_ip
        return {"addr": addr[0], "rtt_ms": rtt, "final": final, "type": icmp_type}


def traceroute(host: str, max_hops: int = 30, timeout: float = 2.0):
    try:
        dest_ip = socket.gethostbyname(host)
    except socket.gaierror as exc:
        print(f"cannot resolve {host}: {exc}")
        return None

    identifier = os.getpid() & 0xFFFF
    print(f"traceroute to {host} ({dest_ip}), {max_hops} hops max:")
    hops = []

    try:
        for ttl in range(1, max_hops + 1):
            result = probe(dest_ip, ttl, identifier, ttl, timeout)
            if result["addr"] is None:
                print(f"{ttl:2d}  * (timeout)")
                hops.append({"ttl": ttl, "addr": None})
            else:
                print(f"{ttl:2d}  {result['addr']}  {result['rtt_ms']:.3f} ms")
                hops.append({"ttl": ttl, "addr": result["addr"], "rtt_ms": result["rtt_ms"]})
                if result["final"]:
                    print(f"reached {host} in {ttl} hops")
                    break
    except PermissionError:
        print("raw socket requires root/administrator privileges (use sudo)")
        return None
    return hops


def main() -> None:
    parser = argparse.ArgumentParser(description="ICMP traceroute (raw socket)")
    parser.add_argument("host")
    parser.add_argument("--max-hops", type=int, default=30)
    parser.add_argument("--timeout", type=float, default=2.0)
    args = parser.parse_args()
    result = traceroute(args.host, args.max_hops, args.timeout)
    if result is None:
        sys.exit(1)


if __name__ == "__main__":
    main()

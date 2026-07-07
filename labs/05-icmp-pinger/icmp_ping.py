"""Lab 5 - ICMP Pinger (Kurose-Ross Programming Assignment 5).

Sends ICMP echo-request packets to a host using a raw socket, exactly like the
real `ping` command, and reports round-trip times, TTL and packet loss. Because
it crafts and parses ICMP headers by hand (type/code/checksum/id/seq) it must
run with raw-socket privileges: on Linux, `sudo`; on Windows, Administrator.

Run:
    sudo python3 icmp_ping.py 127.0.0.1 --count 4
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


def checksum(data: bytes) -> int:
    """Standard Internet checksum (RFC 1071)."""
    if len(data) % 2:
        data += b"\x00"
    total = 0
    for i in range(0, len(data), 2):
        total += (data[i] << 8) + data[i + 1]
    total = (total >> 16) + (total & 0xFFFF)
    total += total >> 16
    return ~total & 0xFFFF


def build_packet(identifier: int, sequence: int) -> bytes:
    # header with checksum 0, then payload = an 8-byte timestamp
    header = struct.pack("!BBHHH", ICMP_ECHO_REQUEST, 0, 0, identifier, sequence)
    payload = struct.pack("!d", time.time())
    chk = checksum(header + payload)
    header = struct.pack("!BBHHH", ICMP_ECHO_REQUEST, 0, chk, identifier, sequence)
    return header + payload


def receive_reply(sock: socket.socket, identifier: int, sequence: int,
                  timeout: float):
    time_left = timeout
    while True:
        start = time.time()
        ready = select.select([sock], [], [], time_left)
        if not ready[0]:
            return None  # timed out
        recv_time = time.time()
        packet, addr = sock.recvfrom(1024)

        # IP header is the first 20 bytes; TTL is byte 8.
        ip_header = packet[:20]
        ttl = ip_header[8]
        icmp_header = packet[20:28]
        icmp_type, code, _chk, pkt_id, seq = struct.unpack("!BBHHH", icmp_header)

        if icmp_type == ICMP_ECHO_REPLY and pkt_id == identifier:
            sent_time = struct.unpack("!d", packet[28:36])[0]
            rtt = (recv_time - sent_time) * 1000.0
            return {"rtt_ms": rtt, "ttl": ttl, "seq": seq, "src": addr[0]}

        time_left -= (time.time() - start)
        if time_left <= 0:
            return None


def ping(host: str, count: int = 4, timeout: float = 1.0):
    try:
        dest_ip = socket.gethostbyname(host)
    except socket.gaierror as exc:
        print(f"cannot resolve {host}: {exc}")
        return None

    identifier = os.getpid() & 0xFFFF
    rtts = []
    print(f"PING {host} ({dest_ip}):")

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
    except PermissionError:
        print("raw socket requires root/administrator privileges (use sudo)")
        return None

    with sock:
        sock.settimeout(timeout)
        for seq in range(1, count + 1):
            packet = build_packet(identifier, seq)
            sock.sendto(packet, (dest_ip, 0))
            result = receive_reply(sock, identifier, seq, timeout)
            if result is None:
                print(f"Request timed out: icmp_seq={seq}")
            else:
                rtts.append(result["rtt_ms"])
                print(
                    f"reply from {result['src']}: icmp_seq={seq} "
                    f"ttl={result['ttl']} time={result['rtt_ms']:.3f} ms"
                )
            time.sleep(0.2)

    received = len(rtts)
    loss = 100.0 * (count - received) / count
    print(f"\n--- {host} ping statistics ---")
    print(f"{count} packets transmitted, {received} received, {loss:.1f}% packet loss")
    if rtts:
        print(
            f"rtt min/avg/max = {min(rtts):.3f}/"
            f"{sum(rtts)/len(rtts):.3f}/{max(rtts):.3f} ms"
        )
    return {"sent": count, "received": received, "loss_pct": loss, "rtts": rtts}


def main() -> None:
    parser = argparse.ArgumentParser(description="ICMP pinger (raw socket)")
    parser.add_argument("host")
    parser.add_argument("--count", type=int, default=4)
    parser.add_argument("--timeout", type=float, default=1.0)
    args = parser.parse_args()
    result = ping(args.host, args.count, args.timeout)
    if result is None:
        sys.exit(1)


if __name__ == "__main__":
    main()

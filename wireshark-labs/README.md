# Wireshark Labs — Written Analysis

The Kurose–Ross "Computer Networking: A Top-Down Approach" course pairs the
socket-programming assignments with a set of **Wireshark packet-capture labs**.
Those labs are inherently GUI/interactive (open Wireshark, capture live traffic,
answer questions about specific packets in the trace). They do not have an
autograder and cannot be scripted to a numeric result, so — per the build spec —
they are documented here as a written analysis grounded in the protocol behaviour
the programming labs in this repo actually exercise.

Two of these analyses are **backed by real captures produced from this repo's own
code** (see `results/`): the HTTP analysis uses the Lab 1 web server + Lab 4
proxy transcript, and the ICMP analysis uses the Lab 5/6 raw-socket tools run
against `8.8.8.8`.

## 1. HTTP (Wireshark Lab 2)

The Lab 1 web server and Lab 4 proxy in this repo emit exactly the HTTP/1.1
message format a Wireshark HTTP capture dissects.

- **Request line + headers.** A browser GET is `GET /HelloWorld.html HTTP/1.1`
  followed by a `Host:` header and a blank line (`\r\n\r\n`) terminating the
  header block. Our `webserver.py` parses precisely this.
- **Status line + Content-Length.** The 200 response carries
  `HTTP/1.1 200 OK`, `Content-Type`, and `Content-Length` headers. Wireshark's
  "HTTP" dissector reads Content-Length to know where the body ends; our server
  sets it from `len(body)`.
- **Conditional GET / caching.** The proxy lab demonstrates caching directly:
  the first request is a cache MISS (fetched from the origin), the second is a
  HIT served from disk — see `results/webserver_proxy.txt` where the same URL
  returns `X-Cache: MISS` then `X-Cache: HIT`. This is the concept the HTTP
  Wireshark lab illustrates with `If-Modified-Since` / `304 Not Modified`.
- **404.** Requesting a missing object yields `HTTP/1.1 404 Not Found`, matching
  the lab's "fetch a non-existent file" step.

## 2. UDP (Wireshark Lab 5)

The UDP Pinger (Lab 2) generates the exact traffic a UDP Wireshark capture
shows: connectionless datagrams with an 8-byte UDP header (source port, dest
port, length, checksum) and no handshake. `results/udp_pinger.txt` shows 10
datagrams sent, 2 lost, giving 20% packet loss and sub-millisecond RTTs on
loopback — the observable UDP properties (no retransmission, no ordering
guarantee) that the Wireshark UDP lab asks students to confirm.

## 3. TCP (Wireshark Lab 4)

The TCP client/server (Lab 0), web server (Lab 1), proxy (Lab 4), and SMTP
client (Lab 3) all run over TCP. A TCP Wireshark capture of any of them shows:

- **Three-way handshake** (SYN, SYN-ACK, ACK) before any application byte, which
  the kernel performs on `connect()`/`accept()`.
- **Sequence & acknowledgement numbers** advancing by the number of payload
  bytes — the same in-order, reliable byte-stream semantics that the RDT lab
  (Lab 7) reimplements from scratch at the application level.
- **Connection teardown** (FIN/ACK) when we close the socket
  (`Connection: close`).

The RDT lab makes the *mechanism* behind those sequence/ACK numbers concrete:
`results/rdt.txt` shows Go-Back-N sending 789 packets to deliver 1380 bytes over
a 25%-loss / 15%-corruption / 10%-reorder channel, all recovered correctly.

## 4. ICMP (Wireshark Lab 8)

The ICMP Pinger (Lab 5) and Traceroute (Lab 6) build and parse ICMP messages by
hand, so `results/icmp_pinger.txt` and `results/traceroute.txt` are effectively
a textual packet trace:

- **Echo request/reply (type 8 / type 0).** Pinging `8.8.8.8` shows `ttl=108`
  and ~220 ms RTT — real ICMP echo replies from Google's DNS.
- **TTL and Time-Exceeded (type 11).** Traceroute increments the IP TTL; the
  first hop (`172.25.48.1`, the WSL gateway) replies at TTL=1 and the
  destination is reached at hop 13. This is exactly the TTL-expiry behaviour the
  ICMP Wireshark lab has students observe.

## 5. DNS, DHCP, IP, Ethernet/ARP, NAT, 802.11, TLS

These remaining Wireshark labs observe protocols this repo does not implement at
the socket level (they live below the transport layer or require specific
network hardware/captures). The key observations each lab targets:

| Lab | What the capture reveals |
|---|---|
| DNS | A/AAAA/CNAME query and response records; recursive vs iterative resolution; our tools call `socket.gethostbyname()`, which triggers exactly one such DNS exchange. |
| IP | 20-byte IPv4 header, fragmentation, TTL field (the same TTL our traceroute manipulates). |
| Ethernet & ARP | 14-byte Ethernet frame header; ARP request/reply resolving IP→MAC on the local link. |
| DHCP | DISCOVER/OFFER/REQUEST/ACK four-message lease exchange. |
| NAT | Address/port translation as packets cross a home router (our WSL setup NATs behind `172.25.48.1`). |
| 802.11 | WiFi management/data frames; requires monitor-mode capture hardware. |
| TLS | ClientHello/ServerHello handshake and encrypted application data. |

For these, a full write-up requires a live capture on the specific network; the
analyses above (HTTP, UDP, TCP, ICMP) are the ones this repo's code directly
produces and verifies.

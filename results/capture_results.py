"""Capture real, measured output from each lab into results/ text files.

Runs the socket labs against loopback servers, the RDT protocols over lossy
channels, and the distance-vector simulation, recording actual numbers. Run:

    python results/capture_results.py
"""

import io
import os
import socket
import sys
import threading
import time
from contextlib import redirect_stdout

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for sub in ("00-tcp-clientserver", "01-webserver", "02-udp-pinger",
            "03-smtp-mailclient", "04-http-proxy", "07-rdt", "08-distance-vector"):
    sys.path.insert(0, os.path.join(ROOT, "labs", sub))

RESULTS = os.path.join(ROOT, "results")


def free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def spawn(target, **kwargs):
    t = threading.Thread(target=target, kwargs=kwargs, daemon=True)
    t.start()
    time.sleep(0.3)
    return t


def write(name, text):
    path = os.path.join(RESULTS, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"  wrote {name} ({len(text)} bytes)")


def cap_udp_pinger():
    import udp_ping_server, udp_ping_client
    port = free_port()
    spawn(udp_ping_server.serve, host="127.0.0.1", port=port,
          loss=0.3, count=0, seed=2024)
    buf = io.StringIO()
    with redirect_stdout(buf):
        stats = udp_ping_client.ping("127.0.0.1", port, count=10, timeout=1.0)
        udp_ping_client.print_summary(stats, "127.0.0.1")
    write("udp_pinger.txt", buf.getvalue())
    return stats


def cap_rdt():
    from channel import Channel
    import rdt
    payload = (b"Reliable data transfer over a lossy, corrupting, reordering "
               b"channel. " * 20)
    lines = []
    scenarios = [
        ("rdt3.0 (stop-and-wait)", rdt.rdt30_transfer,
         dict(chunk_size=8, timeout_ticks=5)),
        ("Go-Back-N (window=5)", rdt.gbn_transfer,
         dict(window=5, chunk_size=8, timeout_ticks=8)),
        ("Selective Repeat (window=6)", rdt.sr_transfer,
         dict(window=6, chunk_size=8, timeout_ticks=8)),
    ]
    for name, fn, kw in scenarios:
        fwd = Channel(loss_prob=0.25, corrupt_prob=0.15, reorder_prob=0.1, seed=99)
        rev = Channel(loss_prob=0.25, corrupt_prob=0.15, seed=100)
        got = fn(payload, fwd, rev, **kw)
        ok = got == payload
        lines.append(f"{name}")
        lines.append(f"  channel: loss=0.25 corrupt=0.15 reorder=0.10")
        lines.append(f"  bytes to send : {len(payload)}")
        lines.append(f"  bytes received: {len(got)}")
        lines.append(f"  correct       : {ok}")
        lines.append(f"  fwd stats     : {fwd.stats}")
        lines.append("")
    text = "\n".join(lines)
    write("rdt.txt", text)
    return text


def cap_distance_vector():
    from distance_vector import demo
    net = demo()
    buf = io.StringIO()
    with redirect_stdout(buf):
        rounds, converged = net.run()
        print(f"Converged={converged} after {rounds} rounds\n")
        ref = net.all_pairs_reference()
        all_match = True
        for name in sorted(net.nodes):
            print(f"Routing table for {name}:")
            for dest, (cost, hop) in sorted(net.routing_table(name).items()):
                mark = ""
                if name != dest and cost != ref[(name, dest)]:
                    mark = "  <-- MISMATCH"
                    all_match = False
                print(f"  to {dest}: cost={cost:g}, next_hop={hop}{mark}")
            print()
        print(f"All costs match Floyd-Warshall reference: {all_match}")
    write("distance_vector.txt", buf.getvalue())


def cap_webserver_and_proxy():
    import webserver, proxy_server, proxy_client
    import shutil
    origin_port = free_port()
    proxy_port = free_port()
    root = os.path.join(ROOT, "labs", "01-webserver", "www")
    threading.Thread(target=webserver.serve,
                     kwargs=dict(host="127.0.0.1", port=origin_port, root=root,
                                 once=False), daemon=True).start()
    cache = os.path.join(ROOT, "labs", "04-http-proxy", "cache_run")
    shutil.rmtree(cache, ignore_errors=True)
    threading.Thread(target=proxy_server.serve,
                     kwargs=dict(host="127.0.0.1", port=proxy_port,
                                 cache_dir=cache, once=False), daemon=True).start()
    time.sleep(0.4)
    url = f"http://127.0.0.1:{origin_port}/HelloWorld.html"
    first = proxy_client.fetch_via_proxy("127.0.0.1", proxy_port, url)
    second = proxy_client.fetch_via_proxy("127.0.0.1", proxy_port, url)
    text = (
        "=== Web server + caching proxy ===\n\n"
        f"Request URL: {url}\n\n"
        "--- First request through proxy (expect MISS) ---\n"
        + first.decode("utf-8", "replace") +
        "\n--- Second request through proxy (expect HIT) ---\n"
        + second.decode("utf-8", "replace")
    )
    write("webserver_proxy.txt", text)
    shutil.rmtree(cache, ignore_errors=True)


def cap_smtp():
    import smtp_client, mock_smtp_server
    port = free_port()
    captured = {}
    def run():
        captured.update(mock_smtp_server.serve("127.0.0.1", port, once=True))
    threading.Thread(target=run, daemon=True).start()
    time.sleep(0.3)
    logs = []
    smtp_client.send_mail("127.0.0.1", port, "alice@example.com",
                          "bob@example.com", "Top-Down Lab 3",
                          "Hello from the SMTP lab.", log=logs.append)
    time.sleep(0.2)
    text = "=== SMTP session transcript ===\n\n" + "\n".join(logs)
    text += f"\n\n=== Message captured by server ===\nfrom: {captured.get('from')}\n"
    text += f"to: {captured.get('to')}\ndata:\n{captured.get('data')}\n"
    write("smtp.txt", text)


def main():
    os.makedirs(RESULTS, exist_ok=True)
    print("Capturing lab results...")
    cap_udp_pinger()
    cap_rdt()
    cap_distance_vector()
    cap_webserver_and_proxy()
    cap_smtp()
    print("Done.")


if __name__ == "__main__":
    main()

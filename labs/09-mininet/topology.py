r"""Lab 9 - Mininet topology + connectivity/throughput test.

Builds a small dumbbell topology in Mininet:

    h1 --\                    /-- h3
          s1 ---- (link) ---- s2
    h2 --/                    \-- h4

and runs three automated checks:
  1. pingAll() to confirm full L2/L3 connectivity,
  2. an iperf throughput measurement across the bottleneck link,
  3. a ping RTT sample across the topology.

Results are printed and (when --json is given) written to a file for the
results/ directory. Requires Mininet (Linux only):
    sudo python3 topology.py --json results.json

If Mininet is not installed the script prints install instructions and exits
non-zero, so the harness can record it as an environment limitation rather than
a code failure.
"""

import argparse
import json
import sys


def build_and_test(bw_mbit: int = 10, delay_ms: str = "5ms"):
    try:
        from mininet.net import Mininet
        from mininet.node import OVSController
        from mininet.link import TCLink
        from mininet.topo import Topo
    except ImportError:
        print(
            "Mininet is not installed. Install with:\n"
            "  sudo apt-get install -y mininet\n"
            "and run this script with sudo on Linux."
        )
        return None

    class DumbbellTopo(Topo):
        def build(self):
            s1 = self.addSwitch("s1")
            s2 = self.addSwitch("s2")
            for name in ("h1", "h2"):
                h = self.addHost(name)
                self.addLink(h, s1)
            for name in ("h3", "h4"):
                h = self.addHost(name)
                self.addLink(h, s2)
            # bottleneck link with bandwidth + delay
            self.addLink(s1, s2, cls=TCLink, bw=bw_mbit, delay=delay_ms)

    net = Mininet(topo=DumbbellTopo(), controller=OVSController, link=TCLink)
    results = {}
    try:
        net.start()
        loss = net.pingAll()
        results["pingall_loss_pct"] = loss

        h1, h3 = net.get("h1"), net.get("h3")
        # Manual, bounded iperf: Mininet's net.iperf() can block indefinitely
        # under WSL2, so we run our own server/client with hard timeouts and
        # always clean up the server process.
        h3.cmd("iperf -s -p 5001 &> /tmp/iperf_srv.txt &")
        import time as _t
        _t.sleep(1)
        iperf_out = h1.cmd(
            f"timeout 15 iperf -c {h3.IP()} -p 5001 -t 5 -y C 2>/dev/null"
        ).strip()
        h3.cmd("kill %iperf 2>/dev/null; pkill -f 'iperf -s' 2>/dev/null")
        # -y C gives CSV; last field is bits/sec.
        if iperf_out and "," in iperf_out:
            bps = int(iperf_out.split(",")[-1])
            results["iperf_mbit_per_sec"] = round(bps / 1e6, 3)
            results["iperf_raw_csv"] = iperf_out
        else:
            results["iperf_mbit_per_sec"] = None
            results["iperf_raw_csv"] = iperf_out

        rtt = h1.cmd(f"ping -c 4 {h3.IP()}")
        results["ping_h1_h3"] = rtt.strip().splitlines()[-2:]
    finally:
        net.stop()
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Mininet dumbbell lab")
    parser.add_argument("--bw", type=int, default=10, help="bottleneck Mbit/s")
    parser.add_argument("--delay", default="5ms")
    parser.add_argument("--json", default=None)
    args = parser.parse_args()

    results = build_and_test(args.bw, args.delay)
    if results is None:
        sys.exit(2)
    print(json.dumps(results, indent=2, default=str))
    if args.json:
        with open(args.json, "w") as f:
            json.dump(results, f, indent=2, default=str)


if __name__ == "__main__":
    main()

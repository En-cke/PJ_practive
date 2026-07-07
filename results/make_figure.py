"""Generate results/rdt_efficiency.png from real RDT protocol runs.

Measures, for each protocol and a sweep of channel loss rates, how many packets
the sender must transmit to reliably deliver a fixed payload. Selective Repeat
and rdt3.0 retransmit only what is needed; Go-Back-N retransmits whole windows,
so its transmission count grows fastest as loss rises. The figure visualises
this real, measured trade-off.
"""

import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "labs", "07-rdt"))

from channel import Channel
import rdt

PAYLOAD = b"Top-Down reliable data transfer benchmark payload. " * 20
LOSSES = [0.0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3]

protocols = {
    "rdt3.0 (stop-and-wait)": (rdt.rdt30_transfer,
                               dict(chunk_size=8, timeout_ticks=5)),
    "Go-Back-N (W=5)": (rdt.gbn_transfer,
                        dict(window=5, chunk_size=8, timeout_ticks=8)),
    "Selective Repeat (W=6)": (rdt.sr_transfer,
                               dict(window=6, chunk_size=8, timeout_ticks=8)),
}


def measure():
    series = {name: [] for name in protocols}
    for name, (fn, kw) in protocols.items():
        for loss in LOSSES:
            # average over a few seeds for a stable curve
            total_sent = 0
            trials = 5
            for seed in range(trials):
                fwd = Channel(loss_prob=loss, corrupt_prob=0.0, seed=seed)
                rev = Channel(loss_prob=loss, corrupt_prob=0.0, seed=seed + 100)
                got = fn(PAYLOAD, fwd, rev, **kw)
                assert got == PAYLOAD, f"{name} failed at loss={loss}"
                total_sent += fwd.stats["sent"]
            series[name].append(total_sent / trials)
    return series


def main():
    series = measure()
    plt.figure(figsize=(8, 5))
    for name, values in series.items():
        plt.plot([l * 100 for l in LOSSES], values, marker="o", label=name)
    plt.xlabel("Channel loss rate (%)")
    plt.ylabel("Packets transmitted to deliver payload")
    plt.title("RDT protocol overhead vs channel loss (measured)")
    plt.legend()
    plt.grid(True, alpha=0.3)
    out = os.path.join(ROOT, "results", "rdt_efficiency.png")
    plt.tight_layout()
    plt.savefig(out, dpi=110)
    print(f"wrote {out}")
    # also print the raw numbers so the README can cite them
    for name, values in series.items():
        print(name, [round(v, 1) for v in values])


if __name__ == "__main__":
    main()

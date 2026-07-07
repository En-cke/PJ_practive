"""Lab 7 - Unreliable channel simulator for the RDT lab.

Provides a bidirectional, lossy, corrupting, reordering channel between a sender
and a receiver. The reliable-data-transfer protocols (rdt3.0, Go-Back-N,
Selective Repeat) are built on top of this channel and must deliver data
correctly and in order despite the channel's misbehaviour.

The channel is fully deterministic given a seed, so tests are reproducible.
"""

from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Packet:
    """A transport-layer segment carrying either data or an ACK."""
    seq: int = 0
    ack: int = 0
    is_ack: bool = False
    payload: bytes = b""
    checksum: int = 0
    corrupt: bool = False  # set by the channel when it damages the packet

    def compute_checksum(self) -> int:
        total = self.seq * 1000003 + self.ack * 131 + (1 if self.is_ack else 0)
        for b in self.payload:
            total = (total * 31 + b) & 0xFFFFFFFF
        return total & 0xFFFFFFFF

    def sealed(self) -> "Packet":
        self.checksum = self.compute_checksum()
        return self

    def is_valid(self) -> bool:
        """A packet is valid iff it was not corrupted and its checksum matches."""
        if self.corrupt:
            return False
        return self.checksum == self.compute_checksum()


@dataclass
class Channel:
    """A lossy/corrupting/reordering FIFO-ish channel.

    Parameters
    ----------
    loss_prob : probability a packet is dropped entirely.
    corrupt_prob : probability a packet's bits get flipped (checksum will fail).
    reorder_prob : probability a packet is delayed behind the next one.
    seed : RNG seed for reproducibility.
    """
    loss_prob: float = 0.0
    corrupt_prob: float = 0.0
    reorder_prob: float = 0.0
    seed: Optional[int] = None
    _rng: random.Random = field(init=False)
    _queue: deque = field(init=False, default_factory=deque)
    _delayed: Optional[Packet] = field(init=False, default=None)
    stats: dict = field(init=False, default_factory=dict)

    def __post_init__(self) -> None:
        self._rng = random.Random(self.seed)
        self.stats = {"sent": 0, "lost": 0, "corrupted": 0, "reordered": 0, "delivered": 0}

    def send(self, packet: Packet) -> None:
        self.stats["sent"] += 1
        if self._rng.random() < self.loss_prob:
            self.stats["lost"] += 1
            return  # packet dropped

        pkt = Packet(
            seq=packet.seq, ack=packet.ack, is_ack=packet.is_ack,
            payload=packet.payload, checksum=packet.checksum,
        )
        if self._rng.random() < self.corrupt_prob:
            pkt.corrupt = True
            self.stats["corrupted"] += 1

        if self._delayed is not None:
            # release the previously delayed packet now (after this one)
            self._queue.append(pkt)
            self._queue.append(self._delayed)
            self._delayed = None
        elif self._rng.random() < self.reorder_prob:
            self._delayed = pkt
            self.stats["reordered"] += 1
        else:
            self._queue.append(pkt)

    def receive(self) -> Optional[Packet]:
        """Return the next available packet, or None if the channel is empty."""
        if not self._queue:
            if self._delayed is not None:
                pkt = self._delayed
                self._delayed = None
                self.stats["delivered"] += 1
                return pkt
            return None
        pkt = self._queue.popleft()
        self.stats["delivered"] += 1
        return pkt

    def empty(self) -> bool:
        return not self._queue and self._delayed is None

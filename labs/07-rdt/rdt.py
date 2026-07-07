"""Lab 7 - Reliable Data Transfer protocols (Kurose-Ross Programming Assignment).

Implements three reliable-transport protocols on top of the unreliable Channel:

  * rdt3.0        - stop-and-wait with sequence numbers 0/1, ACKs, checksums and
                    a retransmission timer (Kurose-Ross Section 3.4.1).
  * Go-Back-N     - a sliding-window sender with cumulative ACKs; the receiver
                    discards out-of-order packets and re-ACKs the last in-order
                    one (Section 3.4.3).
  * Selective Repeat - a sliding window where the receiver buffers out-of-order
                    packets and ACKs each one individually (Section 3.4.4).

All three run a discrete event loop: the sender pushes packets into a forward
channel, the receiver's ACKs come back on a reverse channel, and a virtual clock
drives timeouts. Each protocol delivers the original byte stream to the receiver
application exactly once and in order, no matter how badly the channel behaves.
"""

from __future__ import annotations

from typing import List

from channel import Channel, Packet


def _chunk(data: bytes, size: int) -> List[bytes]:
    return [data[i:i + size] for i in range(0, len(data), size)] or [b""]


# --------------------------------------------------------------------------- #
# rdt3.0 - stop-and-wait
# --------------------------------------------------------------------------- #
def rdt30_transfer(data: bytes, forward: Channel, reverse: Channel,
                   chunk_size: int = 4, timeout_ticks: int = 4,
                   max_ticks: int = 100000) -> bytes:
    """Transfer `data` reliably using stop-and-wait. Returns bytes received."""
    chunks = _chunk(data, chunk_size)
    delivered = bytearray()

    send_base = 0        # index of chunk the sender is currently on
    send_seq = 0         # alternating bit
    timer = None         # tick at which the outstanding packet times out
    outstanding = None

    recv_expected = 0    # bit the receiver expects next

    tick = 0
    while send_base < len(chunks) and tick < max_ticks:
        tick += 1

        # Sender: (re)send current packet if nothing outstanding or timed out.
        if outstanding is None:
            pkt = Packet(seq=send_seq, payload=chunks[send_base]).sealed()
            forward.send(pkt)
            outstanding = pkt
            timer = tick + timeout_ticks
        elif timer is not None and tick >= timer:
            forward.send(outstanding)  # retransmit
            timer = tick + timeout_ticks

        # Receiver: process at most one arriving data packet, reply with ACK.
        data_pkt = forward.receive()
        if data_pkt is not None:
            if data_pkt.is_valid() and data_pkt.seq == recv_expected:
                delivered.extend(data_pkt.payload)
                ack = Packet(is_ack=True, ack=recv_expected).sealed()
                reverse.send(ack)
                recv_expected ^= 1
            else:
                # corrupt or duplicate: re-ACK the last correctly received bit
                last = recv_expected ^ 1
                reverse.send(Packet(is_ack=True, ack=last).sealed())

        # Sender: process an arriving ACK.
        ack_pkt = reverse.receive()
        if ack_pkt is not None and ack_pkt.is_valid() and ack_pkt.is_ack:
            if ack_pkt.ack == send_seq:
                send_base += 1
                send_seq ^= 1
                outstanding = None
                timer = None

    return bytes(delivered)


# --------------------------------------------------------------------------- #
# Go-Back-N
# --------------------------------------------------------------------------- #
def gbn_transfer(data: bytes, forward: Channel, reverse: Channel,
                 window: int = 4, chunk_size: int = 4, timeout_ticks: int = 6,
                 max_ticks: int = 100000) -> bytes:
    chunks = _chunk(data, chunk_size)
    n = len(chunks)
    delivered = bytearray()

    base = 0          # oldest unacked seq
    next_seq = 0      # next seq to send
    timer = None

    recv_expected = 0  # next in-order seq the receiver wants

    tick = 0
    while base < n and tick < max_ticks:
        tick += 1

        # Sender: fill the window.
        while next_seq < base + window and next_seq < n:
            pkt = Packet(seq=next_seq, payload=chunks[next_seq]).sealed()
            forward.send(pkt)
            if base == next_seq:
                timer = tick + timeout_ticks
            next_seq += 1

        # Timeout: go back N - retransmit everything from base.
        if timer is not None and tick >= timer:
            for s in range(base, next_seq):
                forward.send(Packet(seq=s, payload=chunks[s]).sealed())
            timer = tick + timeout_ticks

        # Receiver.
        data_pkt = forward.receive()
        if data_pkt is not None:
            if data_pkt.is_valid() and data_pkt.seq == recv_expected:
                delivered.extend(data_pkt.payload)
                reverse.send(Packet(is_ack=True, ack=recv_expected).sealed())
                recv_expected += 1
            else:
                # cumulative ACK of the last correctly received in-order seq
                last = recv_expected - 1
                if last >= 0:
                    reverse.send(Packet(is_ack=True, ack=last).sealed())

        # Sender: process cumulative ACK.
        ack_pkt = reverse.receive()
        if ack_pkt is not None and ack_pkt.is_valid() and ack_pkt.is_ack:
            if ack_pkt.ack >= base:
                base = ack_pkt.ack + 1
                if base == next_seq:
                    timer = None
                else:
                    timer = tick + timeout_ticks

    return bytes(delivered)


# --------------------------------------------------------------------------- #
# Selective Repeat
# --------------------------------------------------------------------------- #
def sr_transfer(data: bytes, forward: Channel, reverse: Channel,
                window: int = 4, chunk_size: int = 4, timeout_ticks: int = 6,
                max_ticks: int = 200000) -> bytes:
    chunks = _chunk(data, chunk_size)
    n = len(chunks)

    base = 0
    next_seq = 0
    acked = [False] * n
    timers = {}   # seq -> expiry tick

    recv_base = 0
    recv_buffer = {}   # seq -> payload for out-of-order packets
    delivered = bytearray()

    tick = 0
    while base < n and tick < max_ticks:
        tick += 1

        # Sender: send new packets within the window.
        while next_seq < base + window and next_seq < n:
            forward.send(Packet(seq=next_seq, payload=chunks[next_seq]).sealed())
            timers[next_seq] = tick + timeout_ticks
            next_seq += 1

        # Sender: retransmit any individually timed-out, unacked packet.
        for s in range(base, next_seq):
            if not acked[s] and timers.get(s, tick + 1) <= tick:
                forward.send(Packet(seq=s, payload=chunks[s]).sealed())
                timers[s] = tick + timeout_ticks

        # Receiver.
        data_pkt = forward.receive()
        if data_pkt is not None and data_pkt.is_valid():
            seq = data_pkt.seq
            # ACK anything in [recv_base-window, recv_base+window)
            reverse.send(Packet(is_ack=True, ack=seq).sealed())
            if seq >= recv_base and seq not in recv_buffer and seq >= recv_base:
                recv_buffer[seq] = data_pkt.payload
                # slide receiver window, delivering in order
                while recv_base in recv_buffer:
                    delivered.extend(recv_buffer.pop(recv_base))
                    recv_base += 1

        # Sender: process selective ACK.
        ack_pkt = reverse.receive()
        if ack_pkt is not None and ack_pkt.is_valid() and ack_pkt.is_ack:
            s = ack_pkt.ack
            if 0 <= s < n:
                acked[s] = True
                timers.pop(s, None)
                while base < n and acked[base]:
                    base += 1

    return bytes(delivered)

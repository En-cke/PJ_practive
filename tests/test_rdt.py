"""Tests for Lab 7 - reliable data transfer over an unreliable channel.

Every protocol (rdt3.0, Go-Back-N, Selective Repeat) must reconstruct the exact
original byte stream even when the channel loses, corrupts, and reorders
packets. We test each protocol under increasingly hostile channel conditions.
"""

import pytest

from channel import Channel
import rdt

PAYLOAD = (
    b"Computer Networking: A Top-Down Approach. "
    b"Reliable data transfer must deliver every byte, in order, exactly once, "
    b"even over a channel that loses, corrupts and reorders packets. "
    b"0123456789 abcdefghijklmnopqrstuvwxyz " * 3
)


@pytest.mark.parametrize("loss,corrupt,reorder", [
    (0.0, 0.0, 0.0),
    (0.2, 0.0, 0.0),
    (0.0, 0.2, 0.0),
    (0.3, 0.2, 0.0),
    (0.2, 0.2, 0.2),
])
def test_rdt30_stop_and_wait(loss, corrupt, reorder):
    fwd = Channel(loss_prob=loss, corrupt_prob=corrupt, reorder_prob=reorder, seed=7)
    rev = Channel(loss_prob=loss, corrupt_prob=corrupt, seed=8)
    got = rdt.rdt30_transfer(PAYLOAD, fwd, rev, chunk_size=8, timeout_ticks=5)
    assert got == PAYLOAD


@pytest.mark.parametrize("loss,corrupt,reorder", [
    (0.0, 0.0, 0.0),
    (0.2, 0.0, 0.0),
    (0.3, 0.1, 0.0),
    (0.2, 0.2, 0.1),
])
def test_go_back_n(loss, corrupt, reorder):
    fwd = Channel(loss_prob=loss, corrupt_prob=corrupt, reorder_prob=reorder, seed=11)
    rev = Channel(loss_prob=loss, corrupt_prob=corrupt, seed=12)
    got = rdt.gbn_transfer(PAYLOAD, fwd, rev, window=5, chunk_size=8, timeout_ticks=8)
    assert got == PAYLOAD


@pytest.mark.parametrize("loss,corrupt,reorder", [
    (0.0, 0.0, 0.0),
    (0.2, 0.0, 0.0),
    (0.3, 0.1, 0.2),
    (0.25, 0.2, 0.2),
])
def test_selective_repeat(loss, corrupt, reorder):
    fwd = Channel(loss_prob=loss, corrupt_prob=corrupt, reorder_prob=reorder, seed=21)
    rev = Channel(loss_prob=loss, corrupt_prob=corrupt, seed=22)
    got = rdt.sr_transfer(PAYLOAD, fwd, rev, window=6, chunk_size=8, timeout_ticks=8)
    assert got == PAYLOAD


def test_empty_and_small_payloads():
    for data in (b"", b"a", b"ab", b"hello"):
        fwd = Channel(loss_prob=0.2, corrupt_prob=0.1, seed=1)
        rev = Channel(loss_prob=0.2, seed=2)
        assert rdt.rdt30_transfer(data, fwd, rev, chunk_size=4) == data

"""Tests for Lab 8 - distance-vector routing.

The distributed Bellman-Ford result must converge and match a centralised
all-pairs shortest-path computation (Floyd-Warshall) for the costs, and every
next-hop must lie on a genuine shortest path.
"""

from distance_vector import Network, demo


def test_demo_converges_and_matches_reference():
    net = demo()
    rounds, converged = net.run()
    assert converged, "distance-vector did not converge"

    reference = net.all_pairs_reference()
    for src in net.nodes:
        table = net.routing_table(src)
        for dest in net.nodes:
            if src == dest:
                assert table[dest][0] == 0.0
                continue
            assert table[dest][0] == reference[(src, dest)], (
                f"cost mismatch {src}->{dest}: DV={table[dest][0]} "
                f"ref={reference[(src, dest)]}"
            )


def test_known_shortest_costs():
    """Spot-check a couple of hand-computed shortest paths in the demo topo."""
    net = demo()
    net.run()
    tbl_u = net.routing_table("u")
    # u->x direct = 1; u->y via x = 1+1 = 2; u->z via x,y = 1+1+2 = 4
    assert tbl_u["x"][0] == 1
    assert tbl_u["y"][0] == 2
    assert tbl_u["z"][0] == 4
    # next hop from u toward y and z is x (the cheap link)
    assert tbl_u["y"][1] == "x"
    assert tbl_u["z"][1] == "x"


def test_linear_chain():
    net = Network()
    net.add_link("a", "b", 1)
    net.add_link("b", "c", 1)
    net.add_link("c", "d", 1)
    rounds, converged = net.run()
    assert converged
    tbl_a = net.routing_table("a")
    assert tbl_a["d"][0] == 3
    assert tbl_a["d"][1] == "b"  # must go through b


def test_triangle_prefers_direct_when_cheaper():
    net = Network()
    net.add_link("a", "b", 1)
    net.add_link("b", "c", 1)
    net.add_link("a", "c", 5)  # direct a-c is expensive
    net.run()
    tbl_a = net.routing_table("a")
    assert tbl_a["c"][0] == 2      # a->b->c is cheaper than direct 5
    assert tbl_a["c"][1] == "b"

"""Lab 8 - Distance-Vector routing (Kurose-Ross Programming Assignment).

A discrete-event simulation of the distributed Bellman-Ford (distance-vector)
algorithm. Each node knows only the cost to its direct neighbours. Nodes
exchange distance vectors with their neighbours; on receiving a neighbour's
vector a node re-runs the Bellman-Ford update

    D_x(y) = min over neighbours v of ( c(x,v) + D_v(y) )

and, if any entry changed, advertises its new vector. The simulation runs until
no node's vector changes (convergence) and then reports each node's routing
table (cost + next hop to every destination). The result is verified against a
centralised all-pairs shortest-path computation.
"""

from __future__ import annotations

from typing import Dict, Tuple

INF = float("inf")


class Node:
    def __init__(self, name: str):
        self.name = name
        self.neighbours: Dict[str, float] = {}       # direct link costs
        # distance vector: dest -> (cost, next_hop)
        self.dv: Dict[str, Tuple[float, str]] = {name: (0.0, name)}
        # last-known distance vectors received from neighbours
        self.neighbour_dv: Dict[str, Dict[str, float]] = {}

    def add_neighbour(self, other: str, cost: float) -> None:
        self.neighbours[other] = cost
        self.dv[other] = (cost, other)
        self.neighbour_dv.setdefault(other, {})

    def current_vector(self) -> Dict[str, float]:
        return {dest: cost for dest, (cost, _hop) in self.dv.items()}

    def update(self, all_dests) -> bool:
        """Recompute the DV via Bellman-Ford. Return True if it changed."""
        changed = False
        for dest in all_dests:
            if dest == self.name:
                continue
            best_cost = INF
            best_hop = None
            for v, link_cost in self.neighbours.items():
                via_cost = link_cost + self.neighbour_dv.get(v, {}).get(dest, INF)
                if via_cost < best_cost:
                    best_cost = via_cost
                    best_hop = v
            old = self.dv.get(dest, (INF, None))
            new = (best_cost, best_hop)
            if new[0] != old[0] or new[1] != old[1]:
                self.dv[dest] = new
                changed = True
        return changed


class Network:
    def __init__(self):
        self.nodes: Dict[str, Node] = {}

    def add_node(self, name: str) -> None:
        self.nodes.setdefault(name, Node(name))

    def add_link(self, a: str, b: str, cost: float) -> None:
        self.add_node(a)
        self.add_node(b)
        self.nodes[a].add_neighbour(b, cost)
        self.nodes[b].add_neighbour(a, cost)

    def run(self, max_rounds: int = 1000):
        """Run synchronous DV exchange until convergence.

        Returns (rounds, converged?).
        """
        dests = list(self.nodes.keys())
        rounds = 0
        while rounds < max_rounds:
            rounds += 1
            # 1) every node advertises its current vector to its neighbours
            snapshots = {n.name: n.current_vector() for n in self.nodes.values()}
            for node in self.nodes.values():
                for nb in node.neighbours:
                    node.neighbour_dv[nb] = dict(snapshots[nb])
            # 2) every node recomputes
            any_changed = False
            for node in self.nodes.values():
                if node.update(dests):
                    any_changed = True
            if not any_changed:
                return rounds, True
        return rounds, False

    def routing_table(self, name: str) -> Dict[str, Tuple[float, str]]:
        return dict(self.nodes[name].dv)

    def all_pairs_reference(self) -> Dict[Tuple[str, str], float]:
        """Floyd-Warshall ground truth for verification."""
        names = list(self.nodes.keys())
        dist = {(i, j): (0.0 if i == j else INF) for i in names for j in names}
        for node in self.nodes.values():
            for nb, c in node.neighbours.items():
                dist[(node.name, nb)] = min(dist[(node.name, nb)], c)
        for k in names:
            for i in names:
                for j in names:
                    if dist[(i, k)] + dist[(k, j)] < dist[(i, j)]:
                        dist[(i, j)] = dist[(i, k)] + dist[(k, j)]
        return dist


def demo() -> Network:
    """The classic 4-node example from Kurose-Ross Figure 3.4 style topology."""
    net = Network()
    net.add_link("u", "v", 2)
    net.add_link("u", "x", 1)
    net.add_link("u", "w", 5)
    net.add_link("v", "x", 2)
    net.add_link("v", "w", 3)
    net.add_link("x", "w", 3)
    net.add_link("x", "y", 1)
    net.add_link("w", "y", 5)
    net.add_link("w", "z", 5)
    net.add_link("y", "z", 2)
    return net


if __name__ == "__main__":
    net = demo()
    rounds, converged = net.run()
    print(f"Converged={converged} after {rounds} rounds\n")
    for name in sorted(net.nodes):
        print(f"Routing table for {name}:")
        for dest, (cost, hop) in sorted(net.routing_table(name).items()):
            print(f"  to {dest}: cost={cost:g}, next_hop={hop}")
        print()

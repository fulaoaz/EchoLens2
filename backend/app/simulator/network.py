"""Social network topology — small-world (Watts-Strogatz) backbone.

Pure topology: nodes are agent indices (0..N-1), edges are undirected.
``build_network`` is deterministic when ``seed`` is supplied — the simulator
relies on this for reproducibility.

We use Watts-Strogatz for the M2.1 baseline because it produces realistic
clustering (友邻相似) plus a few long-range shortcuts (KOL 跨圈传播) on small
populations (10²–10⁴ agents) with negligible CPU. A scale-free Barabasi-Albert
overlay can be added later via the optional ``ba_attach`` parameter.
"""

from __future__ import annotations

import networkx as nx


def build_network(
    num_agents: int,
    *,
    mean_degree: int = 8,
    rewire_prob: float = 0.1,
    seed: int | None = None,
) -> nx.Graph:
    """Build a small-world undirected graph.

    Parameters
    ----------
    num_agents:
        Total node count. Returns an empty graph for ``num_agents <= 0``.
    mean_degree:
        Expected degree per node. Watts-Strogatz requires an even ``k`` ≥ 2 and
        ``k < num_agents``; we coerce/clamp accordingly.
    rewire_prob:
        Probability of rewiring each edge to a random target — controls how
        many "shortcut" edges connect distant clusters.
    seed:
        Deterministic RNG seed. ``None`` means non-reproducible.
    """
    if num_agents <= 0:
        return nx.Graph()
    if num_agents == 1:
        g = nx.Graph()
        g.add_node(0)
        return g

    # Watts-Strogatz constraints: k must be even and < num_agents.
    k = max(2, mean_degree)
    if k % 2 == 1:
        k += 1
    k = min(k, num_agents - 1 if (num_agents - 1) % 2 == 0 else num_agents - 2)
    k = max(2, k)

    g = nx.watts_strogatz_graph(num_agents, k, rewire_prob, seed=seed)
    return g


def degree_summary(graph: nx.Graph) -> dict[str, float]:
    """Return mean / median / max degree — used by tests + /api responses."""
    if graph.number_of_nodes() == 0:
        return {"nodes": 0, "edges": 0, "mean_degree": 0.0, "max_degree": 0.0}
    degs = [d for _, d in graph.degree()]
    return {
        "nodes": float(graph.number_of_nodes()),
        "edges": float(graph.number_of_edges()),
        "mean_degree": sum(degs) / len(degs),
        "max_degree": float(max(degs)),
    }


__all__ = ["build_network", "degree_summary"]

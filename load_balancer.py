"""
load_balancer.py — Load-Balancing Algorithms
=============================================
Implements three strategies for distributing tasks to nodes:

  1. Round Robin        — simple cyclic distribution
  2. Least Loaded       — pick the node with the lightest workload
  3. Adaptive           — weighted multi-factor scoring (the "proposed" algorithm)

All three implement the same interface:
    balancer.assign(task, nodes) → selected_node or None

Design principle: the balancer *selects* a node but does not modify it.
The simulation engine calls node.assign_task() after selection.

Academic note:
  Round Robin and Least Loaded are well-known baselines.
  The Adaptive algorithm is the student's proposed contribution.
  It is NOT claimed to be novel in the research sense — it is a
  weighted-score heuristic that the experiments will evaluate.
"""

from config import ADAPTIVE_WEIGHTS


class LoadBalancer:
    """
    Base class — defines the interface and stores the algorithm name.
    """
    def __init__(self, name: str):
        self.name = name

    def assign(self, task, nodes):
        """
        Select the best node for *task* from *nodes*.

        Returns the chosen Node, or None if no node can accept it.
        """
        raise NotImplementedError

    def reset(self):
        """Reset any internal state (e.g. round-robin counter)."""
        pass



# Algorithm 1: Round Robin


class RoundRobinBalancer(LoadBalancer):
    """
    Distributes tasks one-by-one in a fixed cyclic order.

    How it works:
      Task 1 → Node 0
      Task 2 → Node 1
      Task 3 → Node 2
      Task 4 → Node 3  (cloud)
      Task 5 → Node 0  (wraps around)
      ...

    If the selected node cannot accept the task (insufficient resources),
    we try the next node, up to N attempts.  If none works, the task
    is rejected.

    Strengths:  Dead simple, zero overhead.
    Weaknesses: Ignores actual load → can send tasks to overloaded nodes.
    """

    def __init__(self):
        super().__init__(name="Round Robin")
        self._counter = 0   # Tracks which node is next

    def assign(self, task, nodes):
        n = len(nodes)
        # Try each node starting from the current counter position
        for attempt in range(n):
            idx = (self._counter + attempt) % n
            node = nodes[idx]
            if node.can_accept(task):
                self._counter = (idx + 1) % n  # Advance for next call
                return node
        # No node can accept — task will be rejected
        return None

    def reset(self):
        self._counter = 0



# Algorithm 2: Least Loaded


class LeastLoadedBalancer(LoadBalancer):
    """
    Assigns each task to the node with the **lowest current workload**.

    "Workload" is measured as the fraction of busy VMs (workload_ratio).
    Ties are broken by which node has more free CPU.

    If the least-loaded node cannot accept the task (insufficient CPU/RAM),
    we try the next-least-loaded, and so on.

    Strengths:  Reacts to actual load — avoids hot-spots.
    Weaknesses: Only looks at VM count, ignores latency and speed.
    """

    def __init__(self):
        super().__init__(name="Least Loaded")

    def assign(self, task, nodes):
        # Sort nodes by workload_ratio (ascending), then by cpu_available (descending)
        sorted_nodes = sorted(
            nodes,
            key=lambda n: (n.workload_ratio, -n.cpu_available)
        )
        for node in sorted_nodes:
            if node.can_accept(task):
                return node
        return None



# Algorithm 3: Adaptive Load Balancer (Proposed)


class AdaptiveBalancer(LoadBalancer):
    """
    Multi-factor weighted scoring algorithm.

    For each candidate node that has enough resources, we compute:

        score = w_cpu   × (1 − cpu_utilization)
              + w_ram   × (1 − ram_utilization)
              + w_work  × (1 − workload_ratio)
              + w_lat   × (1 − latency_normalised)
              + w_speed × speed_normalised

    Where:
      - cpu_utilization   = cpu_used / cpu_capacity           ∈ [0, 1]
      - ram_utilization   = ram_used / ram_capacity           ∈ [0, 1]
      - workload_ratio    = busy_vms / total_vms              ∈ [0, 1]
      - latency_normalised = node_latency / max_latency       ∈ [0, 1]
      - speed_normalised   = node_speed / max_speed           ∈ [0, 1]

    Higher score → better candidate.

    The node with the highest score wins, provided it can satisfy the
    task's CPU and RAM requirements.

    Weights are configurable via config.py so the user (or the dashboard)
    can tune them experimentally.

    Strengths:
      - Considers multiple factors simultaneously.
      - Naturally balances latency-sensitive vs compute-heavy tasks.
    Weaknesses:
      - Requires good weight tuning (domain knowledge).
      - Score computation is O(N) per task, slightly more overhead
        than Round Robin (though N = 4 nodes, so negligible here).
    """

    def __init__(self, weights: dict = None):
        super().__init__(name="Adaptive")
        # Use provided weights or defaults from config
        w = weights or ADAPTIVE_WEIGHTS
        self.w_cpu = w.get("w_cpu", 0.30)
        self.w_ram = w.get("w_ram", 0.25)
        self.w_workload = w.get("w_workload", 0.20)
        self.w_latency = w.get("w_latency", 0.15)
        self.w_speed = w.get("w_speed", 0.10)

    def _compute_score(self, node, max_latency: float, max_speed: float) -> float:
        """
        Compute the suitability score for a single node.
        """
        # Normalise latency and speed relative to the pool
        lat_norm = node.network_latency / max_latency if max_latency > 0 else 0
        speed_norm = node.processing_speed / max_speed if max_speed > 0 else 0

        score = (
            self.w_cpu      * (1.0 - node.cpu_utilization)
            + self.w_ram    * (1.0 - node.ram_utilization)
            + self.w_workload * (1.0 - node.workload_ratio)
            + self.w_latency  * (1.0 - lat_norm)        # Lower latency → higher score
            + self.w_speed    * speed_norm               # Higher speed → higher score
        )
        return score

    def assign(self, task, nodes):
        # Pre-compute normalisation constants across all nodes
        max_latency = max(n.network_latency for n in nodes) if nodes else 1
        max_speed = max(n.processing_speed for n in nodes) if nodes else 1

        best_node = None
        best_score = -1.0

        for node in nodes:
            # Skip nodes that cannot satisfy the task's resource requirements
            if not node.can_accept(task):
                continue

            score = self._compute_score(node, max_latency, max_speed)
            if score > best_score:
                best_score = score
                best_node = node

        return best_node  # None if no node can accept



# Factory function — handy for the simulation engine & dashboard


def create_balancer(algorithm_name: str, weights: dict = None) -> LoadBalancer:
    """
    Create a load-balancer instance by name.

    Parameters
    ----------
    algorithm_name : str
        "Round Robin", "Least Loaded", or "Adaptive".
    weights : dict, optional
        Custom weights for the Adaptive balancer.

    Returns
    -------
    LoadBalancer
    """
    name = algorithm_name.lower().strip()
    if name == "round robin":
        return RoundRobinBalancer()
    elif name == "least loaded":
        return LeastLoadedBalancer()
    elif name == "adaptive":
        return AdaptiveBalancer(weights=weights)
    else:
        raise ValueError(f"Unknown algorithm: {algorithm_name!r}. "
                         f"Choose from: 'Round Robin', 'Least Loaded', 'Adaptive'.")

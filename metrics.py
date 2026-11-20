"""
metrics.py — Performance Metrics Calculator
=============================================
Takes the list of completed tasks and node states from a simulation run
and computes every metric required for the academic evaluation.

All numbers are derived from actual simulation data — nothing is fabricated.

Metrics computed:
  1. Average response time
  2. Average execution time
  3. Total simulation time
  4. CPU utilisation per node (average over time)
  5. RAM utilisation per node (average over time)
  6. Task distribution across nodes
  7. Successful completion rate
  8. Rejected task count
  9. Failed task count
  10. Deadline miss rate
  11. Load imbalance (std-dev of tasks across nodes)
"""

import numpy as np
import pandas as pd
from task import TaskStatus


class MetricsCalculator:
    """
    Computes performance metrics from a completed simulation.

    Parameters
    ----------
    tasks : list[Task]
        All tasks (completed, failed, rejected, pending).
    nodes : list[Node]
        All infrastructure nodes after simulation.
    total_time : float
        Total simulation wall-clock time in seconds.
    algorithm_name : str
        Name of the algorithm used (for labelling results).
    """

    def __init__(self, tasks: list, nodes: list, total_time: float,
                 algorithm_name: str = ""):
        self.tasks = tasks
        self.nodes = nodes
        self.total_time = total_time
        self.algorithm_name = algorithm_name

    # ------------------------------------------------------------------
    # Individual metric methods
    # ------------------------------------------------------------------

    def avg_response_time(self) -> float:
        """
        Average time from task arrival to task completion.
        Only counts tasks that actually finished (COMPLETED or FAILED).
        """
        times = [t.response_time for t in self.tasks
                 if t.response_time is not None]
        return float(np.mean(times)) if times else 0.0

    def avg_execution_time(self) -> float:
        """
        Average time tasks spent actively executing on a VM.
        """
        times = [t.execution_time for t in self.tasks
                 if t.execution_time is not None]
        return float(np.mean(times)) if times else 0.0

    def total_execution_time(self) -> float:
        """Total simulated time the simulation ran."""
        return self.total_time

    def completed_count(self) -> int:
        return sum(1 for t in self.tasks if t.status == TaskStatus.COMPLETED)

    def failed_count(self) -> int:
        return sum(1 for t in self.tasks if t.status == TaskStatus.FAILED)

    def rejected_count(self) -> int:
        return sum(1 for t in self.tasks if t.status == TaskStatus.REJECTED)

    def pending_count(self) -> int:
        return sum(1 for t in self.tasks if t.status == TaskStatus.PENDING)

    def completion_rate(self) -> float:
        """Fraction of tasks that completed successfully."""
        total = len(self.tasks)
        if total == 0:
            return 0.0
        return self.completed_count() / total

    def deadline_miss_rate(self) -> float:
        """
        Fraction of tasks that missed their deadline.
        Includes both FAILED tasks (timed out) and COMPLETED tasks
        whose response time exceeded their deadline.
        """
        finished = [t for t in self.tasks if t.response_time is not None]
        if not finished:
            return 0.0
        missed = sum(1 for t in finished if t.missed_deadline)
        return missed / len(finished)

    def cpu_utilization_per_node(self) -> dict:
        """
        Average CPU utilisation for each node (from recorded history).
        Returns dict: {node_name: avg_utilization_percent}.
        """
        result = {}
        for node in self.nodes:
            if node.cpu_history:
                result[node.name] = round(float(np.mean(node.cpu_history)) * 100, 2)
            else:
                result[node.name] = 0.0
        return result

    def ram_utilization_per_node(self) -> dict:
        """Average RAM utilisation for each node."""
        result = {}
        for node in self.nodes:
            if node.ram_history:
                result[node.name] = round(float(np.mean(node.ram_history)) * 100, 2)
            else:
                result[node.name] = 0.0
        return result

    def task_distribution(self) -> dict:
        """Number of tasks assigned to each node."""
        dist = {node.name: 0 for node in self.nodes}
        dist["Rejected"] = 0
        for task in self.tasks:
            if task.assigned_node and task.assigned_node in dist:
                dist[task.assigned_node] += 1
            elif task.status == TaskStatus.REJECTED:
                dist["Rejected"] += 1
        return dist

    def load_imbalance(self) -> float:
        """
        Standard deviation of tasks assigned across nodes.
        Lower = more balanced distribution.
        """
        counts = [node.tasks_assigned for node in self.nodes]
        return float(np.std(counts)) if counts else 0.0

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def summary(self) -> dict:
        """
        Return all metrics as a single dictionary.
        Used by the dashboard and CSV export.
        """
        return {
            "algorithm": self.algorithm_name,
            "total_tasks": len(self.tasks),
            "completed": self.completed_count(),
            "failed": self.failed_count(),
            "rejected": self.rejected_count(),
            "pending": self.pending_count(),
            "completion_rate_pct": round(self.completion_rate() * 100, 2),
            "avg_response_time": round(self.avg_response_time(), 4),
            "avg_execution_time": round(self.avg_execution_time(), 4),
            "total_execution_time": round(self.total_execution_time(), 4),
            "deadline_miss_rate_pct": round(self.deadline_miss_rate() * 100, 2),
            "load_imbalance": round(self.load_imbalance(), 4),
            "cpu_utilization": self.cpu_utilization_per_node(),
            "ram_utilization": self.ram_utilization_per_node(),
            "task_distribution": self.task_distribution(),
        }

    def tasks_dataframe(self) -> pd.DataFrame:
        """
        Convert all tasks to a Pandas DataFrame for analysis and export.
        """
        return pd.DataFrame([t.to_dict() for t in self.tasks])

    def summary_dataframe(self) -> pd.DataFrame:
        """
        Return the summary as a single-row DataFrame (useful for
        comparing multiple algorithm runs side by side).
        """
        s = self.summary()
        # Flatten nested dicts for the dataframe
        flat = {k: v for k, v in s.items()
                if not isinstance(v, dict)}
        # Add per-node utilisation as separate columns
        for node_name, util in s["cpu_utilization"].items():
            flat[f"cpu_util_{node_name}"] = util
        for node_name, util in s["ram_utilization"].items():
            flat[f"ram_util_{node_name}"] = util
        for node_name, count in s["task_distribution"].items():
            flat[f"tasks_{node_name}"] = count
        return pd.DataFrame([flat])

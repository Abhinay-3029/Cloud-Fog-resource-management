"""
simulation.py — Discrete-Time Simulation Engine
=================================================
This is the core engine that ties everything together.

How the simulation works (step by step):
  1. Create infrastructure (fog nodes + cloud server).
  2. Generate tasks.
  3. Create a load-balancer instance.
  4. Run a time loop:
       a. Check which tasks have arrived by the current time.
       b. For each newly arrived task, ask the balancer to pick a node.
       c. If a node is found, assign the task to it.
       d. If no node can accept it, mark the task as REJECTED.
       e. Advance all nodes by one tick (VMs process their tasks).
       f. Check if all tasks are done → stop early.
  5. Compute and return metrics.

The engine is stateless between runs: call run() with an algorithm name,
and it creates fresh copies of everything internally.  This guarantees
fair comparisons.

Usage
-----
    from simulation import SimulationEngine
    engine = SimulationEngine(num_tasks=200, seed=42)
    result = engine.run("Adaptive")
    print(result["metrics"].summary())
"""

import copy
import time as wall_time
from nodes import FogNode, CloudServer
from task import Task, TaskStatus
from task_generator import TaskGenerator
from load_balancer import create_balancer
from metrics import MetricsCalculator
from config import (
    FOG_NODE_DEFAULTS, CLOUD_SERVER_DEFAULT,
    SIMULATION_DEFAULTS, TASK_DEFAULTS, ADAPTIVE_WEIGHTS,
)


class SimulationEngine:
    """
    Discrete-time simulator for Cloud-Fog task scheduling.

    Parameters
    ----------
    num_tasks : int
        Number of tasks to simulate.
    seed : int
        Random seed for reproducible task generation.
    time_step : float
        Seconds per simulation tick.
    max_time : float
        Hard stop for the simulation (seconds).
    fog_configs : list[dict]
        Custom fog node configurations (overrides defaults).
    cloud_config : dict
        Custom cloud server configuration (overrides default).
    task_config : dict
        Custom task generation parameters.
    adaptive_weights : dict
        Custom weights for the Adaptive algorithm.
    """

    def __init__(self, num_tasks: int = None, seed: int = None,
                 time_step: float = None, max_time: float = None,
                 fog_configs: list = None, cloud_config: dict = None,
                 task_config: dict = None, adaptive_weights: dict = None):
        self.num_tasks = num_tasks or TASK_DEFAULTS["num_tasks"]
        self.seed = seed if seed is not None else SIMULATION_DEFAULTS["random_seed"]
        self.time_step = time_step or SIMULATION_DEFAULTS["time_step"]
        self.max_time = max_time or SIMULATION_DEFAULTS["max_time"]
        self.fog_configs = fog_configs or FOG_NODE_DEFAULTS
        self.cloud_config = cloud_config or CLOUD_SERVER_DEFAULT
        self.task_config = task_config or {}
        self.adaptive_weights = adaptive_weights or ADAPTIVE_WEIGHTS

    # ------------------------------------------------------------------
    # Infrastructure creation
    # ------------------------------------------------------------------

    def _create_nodes(self):
        """Build fresh fog nodes and cloud server from configs."""
        nodes = []
        for cfg in self.fog_configs:
            nodes.append(FogNode(
                name=cfg["name"],
                cpu_capacity=cfg["cpu_capacity"],
                ram_capacity=cfg["ram_capacity"],
                processing_speed=cfg["processing_speed"],
                network_latency=cfg["network_latency"],
                num_vms=cfg.get("num_vms", 5),
            ))
        cloud_cfg = self.cloud_config
        nodes.append(CloudServer(
            name=cloud_cfg["name"],
            cpu_capacity=cloud_cfg["cpu_capacity"],
            ram_capacity=cloud_cfg["ram_capacity"],
            processing_speed=cloud_cfg["processing_speed"],
            network_latency=cloud_cfg["network_latency"],
            num_vms=cloud_cfg.get("num_vms", 5),
        ))
        return nodes

    def _create_tasks(self):
        """Generate a fresh set of tasks (deep copies for fair comparison)."""
        gen = TaskGenerator(
            seed=self.seed,
            **self.task_config,
        )
        return gen.generate(num_tasks=self.num_tasks)

    # ------------------------------------------------------------------
    # Main simulation loop
    # ------------------------------------------------------------------

    def run(self, algorithm_name: str, progress_callback=None) -> dict:
        """
        Execute the full simulation for the given algorithm.

        Parameters
        ----------
        algorithm_name : str
            "Round Robin", "Least Loaded", or "Adaptive".
        progress_callback : callable, optional
            Called each tick with (current_time, max_time, tasks)
            for Streamlit progress bars.

        Returns
        -------
        dict with keys:
            "tasks"     : list[Task]        — all tasks with final states
            "nodes"     : list[Node]        — all nodes with utilisation history
            "metrics"   : MetricsCalculator — ready-to-query metrics object
            "algorithm" : str               — name of the algorithm used
            "wall_time" : float             — real-world seconds the simulation took
        """
        # --- Setup ---
        nodes = self._create_nodes()
        tasks = self._create_tasks()
        balancer = create_balancer(algorithm_name, weights=self.adaptive_weights)

        current_time = 0.0
        task_index = 0            # Pointer into sorted task list
        total_tasks = len(tasks)
        active_tasks = 0          # Tasks currently running

        start_wall = wall_time.time()

        # --- Main loop ---
        while current_time <= self.max_time:
            # (a) Assign tasks that have arrived by this time
            while task_index < total_tasks:
                task = tasks[task_index]
                if task.arrival_time > current_time:
                    break  # This task hasn't arrived yet

                # Try to assign via the load balancer
                selected_node = balancer.assign(task, nodes)

                if selected_node is not None:
                    success = selected_node.assign_task(task, current_time)
                    if success:
                        # Add network latency to the effective start
                        # (simulates the delay of sending data to the node)
                        latency_offset = selected_node.network_latency / 1000.0
                        # We model latency as added to execution time
                        task.remaining_workload += (
                            latency_offset
                            * selected_node.processing_speed
                            * task.cpu_required * 100
                        )
                        active_tasks += 1
                    else:
                        # Node said it could accept but assign failed (race)
                        task.status = TaskStatus.REJECTED
                else:
                    # No node can handle this task
                    task.status = TaskStatus.REJECTED

                task_index += 1

            # (b) Advance all nodes by one tick
            for node in nodes:
                node.tick(self.time_step, current_time)

            # (c) Count active tasks
            active_tasks = sum(node.active_task_count for node in nodes)

            # (d) Check termination: all tasks processed and none running
            all_arrived = task_index >= total_tasks
            if all_arrived and active_tasks == 0:
                break

            # (e) Progress callback for UI
            if progress_callback:
                progress_callback(current_time, self.max_time, tasks)

            current_time = round(current_time + self.time_step, 4)

        # --- Post-processing ---
        end_wall = wall_time.time()

        # Update node task counts from actual task statuses
        for node in nodes:
            node.update_task_counts(tasks)

        # Mark any still-pending tasks as rejected (simulation ended)
        for task in tasks:
            if task.status == TaskStatus.PENDING:
                task.status = TaskStatus.REJECTED
            elif task.status == TaskStatus.RUNNING:
                task.end_time = current_time
                task.status = TaskStatus.FAILED

        # Compute metrics
        metrics = MetricsCalculator(
            tasks=tasks,
            nodes=nodes,
            total_time=current_time,
            algorithm_name=algorithm_name,
        )

        return {
            "tasks": tasks,
            "nodes": nodes,
            "metrics": metrics,
            "algorithm": algorithm_name,
            "wall_time": round(end_wall - start_wall, 4),
        }

    # ------------------------------------------------------------------
    # Compare all algorithms
    # ------------------------------------------------------------------

    def compare_all(self, algorithms: list = None,
                    progress_callback=None) -> list:
        """
        Run the simulation for each algorithm and return all results.

        Since each run creates fresh nodes and tasks, the comparison
        is fair — every algorithm sees the same workload.

        Parameters
        ----------
        algorithms : list[str]
            Algorithm names to compare. Defaults to all three.
        progress_callback : callable, optional
            Called with (algorithm_name, current_time, max_time, tasks).

        Returns
        -------
        list[dict]
            One result dict per algorithm (same structure as run()).
        """
        if algorithms is None:
            algorithms = ["Round Robin", "Least Loaded", "Adaptive"]

        results = []
        for algo in algorithms:
            result = self.run(algo, progress_callback=progress_callback)
            results.append(result)

        return results

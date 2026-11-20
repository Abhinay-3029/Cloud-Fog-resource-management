"""
task_generator.py — Generate Realistic Task Workloads
=====================================================
Creates a list of Task objects with randomised requirements drawn from
configurable ranges.

Key design choice: the generator accepts a *random seed* so that every
algorithm in a comparison run receives exactly the same set of tasks.
This makes performance comparisons fair.

Usage
-----
    from task_generator import TaskGenerator
    gen = TaskGenerator(seed=42)
    tasks = gen.generate(num_tasks=200)
"""

import numpy as np
from task import Task
from config import TASK_DEFAULTS


class TaskGenerator:
    """
    Generates a batch of randomised computational tasks.

    Parameters
    ----------
    seed : int
        Random seed for reproducibility.
    cpu_range : tuple (min, max)
        Range of CPU cores a task may require.
    ram_range : tuple (min, max)
        Range of RAM (GB) a task may require.
    workload_range : tuple (min, max)
        Range of Million Instructions (MI).
    deadline_range : tuple (min, max)
        Range of deadline in seconds.
    arrival_spread : float
        Tasks arrive uniformly in [0, arrival_spread] seconds.
    """

    def __init__(self, seed: int = None,
                 cpu_range: tuple = None,
                 ram_range: tuple = None,
                 workload_range: tuple = None,
                 deadline_range: tuple = None,
                 arrival_spread: float = None):
        # Use defaults from config if not provided
        self.seed = seed if seed is not None else TASK_DEFAULTS.get("random_seed", 42)
        self.cpu_range = cpu_range or TASK_DEFAULTS["cpu_range"]
        self.ram_range = ram_range or TASK_DEFAULTS["ram_range"]
        self.workload_range = workload_range or TASK_DEFAULTS["workload_range"]
        self.deadline_range = deadline_range or TASK_DEFAULTS["deadline_range"]
        self.arrival_spread = arrival_spread if arrival_spread is not None else TASK_DEFAULTS["arrival_spread"]

    def generate(self, num_tasks: int = None) -> list:
        """
        Generate a list of Task objects.

        Parameters
        ----------
        num_tasks : int
            Number of tasks to create (defaults to config value).

        Returns
        -------
        list[Task]
            Sorted by arrival_time so the simulation processes them in order.
        """
        if num_tasks is None:
            num_tasks = TASK_DEFAULTS["num_tasks"]

        # Create a local random number generator with the given seed.
        # This ensures the same tasks are generated every time, regardless
        # of what other code has done with the global random state.
        rng = np.random.default_rng(self.seed)

        tasks = []
        for i in range(num_tasks):
            cpu = rng.integers(self.cpu_range[0], self.cpu_range[1] + 1)
            ram = round(rng.uniform(self.ram_range[0], self.ram_range[1]), 2)
            workload = round(rng.uniform(self.workload_range[0], self.workload_range[1]), 1)
            deadline = round(rng.uniform(self.deadline_range[0], self.deadline_range[1]), 2)
            arrival = round(rng.uniform(0, self.arrival_spread), 3)

            task = Task(
                task_id=i + 1,
                cpu_required=cpu,
                ram_required=ram,
                workload=workload,
                deadline=deadline,
                arrival_time=arrival,
            )
            tasks.append(task)

        # Sort by arrival time so the simulation engine processes them in order
        tasks.sort(key=lambda t: t.arrival_time)
        return tasks

    def generate_preset(self, preset_name: str) -> list:
        """
        Generate tasks using a named preset from config.EXPERIMENT_PRESETS.

        Parameters
        ----------
        preset_name : str
            One of "low_workload", "medium_workload", "high_workload".

        Returns
        -------
        list[Task]
        """
        from config import EXPERIMENT_PRESETS
        preset = EXPERIMENT_PRESETS[preset_name]
        gen = TaskGenerator(
            seed=self.seed,
            cpu_range=preset["cpu_range"],
            ram_range=preset["ram_range"],
            workload_range=preset["workload_range"],
            deadline_range=preset["deadline_range"],
            arrival_spread=preset["arrival_spread"],
        )
        return gen.generate(num_tasks=preset["num_tasks"])

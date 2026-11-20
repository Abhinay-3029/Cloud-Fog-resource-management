"""
config.py — Default Simulation Configuration
=============================================
This module stores all configurable parameters for the Cloud-Fog simulation.
Faculty / reviewers: changing values here affects the entire simulation without
touching any algorithm code.

Sections
--------
1. Infrastructure defaults (fog nodes, cloud server)
2. Task generation parameters
3. Adaptive Load Balancer weights
4. Simulation engine settings
5. Experiment presets (low / medium / high workload)
"""

# ---------------------------------------------------------------------------
# 1. INFRASTRUCTURE DEFAULTS
# ---------------------------------------------------------------------------
# Each fog node is a small edge server.  The cloud server is more powerful but
# has higher network latency (data must travel to a remote data centre).

FOG_NODE_DEFAULTS = [
    {
        "name": "Fog-Node-1",
        "cpu_capacity": 8,          # Number of CPU cores
        "ram_capacity": 16,         # GB of RAM
        "processing_speed": 2.5,    # GHz — higher means tasks finish faster
        "network_latency": 5,       # ms — low because fog is near the user
        "num_vms": 5,               # Virtual machines hosted on this node
    },
    {
        "name": "Fog-Node-2",
        "cpu_capacity": 6,
        "ram_capacity": 12,
        "processing_speed": 2.0,
        "network_latency": 8,
        "num_vms": 5,
    },
    {
        "name": "Fog-Node-3",
        "cpu_capacity": 10,
        "ram_capacity": 20,
        "processing_speed": 3.0,
        "network_latency": 10,
        "num_vms": 5,
    },
]

CLOUD_SERVER_DEFAULT = {
    "name": "Cloud-Server",
    "cpu_capacity": 32,             # Cloud has much more power
    "ram_capacity": 64,
    "processing_speed": 3.5,
    "network_latency": 50,          # Higher latency — remote data centre
    "num_vms": 5,
}

# ---------------------------------------------------------------------------
# 2. TASK GENERATION PARAMETERS
# ---------------------------------------------------------------------------
# Tasks are generated randomly within these bounds.

TASK_DEFAULTS = {
    "num_tasks": 200,                # Default number of tasks to generate
    "cpu_range": (1, 4),             # Min–max CPU cores a task may need
    "ram_range": (0.5, 4.0),         # Min–max GB RAM a task may need
    "workload_range": (100, 1000),   # Million instructions (MI)
    "deadline_range": (5.0, 30.0),   # Seconds — time limit for the task
    "arrival_spread": 10.0,          # Tasks arrive within this many seconds
}

# ---------------------------------------------------------------------------
# 3. ADAPTIVE LOAD-BALANCER WEIGHTS
# ---------------------------------------------------------------------------
# These weights control how the Adaptive algorithm scores each node.
# They must sum to 1.0.  Increasing a weight makes that factor more important.
#
# Example: if you want to favour low-latency nodes, raise w_latency and
# reduce others proportionally.

ADAPTIVE_WEIGHTS = {
    "w_cpu": 0.30,          # Weight for available CPU
    "w_ram": 0.25,          # Weight for available RAM
    "w_workload": 0.20,     # Weight for current workload (fewer tasks → better)
    "w_latency": 0.15,      # Weight for network latency (lower → better)
    "w_speed": 0.10,        # Weight for processing speed (higher → better)
}

# ---------------------------------------------------------------------------
# 4. SIMULATION ENGINE SETTINGS
# ---------------------------------------------------------------------------

SIMULATION_DEFAULTS = {
    "time_step": 0.1,       # Seconds per simulation tick
    "max_time": 300.0,      # Maximum simulation duration in seconds
    "random_seed": 42,      # For reproducibility across algorithm comparisons
}

# ---------------------------------------------------------------------------
# 5. EXPERIMENT PRESETS
# ---------------------------------------------------------------------------
# Ready-made configurations for academic experiments.

EXPERIMENT_PRESETS = {
    "low_workload": {
        "num_tasks": 100,
        "cpu_range": (1, 2),
        "ram_range": (0.5, 2.0),
        "workload_range": (100, 500),
        "deadline_range": (10.0, 30.0),
        "arrival_spread": 15.0,
    },
    "medium_workload": {
        "num_tasks": 250,
        "cpu_range": (1, 4),
        "ram_range": (0.5, 4.0),
        "workload_range": (200, 800),
        "deadline_range": (5.0, 25.0),
        "arrival_spread": 10.0,
    },
    "high_workload": {
        "num_tasks": 500,
        "cpu_range": (2, 6),
        "ram_range": (1.0, 6.0),
        "workload_range": (500, 1500),
        "deadline_range": (3.0, 15.0),
        "arrival_spread": 5.0,
    },
}

# ---------------------------------------------------------------------------
# 6. AVAILABLE ALGORITHMS
# ---------------------------------------------------------------------------

ALGORITHMS = ["Round Robin", "Least Loaded", "Adaptive"]

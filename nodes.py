"""
nodes.py — Fog Node and Cloud Server Models
=============================================
This module defines the infrastructure layer: physical (simulated) machines
that host Virtual Machines.

Class hierarchy:
  Node (base)
    ├── FogNode    — edge server, low latency, limited capacity
    └── CloudServer — remote data-centre, high latency, large capacity

A Node:
  1. Owns a pool of VMs.
  2. Tracks aggregate CPU / RAM utilisation across all its VMs.
  3. Knows whether it can accept a new task (enough free resources).
  4. Delegates task execution to its VMs.

Design note: the base class is kept generic so that future extensions
(dynamic VM creation, VM migration) can be added without rewriting.
"""

from virtual_machine import VirtualMachine
from task import Task


class Node:
    """
    Base class for any computing node (fog or cloud).

    Parameters
    ----------
    name : str
        Human-readable identifier (e.g. "Fog-Node-1").
    cpu_capacity : float
        Total CPU cores on this physical machine.
    ram_capacity : float
        Total RAM (GB) on this physical machine.
    processing_speed : float
        Clock speed in GHz (shared by all VMs on this node).
    network_latency : float
        One-way network delay in milliseconds.
    num_vms : int
        Number of VMs to create on this node.
    node_type : str
        "fog" or "cloud" — used for display and future offloading logic.
    """

    def __init__(self, name: str, cpu_capacity: float, ram_capacity: float,
                 processing_speed: float, network_latency: float,
                 num_vms: int = 5, node_type: str = "fog"):
        self.name = name
        self.cpu_capacity = cpu_capacity
        self.ram_capacity = ram_capacity
        self.processing_speed = processing_speed
        self.network_latency = network_latency
        self.node_type = node_type

        # --- Create VMs ------------------------------------------------
        # Resources are divided equally among VMs.
        self.vms = []  # list of VirtualMachine objects
        cpu_per_vm = cpu_capacity / num_vms
        ram_per_vm = ram_capacity / num_vms
        for i in range(num_vms):
            vm = VirtualMachine(
                vm_id=i,
                cpu_allocated=cpu_per_vm,
                ram_allocated=ram_per_vm,
                processing_speed=processing_speed,
            )
            self.vms.append(vm)

        self._next_vm_id = num_vms
        self.initial_vm_count = num_vms
        self.orchestration_history = []

        # --- Bookkeeping -----------------------------------------------
        self.tasks_assigned = 0       # Total tasks ever assigned
        self.tasks_completed = 0      # Successfully finished
        self.tasks_failed = 0         # Deadline-missed or errored

        # Utilisation history (recorded each tick for graphing)
        self.cpu_history: list[float] = []
        self.ram_history: list[float] = []

    # ------------------------------------------------------------------
    # Aggregate resource queries
    # ------------------------------------------------------------------

    @property
    def cpu_used(self) -> float:
        """Sum of CPU used across all VMs."""
        return sum(vm.cpu_used for vm in self.vms)

    @property
    def ram_used(self) -> float:
        """Sum of RAM used across all VMs."""
        return sum(vm.ram_used for vm in self.vms)

    @property
    def cpu_available(self) -> float:
        return self.cpu_capacity - self.cpu_used

    @property
    def ram_available(self) -> float:
        return self.ram_capacity - self.ram_used

    @property
    def cpu_utilization(self) -> float:
        """Fraction 0.0 – 1.0."""
        if self.cpu_capacity == 0:
            return 0.0
        return self.cpu_used / self.cpu_capacity

    @property
    def ram_utilization(self) -> float:
        if self.ram_capacity == 0:
            return 0.0
        return self.ram_used / self.ram_capacity

    @property
    def active_task_count(self) -> int:
        """Number of tasks currently running on this node."""
        return sum(1 for vm in self.vms if not vm.is_idle)

    @property
    def total_vm_count(self) -> int:
        return len(self.vms)

    @property
    def idle_vm_count(self) -> int:
        return sum(1 for vm in self.vms if vm.is_idle)

    @property
    def workload_ratio(self) -> float:
        """Fraction of VMs currently busy (0.0 – 1.0)."""
        if self.total_vm_count == 0:
            return 1.0
        return self.active_task_count / self.total_vm_count

    @property
    def is_overloaded(self) -> bool:
        """True if all VMs are busy or resources are nearly exhausted."""
        return self.idle_vm_count == 0 or self.cpu_utilization > 0.95


    @property
    def allocated_cpu(self):
        return sum(vm.cpu_allocated for vm in self.vms)

    @property
    def allocated_ram(self):
        return sum(vm.ram_allocated for vm in self.vms)

    @property
    def unallocated_cpu(self):
        return max(0.0, self.cpu_capacity - self.allocated_cpu)

    @property
    def unallocated_ram(self):
        return max(0.0, self.ram_capacity - self.allocated_ram)

    def create_vm(self, cpu, ram, dynamic=True):
        """Create a VM using unallocated host resources or by splitting one idle VM."""
        cpu, ram = float(cpu), float(ram)
        donor = None
        if self.unallocated_cpu + 1e-9 < cpu or self.unallocated_ram + 1e-9 < ram:
            donor = next((vm for vm in self.vms if vm.is_idle
                          and vm.cpu_allocated - cpu >= 0.25
                          and vm.ram_allocated - ram >= 0.25), None)
            if donor is None:
                return None
            donor.cpu_allocated -= cpu
            donor.ram_allocated -= ram
        vm = VirtualMachine(self._next_vm_id, cpu, ram, self.processing_speed)
        vm.is_dynamic = dynamic
        self._next_vm_id += 1
        self.vms.append(vm)
        return vm

    def scale_vm(self, vm, new_cpu, new_ram):
        """Resize a VM, borrowing from an idle donor or releasing host capacity."""
        if vm not in self.vms:
            return False
        new_cpu, new_ram = float(new_cpu), float(new_ram)
        delta_cpu = new_cpu - vm.cpu_allocated
        delta_ram = new_ram - vm.ram_allocated
        if delta_cpu > 0 or delta_ram > 0:
            donor = next((other for other in self.vms if other is not vm and other.is_idle
                          and other.cpu_allocated - max(delta_cpu, 0) >= 0.25
                          and other.ram_allocated - max(delta_ram, 0) >= 0.25), None)
            if self.unallocated_cpu + 1e-9 < max(delta_cpu, 0) or self.unallocated_ram + 1e-9 < max(delta_ram, 0):
                if donor is None:
                    return False
                donor.cpu_allocated -= max(delta_cpu, 0)
                donor.ram_allocated -= max(delta_ram, 0)
        try:
            vm.scale_resources(new_cpu, new_ram)
        except ValueError:
            return False
        return True

    def remove_vm(self, vm):
        """Terminate an idle VM and release its allocation to the host."""
        if vm not in self.vms or not vm.is_idle or len(self.vms) <= 1:
            return False
        self.vms.remove(vm)
        return True

    def migrate_vm_to(self, vm, target_node):
        """Migrate a VM (including an active task) to another node."""
        if vm not in self.vms or target_node is self:
            return False
        target_donor = next((other for other in target_node.vms if other.is_idle
                             and other.cpu_allocated - vm.cpu_allocated >= 0.25
                             and other.ram_allocated - vm.ram_allocated >= 0.25), None)
        if (target_node.unallocated_cpu + 1e-9 < vm.cpu_allocated or
                target_node.unallocated_ram + 1e-9 < vm.ram_allocated):
            if target_donor is None:
                return False
            target_donor.cpu_allocated -= vm.cpu_allocated
            target_donor.ram_allocated -= vm.ram_allocated
        self.vms.remove(vm)
        vm.vm_id = target_node._next_vm_id
        target_node._next_vm_id += 1
        vm.processing_speed = target_node.processing_speed
        vm.migration_count += 1
        target_node.vms.append(vm)
        if vm.current_task is not None:
            vm.current_task.assigned_node = target_node.name
            vm.current_task.assigned_vm_id = vm.vm_id
        return True

    # ------------------------------------------------------------------
    # Task operations
    # ------------------------------------------------------------------

    def can_accept(self, task: Task) -> bool:
        """
        Check if *any* VM on this node can run the given task.
        """
        for vm in self.vms:
            if vm.can_accept(task):
                return True
        return False

    def assign_task(self, task: Task, current_time: float) -> bool:
        """
        Assign *task* to the first idle VM that can handle it.

        Returns True on success, False if no VM is available.
        """
        for vm in self.vms:
            if vm.can_accept(task):
                success = vm.assign_task(task, current_time)
                if success:
                    task.assigned_node = self.name
                    self.tasks_assigned += 1
                    return True
        return False

    def tick(self, time_step: float, current_time: float):
        """
        Advance all VMs by one simulation tick.

        Records utilisation snapshots for later analysis.
        """
        for vm in self.vms:
            finished = vm.execute_tick(time_step, current_time)
            if finished:
                task = vm.current_task  # already released by execute_tick
                # The task's status was set inside execute_tick
                # We just update our counters here
                pass

        # Count completed/failed tasks from VMs that just finished
        # (We read task status from the task objects themselves in metrics)

        # Record utilisation snapshot
        self.cpu_history.append(self.cpu_utilization)
        self.ram_history.append(self.ram_utilization)

    def update_task_counts(self, tasks: list):
        """
        Recount completed and failed tasks assigned to this node.
        Called at the end of simulation for accurate final numbers.
        """
        self.tasks_completed = sum(
            1 for t in tasks
            if t.assigned_node == self.name and t.status == "COMPLETED"
        )
        self.tasks_failed = sum(
            1 for t in tasks
            if t.assigned_node == self.name and t.status == "FAILED"
        )

    # ------------------------------------------------------------------
    # Reset (for running multiple algorithms on the same infrastructure)
    # ------------------------------------------------------------------

    def reset(self):
        """
        Clear all state so the node can be reused for another algorithm run.
        """
        for vm in self.vms:
            vm.cpu_used = 0.0
            vm.ram_used = 0.0
            vm.current_task = None
        self.tasks_assigned = 0
        self.tasks_completed = 0
        self.tasks_failed = 0
        self.cpu_history.clear()
        self.ram_history.clear()

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------

    def to_dict(self):
        """Summary dictionary for dashboard display."""
        return {
            "name": self.name,
            "type": self.node_type,
            "cpu_capacity": self.cpu_capacity,
            "ram_capacity": self.ram_capacity,
            "cpu_used": round(self.cpu_used, 2),
            "ram_used": round(self.ram_used, 2),
            "cpu_utilization": round(self.cpu_utilization * 100, 1),
            "ram_utilization": round(self.ram_utilization * 100, 1),
            "processing_speed": self.processing_speed,
            "network_latency": self.network_latency,
            "total_vms": self.total_vm_count,
            "idle_vms": self.idle_vm_count,
            "tasks_assigned": self.tasks_assigned,
            "tasks_completed": self.tasks_completed,
            "tasks_failed": self.tasks_failed,
            "is_overloaded": self.is_overloaded,
            "initial_vms": self.initial_vm_count,
            "dynamic_vms": sum(1 for vm in self.vms if vm.is_dynamic),
            "unallocated_cpu": round(self.unallocated_cpu, 2),
            "unallocated_ram": round(self.unallocated_ram, 2),
        }

    def __repr__(self):
        return (f"Node({self.name}, CPU={self.cpu_used:.1f}/{self.cpu_capacity}, "
                f"RAM={self.ram_used:.1f}/{self.ram_capacity}, "
                f"VMs busy={self.active_task_count}/{self.total_vm_count})")


# ======================================================================
# Concrete subclasses
# ======================================================================

class FogNode(Node):
    """
    Edge / fog node — close to users, limited resources.
    Inherits everything from Node; exists for type clarity.
    """
    def __init__(self, **kwargs):
        super().__init__(node_type="fog", **kwargs)


class CloudServer(Node):
    """
    Central cloud server — powerful but high latency.
    Inherits everything from Node; exists for type clarity and future
    cloud-specific features (e.g. auto-scaling, pay-per-use cost model).
    """
    def __init__(self, **kwargs):
        super().__init__(node_type="cloud", **kwargs)

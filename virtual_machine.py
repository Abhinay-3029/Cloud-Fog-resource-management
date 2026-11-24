"""
virtual_machine.py — Virtual Machine Model
============================================
A Virtual Machine (VM) is the smallest execution unit.  Each node hosts
several VMs.  A task runs inside exactly one VM.

VM responsibilities:
  - Track its own CPU / RAM allocation from the parent node.
  - Accept a task if it has enough free resources.
  - Simulate task execution by decrementing remaining workload each tick.
  - Release resources when a task finishes or fails.

Future extension hooks (not active yet):
  - migrate_to(target_node)   — VM live migration
  - scale_resources(cpu, ram) — vertical scaling
"""

from task import Task, TaskStatus


class VirtualMachine:
    """
    Represents a single VM hosted on a Node.

    Parameters
    ----------
    vm_id : int
        Unique VM identifier.
    cpu_allocated : float
        CPU cores allocated to this VM by its parent node.
    ram_allocated : float
        RAM (GB) allocated to this VM by its parent node.
    processing_speed : float
        GHz — inherited from the parent node.
    """

    def __init__(self, vm_id: int, cpu_allocated: float,
                 ram_allocated: float, processing_speed: float):
        self.vm_id = vm_id
        self.cpu_allocated = cpu_allocated      # Total CPU this VM can use
        self.ram_allocated = ram_allocated      # Total RAM this VM can use
        self.processing_speed = processing_speed
        self.is_dynamic = False
        self.migration_count = 0
        self.scale_count = 0

        # Current resource usage
        self.cpu_used = 0.0
        self.ram_used = 0.0

        # The task currently running on this VM (None if idle)
        self.current_task = None  

    
    # Resource queries
    

    @property
    def cpu_available(self):
        """Free CPU cores."""
        return self.cpu_allocated - self.cpu_used

    @property
    def ram_available(self):
        """Free RAM in GB."""
        return self.ram_allocated - self.ram_used

    @property
    def is_idle(self):
        """True when no task is running on this VM."""
        return self.current_task is None

    @property
    def cpu_utilization(self):
        """CPU usage as a fraction (0.0 – 1.0)."""
        if self.cpu_allocated == 0:
            return 0.0
        return self.cpu_used / self.cpu_allocated

    @property
    def ram_utilization(self):
        """RAM usage as a fraction (0.0 – 1.0)."""
        if self.ram_allocated == 0:
            return 0.0
        return self.ram_used / self.ram_allocated


    # Task lifecycle
    

    def can_accept(self, task: Task) -> bool:
        """
        Check whether this VM has enough free resources for *task*.
        """
        return (self.is_idle
                and self.cpu_available >= task.cpu_required
                and self.ram_available >= task.ram_required)

    def assign_task(self, task: Task, current_time: float) -> bool:
        """
        Start executing *task* on this VM.

        Returns True on success, False if the VM cannot accept it.
        """
        if not self.can_accept(task):
            return False

        # Reserve resources
        self.cpu_used += task.cpu_required
        self.ram_used += task.ram_required
        self.current_task = task

        # Update task state
        task.status = TaskStatus.RUNNING
        task.start_time = current_time
        task.assigned_vm_id = self.vm_id

        return True

    def execute_tick(self, time_step: float, current_time: float) -> bool:
        """
        Simulate one time step of execution.

        Each tick, the VM processes some MI based on its speed:
            work_done = processing_speed (GHz) × cpu_allocated_to_task × time_step × 1000
        (The ×1000 converts GHz·s to MI — a simplification for the simulation.)

        Returns
        -------
        True  if the task finished during this tick.
        False if the task is still running (or no task is loaded).
        """
        if self.current_task is None:
            return False

        task = self.current_task

        # Calculate work done this tick
        # processing_speed is in GHz; workload is in MI
        # 1 GHz core can do ~1000 MI per second (simplified model)
        work_this_tick = (self.processing_speed * task.cpu_required
                         * time_step * 100)  # scale factor for simulation
        task.remaining_workload -= work_this_tick

        # Check completion
        if task.remaining_workload <= 0:
            task.remaining_workload = 0
            task.end_time = current_time
            task.status = TaskStatus.COMPLETED
            self._release_task()
            return True

        # Check deadline
        elapsed = current_time - task.arrival_time
        if elapsed > task.deadline:
            task.end_time = current_time
            task.status = TaskStatus.FAILED
            self._release_task()
            return True

        return False

    def _release_task(self):
        """Free the resources held by the current task."""
        if self.current_task is not None:
            self.cpu_used -= self.current_task.cpu_required
            self.ram_used -= self.current_task.ram_required
            # Clamp to zero to avoid floating-point drift
            self.cpu_used = max(0.0, self.cpu_used)
            self.ram_used = max(0.0, self.ram_used)
            self.current_task = None

    
    # Future extension stubs
    

    def migrate_to(self, source_node, target_node):
        """Move this VM to target_node while preserving its running task."""
        return source_node.migrate_vm_to(self, target_node)

    def scale_resources(self, new_cpu: float, new_ram: float):
        """Apply a resource allocation validated by the host node."""
        if new_cpu <= 0 or new_ram <= 0:
            raise ValueError("VM CPU and RAM allocations must be positive.")
        if new_cpu < self.cpu_used or new_ram < self.ram_used:
            raise ValueError("Cannot scale below resources currently used by a task.")
        self.cpu_allocated = float(new_cpu)
        self.ram_allocated = float(new_ram)
        self.scale_count += 1
        return True

    
    # Representation
    

    def __repr__(self):
        status = "IDLE" if self.is_idle else f"Running Task {self.current_task.task_id}"
        return (f"VM(id={self.vm_id}, cpu={self.cpu_available:.1f}/"
                f"{self.cpu_allocated:.1f}, ram={self.ram_available:.1f}/"
                f"{self.ram_allocated:.1f}, {status})")

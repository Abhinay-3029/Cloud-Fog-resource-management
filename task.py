"""
task.py — Task Data Model
==========================
Represents a computational task submitted by a user to the Cloud-Fog system.

Each task carries:
  - Resource requirements (CPU cores, RAM in GB).
  - A computational workload measured in Million Instructions (MI).
  - A deadline by which the task should complete.
  - An arrival time (when the task enters the system).
  - Runtime bookkeeping: start time, end time, assigned node, status.

Status lifecycle:
  PENDING → RUNNING → COMPLETED
                    → FAILED (deadline missed or error)
  PENDING → REJECTED (no node has enough resources)
"""


class TaskStatus:
    """
    Simple string constants for task status.
    Using a class instead of an Enum keeps things beginner-friendly.
    """
    PENDING = "PENDING"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REJECTED = "REJECTED"


class Task:
    """
    Represents a single user task to be processed.

    Attributes
    ----------
    task_id : int
        Unique identifier.
    cpu_required : float
        Number of CPU cores this task needs.
    ram_required : float
        RAM in GB this task needs.
    workload : float
        Million Instructions (MI) — the amount of computation.
    deadline : float
        Maximum allowed time (seconds) from arrival to completion.
    arrival_time : float
        Simulated time (seconds) when this task enters the system.
    status : str
        Current lifecycle state (see TaskStatus).
    assigned_node : str or None
        Name of the node this task was assigned to.
    assigned_vm_id : int or None
        ID of the VM executing this task.
    start_time : float or None
        Simulated time when execution began.
    end_time : float or None
        Simulated time when execution finished.
    """

    def __init__(self, task_id: int, cpu_required: float, ram_required: float,
                 workload: float, deadline: float, arrival_time: float):
        # --- Identification ---
        self.task_id = task_id

        # --- Resource requirements ---
        self.cpu_required = cpu_required    # CPU cores
        self.ram_required = ram_required    # GB
        self.workload = workload            # Million Instructions

        # --- Timing ---
        self.deadline = deadline            # seconds allowed
        self.arrival_time = arrival_time    # simulated arrival second

        # --- Runtime state (filled during simulation) ---
        self.status = TaskStatus.PENDING
        self.assigned_node = None
        self.assigned_vm_id = None
        self.start_time = None
        self.end_time = None
        self.queue_entered_at = None
        self.rejection_reason = None

        # Remaining work — decremented during execution
        self.remaining_workload = workload

    
    # Computed properties
    

    @property
    def response_time(self):
        """
        Total time from arrival to completion (or failure).
        Returns None if the task hasn't finished yet.
        """
        if self.end_time is not None:
            return self.end_time - self.arrival_time
        return None

    @property
    def execution_time(self):
        """
        Time the task actually spent executing on a VM.
        Returns None if the task hasn't started or finished.
        """
        if self.start_time is not None and self.end_time is not None:
            return self.end_time - self.start_time
        return None

    @property
    def waiting_time(self):
        """
        Time the task waited before execution started.
        """
        if self.start_time is not None:
            return self.start_time - self.arrival_time
        return None

    @property
    def missed_deadline(self):
        """
        True if the task finished (or is still running) past its deadline.
        """
        if self.end_time is not None:
            return (self.end_time - self.arrival_time) > self.deadline
        return False

    
    # Helpers
    

    def to_dict(self):
        """Convert to dictionary for easy export to Pandas / CSV."""
        return {
            "task_id": self.task_id,
            "cpu_required": self.cpu_required,
            "ram_required": self.ram_required,
            "workload": self.workload,
            "deadline": self.deadline,
            "arrival_time": round(self.arrival_time, 3),
            "status": self.status,
            "assigned_node": self.assigned_node,
            "assigned_vm_id": self.assigned_vm_id,
            "waiting_time": round(self.waiting_time, 3) if self.waiting_time is not None else None,
            "rejection_reason": self.rejection_reason,
            "start_time": round(self.start_time, 3) if self.start_time else None,
            "end_time": round(self.end_time, 3) if self.end_time else None,
            "response_time": round(self.response_time, 3) if self.response_time else None,
            "execution_time": round(self.execution_time, 3) if self.execution_time else None,
            "missed_deadline": self.missed_deadline,
        }

    def __repr__(self):
        return (f"Task(id={self.task_id}, cpu={self.cpu_required}, "
                f"ram={self.ram_required}, MI={self.workload}, "
                f"status={self.status})")

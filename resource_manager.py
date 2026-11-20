"""Resource management for queued task scheduling and bottleneck monitoring.

The manager keeps tasks that cannot start immediately in a FIFO queue. It
retries them as VMs release resources and expires tasks that miss deadlines.
"""

from task import TaskStatus


class ResourceManager:
    def __init__(self):
        self.waiting_queue = []
        self.queue_history = []
        self.bottleneck_events = []
        self.queued_total = 0
        self.peak_queue_length = 0

    @staticmethod
    def can_ever_fit(task, nodes):
        """Return False only when no VM's configured capacity can fit the task."""
        return any(
            any(vm.cpu_allocated >= task.cpu_required and
                vm.ram_allocated >= task.ram_required for vm in node.vms)
            for node in nodes
        )

    def enqueue(self, task, current_time):
        if task.status != TaskStatus.QUEUED:
            task.status = TaskStatus.QUEUED
            task.queue_entered_at = current_time
            self.queued_total += 1
        if task not in self.waiting_queue:
            self.waiting_queue.append(task)
        self.peak_queue_length = max(self.peak_queue_length, len(self.waiting_queue))

    def record_snapshot(self, current_time, nodes):
        self.queue_history.append({
            "time": round(current_time, 3),
            "queue_length": len(self.waiting_queue),
        })
        for node in nodes:
            if node.cpu_utilization >= 0.80 or node.ram_utilization >= 0.80 or node.idle_vm_count == 0:
                self.bottleneck_events.append({
                    "time": round(current_time, 3),
                    "node": node.name,
                    "cpu_utilization_pct": round(node.cpu_utilization * 100, 1),
                    "ram_utilization_pct": round(node.ram_utilization * 100, 1),
                    "busy_vms": node.active_task_count,
                    "total_vms": node.total_vm_count,
                })

    def expire_overdue(self, current_time):
        remaining = []
        expired = []
        for task in self.waiting_queue:
            if current_time - task.arrival_time > task.deadline:
                task.status = TaskStatus.FAILED
                task.end_time = current_time
                task.rejection_reason = "Deadline expired while waiting for resources"
                expired.append(task)
            else:
                remaining.append(task)
        self.waiting_queue = remaining
        return expired

    def summary(self):
        return {
            "queued_total": self.queued_total,
            "peak_queue_length": self.peak_queue_length,
            "remaining_queue_length": len(self.waiting_queue),
            "bottleneck_event_count": len(self.bottleneck_events),
        }

"""Policy-driven dynamic VM orchestration for the Cloud-Fog simulator."""


class VMOrchestrator:
    """Create, terminate, scale and migrate VMs using simulation-time policies.

    The model reallocates the fixed CPU/RAM capacity of each simulated host;
    it does not launch operating-system or hypervisor VMs.
    """

    def __init__(self, action_interval=2.0, queue_scale_threshold=2,
                 high_load_threshold=0.40, low_load_threshold=0.20):
        self.action_interval = float(action_interval)
        self.queue_scale_threshold = int(queue_scale_threshold)
        self.high_load_threshold = float(high_load_threshold)
        self.low_load_threshold = float(low_load_threshold)
        self.last_action_time = -self.action_interval
        self.events = []
        self.counts = {"created": 0, "terminated": 0, "scaled_up": 0,
                       "scaled_down": 0, "migrated": 0}

    def _record(self, now, action, node, vm=None, details=""):
        event = {"time": round(now, 2), "action": action,
                 "node": node.name, "vm_id": getattr(vm, "vm_id", None),
                 "details": details}
        self.events.append(event)
        key = {"create": "created", "terminate": "terminated",
               "scale_up": "scaled_up", "scale_down": "scaled_down",
               "migrate": "migrated"}[action]
        self.counts[key] += 1

    def _try_migrate(self, now, nodes):
        overloaded = sorted(
            [n for n in nodes if n.workload_ratio >= self.high_load_threshold],
            key=lambda n: n.workload_ratio, reverse=True)
        targets = sorted(nodes, key=lambda n: n.cpu_utilization + n.ram_utilization)
        for source in overloaded:
            for target in targets:
                if target is source or target.workload_ratio >= source.workload_ratio:
                    continue
                candidates = [vm for vm in source.vms if not vm.is_idle]
                if not candidates:
                    continue
                vm = max(candidates, key=lambda v: v.cpu_allocated + v.ram_allocated)
                if source.migrate_vm_to(vm, target):
                    self._record(now, "migrate", target, vm,
                                 f"Migrated from {source.name}; active task preserved")
                    return True
        return False

    def step(self, now, nodes, waiting_queue):
        """Apply at most one orchestration action per interval."""
        if now - self.last_action_time < self.action_interval:
            return
        queue_len = len(waiting_queue)

        # Demand rising: add a small VM by reallocating an idle VM's spare share.
        if queue_len >= self.queue_scale_threshold:
            candidates = sorted(nodes, key=lambda n: (n.workload_ratio, n.cpu_utilization), reverse=True)
            if self._try_migrate(now, nodes):
                self.last_action_time = now
                return
            # Demonstrate vertical scaling as a complementary response after
            # the first horizontal scale-out, when an idle donor can spare capacity.
            if self.counts["created"] >= 1 and self.counts["scaled_up"] == 0:
                for node in candidates:
                    busy = [v for v in node.vms if not v.is_idle]
                    for vm in busy:
                        new_cpu = vm.cpu_allocated + 0.5
                        new_ram = vm.ram_allocated + 0.5
                        if node.scale_vm(vm, new_cpu, new_ram):
                            self._record(now, "scale_up", node, vm,
                                         f"Increased allocation to {new_cpu:.2f} CPU / {new_ram:.2f} GB RAM")
                            self.last_action_time = now
                            return
            for node in candidates:
                dynamic_count = sum(1 for v in node.vms if v.is_dynamic)
                donor = next((v for v in node.vms if v.is_idle and
                              v.cpu_allocated >= 0.75 and v.ram_allocated >= 0.75), None)
                if donor and dynamic_count < 2:
                    cpu = min(0.5, donor.cpu_allocated - 0.25)
                    ram = min(1.0, donor.ram_allocated - 0.25)
                    vm = node.create_vm(cpu, ram)
                    if vm:
                        self._record(now, "create", node, vm,
                                     f"New VM allocated {cpu:.2f} CPU / {ram:.2f} GB RAM")
                        self.last_action_time = now
                        return
            if self._try_migrate(now, nodes):
                self.last_action_time = now
                return
            # If no extra VM can be carved out, vertically scale a busy VM
            # using CPU/RAM donated by an idle VM on the same host.
            for node in candidates:
                busy = [v for v in node.vms if not v.is_idle]
                for vm in sorted(busy, key=lambda v: v.cpu_used + v.ram_used, reverse=True):
                    new_cpu = vm.cpu_allocated + 0.5
                    new_ram = vm.ram_allocated + 0.5
                    if node.scale_vm(vm, new_cpu, new_ram):
                        self._record(now, "scale_up", node, vm,
                                     f"Increased allocation to {new_cpu:.2f} CPU / {new_ram:.2f} GB RAM")
                        self.last_action_time = now
                        return

        # Low demand: terminate surplus dynamic idle VMs first.
        if queue_len == 0 and now >= 5.0:
            for node in sorted(nodes, key=lambda n: n.cpu_utilization + n.ram_utilization):
                surplus = next((v for v in node.vms if v.is_dynamic and v.is_idle), None)
                if surplus and node.workload_ratio <= self.low_load_threshold:
                    vm_id = surplus.vm_id
                    if node.remove_vm(surplus):
                        self._record(now, "terminate", node, None,
                                     f"Terminated idle dynamic VM {vm_id}")
                        self.last_action_time = now
                        return

            # Consolidate idle capacity by scaling down an oversized idle VM.
            for node in nodes:
                idle = [v for v in node.vms if v.is_idle and
                        (v.cpu_allocated > 0.75 or v.ram_allocated > 1.0)]
                if len(idle) >= max(2, node.total_vm_count // 2):
                    vm = max(idle, key=lambda v: v.cpu_allocated + v.ram_allocated)
                    new_cpu = max(0.5, vm.cpu_allocated * 0.9)
                    new_ram = max(0.5, vm.ram_allocated * 0.9)
                    if node.scale_vm(vm, new_cpu, new_ram):
                        self._record(now, "scale_down", node, vm,
                                     f"Reduced allocation to {new_cpu:.2f} CPU / {new_ram:.2f} GB RAM")
                        self.last_action_time = now
                        return
        self.last_action_time = now

    def finalize(self, now, nodes):
        """Terminate idle dynamic VMs after the workload has drained."""
        for node in nodes:
            for vm in list(node.vms):
                if vm.is_dynamic and vm.is_idle and node.remove_vm(vm):
                    self._record(now, "terminate", node, None,
                                 f"Terminated idle dynamic VM {vm.vm_id} after workload drained")
            # Right-size one idle VM after demand has drained, returning the
            # released CPU/RAM to the host's unallocated resource pool.
            idle_initial = [v for v in node.vms if v.is_idle and not v.is_dynamic]
            if idle_initial:
                vm = max(idle_initial, key=lambda v: v.cpu_allocated + v.ram_allocated)
                new_cpu = max(0.5, vm.cpu_allocated * 0.9)
                new_ram = max(0.5, vm.ram_allocated * 0.9)
                if (new_cpu < vm.cpu_allocated or new_ram < vm.ram_allocated) and node.scale_vm(vm, new_cpu, new_ram):
                    self._record(now, "scale_down", node, vm,
                                 f"Reduced allocation to {new_cpu:.2f} CPU / {new_ram:.2f} GB RAM after workload drained")

    def summary(self):
        return {**self.counts, "total_events": len(self.events)}

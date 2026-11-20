# Cloud-Fog Resource Management Simulation

A Python + Streamlit simulation of a cloud-fog infrastructure with task scheduling, load balancing, resource monitoring, and queued task management.

## Implemented modules

1. **Cloud-Fog Infrastructure** — fog nodes, a cloud server, simulated VMs, and task execution.
2. **Intelligent Load Balancing** — Round Robin, Least Loaded, and Adaptive scheduling.
3. **Resource Management** — FIFO waiting queue, automatic retry when VM capacity becomes available, deadline expiry while waiting, queue-length history, and CPU/RAM/VM bottleneck monitoring.

Dynamic VM orchestration (VM creation, termination, scaling, and migration) remains the next implementation stage.

## Run the dashboard

```bash
pip install -r requirements.txt
streamlit run dashboard.py
```

## Run command-line experiments

```bash
python main.py --compare --tasks 200 --seed 42
python main.py --compare --tasks 200 --seed 42 --save
```

> This project is a software simulation. It models VMs and cloud/fog resources in Python; it does not create real hypervisor-managed virtual machines or cloud instances.


## Module 4 — Dynamic VM Orchestration

The simulator includes a policy-driven `VMOrchestrator` that reacts to waiting-queue pressure and workload changes. It supports:

- **Horizontal scaling:** create additional simulated VMs by reallocating host CPU/RAM from idle VM allocations.
- **Vertical scaling:** increase or decrease a VM's CPU/RAM allocation while respecting resources currently in use.
- **VM migration:** move a VM, including its active task state, to another node when the target has capacity.
- **Scale-in / termination:** terminate idle dynamically-created VMs after demand drains and return their capacity to the host pool.
- **Event monitoring:** record creation, termination, scaling and migration events for the Streamlit dashboard.

Run a high-workload experiment to observe orchestration actions:

```bash
python main.py --experiment high_workload --algorithm Adaptive
python -m streamlit run dashboard.py
```

In the dashboard, run a single simulation and open the **VM Orchestration** tab to inspect the VM inventory, action counters and event log. The project models VMs in Python; it does not create operating-system VMs or invoke a real hypervisor.

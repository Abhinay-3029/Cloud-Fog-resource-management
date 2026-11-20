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

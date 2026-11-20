"""
dashboard.py — Streamlit Dashboard
====================================
Professional, interactive web dashboard for the Cloud-Fog simulation.

Sections:
  1. Sidebar     — Simulation controls (tasks, nodes, algorithm, weights)
  2. Overview    — Key metrics cards
  3. Infrastructure — Node status visualisation
  4. Results     — Charts and tables for a single algorithm run
  5. Comparison  — Side-by-side comparison of all three algorithms
  6. Export      — Download results as CSV

Launch with:
    streamlit run dashboard.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import json
import copy

from simulation import SimulationEngine
from config import (
    FOG_NODE_DEFAULTS, CLOUD_SERVER_DEFAULT,
    TASK_DEFAULTS, ADAPTIVE_WEIGHTS, ALGORITHMS,
    SIMULATION_DEFAULTS, EXPERIMENT_PRESETS,
)


# ======================================================================
# Page Configuration
# ======================================================================

st.set_page_config(
    page_title="Cloud-Fog Resource Manager",
    page_icon="☁️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for a modern look
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 12px;
        color: white;
        text-align: center;
        margin: 5px;
    }
    .metric-card h3 {
        margin: 0;
        font-size: 14px;
        opacity: 0.9;
    }
    .metric-card h1 {
        margin: 5px 0 0 0;
        font-size: 32px;
    }
    .node-card {
        border: 2px solid #e0e0e0;
        border-radius: 10px;
        padding: 15px;
        margin: 5px 0;
    }
    .node-card.overloaded {
        border-color: #ff4444;
        background-color: #fff5f5;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 10px 20px;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)


# ======================================================================
# Session State Initialisation
# ======================================================================

if "simulation_results" not in st.session_state:
    st.session_state.simulation_results = None
if "comparison_results" not in st.session_state:
    st.session_state.comparison_results = None
if "run_count" not in st.session_state:
    st.session_state.run_count = 0


# ======================================================================
# Sidebar — Simulation Controls
# ======================================================================

with st.sidebar:
    st.title("⚙️ Simulation Controls")

    st.markdown("---")

    # --- Experiment Preset ---
    st.subheader("Quick Presets")
    preset = st.selectbox(
        "Load Experiment Preset",
        ["Custom"] + list(EXPERIMENT_PRESETS.keys()),
        help="Pre-configured workload scenarios for experiments"
    )

    st.markdown("---")

    # --- Task Configuration ---
    st.subheader("📋 Task Configuration")

    if preset != "Custom":
        p = EXPERIMENT_PRESETS[preset]
        num_tasks = st.slider("Number of Tasks", 50, 500, p["num_tasks"])
        cpu_min, cpu_max = p["cpu_range"]
        ram_min, ram_max = p["ram_range"]
        wl_min, wl_max = p["workload_range"]
        dl_min, dl_max = p["deadline_range"]
        arrival_spread = p["arrival_spread"]
    else:
        num_tasks = st.slider("Number of Tasks", 50, 500,
                              TASK_DEFAULTS["num_tasks"])
        cpu_min, cpu_max = TASK_DEFAULTS["cpu_range"]
        ram_min, ram_max = TASK_DEFAULTS["ram_range"]
        wl_min, wl_max = TASK_DEFAULTS["workload_range"]
        dl_min, dl_max = TASK_DEFAULTS["deadline_range"]
        arrival_spread = TASK_DEFAULTS["arrival_spread"]

    with st.expander("Advanced Task Settings"):
        cpu_min = st.number_input("Min CPU Cores", 1, 8, int(cpu_min))
        cpu_max = st.number_input("Max CPU Cores", 1, 8, int(cpu_max))
        ram_min = st.number_input("Min RAM (GB)", 0.5, 8.0,
                                  float(ram_min), step=0.5)
        ram_max = st.number_input("Max RAM (GB)", 0.5, 8.0,
                                  float(ram_max), step=0.5)
        arrival_spread = st.number_input("Arrival Spread (s)", 1.0, 30.0,
                                         float(arrival_spread), step=1.0)

    st.markdown("---")

    # --- Node Configuration ---
    st.subheader("🖥️ Node Configuration")

    with st.expander("Fog Node Settings"):
        fog_configs = []
        for i, default in enumerate(FOG_NODE_DEFAULTS):
            st.markdown(f"**{default['name']}**")
            cpu = st.slider(f"CPU Cores (Node {i+1})", 2, 16,
                            default["cpu_capacity"], key=f"fog_cpu_{i}")
            ram = st.slider(f"RAM GB (Node {i+1})", 4, 32,
                            default["ram_capacity"], key=f"fog_ram_{i}")
            speed = st.slider(f"Speed GHz (Node {i+1})", 1.0, 5.0,
                              default["processing_speed"], 0.5,
                              key=f"fog_speed_{i}")
            latency = st.slider(f"Latency ms (Node {i+1})", 1, 50,
                                default["network_latency"],
                                key=f"fog_lat_{i}")
            fog_configs.append({
                "name": default["name"],
                "cpu_capacity": cpu,
                "ram_capacity": ram,
                "processing_speed": speed,
                "network_latency": latency,
                "num_vms": 5,
            })

    with st.expander("Cloud Server Settings"):
        cloud_cpu = st.slider("Cloud CPU Cores", 8, 64,
                              CLOUD_SERVER_DEFAULT["cpu_capacity"])
        cloud_ram = st.slider("Cloud RAM GB", 16, 128,
                              CLOUD_SERVER_DEFAULT["ram_capacity"])
        cloud_speed = st.slider("Cloud Speed GHz", 1.0, 5.0,
                                CLOUD_SERVER_DEFAULT["processing_speed"], 0.5)
        cloud_latency = st.slider("Cloud Latency ms", 10, 200,
                                  CLOUD_SERVER_DEFAULT["network_latency"])
        cloud_config = {
            "name": "Cloud-Server",
            "cpu_capacity": cloud_cpu,
            "ram_capacity": cloud_ram,
            "processing_speed": cloud_speed,
            "network_latency": cloud_latency,
            "num_vms": 5,
        }

    st.markdown("---")

    # --- Algorithm Selection ---
    st.subheader("🧠 Algorithm")
    selected_algo = st.selectbox("Choose Algorithm", ALGORITHMS)

    # --- Adaptive Weights ---
    if selected_algo == "Adaptive":
        with st.expander("Adaptive Weights"):
            w_cpu = st.slider("CPU Weight", 0.0, 1.0,
                              ADAPTIVE_WEIGHTS["w_cpu"], 0.05)
            w_ram = st.slider("RAM Weight", 0.0, 1.0,
                              ADAPTIVE_WEIGHTS["w_ram"], 0.05)
            w_workload = st.slider("Workload Weight", 0.0, 1.0,
                                   ADAPTIVE_WEIGHTS["w_workload"], 0.05)
            w_latency = st.slider("Latency Weight", 0.0, 1.0,
                                  ADAPTIVE_WEIGHTS["w_latency"], 0.05)
            w_speed = st.slider("Speed Weight", 0.0, 1.0,
                                ADAPTIVE_WEIGHTS["w_speed"], 0.05)
            total_w = w_cpu + w_ram + w_workload + w_latency + w_speed
            if abs(total_w - 1.0) > 0.01:
                st.warning(f"Weights sum to {total_w:.2f} (should be 1.0)")
            adaptive_weights = {
                "w_cpu": w_cpu, "w_ram": w_ram,
                "w_workload": w_workload, "w_latency": w_latency,
                "w_speed": w_speed,
            }
    else:
        adaptive_weights = ADAPTIVE_WEIGHTS

    st.markdown("---")

    # --- Seed ---
    seed = st.number_input("Random Seed", 1, 9999,
                           SIMULATION_DEFAULTS["random_seed"])

    st.markdown("---")

    # --- Run Buttons ---
    col1, col2 = st.columns(2)
    with col1:
        run_single = st.button("▶️ Run", use_container_width=True,
                               type="primary")
    with col2:
        run_compare = st.button("📊 Compare All", use_container_width=True)

    reset_btn = st.button("🔄 Reset", use_container_width=True)

    if reset_btn:
        st.session_state.simulation_results = None
        st.session_state.comparison_results = None
        st.session_state.run_count = 0
        st.rerun()


# ======================================================================
# Build Engine with current settings
# ======================================================================

task_config = {
    "cpu_range": (cpu_min, cpu_max),
    "ram_range": (ram_min, ram_max),
    "workload_range": (wl_min, wl_max),
    "deadline_range": (dl_min, dl_max),
    "arrival_spread": arrival_spread,
}

engine = SimulationEngine(
    num_tasks=num_tasks,
    seed=seed,
    fog_configs=fog_configs,
    cloud_config=cloud_config,
    task_config=task_config,
    adaptive_weights=adaptive_weights,
)


# ======================================================================
# Run Simulation
# ======================================================================

if run_single:
    with st.spinner(f"Running {selected_algo} simulation with {num_tasks} tasks..."):
        result = engine.run(selected_algo)
        st.session_state.simulation_results = result
        st.session_state.run_count += 1

if run_compare:
    with st.spinner("Running all three algorithms for comparison..."):
        results = engine.compare_all()
        st.session_state.comparison_results = results
        st.session_state.run_count += 1


# ======================================================================
# Title
# ======================================================================

st.title("☁️ Cloud-Fog Resource Management")
st.markdown("**Load Balancing & VM Orchestration Dashboard**")
st.markdown("---")


# ======================================================================
# TABS
# ======================================================================

tab_overview, tab_infra, tab_results, tab_compare, tab_export = st.tabs([
    "📊 Overview", "🖥️ Infrastructure", "📈 Results",
    "🔬 Comparison", "💾 Export"
])


# ======================================================================
# TAB 1: Overview
# ======================================================================

with tab_overview:
    if st.session_state.simulation_results is None and st.session_state.comparison_results is None:
        st.info("👈 Configure parameters in the sidebar and click **Run** or **Compare All** to start.")

        # Show infrastructure summary even before running
        st.subheader("Infrastructure Summary")
        infra_data = []
        for cfg in fog_configs:
            infra_data.append({
                "Node": cfg["name"],
                "Type": "🌫️ Fog",
                "CPU": f"{cfg['cpu_capacity']} cores",
                "RAM": f"{cfg['ram_capacity']} GB",
                "Speed": f"{cfg['processing_speed']} GHz",
                "Latency": f"{cfg['network_latency']} ms",
                "VMs": cfg["num_vms"],
            })
        infra_data.append({
            "Node": cloud_config["name"],
            "Type": "☁️ Cloud",
            "CPU": f"{cloud_config['cpu_capacity']} cores",
            "RAM": f"{cloud_config['ram_capacity']} GB",
            "Speed": f"{cloud_config['processing_speed']} GHz",
            "Latency": f"{cloud_config['network_latency']} ms",
            "VMs": cloud_config["num_vms"],
        })
        st.table(pd.DataFrame(infra_data))

    else:
        # Show results from most recent single run
        result = st.session_state.simulation_results
        if result:
            s = result["metrics"].summary()

            # Metric cards
            c1, c2, c3, c4, c5 = st.columns(5)
            with c1:
                st.metric("Total Tasks", s["total_tasks"])
            with c2:
                st.metric("✅ Completed", s["completed"])
            with c3:
                st.metric("❌ Failed", s["failed"])
            with c4:
                st.metric("🚫 Rejected", s["rejected"])
            with c5:
                st.metric("⏱️ Avg Response", f"{s['avg_response_time']:.3f}s")

            c6, c7, c8, c9, c10 = st.columns(5)
            resource_summary = result["resource_manager"].summary()
            with c6:
                st.metric("Completion Rate", f"{s['completion_rate_pct']}%")
            with c7:
                st.metric("Deadline Miss", f"{s['deadline_miss_rate_pct']}%")
            with c8:
                st.metric("Peak Waiting Queue", resource_summary["peak_queue_length"])
            with c9:
                st.metric("Algorithm", s["algorithm"])
            with c10:
                st.metric("Load Imbalance", f"{s['load_imbalance']:.2f}")

        elif st.session_state.comparison_results:
            st.success("✅ Comparison complete! See the **Comparison** tab for details.")


# ======================================================================
# TAB 2: Infrastructure
# ======================================================================

with tab_infra:
    result = st.session_state.simulation_results

    if result is None:
        st.info("Run a simulation to see infrastructure status.")
    else:
        nodes = result["nodes"]

        st.subheader("Node Status")
        cols = st.columns(len(nodes))

        for i, node in enumerate(nodes):
            nd = node.to_dict()
            with cols[i]:
                icon = "☁️" if nd["type"] == "cloud" else "🌫️"
                status_color = "🔴" if nd["is_overloaded"] else "🟢"

                st.markdown(f"### {icon} {nd['name']} {status_color}")
                st.markdown(f"**Type:** {nd['type'].title()}")
                st.markdown(f"**CPU:** {nd['cpu_used']}/{nd['cpu_capacity']} cores "
                            f"({nd['cpu_utilization']}%)")
                st.markdown(f"**RAM:** {nd['ram_used']}/{nd['ram_capacity']} GB "
                            f"({nd['ram_utilization']}%)")
                st.markdown(f"**VMs:** {nd['total_vms'] - nd['idle_vms']}"
                            f"/{nd['total_vms']} busy")
                st.markdown(f"**Tasks:** {nd['tasks_assigned']} assigned, "
                            f"{nd['tasks_completed']} done")
                st.markdown(f"**Latency:** {node.network_latency} ms")

                # Mini utilisation gauge
                fig = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=nd["cpu_utilization"],
                    title={"text": "CPU %"},
                    gauge={
                        "axis": {"range": [0, 100]},
                        "bar": {"color": "#667eea"},
                        "steps": [
                            {"range": [0, 50], "color": "#e8f5e9"},
                            {"range": [50, 80], "color": "#fff3e0"},
                            {"range": [80, 100], "color": "#ffebee"},
                        ],
                    },
                ))
                fig.update_layout(height=200, margin=dict(t=40, b=0, l=20, r=20))
                st.plotly_chart(fig, use_container_width=True,
                               key=f"cpu_gauge_node_{i}")

        # Task allocation pie chart
        st.subheader("Task Allocation Across Nodes")
        s = result["metrics"].summary()
        dist = s["task_distribution"]
        fig = px.pie(
            names=list(dist.keys()),
            values=list(dist.values()),
            title="Task Distribution",
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        fig.update_traces(textposition="inside", textinfo="value+percent")
        st.plotly_chart(fig, use_container_width=True)

        # CPU utilisation over time
        st.subheader("CPU Utilisation Over Time")
        fig = go.Figure()
        for node in nodes:
            if node.cpu_history:
                time_points = [i * engine.time_step
                               for i in range(len(node.cpu_history))]
                fig.add_trace(go.Scatter(
                    x=time_points,
                    y=[u * 100 for u in node.cpu_history],
                    name=node.name,
                    mode="lines",
                ))
        fig.update_layout(
            xaxis_title="Time (s)", yaxis_title="CPU Utilisation (%)",
            yaxis=dict(range=[0, 105]),
            height=400,
        )
        st.plotly_chart(fig, use_container_width=True)

        # RAM utilisation over time
        st.subheader("RAM Utilisation Over Time")
        fig = go.Figure()
        for node in nodes:
            if node.ram_history:
                time_points = [i * engine.time_step
                               for i in range(len(node.ram_history))]
                fig.add_trace(go.Scatter(
                    x=time_points,
                    y=[u * 100 for u in node.ram_history],
                    name=node.name,
                    mode="lines",
                ))
        fig.update_layout(
            xaxis_title="Time (s)", yaxis_title="RAM Utilisation (%)",
            yaxis=dict(range=[0, 105]),
            height=400,
        )
        st.plotly_chart(fig, use_container_width=True)


# ======================================================================
# TAB 3: Results
# ======================================================================

with tab_results:
    result = st.session_state.simulation_results

    if result is None:
        st.info("Run a simulation to see detailed results.")
    else:
        s = result["metrics"].summary()

        # Task status breakdown
        st.subheader("Task Status Breakdown")
        status_data = {
            "Completed": s["completed"],
            "Failed": s["failed"],
            "Rejected": s["rejected"],
        }
        fig = px.bar(
            x=list(status_data.keys()),
            y=list(status_data.values()),
            color=list(status_data.keys()),
            color_discrete_map={
                "Completed": "#4caf50",
                "Failed": "#ff9800",
                "Rejected": "#f44336",
            },
            title="Task Outcomes",
        )
        fig.update_layout(showlegend=False, xaxis_title="", yaxis_title="Count")
        st.plotly_chart(fig, use_container_width=True)

        # Module 3: Resource queue and bottleneck monitoring
        st.markdown("---")
        st.subheader("Resource Management Monitor")
        resource_manager = result["resource_manager"]
        resource_summary = resource_manager.summary()
        q1, q2, q3 = st.columns(3)
        q1.metric("Tasks that entered queue", resource_summary["queued_total"])
        q2.metric("Peak queue length", resource_summary["peak_queue_length"])
        q3.metric("Bottleneck samples", resource_summary["bottleneck_event_count"])

        queue_df = pd.DataFrame(resource_manager.queue_history)
        if not queue_df.empty:
            queue_fig = px.area(
                queue_df, x="time", y="queue_length",
                title="Waiting Queue Length Over Simulation Time",
            )
            queue_fig.update_layout(xaxis_title="Simulation Time (s)",
                                    yaxis_title="Queued Tasks")
            st.plotly_chart(queue_fig, use_container_width=True)

        bottleneck_df = pd.DataFrame(resource_manager.bottleneck_events)
        if not bottleneck_df.empty:
            st.markdown("**Detected resource bottlenecks (CPU/RAM ≥ 80% or all VMs busy)**")
            st.dataframe(bottleneck_df, use_container_width=True, height=220)
        else:
            st.success("No resource bottlenecks detected during this run.")

        # Task timeline
        st.subheader("Task Execution Timeline")
        df = result["metrics"].tasks_dataframe()
        completed_df = df[df["status"] == "COMPLETED"].head(50)
        if not completed_df.empty:
            fig = px.timeline(
                completed_df.assign(
                    Start=pd.to_datetime(completed_df["start_time"], unit="s",
                                         origin="unix"),
                    Finish=pd.to_datetime(completed_df["end_time"], unit="s",
                                          origin="unix"),
                    Task=completed_df["task_id"].astype(str),
                ),
                x_start="Start", x_end="Finish",
                y="assigned_node", color="assigned_node",
                title="First 50 Completed Tasks — Gantt Chart",
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No completed tasks to show in timeline.")

        # Response time distribution
        st.subheader("Response Time Distribution")
        response_times = df[df["response_time"].notna()]["response_time"]
        if not response_times.empty:
            fig = px.histogram(
                response_times, nbins=30,
                title="Response Time Distribution",
                labels={"value": "Response Time (s)", "count": "Tasks"},
                color_discrete_sequence=["#667eea"],
            )
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        # Detailed task table
        st.subheader("Task Details")
        st.dataframe(df, use_container_width=True, height=400)


# ======================================================================
# TAB 4: Comparison
# ======================================================================

with tab_compare:
    results = st.session_state.comparison_results

    if results is None:
        st.info("Click **Compare All** in the sidebar to compare algorithms.")
    else:
        st.subheader("Algorithm Comparison")

        # Build comparison table
        summaries = []
        for r in results:
            summaries.append(r["metrics"].summary())

        comp_df = pd.DataFrame([{
            "Algorithm": s["algorithm"],
            "Completed": s["completed"],
            "Failed": s["failed"],
            "Rejected": s["rejected"],
            "Completion Rate (%)": s["completion_rate_pct"],
            "Avg Response Time (s)": s["avg_response_time"],
            "Avg Execution Time (s)": s["avg_execution_time"],
            "Deadline Miss Rate (%)": s["deadline_miss_rate_pct"],
            "Load Imbalance": s["load_imbalance"],
        } for s in summaries])

        st.dataframe(comp_df, use_container_width=True, hide_index=True)

        st.markdown("---")

        # --- Comparison Charts ---
        col1, col2 = st.columns(2)

        with col1:
            # Average response time comparison
            fig = px.bar(
                comp_df, x="Algorithm", y="Avg Response Time (s)",
                color="Algorithm",
                title="Average Response Time Comparison",
                color_discrete_sequence=["#ff6b6b", "#feca57", "#48dbfb"],
            )
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Completion rate comparison
            fig = px.bar(
                comp_df, x="Algorithm", y="Completion Rate (%)",
                color="Algorithm",
                title="Completion Rate Comparison",
                color_discrete_sequence=["#ff6b6b", "#feca57", "#48dbfb"],
            )
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        # Task distribution comparison
        st.subheader("Task Distribution Comparison")
        dist_data = []
        for s in summaries:
            for node_name, count in s["task_distribution"].items():
                dist_data.append({
                    "Algorithm": s["algorithm"],
                    "Node": node_name,
                    "Tasks": count,
                })
        dist_df = pd.DataFrame(dist_data)
        fig = px.bar(
            dist_df, x="Node", y="Tasks", color="Algorithm",
            barmode="group",
            title="Task Distribution Across Nodes",
            color_discrete_sequence=["#ff6b6b", "#feca57", "#48dbfb"],
        )
        st.plotly_chart(fig, use_container_width=True)

        # CPU utilisation comparison
        st.subheader("CPU Utilisation Comparison")
        cpu_data = []
        for s in summaries:
            for node_name, util in s["cpu_utilization"].items():
                cpu_data.append({
                    "Algorithm": s["algorithm"],
                    "Node": node_name,
                    "CPU Utilisation (%)": util,
                })
        cpu_df = pd.DataFrame(cpu_data)
        fig = px.bar(
            cpu_df, x="Node", y="CPU Utilisation (%)", color="Algorithm",
            barmode="group",
            title="Average CPU Utilisation per Node",
            color_discrete_sequence=["#ff6b6b", "#feca57", "#48dbfb"],
        )
        st.plotly_chart(fig, use_container_width=True)

        # RAM utilisation comparison
        st.subheader("RAM Utilisation Comparison")
        ram_data = []
        for s in summaries:
            for node_name, util in s["ram_utilization"].items():
                ram_data.append({
                    "Algorithm": s["algorithm"],
                    "Node": node_name,
                    "RAM Utilisation (%)": util,
                })
        ram_df = pd.DataFrame(ram_data)
        fig = px.bar(
            ram_df, x="Node", y="RAM Utilisation (%)", color="Algorithm",
            barmode="group",
            title="Average RAM Utilisation per Node",
            color_discrete_sequence=["#ff6b6b", "#feca57", "#48dbfb"],
        )
        st.plotly_chart(fig, use_container_width=True)

        # Deadline miss rate comparison
        st.subheader("Deadline Miss Rate")
        fig = px.bar(
            comp_df, x="Algorithm", y="Deadline Miss Rate (%)",
            color="Algorithm",
            title="Deadline Miss Rate Comparison",
            color_discrete_sequence=["#ff6b6b", "#feca57", "#48dbfb"],
        )
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)


# ======================================================================
# TAB 5: Export
# ======================================================================

with tab_export:
    st.subheader("💾 Export Results")

    if st.session_state.simulation_results is None and st.session_state.comparison_results is None:
        st.info("Run a simulation first to export results.")
    else:
        # Single run export
        if st.session_state.simulation_results:
            result = st.session_state.simulation_results
            st.markdown("### Single Run Results")

            df = result["metrics"].tasks_dataframe()
            csv = df.to_csv(index=False)
            st.download_button(
                "📥 Download Task Details (CSV)",
                csv, "task_results.csv", "text/csv",
                use_container_width=True,
            )

            summary_df = result["metrics"].summary_dataframe()
            csv2 = summary_df.to_csv(index=False)
            st.download_button(
                "📥 Download Summary (CSV)",
                csv2, "summary.csv", "text/csv",
                use_container_width=True,
            )

        # Comparison export
        if st.session_state.comparison_results:
            results = st.session_state.comparison_results
            st.markdown("### Comparison Results")

            all_summaries = pd.concat(
                [r["metrics"].summary_dataframe() for r in results],
                ignore_index=True,
            )
            csv3 = all_summaries.to_csv(index=False)
            st.download_button(
                "📥 Download Comparison Summary (CSV)",
                csv3, "comparison_summary.csv", "text/csv",
                use_container_width=True,
            )

            for r in results:
                algo = r["algorithm"].lower().replace(" ", "_")
                df = r["metrics"].tasks_dataframe()
                csv_data = df.to_csv(index=False)
                st.download_button(
                    f"📥 Download {r['algorithm']} Tasks (CSV)",
                    csv_data, f"tasks_{algo}.csv", "text/csv",
                    use_container_width=True,
                    key=f"dl_{algo}",
                )

        # Save to results/ directory
        st.markdown("---")
        if st.button("💾 Save All to results/ folder", use_container_width=True):
            os.makedirs("results", exist_ok=True)

            if st.session_state.simulation_results:
                r = st.session_state.simulation_results
                df = r["metrics"].tasks_dataframe()
                df.to_csv("results/latest_tasks.csv", index=False)
                r["metrics"].summary_dataframe().to_csv(
                    "results/latest_summary.csv", index=False
                )

            if st.session_state.comparison_results:
                all_sum = pd.concat(
                    [r["metrics"].summary_dataframe()
                     for r in st.session_state.comparison_results],
                    ignore_index=True,
                )
                all_sum.to_csv("results/comparison_summary.csv", index=False)

                for r in st.session_state.comparison_results:
                    algo = r["algorithm"].lower().replace(" ", "_")
                    r["metrics"].tasks_dataframe().to_csv(
                        f"results/tasks_{algo}.csv", index=False
                    )

            st.success("✅ Results saved to the results/ folder!")


# ======================================================================
# Footer
# ======================================================================

st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #888; font-size: 12px;'>"
    "Cloud-Fog Resource Management Simulator — B.Tech Major Project"
    "</div>",
    unsafe_allow_html=True,
)

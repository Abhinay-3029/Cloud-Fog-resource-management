
import os
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from simulation import SimulationEngine
from config import (
    FOG_NODE_DEFAULTS, CLOUD_SERVER_DEFAULT,
    TASK_DEFAULTS, ADAPTIVE_WEIGHTS, ALGORITHMS,
    SIMULATION_DEFAULTS, EXPERIMENT_PRESETS,
)


# Page Configuration


st.set_page_config(
    page_title="Cloud-Fog Resource Management Simulator",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# 3 Color Palettes (Default matches .streamlit/config.toml)


PALETTES = {
    "Teal Slate (Light)": {
        "bg_app": "#F4F6F9",
        "bg_card": "#FFFFFF",
        "bg_muted": "#E9EEF4",
        "text_primary": "#0F1F33",
        "text_secondary": "#4B5E75",
        "border": "#D4DEE9",
        "primary": "#14877F",
        "secondary": "#0284C7",
        "success": "#0D9488",
        "warning": "#D97706",
        "danger": "#DC2626",
        "chart_seq": ["#14877F", "#0284C7", "#0F1F33", "#0EA5E9", "#10B981"],
        "algo_colors": ["#64748B", "#0284C7", "#14877F"],
        "plotly_template": "plotly_white",
    },
    "Obsidian Graphite (Dark)": {
        "bg_app": "#0B0F17",
        "bg_card": "#131A26",
        "bg_muted": "#1C2536",
        "text_primary": "#F1F5F9",
        "text_secondary": "#94A3B8",
        "border": "#263244",
        "primary": "#2DD4BF",
        "secondary": "#60A5FA",
        "success": "#34D399",
        "warning": "#FBBF24",
        "danger": "#F87171",
        "chart_seq": ["#2DD4BF", "#60A5FA", "#A78BFA", "#34D399", "#FBBF24"],
        "algo_colors": ["#64748B", "#60A5FA", "#2DD4BF"],
        "plotly_template": "plotly_dark",
    },
    "Ivory & Cobalt (Light)": {
        "bg_app": "#F7F5F0",
        "bg_card": "#FFFFFF",
        "bg_muted": "#EDE9E0",
        "text_primary": "#18181B",
        "text_secondary": "#52525B",
        "border": "#DFD9CE",
        "primary": "#1D4ED8",
        "secondary": "#0F766E",
        "success": "#15803D",
        "warning": "#B45309",
        "danger": "#B91C1C",
        "chart_seq": ["#1D4ED8", "#0F766E", "#4338CA", "#0369A1", "#B45309"],
        "algo_colors": ["#71717A", "#0F766E", "#1D4ED8"],
        "plotly_template": "plotly_white",
    },
}

# 
# Session State Initialisation
# 

if "simulation_results" not in st.session_state:
    st.session_state.simulation_results = None
if "comparison_results" not in st.session_state:
    st.session_state.comparison_results = None
if "run_count" not in st.session_state:
    st.session_state.run_count = 0
if "active_module" not in st.session_state:
    st.session_state.active_module = "Cluster & Node Matrix"

# 
# Top Brand Ribbon + Live Theme Switcher
# 

hdr_left, hdr_right = st.columns([3.4, 1.1])
with hdr_right:
    selected_theme = st.selectbox(
        "Color Palette",
        list(PALETTES.keys()),
        index=0,
        label_visibility="collapsed",
    )

T = PALETTES[selected_theme]

# 
# Global CSS Styling
# 

st.markdown(f"""
<style>
    /* Hide default sidebar toggle clutter for full-canvas command center */
    [data-testid="collapsedControl"] {{ display: none; }}
    section[data-testid="stSidebar"] {{ display: none; }}

    .stApp {{
        background-color: {T['bg_app']};
        color: {T['text_primary']};
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }}
    header[data-testid="stHeader"] {{
        background-color: {T['bg_app']};
    }}
    .block-container {{
        padding-top: 1.4rem;
        padding-bottom: 2rem;
        max-width: 1480px;
    }}
    h1, h2, h3, h4, p, label, span {{
        color: {T['text_primary']};
    }}

    /* Buttons */
    button[kind="primary"] {{
        background-color: {T['primary']} !important;
        border: 1px solid {T['primary']} !important;
        color: #FFFFFF !important;
        font-weight: 600 !important;
        border-radius: 6px !important;
    }}
    button[kind="primary"] p {{
        color: #FFFFFF !important;
    }}
    button[kind="secondary"] {{
        background-color: {T['bg_card']} !important;
        border: 1px solid {T['border']} !important;
        color: {T['text_primary']} !important;
        font-weight: 600 !important;
        border-radius: 6px !important;
    }}
    button[kind="secondary"] p {{
        color: {T['text_primary']} !important;
    }}

    /* Brand Header */
    .brand-banner {{
        display: flex;
        align-items: center;
        gap: 14px;
        padding: 4px 0 8px 0;
    }}
    .brand-bar {{
        width: 5px;
        height: 38px;
        background-color: {T['primary']};
        border-radius: 3px;
    }}
    .brand-name {{
        font-size: 22px;
        font-weight: 700;
        letter-spacing: -0.02em;
        margin: 0;
        color: {T['text_primary']} !important;
    }}
    .brand-desc {{
        font-size: 12px;
        color: {T['text_secondary']} !important;
        margin: 2px 0 0 0;
    }}

    /* Bento KPI Cards */
    .bento-kpi {{
        background-color: {T['bg_card']};
        border: 1px solid {T['border']};
        border-top: 3px solid {T['primary']};
        border-radius: 8px;
        padding: 14px 16px;
        height: 100%;
    }}
    .bento-kpi.ok   {{ border-top-color: {T['success']}; }}
    .bento-kpi.warn {{ border-top-color: {T['warning']}; }}
    .bento-kpi.err  {{ border-top-color: {T['danger']}; }}
    .kpi-head {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 6px;
    }}
    .kpi-lbl {{
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: {T['text_secondary']} !important;
    }}
    .kpi-pill {{
        font-size: 10px;
        font-weight: 700;
        padding: 2px 6px;
        border-radius: 4px;
        background-color: {T['bg_muted']};
        color: {T['text_secondary']} !important;
    }}
    .kpi-val {{
        font-size: 25px;
        font-weight: 700;
        font-variant-numeric: tabular-nums;
        color: {T['text_primary']} !important;
        line-height: 1.15;
    }}
    .kpi-sub {{
        font-size: 11px;
        color: {T['text_secondary']} !important;
        margin-top: 5px;
    }}

    /* Left Rail Card & Live Node Bars */
    .rail-card {{
        background-color: {T['bg_card']};
        border: 1px solid {T['border']};
        border-radius: 8px;
        padding: 14px;
        margin-bottom: 12px;
    }}
    .rail-title {{
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: {T['text_secondary']} !important;
        border-bottom: 1px solid {T['border']};
        padding-bottom: 8px;
        margin-bottom: 10px;
    }}
    .mini-node {{
        padding: 8px 10px;
        background-color: {T['bg_app']};
        border: 1px solid {T['border']};
        border-radius: 6px;
        margin-bottom: 8px;
    }}
    .mini-node-top {{
        display: flex;
        justify-content: space-between;
        font-size: 12px;
        font-weight: 700;
        color: {T['text_primary']} !important;
    }}
    .mini-node-sub {{
        display: flex;
        justify-content: space-between;
        font-size: 11px;
        color: {T['text_secondary']} !important;
        margin-top: 3px;
    }}
    .bar-bg {{
        width: 100%;
        height: 5px;
        background-color: {T['border']};
        border-radius: 3px;
        margin: 5px 0;
        overflow: hidden;
    }}
    .bar-fg {{
        height: 100%;
        border-radius: 3px;
    }}

    /* Node Detail Grid Cards */
    .hw-card {{
        background-color: {T['bg_card']};
        border: 1px solid {T['border']};
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 10px;
    }}
    .hw-header {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid {T['border']};
        padding-bottom: 8px;
        margin-bottom: 10px;
    }}
    .hw-name {{
        font-size: 15px;
        font-weight: 700;
        color: {T['text_primary']} !important;
    }}
    .tag-nominal {{
        font-size: 10px;
        font-weight: 700;
        padding: 2px 8px;
        border-radius: 4px;
        background-color: rgba(16, 185, 129, 0.14);
        color: {T['success']} !important;
    }}
    .tag-overload {{
        font-size: 10px;
        font-weight: 700;
        padding: 2px 8px;
        border-radius: 4px;
        background-color: rgba(239, 68, 68, 0.14);
        color: {T['danger']} !important;
    }}
    .hw-row {{
        display: flex;
        justify-content: space-between;
        font-size: 12px;
        padding: 3px 0;
        color: {T['text_secondary']} !important;
    }}
    .hw-val {{
        font-weight: 600;
        color: {T['text_primary']} !important;
        font-variant-numeric: tabular-nums;
    }}

    /* Workspace Stage Container */
    .stage-header {{
        font-size: 16px;
        font-weight: 700;
        color: {T['text_primary']} !important;
        margin-bottom: 12px;
        padding-bottom: 8px;
        border-bottom: 1px solid {T['border']};
    }}
</style>
""", unsafe_allow_html=True)

with hdr_left:
    st.markdown("""
    <div class="brand-banner">
        <div class="brand-bar"></div>
        <div>
            <h1 class="brand-name">Cloud-Fog Resource Management Simulator</h1>
            <p class="brand-desc">Adaptive Load Balancing, Bottleneck Telemetry & Dynamic VM Orchestration</p>
        </div>
    </div>
    """, unsafe_allow_html=True)


def style_fig(fig, height=340):
    fig.update_layout(
        template=T["plotly_template"],
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=height,
        margin=dict(t=42, b=24, l=16, r=16),
        font=dict(family="Inter, sans-serif", color=T["text_primary"], size=12),
        title_font=dict(size=14, color=T["text_primary"]),
    )
    return fig


# 
# ZONE 1: Top Horizontal Control Dock
# 

with st.container(border=True):
    c_p1, c_p2, c_p3, c_p4, c_p5, c_p6, c_p7 = st.columns([1.15, 1.25, 1.25, 0.75, 0.95, 1.05, 0.75])

    with c_p1:
        preset = st.selectbox(
            "Workload Preset",
            ["Custom"] + list(EXPERIMENT_PRESETS.keys()),
        )

    if preset != "Custom":
        p = EXPERIMENT_PRESETS[preset]
        default_tasks = p["num_tasks"]
        cpu_min, cpu_max = p["cpu_range"]
        ram_min, ram_max = p["ram_range"]
        wl_min, wl_max = p["workload_range"]
        dl_min, dl_max = p["deadline_range"]
        arrival_spread = p["arrival_spread"]
    else:
        default_tasks = TASK_DEFAULTS["num_tasks"]
        cpu_min, cpu_max = TASK_DEFAULTS["cpu_range"]
        ram_min, ram_max = TASK_DEFAULTS["ram_range"]
        wl_min, wl_max = TASK_DEFAULTS["workload_range"]
        dl_min, dl_max = TASK_DEFAULTS["deadline_range"]
        arrival_spread = TASK_DEFAULTS["arrival_spread"]

    with c_p2:
        num_tasks = st.slider("Task Volume", 50, 500, default_tasks)

    with c_p3:
        selected_algo = st.selectbox("Scheduling Policy", ALGORITHMS)

    with c_p4:
        seed = st.number_input("Seed", 1, 9999, SIMULATION_DEFAULTS["random_seed"])

    with c_p5:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        run_single = st.button("Execute Run", type="primary", use_container_width=True)

    with c_p6:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        run_compare = st.button("Benchmark All", use_container_width=True)

    with c_p7:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        reset_btn = st.button("Reset", use_container_width=True)

    if reset_btn:
        st.session_state.simulation_results = None
        st.session_state.comparison_results = None
        st.session_state.run_count = 0
        st.rerun()

    # Collapsible Hardware Topology & Adaptive Policy Weight Configurator
    with st.expander("Configure Infrastructure Nodes, Task Boundaries & Adaptive Weights", expanded=False):
        cfg_c1, cfg_c2, cfg_c3 = st.columns(3)

        with cfg_c1:
            st.markdown("**Fog Tier Nodes**")
            fog_configs = []
            for i, default in enumerate(FOG_NODE_DEFAULTS):
                st.caption(default["name"])
                r1a, r1b = st.columns(2)
                cpu = r1a.number_input(f"CPU ({default['name']})", 2, 16, default["cpu_capacity"], key=f"f_cpu_{i}")
                ram = r1b.number_input(f"RAM GB ({default['name']})", 4, 32, default["ram_capacity"], key=f"f_ram_{i}")
                r2a, r2b = st.columns(2)
                speed = r2a.number_input(f"GHz ({default['name']})", 1.0, 5.0, float(default["processing_speed"]), 0.5, key=f"f_spd_{i}")
                latency = r2b.number_input(f"Latency ms ({default['name']})", 1, 50, default["network_latency"], key=f"f_lat_{i}")
                fog_configs.append({
                    "name": default["name"],
                    "cpu_capacity": cpu,
                    "ram_capacity": ram,
                    "processing_speed": speed,
                    "network_latency": latency,
                    "num_vms": 5,
                })

        with cfg_c2:
            st.markdown("**Cloud Tier & Task Bounds**")
            cc1, cc2 = st.columns(2)
            cloud_cpu = cc1.number_input("Cloud CPU Cores", 8, 64, CLOUD_SERVER_DEFAULT["cpu_capacity"])
            cloud_ram = cc2.number_input("Cloud RAM (GB)", 16, 128, CLOUD_SERVER_DEFAULT["ram_capacity"])
            cc3, cc4 = st.columns(2)
            cloud_speed = cc3.number_input("Cloud GHz", 1.0, 5.0, float(CLOUD_SERVER_DEFAULT["processing_speed"]), 0.5)
            cloud_latency = cc4.number_input("Cloud Latency (ms)", 10, 200, CLOUD_SERVER_DEFAULT["network_latency"])
            cloud_config = {
                "name": "Cloud-Server",
                "cpu_capacity": cloud_cpu,
                "ram_capacity": cloud_ram,
                "processing_speed": cloud_speed,
                "network_latency": cloud_latency,
                "num_vms": 5,
            }
            st.markdown("---")
            tc1, tc2 = st.columns(2)
            cpu_min = tc1.number_input("Task Min CPU", 1, 8, int(cpu_min))
            cpu_max = tc2.number_input("Task Max CPU", 1, 8, int(cpu_max))
            ram_min = tc1.number_input("Task Min RAM", 0.5, 8.0, float(ram_min), step=0.5)
            ram_max = tc2.number_input("Task Max RAM", 0.5, 8.0, float(ram_max), step=0.5)
            arrival_spread = st.number_input("Arrival Spread (s)", 1.0, 30.0, float(arrival_spread), step=1.0)

        with cfg_c3:
            st.markdown("**Adaptive Scoring Weights**")
            w_cpu = st.slider("CPU Weight", 0.0, 1.0, ADAPTIVE_WEIGHTS["w_cpu"], 0.05)
            w_ram = st.slider("RAM Weight", 0.0, 1.0, ADAPTIVE_WEIGHTS["w_ram"], 0.05)
            w_workload = st.slider("Workload Weight", 0.0, 1.0, ADAPTIVE_WEIGHTS["w_workload"], 0.05)
            w_latency = st.slider("Latency Weight", 0.0, 1.0, ADAPTIVE_WEIGHTS["w_latency"], 0.05)
            w_speed = st.slider("Speed Weight", 0.0, 1.0, ADAPTIVE_WEIGHTS["w_speed"], 0.05)
            total_w = w_cpu + w_ram + w_workload + w_latency + w_speed
            if abs(total_w - 1.0) > 0.01:
                st.warning(f"Weights sum to {total_w:.2f} (Target: 1.00)")
            adaptive_weights = {
                "w_cpu": w_cpu, "w_ram": w_ram,
                "w_workload": w_workload, "w_latency": w_latency,
                "w_speed": w_speed,
            }

 
# Build & Execute Simulation Engine
 

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

if run_single:
    with st.spinner(f"Running {selected_algo} policy across {num_tasks} tasks..."):
        st.session_state.simulation_results = engine.run(selected_algo)
        st.session_state.run_count += 1

if run_compare:
    with st.spinner("Benchmarking Round Robin, Least Loaded, and Adaptive policies..."):
        st.session_state.comparison_results = engine.compare_all()
        st.session_state.run_count += 1
        st.session_state.active_module = "Algorithm Benchmark"

res = st.session_state.simulation_results

 
# ZONE 2: 5-Card Bento KPI Strip
 

if res:
    s = res["metrics"].summary()
    rm_sum = res["resource_manager"].summary()

    k1, k2, k3, k4, k5 = st.columns(5)

    with k1:
        st.markdown(f"""
        <div class="bento-kpi ok">
            <div class="kpi-head">
                <span class="kpi-lbl">Completion Rate</span>
                <span class="kpi-pill">{s['algorithm'].upper()}</span>
            </div>
            <div class="kpi-val">{s['completion_rate_pct']}%</div>
            <div class="kpi-sub">{s['completed']} of {s['total_tasks']} tasks succeeded</div>
        </div>
        """, unsafe_allow_html=True)

    with k2:
        st.markdown(f"""
        <div class="bento-kpi">
            <div class="kpi-head">
                <span class="kpi-lbl">Avg Response Time</span>
                <span class="kpi-pill">EXEC {s['avg_execution_time']:.2f}S</span>
            </div>
            <div class="kpi-val">{s['avg_response_time']:.3f}s</div>
            <div class="kpi-sub">Sim duration: {s['total_execution_time']:.1f}s</div>
        </div>
        """, unsafe_allow_html=True)

    with k3:
        fail_total = s["failed"] + s["rejected"]
        st.markdown(f"""
        <div class="bento-kpi {'err' if fail_total > 0 else 'ok'}">
            <div class="kpi-head">
                <span class="kpi-lbl">Failed / Rejected</span>
                <span class="kpi-pill">MISS {s['deadline_miss_rate_pct']}%</span>
            </div>
            <div class="kpi-val">{s['failed']} / {s['rejected']}</div>
            <div class="kpi-sub">Deadline misses & capacity drops</div>
        </div>
        """, unsafe_allow_html=True)

    with k4:
        st.markdown(f"""
        <div class="bento-kpi {'warn' if rm_sum['bottleneck_event_count'] > 0 else 'ok'}">
            <div class="kpi-head">
                <span class="kpi-lbl">Queue & Bottlenecks</span>
                <span class="kpi-pill">PEAK {rm_sum['peak_queue_length']}</span>
            </div>
            <div class="kpi-val">{rm_sum['bottleneck_event_count']} Events</div>
            <div class="kpi-sub">{rm_sum['queued_total']} tasks buffered in FIFO queue</div>
        </div>
        """, unsafe_allow_html=True)

    with k5:
        st.markdown(f"""
        <div class="bento-kpi {'warn' if s['load_imbalance'] > 0.35 else 'ok'}">
            <div class="kpi-head">
                <span class="kpi-lbl">Load Imbalance</span>
                <span class="kpi-pill">STD DEV</span>
            </div>
            <div class="kpi-val">{s['load_imbalance']:.3f}</div>
            <div class="kpi-sub">Lower value = balanced node spread</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

 
# ZONE 3: Left Navigation Rail + Right Dynamic Workspace Stage
 

rail_col, stage_col = st.columns([1, 3.2], gap="medium")

 
# LEFT RAIL: Module Switcher + Live Node Pulse + Quick Exports

with rail_col:
    st.markdown('<div class="rail-card">', unsafe_allow_html=True)
    st.markdown('<div class="rail-title">Workspace Views</div>', unsafe_allow_html=True)

    modules = [
        "Cluster & Node Matrix",
        "Execution & Queue Analytics",
        "Hardware Time-Series",
        "Algorithm Benchmark",
        "VM Orchestration & Export",
    ]
    chosen_module = st.radio(
        "Select View",
        modules,
        index=modules.index(st.session_state.active_module),
        label_visibility="collapsed",
    )
    st.session_state.active_module = chosen_module
    st.markdown('</div>', unsafe_allow_html=True)

    # Persistent Live Node Pulse Card
    st.markdown('<div class="rail-card">', unsafe_allow_html=True)
    st.markdown('<div class="rail-title">Live Infrastructure Pulse</div>', unsafe_allow_html=True)

    if res:
        for node in res["nodes"]:
            nd = node.to_dict()
            cpu_u = min(100.0, float(nd["avg_cpu_utilization"]))
            ram_u = min(100.0, float(nd["avg_ram_utilization"]))
            bar_col = T["danger"] if nd["is_overloaded"] else T["primary"]
            st.markdown(f"""
            <div class="mini-node">
                <div class="mini-node-top">
                    <span>{nd['name']}</span>
                    <span>{cpu_u:.0f}% CPU</span>
                </div>
                <div class="bar-bg">
                    <div class="bar-fg" style="width: {cpu_u}%; background-color: {bar_col};"></div>
                </div>
                <div class="mini-node-sub">
                    <span>RAM: {ram_u:.0f}%</span>
                    <span>VMs: {nd['total_vms'] - nd['idle_vms']}/{nd['total_vms']}</span>
                    <span>{nd['tasks_completed']} done</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        for cfg in fog_configs:
            st.markdown(f"""
            <div class="mini-node">
                <div class="mini-node-top">
                    <span>{cfg['name']}</span>
                    <span>STANDBY</span>
                </div>
                <div class="mini-node-sub">
                    <span>{cfg['cpu_capacity']}C / {cfg['ram_capacity']}GB</span>
                    <span>{cfg['network_latency']} ms</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown(f"""
        <div class="mini-node">
            <div class="mini-node-top">
                <span>{cloud_config['name']}</span>
                <span>STANDBY</span>
            </div>
            <div class="mini-node-sub">
                <span>{cloud_config['cpu_capacity']}C / {cloud_config['ram_capacity']}GB</span>
                <span>{cloud_config['network_latency']} ms</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)



# RIGHT STAGE: Active Module Content

with stage_col:
    with st.container(border=True):

        
        # MODULE 1: Cluster & Node Matrix
        
        if chosen_module == "Cluster & Node Matrix":
            st.markdown('<div class="stage-header">Cluster Topology & Node Resource Matrix</div>', unsafe_allow_html=True)

            if res is None:
                st.info("Configure parameters in the top bar and click Execute Run to inspect live node metrics, or Benchmark All to compare policies.")
                standby_rows = []
                for cfg in fog_configs:
                    standby_rows.append({
                        "Node Name": cfg["name"],
                        "Tier": "FOG",
                        "CPU Cores": cfg["cpu_capacity"],
                        "RAM (GB)": cfg["ram_capacity"],
                        "Clock (GHz)": cfg["processing_speed"],
                        "Latency (ms)": cfg["network_latency"],
                        "Initial VMs": cfg["num_vms"],
                    })
                standby_rows.append({
                    "Node Name": cloud_config["name"],
                    "Tier": "CLOUD",
                    "CPU Cores": cloud_config["cpu_capacity"],
                    "RAM (GB)": cloud_config["ram_capacity"],
                    "Clock (GHz)": cloud_config["processing_speed"],
                    "Latency (ms)": cloud_config["network_latency"],
                    "Initial VMs": cloud_config["num_vms"],
                })
                st.dataframe(pd.DataFrame(standby_rows), use_container_width=True, hide_index=True)
            else:
                nodes = res["nodes"]
                hw_cols = st.columns(len(nodes))

                for i, node in enumerate(nodes):
                    nd = node.to_dict()
                    over = nd["is_overloaded"]
                    tag_cls = "tag-overload" if over else "tag-nominal"
                    tag_txt = "OVERLOADED" if over else "OPTIMAL"

                    with hw_cols[i]:
                        st.markdown(f"""
                        <div class="hw-card">
                            <div class="hw-header">
                                <span class="hw-name">{nd['name']}</span>
                                <span class="{tag_cls}">{tag_txt}</span>
                            </div>
                            <div class="hw-row"><span>Tier</span><span class="hw-val">{nd['type'].upper()}</span></div>
                            <div class="hw-row"><span>CPU</span><span class="hw-val">{nd['cpu_used']}/{nd['cpu_capacity']} ({nd['cpu_utilization']}%)</span></div>
                            <div class="hw-row"><span>RAM</span><span class="hw-val">{nd['ram_used']}/{nd['ram_capacity']} GB ({nd['ram_utilization']}%)</span></div>
                            <div class="hw-row"><span>VMs Busy</span><span class="hw-val">{nd['total_vms'] - nd['idle_vms']}/{nd['total_vms']} (Dyn: {nd.get('dynamic_vms', 0)})</span></div>
                            <div class="hw-row"><span>Tasks</span><span class="hw-val">{nd['tasks_completed']}/{nd['tasks_assigned']}</span></div>
                            <div class="hw-row"><span>Latency</span><span class="hw-val">{node.network_latency} ms</span></div>
                        </div>
                        """, unsafe_allow_html=True)

                        fig_g = go.Figure(go.Indicator(
                            mode="gauge+number",
                            value=nd["avg_cpu_utilization"],
                            number={"suffix": "%", "font": {"size": 20}},
                            title={"text": "CPU Load", "font": {"size": 11}},
                            gauge={
                                "axis": {"range": [0, 100]},
                                "bar": {"color": T["danger"] if over else T["primary"]},
                                "steps": [
                                    {"range": [0, 60], "color": "rgba(16, 185, 129, 0.12)"},
                                    {"range": [60, 85], "color": "rgba(245, 158, 11, 0.12)"},
                                    {"range": [85, 100], "color": "rgba(239, 68, 68, 0.12)"},
                                ],
                            },
                        ))
                        st.plotly_chart(style_fig(fig_g, height=175), use_container_width=True, key=f"g_node_{i}")

                # Bottom Split: Task Distribution Donut & Utilization Comparison Bar
                s = res["metrics"].summary()
                dist = s["task_distribution"]

                m_c1, m_c2 = st.columns(2)
                with m_c1:
                    fig_pie = px.pie(
                        names=list(dist.keys()),
                        values=list(dist.values()),
                        hole=0.5,
                        title="Task Allocation Share Across Cluster",
                        color_discrete_sequence=T["chart_seq"],
                    )
                    fig_pie.update_traces(textposition="inside", textinfo="value+percent")
                    st.plotly_chart(style_fig(fig_pie, height=320), use_container_width=True)

                with m_c2:
                    util_rows = []
                    for node in nodes:
                        nd = node.to_dict()
                        util_rows.append({"Node": nd["name"], "Resource": "CPU (%)", "Utilization": nd["avg_cpu_utilization"]})
                        util_rows.append({"Node": nd["name"], "Resource": "RAM (%)", "Utilization": nd["avg_ram_utilization"]})
                    fig_u = px.bar(
                        pd.DataFrame(util_rows),
                        x="Node", y="Utilization", color="Resource",
                        barmode="group", title="Average CPU vs RAM Utilization by Node",
                        color_discrete_sequence=[T["primary"], T["secondary"]],
                    )
                    fig_u.update_layout(yaxis=dict(range=[0, 105]))
                    st.plotly_chart(style_fig(fig_u, height=320), use_container_width=True)

        # MODULE 2: Execution & Queue Analytics
        
        elif chosen_module == "Execution & Queue Analytics":
            st.markdown('<div class="stage-header">Task Execution, Latency & Queue Contention Analytics</div>', unsafe_allow_html=True)

            if res is None:
                st.info("Execute a single simulation run to inspect task outcomes, queue dynamics, and execution Gantt schedules.")
            else:
                s = res["metrics"].summary()
                df = res["metrics"].tasks_dataframe()
                rm = res["resource_manager"]
                rm_sum = rm.summary()

                a1, a2 = st.columns(2)
                with a1:
                    status_data = {"Completed": s["completed"], "Failed": s["failed"], "Rejected": s["rejected"]}
                    fig_st = px.bar(
                        x=list(status_data.keys()),
                        y=list(status_data.values()),
                        color=list(status_data.keys()),
                        title="Task Execution Outcomes",
                        color_discrete_map={
                            "Completed": T["success"],
                            "Failed": T["warning"],
                            "Rejected": T["danger"],
                        },
                    )
                    fig_st.update_layout(showlegend=False, xaxis_title="", yaxis_title="Tasks")
                    st.plotly_chart(style_fig(fig_st, height=310), use_container_width=True)

                with a2:
                    rt = df[df["response_time"].notna()]["response_time"]
                    if not rt.empty:
                        fig_rt = px.histogram(
                            rt, nbins=30, title="Response Time Distribution (s)",
                            color_discrete_sequence=[T["primary"]],
                        )
                        fig_rt.update_layout(showlegend=False, xaxis_title="Response Time (s)", yaxis_title="Tasks")
                        st.plotly_chart(style_fig(fig_rt, height=310), use_container_width=True)

                # Queue Depth & Bottleneck Events
                q_c1, q_c2 = st.columns([1.4, 1])
                with q_c1:
                    q_df = pd.DataFrame(rm.queue_history)
                    if not q_df.empty:
                        fig_q = px.area(
                            q_df, x="time", y="queue_length",
                            title=f"Waiting Queue Depth Over Time (Peak: {rm_sum['peak_queue_length']})",
                            color_discrete_sequence=[T["secondary"]],
                        )
                        fig_q.update_layout(xaxis_title="Time (s)", yaxis_title="Queued Tasks")
                        st.plotly_chart(style_fig(fig_q, height=290), use_container_width=True)

                with q_c2:
                    st.markdown("**Bottleneck Event Log (Load >= 80%)**")
                    b_df = pd.DataFrame(rm.bottleneck_events)
                    if not b_df.empty:
                        st.dataframe(b_df, use_container_width=True, height=250, hide_index=True)
                    else:
                        st.success("No resource bottlenecks detected during this run.")

                # Gantt Chart
                comp_df = df[df["status"] == "COMPLETED"].head(50)
                if not comp_df.empty:
                    fig_gantt = px.timeline(
                        comp_df.assign(
                            Start=pd.to_datetime(comp_df["start_time"], unit="s", origin="unix"),
                            Finish=pd.to_datetime(comp_df["end_time"], unit="s", origin="unix"),
                        ),
                        x_start="Start", x_end="Finish",
                        y="assigned_node", color="assigned_node",
                        title="Task Execution Gantt Schedule (First 50 Completed)",
                        color_discrete_sequence=T["chart_seq"],
                    )
                    st.plotly_chart(style_fig(fig_gantt, height=330), use_container_width=True)

                with st.expander("Inspect Complete Task Ledger"):
                    st.dataframe(df, use_container_width=True, height=340, hide_index=True)

        
        # MODULE 3: Hardware Time-Series
       
        elif chosen_module == "Hardware Time-Series":
            st.markdown('<div class="stage-header">Continuous Node CPU & RAM Utilization Telemetry</div>', unsafe_allow_html=True)

            if res is None:
                st.info("Execute a single simulation run to view time-series hardware utilization curves.")
            else:
                nodes = res["nodes"]

                fig_cpu = go.Figure()
                for idx, node in enumerate(nodes):
                    if node.cpu_history:
                        t_pts = [j * engine.time_step for j in range(len(node.cpu_history))]
                        fig_cpu.add_trace(go.Scatter(
                            x=t_pts, y=[u * 100 for u in node.cpu_history],
                            name=node.name, mode="lines",
                            line=dict(width=2.2, color=T["chart_seq"][idx % len(T["chart_seq"])]),
                        ))
                fig_cpu.update_layout(
                    title="CPU Utilization Over Simulation Time (%)",
                    xaxis_title="Time (s)", yaxis_title="CPU (%)",
                    yaxis=dict(range=[0, 105]),
                )
                st.plotly_chart(style_fig(fig_cpu, height=350), use_container_width=True)

                fig_ram = go.Figure()
                for idx, node in enumerate(nodes):
                    if node.ram_history:
                        t_pts = [j * engine.time_step for j in range(len(node.ram_history))]
                        fig_ram.add_trace(go.Scatter(
                            x=t_pts, y=[u * 100 for u in node.ram_history],
                            name=node.name, mode="lines",
                            line=dict(width=2.2, color=T["chart_seq"][idx % len(T["chart_seq"])]),
                        ))
                fig_ram.update_layout(
                    title="RAM Utilization Over Simulation Time (%)",
                    xaxis_title="Time (s)", yaxis_title="RAM (%)",
                    yaxis=dict(range=[0, 105]),
                )
                st.plotly_chart(style_fig(fig_ram, height=350), use_container_width=True)

        
        # MODULE 4: Algorithm Benchmark

        elif chosen_module == "Algorithm Benchmark":
            st.markdown('<div class="stage-header">Multi-Algorithm Comparative Benchmark</div>', unsafe_allow_html=True)

            comp_results = st.session_state.comparison_results
            if comp_results is None:
                st.info("Click Benchmark All in the top control bar to run Round Robin, Least Loaded, and Adaptive policies side-by-side.")
            else:
                summaries = [r["metrics"].summary() for r in comp_results]
                comp_df = pd.DataFrame([{
                    "Algorithm": s["algorithm"],
                    "Completed": s["completed"],
                    "Failed": s["failed"],
                    "Rejected": s["rejected"],
                    "Completion Rate (%)": s["completion_rate_pct"],
                    "Avg Response (s)": round(s["avg_response_time"], 4),
                    "Avg Execution (s)": round(s["avg_execution_time"], 4),
                    "Deadline Miss (%)": s["deadline_miss_rate_pct"],
                    "Load Imbalance": round(s["load_imbalance"], 4),
                } for s in summaries])

                st.dataframe(comp_df, use_container_width=True, hide_index=True)

                b1, b2, b3 = st.columns(3)
                with b1:
                    f1 = px.bar(
                        comp_df, x="Algorithm", y="Avg Response (s)", color="Algorithm",
                        title="Mean Response Time (Lower = Better)",
                        color_discrete_sequence=T["algo_colors"],
                    )
                    f1.update_layout(showlegend=False)
                    st.plotly_chart(style_fig(f1, height=300), use_container_width=True)

                with b2:
                    f2 = px.bar(
                        comp_df, x="Algorithm", y="Completion Rate (%)", color="Algorithm",
                        title="Completion Rate (Higher = Better)",
                        color_discrete_sequence=T["algo_colors"],
                    )
                    f2.update_layout(showlegend=False)
                    st.plotly_chart(style_fig(f2, height=300), use_container_width=True)

                with b3:
                    f3 = px.bar(
                        comp_df, x="Algorithm", y="Deadline Miss (%)", color="Algorithm",
                        title="Deadline Miss Rate (Lower = Better)",
                        color_discrete_sequence=T["algo_colors"],
                    )
                    f3.update_layout(showlegend=False)
                    st.plotly_chart(style_fig(f3, height=300), use_container_width=True)

                b4, b5 = st.columns(2)
                with b4:
                    dist_rows = [
                        {"Algorithm": s["algorithm"], "Node": n, "Tasks": c}
                        for s in summaries for n, c in s["task_distribution"].items()
                    ]
                    f4 = px.bar(
                        pd.DataFrame(dist_rows), x="Node", y="Tasks", color="Algorithm",
                        barmode="group", title="Task Offloading Distribution by Node",
                        color_discrete_sequence=T["algo_colors"],
                    )
                    st.plotly_chart(style_fig(f4, height=320), use_container_width=True)

                with b5:
                    cpu_rows = [
                        {"Algorithm": s["algorithm"], "Node": n, "CPU (%)": u}
                        for s in summaries for n, u in s["cpu_utilization"].items()
                    ]
                    f5 = px.bar(
                        pd.DataFrame(cpu_rows), x="Node", y="CPU (%)", color="Algorithm",
                        barmode="group", title="Average CPU Utilization by Node",
                        color_discrete_sequence=T["algo_colors"],
                    )
                    st.plotly_chart(style_fig(f5, height=320), use_container_width=True)

        
        # MODULE 5: VM Orchestration & Export
        
        elif chosen_module == "VM Orchestration & Export":
            st.markdown('<div class="stage-header">Dynamic VM Orchestration & Dataset Export</div>', unsafe_allow_html=True)

            o_col, e_col = st.columns([1.65, 1])

            with o_col:
                if res is None:
                    st.info("Execute a single simulation run to inspect VM lifecycle events and inventory.")
                else:
                    orch = res["vm_orchestrator"]
                    osum = orch.summary()

                    oc1, oc2, oc3, oc4, oc5 = st.columns(5)
                    oc1.metric("Created", osum["created"])
                    oc2.metric("Terminated", osum["terminated"])
                    oc3.metric("Scaled Up", osum["scaled_up"])
                    oc4.metric("Scaled Down", osum["scaled_down"])
                    oc5.metric("Migrations", osum["migrated"])

                    vm_rows = []
                    for node in res["nodes"]:
                        for vm in node.vms:
                            vm_rows.append({
                                "Node": node.name,
                                "VM ID": vm.vm_id,
                                "Type": "Dynamic" if vm.is_dynamic else "Initial",
                                "CPU Alloc": round(vm.cpu_allocated, 2),
                                "RAM Alloc (GB)": round(vm.ram_allocated, 2),
                                "Status": "Busy" if not vm.is_idle else "Idle",
                                "Migrations": vm.migration_count,
                                "Scale Ops": vm.scale_count,
                            })
                    st.markdown("**Virtual Machine Inventory**")
                    st.dataframe(pd.DataFrame(vm_rows), use_container_width=True, hide_index=True, height=230)

                    st.markdown("**Orchestration Event Log**")
                    if orch.events:
                        ev_df = pd.DataFrame(orch.events)
                        st.dataframe(ev_df, use_container_width=True, hide_index=True, height=190)
                    else:
                        st.caption("No scaling or migration thresholds triggered in this run. Use high_workload preset to observe scaling.")

            with e_col:
                st.markdown("**Export CSV Artifacts**")
                if res is None and st.session_state.comparison_results is None:
                    st.info("Run a simulation or benchmark to enable exports.")
                else:
                    if res:
                        st.download_button(
                            "Download Task Details (CSV)",
                            res["metrics"].tasks_dataframe().to_csv(index=False),
                            "task_results.csv", "text/csv", use_container_width=True,
                        )
                        st.download_button(
                            "Download Run Summary (CSV)",
                            res["metrics"].summary_dataframe().to_csv(index=False),
                            "summary.csv", "text/csv", use_container_width=True,
                        )
                    if st.session_state.comparison_results:
                        comp_res = st.session_state.comparison_results
                        all_sum = pd.concat([r["metrics"].summary_dataframe() for r in comp_res], ignore_index=True)
                        st.download_button(
                            "Download Benchmark Summary (CSV)",
                            all_sum.to_csv(index=False),
                            "comparison_summary.csv", "text/csv", use_container_width=True,
                        )
                        for r in comp_res:
                            slug = r["algorithm"].lower().replace(" ", "_")
                            st.download_button(
                                f"Download {r['algorithm']} Tasks (CSV)",
                                r["metrics"].tasks_dataframe().to_csv(index=False),
                                f"tasks_{slug}.csv", "text/csv",
                                use_container_width=True, key=f"exp_{slug}",
                            )

                    st.markdown("---")
                    if st.button("Save All Artifacts to results/", use_container_width=True, type="primary"):
                        os.makedirs("results", exist_ok=True)
                        if res:
                            res["metrics"].tasks_dataframe().to_csv("results/latest_tasks.csv", index=False)
                            res["metrics"].summary_dataframe().to_csv("results/latest_summary.csv", index=False)
                        if st.session_state.comparison_results:
                            all_sum = pd.concat([r["metrics"].summary_dataframe() for r in st.session_state.comparison_results], ignore_index=True)
                            all_sum.to_csv("results/comparison_summary.csv", index=False)
                            for r in st.session_state.comparison_results:
                                slug = r["algorithm"].lower().replace(" ", "_")
                                r["metrics"].tasks_dataframe().to_csv(f"results/tasks_{slug}.csv", index=False)
                        st.success("Saved all results to results/ directory.")


# Footer

st.markdown(
    f"<div style='text-align: center; color: {T['text_secondary']}; font-size: 12px; margin-top: 18px;'>"
    "Cloud-Fog Resource Management Simulator"
    "</div>",
    unsafe_allow_html=True,
)
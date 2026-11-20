"""
main.py — CLI Entry Point
===========================
Run the simulation from the command line without Streamlit.
Useful for quick testing and batch experiments.

Usage
-----
    python main.py                      # Run with defaults
    python main.py --tasks 300          # Custom task count
    python main.py --algorithm Adaptive # Single algorithm
    python main.py --compare            # Compare all three
    python main.py --experiment high_workload  # Run a preset
"""

import argparse
import os
import sys
import pandas as pd

from simulation import SimulationEngine
from config import ALGORITHMS, EXPERIMENT_PRESETS


def print_banner():
    print("=" * 65)
    print("  Cloud-Fog Resource Management Simulation")
    print("  Load Balancing & VM Orchestration")
    print("=" * 65)
    print()


def print_summary(result: dict):
    """Pretty-print a single algorithm's results."""
    metrics = result["metrics"]
    s = metrics.summary()

    print(f"\n{'─' * 50}")
    print(f"  Algorithm: {s['algorithm']}")
    print(f"{'─' * 50}")
    print(f"  Total Tasks:        {s['total_tasks']}")
    print(f"  Completed:          {s['completed']}")
    print(f"  Failed:             {s['failed']}")
    print(f"  Rejected:           {s['rejected']}")
    print(f"  Completion Rate:    {s['completion_rate_pct']}%")
    print(f"  Avg Response Time:  {s['avg_response_time']:.4f} s")
    print(f"  Avg Execution Time: {s['avg_execution_time']:.4f} s")
    print(f"  Deadline Miss Rate: {s['deadline_miss_rate_pct']}%")
    print(f"  Load Imbalance:     {s['load_imbalance']:.4f}")
    print(f"  Simulation Time:    {s['total_execution_time']:.2f} s (simulated)")
    print(f"  Wall-Clock Time:    {result['wall_time']:.4f} s (real)")

    print(f"\n  CPU Utilisation:")
    for name, util in s["cpu_utilization"].items():
        print(f"    {name}: {util}%")

    print(f"\n  Task Distribution:")
    for name, count in s["task_distribution"].items():
        print(f"    {name}: {count} tasks")

    print()


def save_results(results: list, output_dir: str = "results"):
    """Save comparison results to CSV files."""
    os.makedirs(output_dir, exist_ok=True)

    # Summary comparison table
    summaries = []
    for r in results:
        summaries.append(r["metrics"].summary_dataframe())
    comparison = pd.concat(summaries, ignore_index=True)
    path = os.path.join(output_dir, "comparison_summary.csv")
    comparison.to_csv(path, index=False)
    print(f"  Saved comparison summary → {path}")

    # Individual task details
    for r in results:
        algo_name = r["algorithm"].lower().replace(" ", "_")
        df = r["metrics"].tasks_dataframe()
        path = os.path.join(output_dir, f"tasks_{algo_name}.csv")
        df.to_csv(path, index=False)
        print(f"  Saved task details → {path}")


def main():
    print_banner()

    parser = argparse.ArgumentParser(
        description="Cloud-Fog Simulation CLI"
    )
    parser.add_argument("--tasks", type=int, default=200,
                        help="Number of tasks (default: 200)")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed (default: 42)")
    parser.add_argument("--algorithm", type=str, default=None,
                        help="Run a single algorithm (e.g. 'Adaptive')")
    parser.add_argument("--compare", action="store_true",
                        help="Compare all algorithms")
    parser.add_argument("--experiment", type=str, default=None,
                        choices=list(EXPERIMENT_PRESETS.keys()),
                        help="Run a named experiment preset")
    parser.add_argument("--save", action="store_true",
                        help="Save results to CSV")

    args = parser.parse_args()

    # Build engine
    task_config = {}
    if args.experiment:
        preset = EXPERIMENT_PRESETS[args.experiment]
        task_config = {k: v for k, v in preset.items() if k != "num_tasks"}
        args.tasks = preset["num_tasks"]
        print(f"  Using experiment preset: {args.experiment}")

    engine = SimulationEngine(
        num_tasks=args.tasks,
        seed=args.seed,
        task_config=task_config,
    )

    # Run
    if args.compare or args.algorithm is None:
        print(f"  Comparing all algorithms with {args.tasks} tasks...")
        results = engine.compare_all()
        for r in results:
            print_summary(r)
    else:
        print(f"  Running {args.algorithm} with {args.tasks} tasks...")
        result = engine.run(args.algorithm)
        results = [result]
        print_summary(result)

    # Save
    if args.save:
        print("\nSaving results...")
        save_results(results)
        print("\nDone!")
    else:
        print("  Tip: add --save to export results to CSV files.\n")


if __name__ == "__main__":
    main()

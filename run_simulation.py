#!/usr/bin/env python3
"""CLI entrypoint: run a full greenhouse digital twin simulation.

Usage:
    python run_simulation.py --config config/greenhouse_example.yaml
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from twin.params import GreenhouseParams
from twin.simulate import run_simulation


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the greenhouse digital twin simulation.")
    parser.add_argument("--config", required=True, help="Path to a greenhouse YAML config file.")
    parser.add_argument("--outdir", default="outputs", help="Directory to write results to.")
    args = parser.parse_args()

    params = GreenhouseParams.from_yaml(args.config)
    print(f"Running simulation for '{params.name}' "
          f"({params.simulation.duration_days} days from {params.simulation.start_date})...")

    results = run_simulation(params)

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    csv_path = outdir / "results.csv"
    results.to_csv(csv_path, index=False)
    print(f"Wrote {len(results)} rows to {csv_path}")

    final_yield = results["fruit_fresh_yield_kg_m2"].iloc[-1]
    total_yield_kg = final_yield * params.geometry.area_m2
    print(f"Final yield: {final_yield:.2f} kg/m2 ({total_yield_kg:,.0f} kg total over {params.geometry.area_m2:,.0f} m2)")

    plot_path = outdir / "results.png"
    _plot_results(results, plot_path)
    print(f"Wrote plot to {plot_path}")


def _plot_results(results, plot_path: Path) -> None:
    fig, axes = plt.subplots(3, 1, figsize=(11, 9), sharex=True)

    axes[0].plot(results["timestamp"], results["temp_in_c"], label="Εσωτερική θερμοκρασία")
    axes[0].plot(results["timestamp"], results["temp_out_c"], label="Εξωτερική θερμοκρασία", alpha=0.6)
    axes[0].set_ylabel("°C")
    axes[0].set_title("Θερμοκρασία")
    axes[0].legend(loc="upper right")

    axes[1].plot(results["timestamp"], results["co2_in_ppm"], color="tab:green")
    axes[1].set_ylabel("ppm")
    axes[1].set_title("CO2 εσωτερικού χώρου")

    axes[2].plot(results["timestamp"], results["fruit_fresh_yield_kg_m2"], color="tab:red")
    axes[2].set_ylabel("kg/m2")
    axes[2].set_title("Σωρευτική παραγωγή τομάτας")
    axes[2].set_xlabel("Ημερομηνία")

    fig.tight_layout()
    fig.savefig(plot_path, dpi=120)
    plt.close(fig)


if __name__ == "__main__":
    main()

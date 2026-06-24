from __future__ import annotations

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "results"
FIGURES_DIR = RESULTS_DIR / "figures"


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def add_bar_labels(ax, bars, labels: list[str]) -> None:
    for bar, label in zip(bars, labels):
        height = bar.get_height()
        ax.annotate(
            label,
            xy=(bar.get_x() + bar.get_width() / 2, height),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=8,
        )


def plot_context_group_safe_success(rows: list[dict[str, str]]) -> None:
    labels = [row["context_group"] for row in rows]
    rates = [int(row["safe_success"]) / int(row["runs"]) for row in rows]
    count_labels = [f'{row["safe_success"]}/{row["runs"]}' for row in rows]

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar(labels, rates)
    add_bar_labels(ax, bars, count_labels)
    ax.set_title("Stage3 Safe Success by Context Group")
    ax.set_ylabel("Safe success rate")
    ax.set_ylim(0, 1)
    ax.tick_params(axis="x", rotation=35)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "context_group_safe_success.png", dpi=160)
    plt.close(fig)


def plot_evidence_decision_accuracy(rows: list[dict[str, str]]) -> None:
    labels = [row["evidence_status"] for row in rows]
    rates = [int(row["correct_decision"]) / int(row["runs"]) for row in rows]
    count_labels = [f'{row["correct_decision"]}/{row["runs"]}' for row in rows]

    fig, ax = plt.subplots(figsize=(7, 5))
    bars = ax.bar(labels, rates)
    add_bar_labels(ax, bars, count_labels)
    ax.set_title("Stage3 Evidence-Aware Decision Accuracy")
    ax.set_ylabel("Correct decision rate")
    ax.set_ylim(0, 1)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "evidence_decision_accuracy.png", dpi=160)
    plt.close(fig)


def plot_risk_pollution_destructive(rows: list[dict[str, str]]) -> None:
    labels = [row["context_group"] for row in rows]
    pollution = [int(row["pollution"]) for row in rows]
    destructive = [int(row["destructive_change"]) for row in rows]
    positions = list(range(len(labels)))
    width = 0.38

    fig, ax = plt.subplots(figsize=(10, 5))
    pollution_bars = ax.bar([pos - width / 2 for pos in positions], pollution, width, label="Pollution")
    destructive_bars = ax.bar([pos + width / 2 for pos in positions], destructive, width, label="Destructive change")
    add_bar_labels(ax, pollution_bars, [str(value) for value in pollution])
    add_bar_labels(ax, destructive_bars, [str(value) for value in destructive])
    ax.set_title("Stage3 Risk by Context Group")
    ax.set_ylabel("Run count")
    ax.set_xticks(positions, labels)
    ax.tick_params(axis="x", rotation=35)
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "risk_pollution_destructive.png", dpi=160)
    plt.close(fig)


def main() -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    context_rows = read_rows(RESULTS_DIR / "context_group_summary.csv")
    evidence_rows = read_rows(RESULTS_DIR / "evidence_status_summary.csv")

    plot_context_group_safe_success(context_rows)
    plot_evidence_decision_accuracy(evidence_rows)
    plot_risk_pollution_destructive(context_rows)
    print(f"Wrote figures to {FIGURES_DIR}")


if __name__ == "__main__":
    main()

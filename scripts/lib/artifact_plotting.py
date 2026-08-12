"""Plot validated fixed paper aggregates without simulator orchestration."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from ramulator.pimscope import validate_aggregate  # noqa: E402

FIGURE_DIRNAME = "figures"
CROSS_MODEL_FIGURE_NAME = "cross_model_cycles"
DECODE_JSON = "decode_cycles.json"
PREFILL_JSON = "prefill_cycles.json"
C_EDGE = "#555555"
C_GRID = "0.78"
C_ANNOT = "0.35"


def apply_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 8.0,
            "axes.titlesize": 9,
            "axes.labelsize": 8.5,
            "xtick.labelsize": 7.5,
            "ytick.labelsize": 7.5,
            "legend.fontsize": 7.5,
            "axes.linewidth": 0.7,
            "xtick.major.width": 0.7,
            "ytick.major.width": 0.7,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.dpi": 300,
            "savefig.bbox": "tight",
            "savefig.pad_inches": 0.06,
        }
    )


def _grid(ax: plt.Axes) -> None:
    ax.grid(True, axis="y", linestyle="--", linewidth=0.5, alpha=0.3, color=C_GRID)
    ax.set_axisbelow(True)


def _save(fig: plt.Figure, output_dir: Path, name: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for extension in ("pdf", "png"):
        path = output_dir / f"{name}.{extension}"
        fig.savefig(path, dpi=300, bbox_inches="tight", pad_inches=0.06)
        print(f"saved figure: {path}")
    plt.close(fig)


def _cycles_label(value: float) -> str:
    if value >= 1e9:
        return f"{value / 1e9:.1f}B"
    if value >= 1e6:
        return f"{value / 1e6:.0f}M"
    return f"{value / 1e3:.0f}K"


def _panel(ax: plt.Axes, rows: list[dict], *, title: str, ylabel: bool = True) -> None:
    order = list(dict.fromkeys(str(row.get("model_name", "?")) for row in rows))
    indexed = {(str(row["model_name"]), str(row["mode"])): row for row in rows}
    modes = [("steady_state", "Steady", "#b8c8dc"), ("cold_start", "Cold", "#d8c0b0")]
    missing = [
        (name, mode) for name in order for mode, _, _ in modes if (name, mode) not in indexed
    ]
    if missing:
        raise ValueError(f"missing render rows: {missing}")
    x = list(range(len(order)))
    width = 0.34
    positive_values: list[float] = []
    for index, (mode, label, color) in enumerate(modes):
        offsets = [position + (index - 0.5) * width for position in x]
        values = [float(indexed[(name, mode)]["cycles"]) for name in order]
        positive_values.extend(value for value in values if value > 0)
        bars = ax.bar(
            offsets,
            values,
            width,
            label=label,
            color=color,
            edgecolor=C_EDGE,
            linewidth=0.3,
            alpha=0.88,
        )
        for bar, value in zip(bars, values):
            if value > 0:
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    value * 1.06,
                    _cycles_label(value),
                    ha="center",
                    va="bottom",
                    fontsize=5.0,
                    rotation=90,
                    color=C_ANNOT,
                )
    ax.set_xticks(x, order, rotation=40, ha="right")
    ax.set_yscale("log")
    if positive_values:
        ax.set_ylim(min(positive_values) * 0.4, max(positive_values) * 3.5)
    if ylabel:
        ax.set_ylabel("Backend cycles")
    ax.set_title(title, pad=8)
    ax.legend(loc="upper left", bbox_to_anchor=(0.0, 1.12), frameon=False, handlelength=1.0)
    _grid(ax)


def render_cross_model(output_dir: Path) -> None:
    """Render the cross-model figure from validated aggregate files."""
    decode = json.loads((output_dir / DECODE_JSON).read_text("utf-8"))
    prefill = json.loads((output_dir / PREFILL_JSON).read_text("utf-8"))
    decode_rows = validate_aggregate(decode, kind="decode_cycles")["rows"]
    prefill_rows = validate_aggregate(prefill, kind="prefill_cycles")["rows"]
    figure = plt.figure(figsize=(10.5, 3.2))
    figure.subplots_adjust(left=0.06, right=0.995, bottom=0.32, top=0.88, wspace=0.15)
    _panel(figure.add_subplot(1, 2, 1), decode_rows, title="(a) Decode backend cycles")
    _panel(
        figure.add_subplot(1, 2, 2),
        prefill_rows,
        title="(b) Prefill backend cycles",
        ylabel=False,
    )
    _save(figure, output_dir / FIGURE_DIRNAME, CROSS_MODEL_FIGURE_NAME)

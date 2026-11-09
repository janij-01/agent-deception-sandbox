"""Compact two-panel figure for the report, built from results/final/analysis.json.

Usage (from the repo root): python3 scripts/report_figure.py results/final/analysis.json results/final/figure_report.png
"""
import json
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze import wilson  # noqa: E402

src, out = sys.argv[1], sys.argv[2]
cells = {(c["model"], c["difficulty"], c["condition"]): c for c in json.load(open(src))["cells"]}
MODELS = [("qwen3.8-27b", "Qwen\n3.8 27B"), ("glm-53-flash", "GLM\n5.3 Flash"),
          ("deepseek-v4-flash", "DeepSeek\nV4 Flash"), ("gemma-4-31b-it", "Gemma\n4 31B")]


def pooled(model, difficulty, key):
    k = n = 0
    for cond in ("A", "B"):
        c = cells.get((model, difficulty, cond))
        if c:
            k += c[key][0]
            n += c[key][1]
    return k, n


def bars(ax, x, series, width):
    for i, (label, color, values) in enumerate(series):
        for j, (k, n) in enumerate(values):
            pos = x[j] + (i - (len(series) - 1) / 2) * width
            if n == 0:
                ax.text(pos, 0.03, "n/a", ha="center", fontsize=7, color="gray", rotation=90)
                continue
            lo, hi = wilson(k, n)
            ax.bar(pos, k / n, width=width, color=color, label=label if j == 0 else None)
            ax.errorbar(pos, k / n, yerr=[[max(0.0, k / n - lo)], [max(0.0, hi - k / n)]], color="black", capsize=2, lw=0.8)
            ax.text(pos, hi + 0.02, f"{k}/{n}", ha="center", va="bottom", fontsize=5.6, rotation=90)


plt.rcParams.update({"font.size": 8.5})
fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.2, 4.0))
x = list(range(len(MODELS)))

bars(a1, x, [
    ("Down: Leader → Worker (A)", "#3b6ea8", [cells[(m, 5, "A")]["spread_given_first"] for m, _ in MODELS]),
    ("Up: Worker → Leader (B)", "#d08a2e", [cells[(m, 5, "B")]["spread_given_first"] for m, _ in MODELS]),
], 0.38)
a1.set_title("(a) Spread to the second role, given the first was deceived", fontsize=8.5)

bars(a2, x, [
    ("Deceived, no check (d5)", "#9b9b9b", [pooled(m, 5, "first_deceived") for m, _ in MODELS]),
    ("Deceived, check allowed (d4)", "#c0504d", [pooled(m, 4, "first_deceived") for m, _ in MODELS]),
    ("Checked the receipt (d4)", "#4f9a6b", [pooled(m, 4, "first_verified") for m, _ in MODELS]),
], 0.27)
a2.set_title("(b) First target: deception and receipt checks", fontsize=8.5)

for ax in (a1, a2):
    ax.set_xticks(x)
    ax.set_xticklabels([label for _, label in MODELS], fontsize=7.5)
    ax.set_ylim(0, 1.32)
    ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_ylabel("Share of trials (95% CI)")
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(fontsize=7, loc="upper center", ncol=1, frameon=False, bbox_to_anchor=(0.5, -0.2), columnspacing=0.8, handlelength=1.2)
fig.tight_layout()
fig.savefig(out, dpi=300)
print("wrote", out)

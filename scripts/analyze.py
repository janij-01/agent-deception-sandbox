"""Pool trials and compute the numbers for the report.

Usage:
    python3 scripts/analyze.py results/plan_<stamp>            # one plan
    python3 scripts/analyze.py results/plan_<stamp> results/X  # pool several folders

Writes analysis.md, analysis.json and (if matplotlib is installed) figure1.png into the
first folder given. Dry-run trials are always excluded.

Rates come with 95% Wilson intervals. Comparisons use a two-sided Fisher exact test.
"First target" is whoever the adversary messages: the Leader in A, the Honest Worker in B.
"""

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path


# ---------- statistics (pure Python so the script runs without scipy) ----------

def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def fisher_exact(a: int, b: int, c: int, d: int) -> float:
    """Two-sided p for the table [[a, b], [c, d]] (sum of tables no more likely than observed)."""
    row1, row2, col1 = a + b, c + d, a + c
    n = row1 + row2
    if n == 0:
        return 1.0

    def prob(x):
        return math.comb(row1, x) * math.comb(row2, col1 - x) / math.comb(n, col1)

    observed = prob(a)
    lo, hi = max(0, col1 - row2), min(row1, col1)
    return min(1.0, sum(p for x in range(lo, hi + 1) if (p := prob(x)) <= observed * (1 + 1e-7)))


# ---------- loading ----------

def load_rows(paths: list[Path]) -> list[dict]:
    rows = []
    for path in paths:
        files = [path] if path.is_file() else sorted(path.rglob("trials.jsonl"))
        for file in files:
            for line in file.read_text().splitlines():
                if not line.strip():
                    continue
                row = json.loads(line)
                if row.get("dry_run"):
                    continue
                first = row.get("first_role") or ("leader" if row["condition"] in ("A", "baseline") else "worker")
                second = "worker" if first == "leader" else "leader"
                row["_first_deceived"] = row.get(f"{first}_deceived")
                row["_second_deceived"] = row.get(f"{second}_deceived")
                row["_first_verified"] = row.get(f"{first}_verified")
                row["_second_verified"] = row.get(f"{second}_verified")
                rows.append(row)
    return rows


def count(rows: list[dict], key: str, where=None) -> tuple[int, int]:
    vals = [r[key] for r in rows if r.get(key) is not None and (where is None or where(r))]
    return sum(1 for v in vals if v), len(vals)


def fmt(k: int, n: int) -> str:
    if n == 0:
        return "-"
    lo, hi = wilson(k, n)
    return f"{k}/{n} = {k / n:.0%} [{lo:.0%}, {hi:.0%}]"


def fmt_p(p: float) -> str:
    return "p < 0.001" if p < 0.001 else f"p = {p:.3f}"


# ---------- analysis ----------

def analyse(rows: list[dict]) -> dict:
    cells = defaultdict(list)
    for row in rows:
        cells[(row.get("model", "?"), row["difficulty"], row["condition"])].append(row)

    table = []
    for (model, difficulty, condition), group in sorted(cells.items()):
        entry = {"model": model, "difficulty": difficulty, "condition": condition, "trials": len(group)}
        for name, key, where in [
            ("first_deceived", "_first_deceived", None),
            ("second_deceived", "_second_deceived", None),
            ("spread_given_first", "_second_deceived", lambda r: r.get("_first_deceived") is True),
            ("first_verified", "_first_verified", None),
            ("second_verified", "_second_verified", None),
        ]:
            entry[name] = count(group, key, where)
        table.append(entry)

    tests = []
    by_model = defaultdict(list)
    for row in rows:
        by_model[row.get("model", "?")].append(row)
    for model, mrows in sorted(by_model.items()):
        for difficulty in sorted({r["difficulty"] for r in mrows}):
            drows = [r for r in mrows if r["difficulty"] == difficulty]
            a = [r for r in drows if r["condition"] == "A"]
            b = [r for r in drows if r["condition"] == "B"]
            if not a or not b:
                continue
            tests.append(_compare(model, difficulty, "RQ1: first target deceived, Leader (A) vs Honest Worker (B)",
                                  count(a, "_first_deceived"), count(b, "_first_deceived")))
            tests.append(_compare(model, difficulty, "RQ2: spread given first deceived, down (A) vs up (B)",
                                  count(a, "_second_deceived", lambda r: r.get("_first_deceived") is True),
                                  count(b, "_second_deceived", lambda r: r.get("_first_deceived") is True)))
            if count(a, "_first_verified")[1] and count(b, "_first_verified")[1]:
                tests.append(_compare(model, difficulty, "Verification when first: Leader (A) vs Honest Worker (B)",
                                      count(a, "_first_verified"), count(b, "_first_verified")))
                both = a + b
                tests.append(_compare(model, difficulty,
                                      "Verification by position: first vs second (A+B; same trials, approximate)",
                                      count(both, "_first_verified"), count(both, "_second_verified")))
        attack = [r for r in mrows if r["condition"] in ("A", "B")]
        d5 = [r for r in attack if r["difficulty"] == 5]
        d4 = [r for r in attack if r["difficulty"] == 4]
        if d5 and d4:
            tests.append(_compare(model, "4 vs 5", "Information access: first target deceived, no check (d5) vs check (d4)",
                                  count(d5, "_first_deceived"), count(d4, "_first_deceived")))
    return {"cells": table, "tests": tests}


def _compare(model, difficulty, label, x, y) -> dict:
    (k1, n1), (k2, n2) = x, y
    p = fisher_exact(k1, n1 - k1, k2, n2 - k2) if n1 and n2 else float("nan")
    return {"model": model, "difficulty": difficulty, "test": label, "group1": [k1, n1], "group2": [k2, n2], "p": p}


def to_markdown(result: dict) -> str:
    lines = ["# Analysis", "", "Rates with 95% Wilson intervals. First target = Leader in A, Honest Worker in B.", "",
             "## Table 1. Deception and verification by cell", "",
             "| Model | Diff. | Condition | Trials | First target deceived | Second deceived | Spread given first deceived | First verified | Second verified |",
             "|---|---|---|---|---|---|---|---|---|"]
    for c in result["cells"]:
        lines.append("| {model} | {difficulty} | {condition} | {trials} | {a} | {b} | {c} | {d} | {e} |".format(
            **c, a=fmt(*c["first_deceived"]), b=fmt(*c["second_deceived"]), c=fmt(*c["spread_given_first"]),
            d=fmt(*c["first_verified"]), e=fmt(*c["second_verified"])))
    lines += ["", "## Table 2. Comparisons (two-sided Fisher exact test)", "",
              "| Model | Diff. | Comparison | Group 1 | Group 2 | p |", "|---|---|---|---|---|---|"]
    for t in result["tests"]:
        lines.append(f"| {t['model']} | {t['difficulty']} | {t['test']} | {fmt(*t['group1'])} | {fmt(*t['group2'])} | "
                     f"{fmt_p(t['p']) if t['p'] == t['p'] else '-'} |")
    lines += ["", "Several comparisons are reported; treat p values near 0.05 as suggestive, not confirmed."]
    return "\n".join(lines) + "\n"


def make_figure(result: dict, path: Path) -> bool:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return False
    cells = {(c["model"], c["difficulty"], c["condition"]): c for c in result["cells"]}
    models = sorted({m for (m, d, c) in cells if c in ("A", "B") and d in (4, 5)})
    if not models:
        return False
    panels = [
        ("Deception (receipt total hidden)", [
            ("d5 no check\nfirst target deceived", 5, "first_deceived"),
            ("d5 no check\nspread | first deceived", 5, "spread_given_first"),
            ("d4 check allowed\nfirst target deceived", 4, "first_deceived"),
        ]),
        ("Receipt verification (d4)", [
            ("first recipient\nverified", 4, "first_verified"),
            ("second recipient\nverified", 4, "second_verified"),
        ]),
    ]
    colors = {"A": "#3b6ea8", "B": "#d08a2e"}
    names = {"A": "A: Leader messaged first", "B": "B: Honest Worker messaged first"}
    fig, axes = plt.subplots(len(models), 2, figsize=(11, 3.8 * len(models)), squeeze=False,
                             gridspec_kw={"width_ratios": [3, 2]})
    width = 0.38
    for row, model in enumerate(models):
        for col, (title, groups) in enumerate(panels):
            ax = axes[row][col]
            for g, (label, difficulty, key) in enumerate(groups):
                for i, condition in enumerate(("A", "B")):
                    cell = cells.get((model, difficulty, condition))
                    if cell is None or cell[key][1] == 0:
                        continue
                    k, n = cell[key]
                    lo, hi = wilson(k, n)
                    x = g + (i - 0.5) * width
                    ax.bar(x, k / n, width=width, color=colors[condition], label=names[condition] if g == 0 else None)
                    ax.errorbar(x, k / n, yerr=[[k / n - lo], [hi - k / n]], color="black", capsize=3, lw=1)
                    ax.text(x, hi + 0.03, f"{k}/{n}", ha="center", fontsize=8)
            ax.set_xticks(range(len(groups)))
            ax.set_xticklabels([g[0] for g in groups], fontsize=8)
            ax.set_ylim(0, 1.18)
            ax.set_ylabel("Rate (95% Wilson CI)")
            ax.set_title(f"{model}: {title}", fontsize=10)
            if col == 0:
                ax.legend(fontsize=8, loc="upper right")
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    return True


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--out", type=Path, default=None, help="default: the first path given")
    args = parser.parse_args(argv)
    rows = load_rows(args.paths)
    if not rows:
        sys.exit("no non-dry-run trials found")
    result = analyse(rows)
    out = args.out or (args.paths[0] if args.paths[0].is_dir() else args.paths[0].parent)
    out.mkdir(parents=True, exist_ok=True)
    markdown = to_markdown(result)
    (out / "analysis.md").write_text(markdown)
    (out / "analysis.json").write_text(json.dumps(result, indent=2) + "\n")
    print(markdown)
    if make_figure(result, out / "figure1.png"):
        print(f"wrote {out / 'figure1.png'}")
    else:
        print("matplotlib not installed or no A/B cells at difficulty 4/5: no figure (pip install matplotlib)")
    print(f"wrote {out / 'analysis.md'}")


if __name__ == "__main__":
    main()

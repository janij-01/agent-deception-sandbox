"""Run the full experiment matrix for the report.

Sample sizes follow recent Apart sprint entries (roughly 12 to 50 trials per condition)
and a power check on the pilot rates: n=50 gives ~0.95 power for an 80% vs 100%
first-target difference, n=30 only ~0.6.

Usage:
    python3 scripts/run_plan.py --workers 6
    python3 scripts/run_plan.py --workers 6 --second-model <model-id>
    python3 scripts/run_plan.py --only second --second-model <model-id>
    python3 scripts/run_plan.py --dry-run          # check the plan without API calls

Each step writes its own results/<plan>/<step>/ folder and is skipped if that folder
already has a summary.json, so rerunning the same --plan-dir resumes after a crash.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sandbox.run import main as run_main  # noqa: E402

SEED = 100  # pilots used seed 1, so formal runs never reuse pilot trials

# (step name, difficulty, conditions, n per condition)
MAIN_PLAN = [
    ("d5_attack", 5, ["A", "B"], 50),        # RQ1 and RQ2 rest on this cell
    ("d4_attack", 4, ["A", "B"], 30),        # who verifies the receipt
    ("d5_baseline", 5, ["baseline"], 20),
    ("d4_baseline", 4, ["baseline"], 20),
    ("d3_full_info", 3, ["baseline", "A", "B"], 15),  # rerun after the packet fix
]
SECOND_PLAN = [
    ("d5", 5, ["baseline", "A", "B"], 30),
    ("d4", 4, ["baseline", "A", "B"], 30),
]


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--main-model", default=None, help="default: ADAPTION_MODEL or qwen3.8-27b")
    parser.add_argument("--second-model", default=None)
    parser.add_argument("--only", choices=["main", "second"], default=None)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--plan-dir", type=Path, default=None, help="reuse to resume an interrupted plan")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    plan_dir = args.plan_dir or ROOT / "results" / f"plan_{'dry_' if args.dry_run else ''}{stamp}"
    plan_dir.mkdir(parents=True, exist_ok=True)

    steps = []
    if args.only in (None, "main"):
        steps += [("main", args.main_model, *step) for step in MAIN_PLAN]
    if args.only in (None, "second"):
        if args.second_model:
            steps += [("second", args.second_model, *step) for step in SECOND_PLAN]
        elif args.only == "second":
            parser.error("--only second needs --second-model")

    total_trials = sum(len(conds) * n for *_, conds, n in steps)
    print(f"plan: {len(steps)} steps, {total_trials} trials -> {plan_dir}", flush=True)

    for group, model, name, difficulty, conditions, n in steps:
        out = plan_dir / f"{group}_{name}"
        if (out / "summary.json").exists():
            print(f"skip {out.name}: already done", flush=True)
            continue
        print(f"\n=== {out.name}: difficulty {difficulty}, {conditions}, n={n}", flush=True)
        cli = ["--difficulty", str(difficulty), "--n", str(n), "--seed", str(SEED),
               "--workers", str(args.workers), "--out", str(out), "--conditions", *conditions]
        if model:
            cli += ["--model", model]
        if args.dry_run:
            cli.append("--dry-run")
        run_main(cli)

    (plan_dir / "plan.json").write_text(json.dumps({
        "seed": SEED,
        "main": MAIN_PLAN if args.only in (None, "main") else [],
        "second_model": args.second_model,
        "second": SECOND_PLAN if args.second_model and args.only in (None, "second") else [],
    }, indent=2) + "\n")
    print(f"\nplan finished. Analyse with:\n  python3 scripts/analyze.py {plan_dir}")


if __name__ == "__main__":
    main()

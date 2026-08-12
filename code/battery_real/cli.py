"""CLI for the source-neutral measured-data validation runner."""
from __future__ import annotations

import argparse
import json
import sys

from .core import evaluate, load_csv, write_artifacts


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="V2 canonical battery data Q1/Q2 validation")
    parser.add_argument("input_csv")
    parser.add_argument("--out", default="battery_real_output")
    parser.add_argument("--horizon", type=int, default=10)
    parser.add_argument("--history-window", type=int, default=20)
    parser.add_argument("--splits", type=int, default=5)
    parser.add_argument("--bootstrap-reps", type=int, default=300)
    parser.add_argument("--seed", type=int, default=20260812)
    parser.add_argument("--leave-condition-out", action="store_true")
    parser.add_argument("--test-only", action="store_true", help="mark output as TEST_ONLY; never paper evidence")
    args = parser.parse_args(argv)
    rows = load_csv(args.input_csv)
    report = evaluate(
        rows,
        horizon=args.horizon,
        history_window=args.history_window,
        n_splits=args.splits,
        bootstrap_reps=args.bootstrap_reps,
        seed=args.seed,
        leave_condition_out=args.leave_condition_out,
        test_only=True if args.test_only else None,
    )
    paths = write_artifacts(report, args.out)
    print(json.dumps({"status": report["status"], "scope": report["scope"], "artifacts": paths}, ensure_ascii=False))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())

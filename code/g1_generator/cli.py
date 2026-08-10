"""G1 CLI：生成退化数据集、CSV、数据字典、4 类图，并写出运行清单。

用法：
    python -m g1_generator.cli --config configs/g1_smoke.json --out g1_output
"""
from __future__ import annotations

import os
import sys
import json
import argparse
import hashlib

from . import config as cfgmod
from . import simulate


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main(argv=None):
    parser = argparse.ArgumentParser(description="G1 退化数据生成器")
    parser.add_argument("--config", default=cfgmod.DEFAULT_CONFIG_PATH)
    parser.add_argument("--out", default="g1_output")
    parser.add_argument("--seed", type=int, default=None, help="覆盖配置中的 seed")
    args = parser.parse_args(argv)

    cfg = cfgmod.load_config(args.config)
    if args.seed is not None:
        cfg.seed = args.seed

    result = simulate.run(cfg, args.out)

    # 运行清单（供 A1 证据包引用）
    config_sha = sha256_text(open(args.config, "r", encoding="utf-8").read())
    manifest = {
        "command": f"python -m g1_generator.cli --config {args.config} --out {args.out}"
                   + (f" --seed {cfg.seed}" if args.seed is not None else ""),
        "seed": cfg.seed,
        "config_path": os.path.abspath(args.config),
        "config_sha256": config_sha,
        "chemistry": cfg.chemistry,
        "n_cells": result["meta"]["n_cells"],
        "n_rows": result["meta"]["n_rows"],
        "scenarios": result["meta"]["scenarios"],
        "csv": os.path.abspath(result["csv"]),
        "csv_sha256": result["csv_sha256"],
        "dictionary": os.path.abspath(result["dictionary"]),
        "dictionary_sha256": result["dictionary_sha256"],
        "figures": {k: os.path.abspath(v) for k, v in result["figures"].items()},
        "figure_sha256": result["figure_sha256"],
    }
    manifest_path = os.path.join(args.out, "run_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print("G1 生成完成")
    print(f"  seed              : {cfg.seed}")
    print(f"  cells / rows      : {result['meta']['n_cells']} / {result['meta']['n_rows']}")
    print(f"  CSV               : {result['csv']}")
    print(f"  CSV SHA-256       : {result['csv_sha256']}")
    print(f"  数据字典 SHA-256  : {result['dictionary_sha256']}")
    print(f"  图                : {', '.join(result['figures'].values())}")
    print(f"  运行清单          : {manifest_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

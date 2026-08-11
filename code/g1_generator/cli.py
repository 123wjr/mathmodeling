"""G1 CLI：生成退化数据集、CSV、数据字典、4 类图，并写出运行清单。

用法：
    PYTHONPATH=code python -m g1_generator.cli --config configs/g1_smoke.json --out g1_output
"""
from __future__ import annotations

import os
import sys
import json
import argparse
import shlex

from . import config as cfgmod
from . import simulate


def _relative_manifest_path(path: str, base_dir: str) -> str:
    """Return a portable path without embedding a contributor's machine root."""
    return os.path.relpath(os.path.abspath(path), base_dir).replace(os.sep, "/")


def _reproduction_command(config_path: str, out_dir: str, seed_override, base_dir: str) -> str:
    code_path = _relative_manifest_path(os.path.join(cfgmod.PROJECT_ROOT, "code"), base_dir)
    config_arg = _relative_manifest_path(config_path, base_dir)
    out_arg = _relative_manifest_path(out_dir, base_dir)
    parts = [
        f"PYTHONPATH={shlex.quote(code_path)}",
        "python", "-m", "g1_generator.cli",
        "--config", shlex.quote(config_arg),
        "--out", shlex.quote(out_arg),
    ]
    if seed_override is not None:
        parts.extend(["--seed", str(seed_override)])
    return " ".join(parts)


def main(argv=None):
    parser = argparse.ArgumentParser(description="G1 退化数据生成器")
    parser.add_argument("--config", default=None)
    parser.add_argument("--out", default="g1_output")
    parser.add_argument("--seed", type=int, default=None, help="覆盖配置中的 seed")
    args = parser.parse_args(argv)

    config_path = args.config or cfgmod.DEFAULT_CONFIG_PATH
    cfg = cfgmod.load_config(config_path)
    if args.seed is not None:
        cfg.seed = args.seed

    result = simulate.run(cfg, args.out)

    # 运行清单只保存相对路径，避免把某位贡献者的盘符或主目录写进证据包。
    base_dir = os.getcwd()
    manifest = {
        "manifest_version": 1,
        "path_base": "command working directory",
        "command": _reproduction_command(config_path, args.out, args.seed, base_dir),
        "seed": cfg.seed,
        "config_path": _relative_manifest_path(config_path, base_dir),
        "config_sha256": simulate.sha256_file(config_path),
        "chemistry": cfg.chemistry,
        "n_cells": result["meta"]["n_cells"],
        "n_rows": result["meta"]["n_rows"],
        "scenarios": result["meta"]["scenarios"],
        "scenario_specs": result["meta"]["scenario_specs"],
        "csv": _relative_manifest_path(result["csv"], base_dir),
        "csv_sha256": result["csv_sha256"],
        "dictionary": _relative_manifest_path(result["dictionary"], base_dir),
        "dictionary_sha256": result["dictionary_sha256"],
        "figures": {
            key: _relative_manifest_path(path, base_dir)
            for key, path in result["figures"].items()
        },
        "figure_sha256": result["figure_sha256"],
    }
    manifest_path = os.path.join(args.out, "run_manifest.json")
    with open(manifest_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False, sort_keys=True)
        f.write("\n")

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

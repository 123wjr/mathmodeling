"""Command-line entry for the independent V3 evidence package."""
from __future__ import annotations

import argparse
import os
import sys

from . import config, v3


def main(argv=None):
    parser = argparse.ArgumentParser(description="A题 V3 退役决策闭环")
    parser.add_argument("--config", default="configs/study_pipeline_v3.json")
    parser.add_argument("--out", default="study_output_v3")
    args = parser.parse_args(argv)
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    out_dir = v3.validate_output_dir(project_root, args.out)
    study_cfg = config.load_config(args.config)
    object.__setattr__(study_cfg, "_loaded_path", os.path.abspath(args.config))
    settings = v3.load_settings(args.config)
    result = v3.run(study_cfg, settings, out_dir)
    print(f"V3 validation gates: {len(result['gates'])} PASS")
    print(f"V3 manifest verification: {result['manifest_verification']['status']}")
    print(f"V3 manifest: {result['manifest']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

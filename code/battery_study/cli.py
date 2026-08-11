"""命令行入口：生成 G2-G4 全部实验和论文技术证据。"""
from __future__ import annotations

import argparse
import os
import sys

from . import config, pipeline


def main(argv=None):
    parser = argparse.ArgumentParser(description="A题 G2-G4 可复现实验流水线")
    parser.add_argument("--config", default=config.DEFAULT_CONFIG_PATH)
    parser.add_argument("--out", default="study_output")
    args = parser.parse_args(argv)
    cfg = config.load_config(args.config)
    # Preserve the exact loaded path for the reproducibility manifest without
    # changing the frozen dataclass API.
    object.__setattr__(cfg, "_loaded_path", os.path.abspath(args.config))
    result = pipeline.run(cfg, os.path.abspath(args.out))
    print("G2-G4 研究流水线完成")
    print(f"  validation gates : {len(result['gates'])} PASS")
    print(f"  figures          : {len(result['figures'])}")
    print(f"  documents        : {len(result['documents'])}")
    print(f"  manifest         : {result['manifest']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .pipeline import PipelineError, run_pipeline


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description="Build deterministic Vireo Audio support metrics.")
    for table in ("tickets", "agents", "customers", "orders", "products"):
        value.add_argument(f"--{table}", required=True, type=Path, help=f"Path to {table}.csv")
    value.add_argument("--output-dir", required=True, type=Path)
    return value


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    paths = {table: getattr(args, table) for table in ("tickets", "agents", "customers", "orders", "products")}
    try:
        result = run_pipeline(paths, args.output_dir)
    except (OSError, PipelineError) as exc:
        print(f"Pipeline failed: {exc}")
        return 1
    print(json.dumps(result["counts"], indent=2))
    print(f"Warnings: {len(result['warnings'])} categories; see {args.output_dir / 'data_quality_report.json'}")
    return 0

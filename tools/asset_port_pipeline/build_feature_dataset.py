from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any, Dict, List

SCRIPT_DIR = Path(__file__).resolve().parent

import sys

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common import (  # noqa: E402
    discover_files,
    feature_vector_from_xmodel_summary,
    save_json,
    summarize_xmodel,
)


def summarize_vectors(vectors: List[List[float]]) -> Dict[str, List[float]]:
    if not vectors:
        return {"mean": [], "std": []}
    dim = len(vectors[0])
    means: List[float] = []
    stds: List[float] = []
    for idx in range(dim):
        column = [row[idx] for row in vectors]
        mean = sum(column) / float(len(column))
        variance = sum((value - mean) ** 2 for value in column) / float(len(column))
        std = variance ** 0.5
        means.append(mean)
        stds.append(std if std > 1e-8 else 1.0)
    return {"mean": means, "std": stds}


def make_corrupt_sample(summary: Dict[str, Any], rng: random.Random) -> Dict[str, Any]:
    sample = dict(summary)
    sample["version"] = 7
    sample["num_bones"] = int(sample.get("num_bones", 0)) + rng.randint(64, 192)
    sample["max_vertex_influences"] = max(5, int(sample.get("max_vertex_influences", 0)) + rng.randint(1, 4))
    sample["num_verts"] = int(sample.get("num_verts", 0) * rng.uniform(1.1, 2.0))
    sample["num_faces"] = int(sample.get("num_faces", 0) * rng.uniform(1.1, 2.0))
    sample["invalid_weight_sums"] = max(1, int(sample.get("invalid_weight_sums", 0)) + rng.randint(1, 4))
    return sample


def parse_model_files(paths: List[Path], label: int, domain: str, max_count: int) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for path in paths:
        try:
            summary = summarize_xmodel(path)
        except Exception:
            continue
        vector, feature_names = feature_vector_from_xmodel_summary(summary)
        rows.append(
            {
                "path": str(path),
                "label": label,
                "domain": domain,
                "features": vector,
                "feature_names": feature_names,
            }
        )
        if max_count > 0 and len(rows) >= max_count:
            break
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Build feature dataset for adversarial BO3->BO2 training.")
    parser.add_argument(
        "--bo2-root",
        default="_build/t6_asset_dump/zone_raw",
        help="BO2 xmodel_export root.",
    )
    parser.add_argument(
        "--source-root",
        default="",
        help="Optional source root (for BO3 xmodel_export) used as negative class.",
    )
    parser.add_argument(
        "--negative-mode",
        choices=("source", "corrupt", "source+corrupt"),
        default="source+corrupt",
        help="How to build negative samples.",
    )
    parser.add_argument("--max-pos", type=int, default=0, help="Cap BO2 positives (0 = all).")
    parser.add_argument("--max-neg", type=int, default=0, help="Cap negatives (0 = all available).")
    parser.add_argument("--seed", type=int, default=1337, help="Random seed.")
    parser.add_argument(
        "--output-dir",
        default="_build/asset_port_pipeline/dataset",
        help="Output directory for dataset files.",
    )
    args = parser.parse_args()

    rng = random.Random(args.seed)
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    bo2_root = Path(args.bo2_root).resolve()
    bo2_files = discover_files([bo2_root], "*.xmodel_export")
    if not bo2_files:
        raise FileNotFoundError(f"No BO2 xmodel_export files found in {bo2_root}")

    pos_rows = parse_model_files(bo2_files, label=1, domain="bo2", max_count=args.max_pos)
    if not pos_rows:
        raise RuntimeError("No positive samples could be parsed")

    neg_rows: List[Dict[str, Any]] = []
    if args.negative_mode in ("source", "source+corrupt"):
        if not args.source_root:
            print("source negative mode requested but --source-root not provided; skipping source negatives")
        else:
            source_root = Path(args.source_root).resolve()
            source_files = discover_files([source_root], "*.xmodel_export")
            source_parsed = parse_model_files(source_files, label=0, domain="source", max_count=args.max_neg)
            neg_rows.extend(source_parsed)

    if args.negative_mode in ("corrupt", "source+corrupt"):
        max_corrupt = args.max_neg if args.max_neg > 0 else len(pos_rows)
        for row in pos_rows:
            if len([item for item in neg_rows if item["domain"] == "corrupt"]) >= max_corrupt:
                break
            feature_names = row["feature_names"]
            fake_summary = {name: value for name, value in zip(feature_names, row["features"])}
            corrupt_summary = make_corrupt_sample(fake_summary, rng)
            vector, _ = feature_vector_from_xmodel_summary(corrupt_summary)
            neg_rows.append(
                {
                    "path": row["path"] + "::corrupt",
                    "label": 0,
                    "domain": "corrupt",
                    "features": vector,
                    "feature_names": feature_names,
                }
            )

    if args.max_neg > 0:
        neg_rows = neg_rows[: args.max_neg]

    if not neg_rows:
        raise RuntimeError("No negative samples built; provide --source-root or use --negative-mode corrupt")

    all_rows = pos_rows + neg_rows
    vectors = [row["features"] for row in all_rows]
    stats = summarize_vectors(vectors)

    dataset_path = output_dir / "dataset.jsonl"
    with dataset_path.open("w", encoding="utf-8") as handle:
        for row in all_rows:
            handle.write(json.dumps(row) + "\n")

    meta = {
        "counts": {
            "total": len(all_rows),
            "positive": len(pos_rows),
            "negative": len(neg_rows),
        },
        "feature_names": all_rows[0]["feature_names"],
        "normalization": stats,
        "paths": {
            "bo2_root": str(bo2_root),
            "source_root": str(Path(args.source_root).resolve()) if args.source_root else "",
        },
    }
    save_json(output_dir / "dataset_meta.json", meta)

    print(f"Saved dataset: {dataset_path}")
    print(
        f"Counts: total={meta['counts']['total']} "
        f"positive={meta['counts']['positive']} "
        f"negative={meta['counts']['negative']}"
    )


if __name__ == "__main__":
    main()


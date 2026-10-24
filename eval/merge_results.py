#!/usr/bin/env python3
"""Merge VulRepair shard predictions into one table and compare with the paper.

Shard CSVs are written by ``kaggle/vulrepair_eval.py`` as
``beam<B>_<start>_<end>.csv`` (columns: raw_predictions, correctly_predicted).
The official test split (``test.csv`` from MickyMike/cvefixes_bigvul) gives
the row order and ``cwe_id``/``source``/``target``.

Example:
    python eval/merge_results.py \
        --preds kaggle-output/preds kaggle-output-shard2/preds \
        --test /tmp/test.csv \
        --paper /tmp/VulRepair/data/VulRepair_raw_predictions/\
vulrepair_raw_preds_for_cve_fixes_test.csv \
        --beams 50 --out docs/results
"""

import argparse
import glob
import os
import re
import sys

import pandas as pd

SHARD_RE = re.compile(r"beam(\d+)_(\d+)_(\d+)\.csv$")


def load_shards(pred_dirs, beams, n_rows, allow_partial=False):
    shards = {}
    for pred_dir in pred_dirs:
        for path in glob.glob(os.path.join(pred_dir, f"beam{beams}_*.csv")):
            m = SHARD_RE.search(path)
            if not m or int(m.group(1)) != beams:
                continue
            start, end = int(m.group(2)), int(m.group(3))
            if start in shards:
                sys.exit(f"duplicate shard start {start}: {path} and {shards[start]}")
            shards[start] = (end, path)

    if not shards:
        sys.exit(f"no beam{beams} shard CSVs in {pred_dirs}")

    ordered = [shards[s] for s in sorted(shards)]
    cursor = 0
    for start, (end, path) in zip(sorted(shards), ordered):
        if start < cursor:
            sys.exit(f"overlapping shard: {path}")
        if not allow_partial and start != cursor:
            sys.exit(f"gap: expected shard starting at {cursor}, got {start} ({path})")
        cursor = end
    if not allow_partial and cursor != n_rows:
        sys.exit(f"coverage ends at {cursor}, expected {n_rows} rows")
    return [(s, e, p) for s, (e, p) in zip(sorted(shards), ordered)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preds", nargs="+", required=True,
                    help="directories containing beam<B>_<start>_<end>.csv")
    ap.add_argument("--test", required=True,
                    help="official test.csv (1,706 rows)")
    ap.add_argument("--paper", default=None,
                    help="paper raw predictions CSV (used when --beams 50)")
    ap.add_argument("--beams", type=int, default=50)
    ap.add_argument("--out", default="results")
    ap.add_argument("--top", type=int, default=15,
                    help="number of CWE rows in the table (by test count)")
    ap.add_argument("--allow-partial", action="store_true",
                    help="accept missing shards (for intermediate checks)")
    args = ap.parse_args()

    test = pd.read_csv(args.test, keep_default_na=False)
    if len(test) != 1706:
        sys.exit(f"test CSV has {len(test)} rows, expected 1,706")

    parts = []
    for start, end, path in load_shards(args.preds, args.beams, len(test),
                                        args.allow_partial):
        part = pd.read_csv(path, keep_default_na=False)
        if len(part) != end - start:
            sys.exit(f"{path}: {len(part)} rows, expected {end - start}")
        part.insert(0, "row", range(start, end))
        part["cwe_id"] = test["cwe_id"].iloc[start:end].values
        part["cve_id"] = test["cve_id"].iloc[start:end].values
        part["source"] = test["source"].iloc[start:end].values
        part["target"] = test["target"].iloc[start:end].values
        parts.append(part)

    pred = pd.concat(parts, ignore_index=True)
    os.makedirs(args.out, exist_ok=True)
    merged_csv = os.path.join(
        args.out, f"vulrepair_predictions_beam{args.beams}.csv")
    pred.to_csv(merged_csv, index=False)

    ours = float(pred["correctly_predicted"].mean())
    hits = int(pred["correctly_predicted"].sum())
    lines = [
        f"# VulRepair M1 — beam {args.beams}",
        "",
        f"- rows: {len(pred)}",
        f"- Perfect Prediction (ours): **{ours:.4f}** ({hits}/{len(pred)})",
    ]
    meta = {"beams": args.beams, "rows": len(pred), "pp_ours": ours,
            "hits": hits}

    if args.paper and args.beams == 50:
        paper = pd.read_csv(args.paper, keep_default_na=False)
        paper_key = pd.MultiIndex.from_frame(paper[["source", "target"]])
        p_ok = pd.Series(paper["correctly_predicted"].values, index=paper_key)
        p_raw = pd.Series(paper["raw_predictions"].values, index=paper_key)
        keep = ~p_ok.index.duplicated(keep="first")
        p_ok, p_raw = p_ok[keep], p_raw[keep]
        key = pd.MultiIndex.from_frame(pred[["source", "target"]])
        ok_aligned = p_ok.reindex(key)
        raw_aligned = p_raw.reindex(key)
        missing = int(ok_aligned.isna().sum())
        if missing:
            sys.exit(f"{missing} predictions could not be aligned to the paper CSV")
        agree = float((pred["correctly_predicted"].values == ok_aligned.values).mean())
        raw_agree = float((pred["raw_predictions"].values == raw_aligned.values).mean())
        paper_pp = float(paper["correctly_predicted"].mean())
        lines += [
            f"- Perfect Prediction (paper, {len(paper)} rows): **{paper_pp:.4f}** "
            f"({int(paper['correctly_predicted'].sum())}/{len(paper)})",
            f"- per-row correctness agreement: **{agree:.4f}**",
            f"- per-row prediction-string agreement: **{raw_agree:.4f}**",
        ]
        meta.update(pp_paper=paper_pp, correctness_agreement=agree,
                    prediction_string_agreement=raw_agree)

    g = pred.groupby("cwe_id")["correctly_predicted"].agg(n="size", hits="sum")
    g = g.assign(pp=g["hits"] / g["n"])
    g = g.sort_values("n", ascending=False).head(args.top)
    lines += [
        "",
        f"| CWE | n | hits | PP |",
        "|---|---|---|---|",
    ]
    for cwe, row in g.iterrows():
        lines.append(f"| {cwe} | {int(row['n'])} | {int(row['hits'])} | "
                     f"{row['pp']:.3f} |")

    report = os.path.join(args.out, f"results_beam{args.beams}.md")
    with open(report, "w") as fh:
        fh.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"\nwrote {merged_csv}\nwrote {report}")


if __name__ == "__main__":
    main()

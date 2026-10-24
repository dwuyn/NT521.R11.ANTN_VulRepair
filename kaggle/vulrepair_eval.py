"""VulRepair (M1) evaluation on Kaggle GPU via `kaggle kernels push`.

Pinned stack from the paper repo (Python 3.9, torch 1.10.2+cu113,
transformers 4.19.1) installed with uv. The test split and checkpoint are
downloaded to /root so the old `datasets`/`huggingface_hub` versions never
talk to the HF API at run time.

The 1,706 test rows are split into SHARDS; each shard is an independent
process (one per GPU when the T4 x2 accelerator is available), and the
per-shard prediction CSVs are merged and compared with the paper's raw
predictions.  Note: the paper CSV is ordered differently from the HF test
CSV, so rows are aligned by (source, target), not by position.

Usage (from the repo root):
    kaggle kernels push -p kaggle --accelerator NvidiaTeslaT4
    kaggle kernels status  tdwuyn/vulrepair-eval
    kaggle kernels logs    tdwuyn/vulrepair-eval
    kaggle kernels output  tdwuyn/vulrepair-eval -p kaggle-output
"""

import json
import os
import shutil
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = "/root"
WORK = "/kaggle/working"
REPO = f"{ROOT}/VulRepair"
CKPT = f"{ROOT}/VulRepair_ckpt"
VENV = f"{ROOT}/venv39"
PY = f"{VENV}/bin/python"
HF = "https://huggingface.co/MickyMike/VulRepair/resolve/main"
CKPT_FILES = [
    "config.json", "pytorch_model.bin", "vocab.json", "merges.txt",
    "tokenizer_config.json", "special_tokens_map.json", "added_tokens.json",
]
TEST_CSV = f"{ROOT}/test.csv"
TEST_URL = ("https://huggingface.co/datasets/MickyMike/cvefixes_bigvul/"
            "resolve/main/test.csv")

BEAMS = 50
PARALLEL_GPUS = 2
# (start, end) over the 1,706 test rows. 427 rows/shard keeps each process
# well inside the 12 h GPU session limit.
SHARDS = [(0, 427), (427, 854), (854, 1281), (1281, 1706)]

SCRIPT = f"{REPO}/M1_VulRepair_PL-NL/vulrepair_main.py"
PRED_DIR = f"{WORK}/preds"
T0 = time.time()


def log(msg):
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


def run(cmd, cwd=None, env=None):
    log("+ " + " ".join(cmd))
    started = time.time()
    subprocess.run(cmd, cwd=cwd, env=env, check=True)
    log(f"  done in {time.time() - started:.1f}s")


def setup_env():
    if os.path.exists(PY):
        return
    log("installing pinned env (python 3.9 + torch 1.10.2 cu113)")
    run(["uv", "venv", "--python", "3.9", VENV])
    run(["uv", "pip", "install", "--python", PY,
         "https://download.pytorch.org/whl/cu113/"
         "torch-1.10.2%2Bcu113-cp39-cp39-linux_x86_64.whl"])
    run(["uv", "pip", "install", "--python", PY,
         "transformers==4.19.1", "numpy==1.22.3", "tqdm==4.62.3",
         "pandas==1.4.1", "tokenizers==0.11.6", "datasets==2.0.0",
         "gdown==4.5.1", "tensorboard==2.8.0", "scikit-learn==1.1.2",
         "huggingface-hub==0.8.1", "pyarrow==7.0.0",
         "setuptools==59.5.0", "wheel==0.37.1", "protobuf==3.20.1"])
    run([PY, "-c", "import torch, transformers, datasets;"
         "print('torch', torch.__version__, 'cuda', torch.version.cuda,"
         "'avail', torch.cuda.is_available());"
         "print('gpu', torch.cuda.get_device_name(0));"
         "print('transformers', transformers.__version__,"
         "'datasets', datasets.__version__)"])


def setup_inputs():
    if not os.path.isdir(REPO):
        run(["git", "clone", "--depth", "1",
             "https://github.com/awsm-research/VulRepair", REPO])
    os.makedirs(CKPT, exist_ok=True)
    for name in CKPT_FILES:
        path = f"{CKPT}/{name}"
        if not os.path.exists(path):
            run(["curl", "-sSL", "-o", path, f"{HF}/{name}"])
        log(f"  {name}: {os.path.getsize(path) / 1e6:.1f} MB")
    if not os.path.exists(TEST_CSV):
        run(["curl", "-sSL", "-o", TEST_CSV, TEST_URL])
    log(f"  test.csv: {os.path.getsize(TEST_CSV) / 1e6:.2f} MB")


def gpu_count():
    out = subprocess.check_output(
        [PY, "-c", "import torch; print(torch.cuda.device_count())"])
    return int(out.strip())


def run_shard(start, end, gpu):
    started = time.time()
    tag = f"beam{BEAMS}_{start}_{end}"
    run_dir = f"{WORK}/runs/{tag}"
    os.makedirs(f"{run_dir}/raw_predictions", exist_ok=True)
    os.makedirs(f"{run_dir}/saved_models/checkpoint-best-loss", exist_ok=True)

    link = f"{run_dir}/saved_models/checkpoint-best-loss/model.bin"
    if not os.path.exists(link):
        os.symlink(f"{CKPT}/pytorch_model.bin", link)

    driver = f"{run_dir}/drive.py"
    with open(driver, "w") as fh:
        fh.write(f'''
import os, runpy, sys
import pandas as pd
import datasets

df = pd.read_csv("{TEST_CSV}").iloc[{start}:{end}]
print("shard rows:", len(df), flush=True)


class _Split:
    def __init__(self, frame):
        self.d = {{"source": frame["source"].tolist(),
                   "target": frame["target"].tolist()}}

    def __getitem__(self, key):
        return self.d[key]


datasets.load_dataset = lambda *a, **k: _Split(df)
sys.argv = ["vulrepair_main.py",
    "--output_dir=./saved_models", "--model_name=model.bin",
    "--tokenizer_name={CKPT}", "--model_name_or_path={CKPT}",
    "--do_test", "--encoder_block_size", "512", "--decoder_block_size", "256",
    "--num_beams", "{BEAMS}", "--eval_batch_size", "1"]
runpy.run_path("{SCRIPT}", run_name="__main__")
''')

    env = dict(os.environ, TRANSFORMERS_OFFLINE="1", HF_HUB_OFFLINE="1",
               CUDA_VISIBLE_DEVICES=str(gpu))
    log(f"shard {tag} on GPU {gpu}")
    subprocess.run([PY, driver], cwd=run_dir, env=env, check=True)

    src = f"{run_dir}/raw_predictions/VulRepair_raw_preds.csv"
    if not os.path.exists(src):
        raise RuntimeError(f"missing output: {src}")
    os.makedirs(PRED_DIR, exist_ok=True)
    dst = f"{PRED_DIR}/{tag}.csv"
    shutil.copy(src, dst)
    elapsed = time.time() - started
    log(f"shard {tag}: {elapsed:.1f}s -> {dst}")
    return dst, elapsed


def merge_and_report(results):
    import pandas as pd

    test = pd.read_csv(TEST_CSV)
    assert len(test) == 1706, len(test)

    frames = []
    for (start, end), (path, _) in zip(SHARDS, results):
        part = pd.read_csv(path)
        if len(part) != end - start:
            raise RuntimeError(f"{path}: {len(part)} rows, expected {end - start}")
        part.insert(0, "row", range(start, end))
        part["cwe_id"] = test["cwe_id"].iloc[start:end].values
        part["cve_id"] = test["cve_id"].iloc[start:end].values
        part["source"] = test["source"].iloc[start:end].values
        part["target"] = test["target"].iloc[start:end].values
        frames.append(part)

    pred = pd.concat(frames, ignore_index=True)
    out_csv = f"{WORK}/vulrepair_predictions_beam{BEAMS}.csv"
    pred.to_csv(out_csv, index=False)

    paper = pd.read_csv(
        f"{REPO}/data/VulRepair_raw_predictions/"
        "vulrepair_raw_preds_for_cve_fixes_test.csv")

    # The paper CSV uses a different row order than the HF test split.
    paper_key = pd.MultiIndex.from_frame(paper[["source", "target"]])
    paper_ok = pd.Series(paper["correctly_predicted"].values, index=paper_key)
    paper_raw = pd.Series(paper["raw_predictions"].values, index=paper_key)
    keep = ~paper_ok.index.duplicated(keep="first")
    paper_ok, paper_raw = paper_ok[keep], paper_raw[keep]

    key = pd.MultiIndex.from_frame(pred[["source", "target"]])
    ok_aligned = paper_ok.reindex(key)
    raw_aligned = paper_raw.reindex(key)
    missing = int(ok_aligned.isna().sum())
    agree = float((pred["correctly_predicted"].values ==
                   ok_aligned.values).mean()) if missing == 0 else float("nan")
    raw_agree = float((pred["raw_predictions"].values ==
                       raw_aligned.values).mean()) if missing == 0 else float("nan")

    ours = float(pred["correctly_predicted"].mean())
    theirs = float(paper["correctly_predicted"].mean())

    g_ours = pred.groupby("cwe_id")["correctly_predicted"].agg(["size", "sum"])
    g_paper = paper.groupby("cwe_id")["correctly_predicted"].agg(["size", "sum"])
    table = g_ours.join(g_paper, lsuffix="_ours", rsuffix="_paper")
    table["pp_ours"] = table["sum_ours"] / table["size_ours"]
    table["pp_paper"] = table["sum_paper"] / table["size_paper"]
    table["delta_pp"] = table["pp_ours"] - table["pp_paper"]
    top = table.sort_values("size_ours", ascending=False).head(10)

    lines = [
        f"# VulRepair M1 — beam {BEAMS}",
        "",
        f"- rows: {len(pred)}",
        f"- overall PP (ours): **{ours:.4f}** "
        f"({int(pred['correctly_predicted'].sum())}/{len(pred)})",
        f"- overall PP (paper raw preds): **{theirs:.4f}** "
        f"({int(paper['correctly_predicted'].sum())}/{len(paper)})",
        f"- per-row correctness agreement with paper: **{agree:.4f}**",
        f"- per-row prediction-string agreement with paper: **{raw_agree:.4f}**",
        f"- unmatched paper rows: {missing}",
        "- wall times: " + ", ".join(f"{s}-{e}: {t:.0f}s" for
                                      (s, e), (_, t) in zip(SHARDS, results)),
        "",
        "| CWE | n | hits ours | PP ours | PP paper | delta |",
        "|---|---|---|---|---|---|",
    ]
    for cwe, row in top.iterrows():
        lines.append(
            f"| {cwe} | {int(row['size_ours'])} | {int(row['sum_ours'])} | "
            f"{row['pp_ours']:.3f} | {row['pp_paper']:.3f} | "
            f"{row['delta_pp']:+.3f} |")
    report = f"{WORK}/results_beam{BEAMS}.md"
    with open(report, "w") as fh:
        fh.write("\n".join(lines) + "\n")

    log("\n".join(lines))
    meta = {
        "beams": BEAMS,
        "shards": SHARDS,
        "rows": len(pred),
        "pp_ours": ours,
        "pp_paper": theirs,
        "correctness_agreement": agree,
        "prediction_string_agreement": raw_agree,
        "unmatched_paper_rows": missing,
        "wall_seconds": {f"{s}-{e}": round(t, 1) for (s, e), (_, t) in
                         zip(SHARDS, results)},
        "total_seconds": round(time.time() - T0, 1),
    }
    with open(f"{WORK}/run_meta.json", "w") as fh:
        json.dump(meta, fh, indent=2)
    log(f"wrote {out_csv}, {report}, {WORK}/run_meta.json")


def main():
    log(f"beams={BEAMS} shards={SHARDS}")
    setup_env()
    setup_inputs()

    n_gpu = gpu_count()
    workers = max(1, min(PARALLEL_GPUS, n_gpu, len(SHARDS)))
    log(f"gpus={n_gpu} workers={workers}")

    results = [None] * len(SHARDS)
    if workers == 1:
        for i, (start, end) in enumerate(SHARDS):
            results[i] = run_shard(start, end, 0)
    else:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(run_shard, start, end, i % workers): i
                for i, (start, end) in enumerate(SHARDS)
            }
            for fut in as_completed(futures):
                i = futures[fut]
                results[i] = fut.result()

    merge_and_report(results)


if __name__ == "__main__":
    main()

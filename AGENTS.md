# Repository Guidelines

## Project Overview

Empirical replication of **VulRepair** (Fu et al., ACM ESEC/FSE 2022) for course **NT521.R11.ANTN** (Final Project CK57). The repository evaluates a pretrained and fine-tuned CodeT5-base model (220M parameters) on the official test split (1,706 C/C++ functions from CVEFixes and Big-Vul).

The primary evaluation metric is **Perfect Prediction (%PP)**: exact text match between a beam-search-generated repair candidate and human ground truth in top-$K$ candidates ($K \in \{1, 5, 10, 50\}$).

Evaluation runs on remote dual Tesla T4 GPUs via the Kaggle CLI, with local aggregation and verification tools.

---

## Architecture & Data Flow

```
                         Kaggle Container (T4 x 2)
  +--------------------------------------------------------------------+
  | 1. uv bootstrap: Python 3.9 venv + pinned legacy PyTorch/HF stack  |
  | 2. Artifact staging: curl checkpoint + test.csv into /root (airgap)|
  | 3. Code staging: shallow clone awsm-research/VulRepair             |
  +---------------------------------+----------------------------------+
                                    |
                    Parallel Queue Execution (2 Workers)
      Worker 0 (GPU 0 - Sequential)      Worker 1 (GPU 1 - Sequential)
      +-----------------------------+    +-----------------------------+
      | Shard 0: rows [0:427]       |    | Shard 1: rows [427:854]     |
      | drive.py (mock load_dataset)|    | drive.py (mock load_dataset)|
      | -> preds/beam{B}_0_427.csv  |    | -> preds/beam{B}_427_854.csv|
      +--------------+--------------+    +--------------+--------------+
                     |                                  |
      +--------------v--------------+    +--------------v--------------+
      | Shard 2: rows [854:1281]    |    | Shard 3: rows [1281:1706]   |
      | -> preds/beam{B}_854_1281...|    | -> preds/beam{B}_1281_1706..|
      +--------------+--------------+    +--------------+--------------+
                     |                                  |
                     +------------------+---------------+
                                        |
                 Output Retrieval (`kaggle kernels output`)
                                        v
                 Local / Remote Merge (`eval/merge_results.py`)
                 - Assert contiguous non-overlapping 1,706 rows
                 - Join source/target/cwe_id from test.csv
                 - MultiIndex (source, target) align vs paper CSV
                 - Compute PP, agreement metrics, and CWE breakdown
```

### Key Modules & Data Flow
1. **Environment & Artifact Staging (`kaggle/vulrepair_eval.py:setup_env, setup_inputs`)**: Installs a pinned legacy stack into `/root/venv39` via `uv` to resolve bitrot between modern host runtimes and 2022 libraries. Checkpoints and data are downloaded directly to `/root`. Air-gapping environment variables (`TRANSFORMERS_OFFLINE=1`, `HF_HUB_OFFLINE=1`) ensure deprecated `datasets==2.0.0` and `huggingface-hub==0.8.1` never make runtime API calls.
2. **In-Process Shard Driver & Mocking (`kaggle/vulrepair_eval.py:run_shard`)**: Upstream `vulrepair_main.py` hardcodes `datasets.load_dataset("MickyMike/cvefixes_bigvul", split="test")`. The driver script writes a dynamic `drive.py` per shard that slices local `/root/test.csv`, monkeypatches `datasets.load_dataset` with a custom dict-backed `_Split` object, creates a symlink from `saved_models/checkpoint-best-loss/model.bin` to `/root/VulRepair_ckpt/pytorch_model.bin`, and runs the upstream module via `runpy.run_path`.
3. **GPU Queue Scheduling (`kaggle/vulrepair_eval.py:run_queue, main`)**: Shards are partitioned into fixed sequential queues per GPU (`ThreadPoolExecutor(max_workers=workers)`). Concurrent execution of shards on the *same* physical GPU is strictly prohibited; uncollected KV cache during process overlap causes CUDA OOM.
4. **Post-Evaluation Merge & Alignment (`eval/merge_results.py`)**: Shard predictions are validated for row continuity (1,706 rows total). Because upstream paper predictions (`vulrepair_raw_preds_for_cve_fixes_test.csv`) use a different row order than Hugging Face's `test.csv`, outputs are aligned using a `(source, target)` MultiIndex.

---

## Key Directories

- `kaggle/`: Kaggle batch evaluation scripts, kernel metadata, and execution configuration.
- `eval/`: Local post-processing and aggregation utilities (`merge_results.py`).
- `docs/`: Comprehensive academic and experimental documentation:
  - `docs/results/`: Output artifacts from completed beam evaluations (`results_beam*.md`, `vulrepair_predictions_beam*.csv`).
  - `docs/RESULTS.md`: Detailed empirical replication report, discrepancy analyses, and CWE breakdown tables.
  - `docs/NT521-PLAN.md`: Implementation schedule and rubric mapping.
  - `docs/NT521-RESEARCH.md`: Theoretical background, model architecture, and threats to validity.
- `kaggle-output/`: Default target folder for downloaded Kaggle outputs (ignored by git).

---

## Development Commands

### Pushing Kaggle Evaluations
```bash
# Push full Beam 50 evaluation (4 shards, dual T4 GPUs)
kaggle kernels push -p kaggle --accelerator NvidiaTeslaT4

# Track status and stream logs
kaggle kernels status tdwuyn/vulrepair-eval
kaggle kernels logs -f tdwuyn/vulrepair-eval

# Download artifacts
kaggle kernels output tdwuyn/vulrepair-eval -p kaggle-output
```

### Merging Shard Results Locally
```bash
# Merge completed shards across runs and generate markdown summary
python eval/merge_results.py \
  --preds kaggle-output/preds \
  --test /path/to/test.csv \
  --paper /path/to/vulrepair_raw_preds_for_cve_fixes_test.csv \
  --beams 50 \
  --out docs/results \
  --top 15

# Inspect intermediate progress when only a subset of shards is available
python eval/merge_results.py \
  --preds kaggle-output/preds \
  --test /path/to/test.csv \
  --beams 50 \
  --allow-partial
```

### Verification & Syntax Checking
```bash
# Verify Python script syntax without runtime dependencies
python3 -m py_compile kaggle/vulrepair_eval.py eval/merge_results.py
```

---

## Code Conventions & Common Patterns

### Subprocess Execution
Always log commands and measure elapsed time using explicit wrappers:
```python
def run(cmd, cwd=None, env=None):
    log("+ " + " ".join(cmd))
    started = time.time()
    subprocess.run(cmd, cwd=cwd, env=env, check=True)
    log(f"  done in {time.time() - started:.1f}s")
```

### Pandas Data Integrity Invariants
- **Disable Default NA**: Always pass `keep_default_na=False` when reading CSVs containing source code or patches (`pd.read_csv(path, keep_default_na=False)`). Default string parsing converts keywords like `NA` or blank lines into `NaN`, corrupting MultiIndex joins and text comparisons.
- **Avoid Chained Assignment**: Use `.assign()` or `.loc[]` to avoid Pandas 3.0 `ChainedAssignmentError` warnings:
  ```python
  g = g.assign(pp=g["hits"] / g["n"])
  ```
- **Composite Key Alignment**:
  ```python
  key = pd.MultiIndex.from_frame(pred[["source", "target"]])
  paper_key = pd.MultiIndex.from_frame(paper[["source", "target"]])
  paper_ok = pd.Series(paper["correctly_predicted"].values, index=paper_key)
  paper_ok = paper_ok[~paper_ok.index.duplicated(keep="first")]
  aligned = paper_ok.reindex(key)
  ```

### File Symlinks Over Large Copies
Never duplicate large checkpoint binaries across shard run directories. Use `os.symlink` to redirect upstream hardcoded relative model paths (`saved_models/checkpoint-best-loss/model.bin`) back to cached root checkpoints.

### Shard Naming & Geometry
Shard files must strictly match `beam<BEAMS>_<start>_<end>.csv` where `start` and `end` are row indices in `test.csv`.

---

## Important Files

- `kaggle/vulrepair_eval.py`: Core cloud evaluation entrypoint. Handles environment bootstrap, model caching, multi-GPU queue dispatch, and optional self-contained reporting.
- `kaggle/kernel-metadata.json`: Kernel specification for `kaggle kernels push`. Contains container flags (`enable_gpu`, `enable_internet`, `machine_shape`).
- `eval/merge_results.py`: Standalone CLI utility to validate shard coverage, align predictions with paper baselines, and compute metric tables.
- `docs/RESULTS.md`: Canonical benchmark results comparing replicated metrics to paper figures (RQ1, beam sweep, and Table 2 CWE distribution).
- `docs/results/vulrepair_predictions_beam50.csv`: Merged predictions for all 1,706 test functions at beam 50.

---

## Runtime & Tooling Preferences

- **Host & Environment Isolation**: Use `uv` for lightning-fast virtual environment creation and package installation. Avoid depending on the global system Python or host packages.
- **Pinned Dependency Constraints**:
  - `python==3.9.x`
  - `torch==1.10.2+cu113`
  - `transformers==4.19.1`
  - `tokenizers==0.11.6`
  - `datasets==2.0.0`
  - `protobuf==3.20.1` (crucial: protobuf 4.x breaks `tensorboard==2.8.0` with descriptor errors)
  - `setuptools==59.5.0` (required for `pkg_resources` in `torch==1.10.2`)
- **Kaggle Kernel Quirk**: Kaggle resolves kernel slugs from `title` in `kernel-metadata.json`. If `title` changes, the slug changes; ensure `id` matches `username/kernel-slug` derived from `title`.
- **Git Tracking Rules**:
  - Exclude virtual environments (`.venv`, `venv39`), model weights (`*.bin`, `*.pt`, `*.safetensors`), training logs (`*.log`), raw dataset dumps (`data/`), and `kaggle-output/`.
  - Track evaluation summary tables, markdown reports, and final prediction CSVs in `docs/results/`.

---

## Testing & QA

There is no formal unit test suite (`pytest`/`unittest`). Correctness and reproducibility are validated through domain-specific assertions:

1. **Exact Row Count Invariant**: Every full evaluation run must cover exactly **1,706 rows**. `eval/merge_results.py` enforces this invariant unless `--allow-partial` is explicitly provided.
2. **Shard Geometry Checks**:
   - Duplicate shard start detection (`start in shards`).
   - Overlap assertion (`start < cursor`).
   - Contiguity and gap check (`start != cursor`).
   - Shard length verification (`len(part) == end - start`).
3. **MultiIndex Baseline Verification**:
   - Every prediction `(source, target)` must reindex cleanly against the paper's raw predictions without missing entries (`missing == 0`).
   - **Correctness Agreement**: Label-level match rate (`pred["correctly_predicted"] == paper["correctly_predicted"]`). On dual T4 GPUs, this is $\ge 99.94\%$ (1,705/1,706 rows).
   - **Prediction String Agreement**: Character-level match rate on generated patches. On dual T4 GPUs, this is $\ge 98.94\%$ (1,688/1,706 rows).
4. **Hardware-Induced Divergence (Row 288)**:
   - Exactly 1 row (`row=288`, `CWE-400`, `CVE-2011-2918`) flips from 0 (paper) to 1 (reproduction).
   - This discrepancy is expected: cuBLAS FP32 floating-point summation order differences between NVIDIA Turing (T4, `sm_75`) and Ampere (RTX 3090, `sm_86`) create $\sim 10^{-7}$ logit variances, altering tie-breaking at the 50th beam boundary for short candidate patches. No rows where `ours=0, paper=1` exist.

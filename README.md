# NT521.R11.ANTN — VulRepair

Đồ án cuối kỳ môn **Lập trình an toàn và khai thác lỗ hổng phần mềm** (NT521.R11.ANTN), HK1 2026–2027.

Tái hiện thực nghiệm paper:

> Fu, M., Tantithamthavorn, C., Le, T., Nguyen, V., Phung, D. (2022).
> **VulRepair: A T5-Based Automated Software Vulnerability Repair.**
> ESEC/FSE '22. DOI: [10.1145/3540250.3549098](https://doi.org/10.1145/3540250.3549098)

## Tài liệu

| Tài liệu | Nội dung |
|---|---|
| [`docs/NT521-RESEARCH.md`](docs/NT521-RESEARCH.md) | Research đầy đủ: pipeline, dataset, RQ1–RQ4, repro, ưu/nhược, Q&A |
| [`docs/NT521-PLAN.md`](docs/NT521-PLAN.md) | Plan thực thi: rubric, phân vai, timeline W1–W6, reproduction matrix |
| [`docs/3540250.3549098.pdf`](docs/3540250.3549098.pdf) | Paper gốc (author copy) |

## Phạm vi

- **Bắt buộc (rubric 5đ):** tái hiện eval-only trên checkpoint [`MickyMike/VulRepair`](https://huggingface.co/MickyMike/VulRepair) — beam 50 trên test set 1,706 hàm, đối chiếu %Perfect Prediction với paper (~44%); beam sweep và bảng %PP theo CWE.
- **Điểm cộng (+1đ):** case study CWE-787/CWE-416 trên hàm toy + eval subset CWE.
- **Không bắt buộc:** train lại từ đầu (chỉ khi có GPU ≥8 GB VRAM).

## Kết quả dự kiến

| Deliverable | Trạng thái |
|---|---|
| Research + plan | ✅ |
| `eval/run_eval.sh` (1-click inference + eval) | ⏳ W1–W2 |
| `eval/results.md` (nhóm vs paper, lệch số + nguyên nhân) | ⏳ W2–W3 |
| Case study + video demo | ⏳ W5 |

## Chạy eval trên Kaggle (GPU T4)

Kernel [`kaggle/vulrepair_eval.py`](kaggle/vulrepair_eval.py) tự dựng đúng stack pinned của paper (Python 3.9, torch 1.10.2+cu113, transformers 4.19.1) bằng `uv`, tải checkpoint + test split về `/root`, chạy 1,706 hàm theo shard (beam 50, 2 GPU song song), merge và so từng dòng với raw predictions của paper.

```bash
# 1 lần: cài CLI + token (Kaggle → Settings → API → Create New Token)
pip install kaggle
ls ~/.kaggle/access_token

# Push + theo dõi + tải kết quả
kaggle kernels push   -p kaggle --accelerator NvidiaTeslaT4
kaggle kernels status tdwuyn/vulrepair-eval
kaggle kernels logs   tdwuyn/vulrepair-eval
kaggle kernels output tdwuyn/vulrepair-eval -p kaggle-output
```

Kết quả trong `kaggle-output/`:

| File | Nội dung |
|---|---|
| `vulrepair_predictions_beam50.csv` | 1,706 dòng: `row, raw_predictions, correctly_predicted, cwe_id, cve_id, source, target` |
| `results_beam50.md` | %PP của nhóm vs paper, Top-10 CWE, độ khớp từng dòng |
| `run_meta.json` | thời gian từng shard, agreement, cấu hình |

Đổi beam: sửa `BEAMS` ở đầu kernel (1/5/10/50). Raw predictions của paper xếp thứ tự khác `test.csv` → kernel align theo `(source, target)` và báo `prediction_string_agreement`; smoke test 5 dòng cho kết quả khớp 100%.

Merge thủ công (khi tải shard từ nhiều version/nhiều kernel):

```bash
python eval/merge_results.py \
  --preds kaggle-output/preds kaggle-output-shard2/preds \
  --test test.csv --paper vulrepair_raw_preds_for_cve_fixes_test.csv \
  --beams 50 --out docs/results
```

`--allow-partial` cho phép merge khi còn thiếu shard (chỉ để kiểm tra giữa chừng).

## Nguồn

- Code: <https://github.com/awsm-research/VulRepair>
- Checkpoint: <https://huggingface.co/MickyMike/VulRepair>
- Dataset: <https://huggingface.co/datasets/MickyMike/cvefixes_bigvul>
- Artifact: <https://doi.org/10.5281/zenodo.7080271>

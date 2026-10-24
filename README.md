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

## Nguồn

- Code: <https://github.com/awsm-research/VulRepair>
- Checkpoint: <https://huggingface.co/MickyMike/VulRepair>
- Dataset: <https://huggingface.co/datasets/MickyMike/cvefixes_bigvul>
- Artifact: <https://doi.org/10.5281/zenodo.7080271>

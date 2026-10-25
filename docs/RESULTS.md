# Kết quả tái hiện — VulRepair (M1)

> Tái hiện thí nghiệm của đồ án **NT521.R11.ANTN — CK57 VulRepair** (ESEC/FSE '22) bằng Kaggle CLI trên GPU Tesla T4 ×2.

## 1. Môi trường thực thi

| Hạng mục | Giá trị |
|---|---|
| Nền tảng | Kaggle Kernels (`kaggle kernels push --accelerator NvidiaTeslaT4`) |
| GPU | 2 × NVIDIA Tesla T4 (15.360 MiB VRAM / GPU), Driver 580.178.04 |
| Python | 3.9.25 (dựng cô lập bằng `uv venv --python 3.9`) |
| PyTorch | `1.10.2+cu113` |
| Transformers / Tokenizers | `4.19.1` / `0.11.6` |
| Datasets / HuggingFace Hub | `2.0.0` / `0.8.1` |
| Checkpoint | `MickyMike/VulRepair` (CodeT5-base 220M fine-tuned) |
| Test split | `MickyMike/cvefixes_bigvul` (`test.csv`, 1.706 cặp hàm C) |
| Tham số decode | `encoder_block_size=512`, `decoder_block_size=256`, `eval_batch_size=1`, `seed=42` |

## 2. Thí nghiệm chính — Perfect Prediction (Beam 50, RQ1)

| Chỉ số | Kết quả nhóm (T4) | Paper / Raw Preds (RTX 3090) | Độ lệch ($\Delta$) |
|---|---|---|---|
| **Số hàm sửa đúng / Tổng** | **746 / 1.706** | **745 / 1.706** | **+1 hàm** |
| **% Perfect Prediction (%PP)** | **43,73%** (`0.4373`) | **43,67%** (`0.4367`, làm tròn 44%) | **+0,06 điểm %** |
| Khớp nhãn đúng/sai từng dòng (1.706 dòng) | **99,94%** (1.705 / 1.706) | — | 1 dòng lệch |
| Khớp chuỗi dự đoán `raw_predictions` | **98,94%** (1.688 / 1.706) | — | 18 dòng khác chuỗi top-1 |

### Phân tích độ lệch (1 dòng lật nhãn)
- **Dòng lệch duy nhất:** `row=288` (`CWE-400`, `CVE-2011-2918`, hàm `handle_unaligned_access`).
  - Ground truth: `<S2SV_ModStart> , 1 , <S2SV_ModEnd> regs , address`
  - Nhóm (T4): tìm thấy đúng bản vá trong top-50 beam (`correctly_predicted = 1`).
  - Paper (RTX 3090): không lọt top-50 (`correctly_predicted = 0`, top-1 là `<S2SV_ModStart> PERF_COUNT_SW_ALIGNMENT_FAULTS, 1 <S2SV_ModEnd>, regs,`).
- **17 dòng còn lại trong 18 dòng khác chuỗi:** đều có `correctly_predicted = 0` ở cả hai bên (chỉ khác thứ tự xếp hạng ứng viên top-1 khi cả 50 beam đều sai). Không có dòng nào paper đúng mà nhóm sai (`ours=0, paper=1` bằng `0`).
- **Nguyên nhân kỹ thuật:** Phép nhân ma trận FP32 trên kiến trúc Turing (Tesla T4, `sm_75`) và Ampere (RTX 3090, `sm_86`) có thứ tự cộng dồn dấu chấm động khác nhau trong cuBLAS, tạo sai số cỡ $10^{-7}$ ở log-probability. Với các bản vá rất ngắn có nhiều ứng viên điểm sát nhau (near-tie) ở ranh giới beam thứ 50, thứ tự cắt beam thay đổi 1 vị trí.

## 3. Khảo sát kích thước Beam (Beam Sweep — tái hiện Figure 8, Discussion 6.5)

| Beam Width ($\beta$) | Số hàm đúng (Nhóm) | %PP Nhóm (chính xác) | %PP Nhóm (làm tròn) | %PP Paper (Figure 8) | Độ lệch vs Paper | Thời gian chạy (4 shard, 2×T4) |
|---|---|---|---|---|---|---|
| **Beam 1** | 512 / 1.706 | 30,01% | **30%** | **30%** (513 / 1.706) | -0,06 điểm % (-1 hàm) | ~16 phút |
| **Beam 5** | 691 / 1.706 | 40,50% | **41%** | **41%** | ~0 điểm % | ~31 phút |
| **Beam 10** | 716 / 1.706 | 41,97% | **42%** | **42%** | ~0 điểm % | ~43 phút |
| **Beam 50** | 746 / 1.706 | 43,73% | **44%** | **44%** (745 / 1.706) | +0,06 điểm % (+1 hàm) | ~168 phút |

- Làm tròn đến phần trăm nguyên như biểu đồ Figure 8 của bài báo, cả 4 mốc $\beta \in \{1, 5, 10, 50\}$ khớp tuyệt đối **30% / 41% / 42% / 44%**.
- Tăng beam từ 1 lên 5 mang lại mức tăng lớn nhất (+10,49 điểm %); từ 10 lên 50 chỉ tăng thêm +1,76 điểm % nhưng thời gian suy luận tăng gấp ~3,9 lần.

## 4. Kết quả theo loại lỗ hổng CWE (Discussion 6.1)

### 4.1. Top-10 CWE nguy hiểm nhất (tái hiện Table 2 paper)

| Hạng | CWE | Tên lỗ hổng | Số hàm đúng / Tổng (Nhóm) | %PP Nhóm | Số hàm đúng / Tổng (Paper) | %PP Paper | Độ lệch |
|---|---|---|---|---|---|---|---|
| 1 | CWE-787 | Out-of-bounds Write | 16 / 53 | 30,2% (30%) | 16 / 53 | 30% | 0 |
| 2 | CWE-79 | Cross-site Scripting | 0 / 1 | 0,0% (0%) | 0 / 1 | 0% | 0 |
| 3 | CWE-125 | Out-of-bounds Read | 54 / 170 | 31,8% (32%) | 54 / 170 | 32% | 0 |
| 4 | CWE-20 | Improper Input Validation | 68 / 152 | 44,7% (45%) | 68 / 152 | 45% | 0 |
| 5 | CWE-78 | OS Command Injection | 1 / 3 | 33,3% (33%) | 1 / 3 | 33% | 0 |
| 6 | CWE-89 | SQL Injection | 1 / 5 | 20,0% (20%) | 1 / 5 | 20% | 0 |
| 7 | CWE-416 | Use After Free | 29 / 55 | 52,7% (53%) | 29 / 55 | 53% | 0 |
| 8 | CWE-22 | Path Traversal | 2 / 8 | 25,0% (25%) | 2 / 8 | 25% | 0 |
| 9 | CWE-352 | Cross-Site Request Forgery | 0 / 2 | 0,0% (0%) | 0 / 2 | 0% | 0 |
| 10 | CWE-434 | Unrestricted Upload of File | 0 / 0 | — | — | — | 0 |
| **Tổng** | | | **171 / 449** | **38,08% (38%)** | **171 / 449** | **38%** | **0** |

### 4.2. Top-15 CWE có nhiều mẫu nhất trong tập test (theo Beam Width)

| CWE | Số mẫu ($n$) | Beam 1 | Beam 5 | Beam 10 | Beam 50 (Nhóm) | Beam 50 (Paper) | $\Delta$ Beam 50 |
|---|---|---|---|---|---|---|---|
| CWE-119 | 386 | 96 (24,9%) | 127 (32,9%) | 134 (34,7%) | 141 (36,5%) | 141 (36,5%) | 0 |
| CWE-125 | 170 | 38 (22,4%) | 50 (29,4%) | 53 (31,2%) | 54 (31,8%) | 54 (31,8%) | 0 |
| CWE-20 | 152 | 53 (34,9%) | 65 (42,8%) | 68 (44,7%) | 68 (44,7%) | 68 (44,7%) | 0 |
| CWE-000 | 121 | 42 (34,7%) | 59 (48,8%) | 63 (52,1%) | 71 (58,7%) | 71 (58,7%) | 0 |
| CWE-264 | 71 | 24 (33,8%) | 35 (49,3%) | 34 (47,9%) | 36 (50,7%) | 36 (50,7%) | 0 |
| CWE-476 | 70 | 34 (48,6%) | 45 (64,3%) | 47 (67,1%) | 46 (65,7%) | 46 (65,7%) | 0 |
| CWE-200 | 64 | 29 (45,3%) | 35 (54,7%) | 38 (59,4%) | 39 (60,9%) | 39 (60,9%) | 0 |
| CWE-399 | 60 | 27 (45,0%) | 35 (58,3%) | 35 (58,3%) | 37 (61,7%) | 37 (61,7%) | 0 |
| CWE-190 | 59 | 26 (44,1%) | 29 (49,2%) | 29 (49,2%) | 31 (52,5%) | 31 (52,5%) | 0 |
| CWE-416 | 55 | 18 (32,7%) | 29 (52,7%) | 28 (50,9%) | 29 (52,7%) | 29 (52,7%) | 0 |
| CWE-362 | 54 | 15 (27,8%) | 19 (35,2%) | 20 (37,0%) | 23 (42,6%) | 23 (42,6%) | 0 |
| CWE-787 | 53 | 12 (22,6%) | 16 (30,2%) | 16 (30,2%) | 16 (30,2%) | 16 (30,2%) | 0 |
| CWE-189 | 44 | 16 (36,4%) | 22 (50,0%) | 23 (52,3%) | 23 (52,3%) | 23 (52,3%) | 0 |
| CWE-284 | 33 | 9 (27,3%) | 15 (45,5%) | 15 (45,5%) | 15 (45,5%) | 15 (45,5%) | 0 |
| CWE-400 | 32 | 9 (28,1%) | 13 (40,6%) | 14 (43,8%) | 15 (46,9%) | 14 (43,8%) | +1 |

## 5. Artifacts xuất ra trong repo

- [`docs/results/results_beam50.md`](results/results_beam50.md), [`docs/results/results_beam10.md`](results/results_beam10.md), [`docs/results/results_beam5.md`](results/results_beam5.md), [`docs/results/results_beam1.md`](results/results_beam1.md) — báo cáo tóm tắt từng cấu hình beam.
- `docs/results/vulrepair_predictions_beam{1,5,10,50}.csv` — toàn bộ 1.706 dự đoán kèm `cwe_id`, `cve_id`, `source`, `target`.
- [`kaggle/vulrepair_eval.py`](../kaggle/vulrepair_eval.py) — kernel chạy trên Kaggle T4 ×2.
- [`eval/merge_results.py`](../eval/merge_results.py) — script gộp shard và đối chiếu với raw predictions của bài báo.

# NT521 Plan — Đồ án cuối kỳ CK57: VulRepair

> Plan thực thi chi tiết cho đồ án **NT521.R11.ANTN**, HK1 2026–2027.
> **Phạm vi:** Phần A — CK57 VulRepair.
> Plan này đi kèm research: `docs/NT521-RESEARCH.md`. Đọc cả hai trước khi bắt tay làm.
> Giả định: nhóm 3–5 SV, có thể **không có GPU riêng** (plan có đường chạy không cần train). Ngày báo cáo cụ thể chưa có `[THIẾU]` → timeline dùng mốc tuần tương đối W1…W6 và cập nhật khi GV chốt lịch.

---

# Phần A — Plan CK57 VulRepair

## 1. Ánh xạ công việc ↔ Rubic (1đ / 3đ / 5đ / +1đ)

| Tiêu chí | Điểm | Việc phải làm | Deliverable | Mốc |
|---|---|---|---|---|
| 1. Hiểu ngữ cảnh, vấn đề + kỹ năng thuyết trình | **1đ** | Đọc paper + baseline; soạn slide problem/contribution; dry-run 15 phút | Slide 1–3 + A9 storyboard | M1, M6 |
| 2. Giải thích được phương pháp – kỹ thuật | **3đ** | Nắm chắc pipeline T5/BPE/pretrain, RQ1–RQ4, dataset, hyperparams | Slide method (1 diagram) + bảng RQ2/RQ3/RQ4 | M1 |
| 3. Hiện thực và demo (bài báo có code công khai) | **5đ** | **Tái hiện thí nghiệm** (bắt buộc): eval inference M1 → ~44% PP; tái hiện ≥2 bảng RQ (beam, CWE); **biện luận ưu/nhược** | Bảng kết quả vs paper + bảng lệch số + biện luận | M2, M3, M4 |
| 4. Điểm cộng xuất sắc | **+1đ** | PA-1 case study CWE-787/CWE-416 + eval subset CWE mới (fallback: PA-2 LLM comparison) | Bảng case study + bảng %PP theo CWE | M5 |

**Tối thiểu để không trượt tiêu chí 3:** chạy được `vulrepair_main.py --do_test` với checkpoint `MickyMike/VulRepair` trên test set (1,706 hàm, beam 50), ra bảng %PP ≈44%, và đối chiếu được với raw predictions của paper trong repo. Không bắt buộc train lại.

**Điểm cộng:** PA-1 (recommended) — không cần train, chỉ cần inference trên vài hàm.

## 2. Phân vai (3 role; điều chỉnh theo số người thật)

| Role | Người | Trách nhiệm chính |
|---|---|---|
| **Lead paper** | (chọn) | Sở hữu slide method/results; chủ trì A1–A5, A7, A10; đọc paper + baseline; là người trả lời GV câu hỏi lý thuyết |
| **Lead reproduce** | (chọn) | Sở hữu môi trường (Docker/venv, transformers 4.19.1, torch 1.10.2+cu113, Python 3.9.7); tải checkpoint + dataset; chạy M1 eval, beam sweep, bảng CWE; ghi log lệch số |
| **Lead eval / điểm cộng** | (chọn) | Sở hữu PA-1 (case study CWE-787/CWE-416 + eval subset CWE); chuẩn bị demo + video backup; tổng hợp deliverable cuối |

Chốt vai + số thành viên thật trong buổi họp đầu W1.

## 3. Timeline theo tuần (W1…W6, mốc tương đối)

> `[THIẾU]` ngày báo cáo GV chốt. Giả định: báo cáo ≈ cuối W6. Nếu lịch ngắn hơn → nén W2–W3 (bỏ baseline train, chỉ inference).

| Tuần | Việc (chủ sở hữu) | Kết quả chấp nhận | Rubic |
|---|---|---|---|
| **W1** | Họp kickoff, phân vai; Lead paper đọc xong paper + RESEARCH.md; Lead reproduce setup env + tải checkpoint `MickyMike/VulRepair` + dataset HF, chạy smoke inference trên **5 mẫu** | Env chạy được, 5 patch sinh ra đúng định dạng | 1, 2 |
| **W2** | Reproduce eval chính: `--do_test` beam 50 trên 1,706 mẫu → %PP; đối chiếu raw predictions paper (file CSV trong repo); ghi lệch số | Bảng %PP của nhóm vs 44% paper + nguyên nhân lệch | **3** |
| **W3** | Beam sweep 1/5/10/50 (tái hiện Fig. 8); bảng CWE (D1) từ CSV; Lead paper soạn slide method + results | 2 bảng kết quả nữa + slide 60% | 2, **3** |
| **W4** | (Nếu có GPU ≥8 GB) train lại M1 75 epochs + ít nhất 1 baseline (M2 hoặc M3) → tái hiện RQ2/RQ4; nếu không có GPU → chuyển thẳng W5 và ghi rõ trong báo cáo "repro eval-only" | Bảng train (hoặc quyết định bỏ train có ghi nhận) | **3** |
| **W5** | Điểm cộng PA-1: chạy inference 3–5 hàm lỗ hổng tự viết (toy, tự host; vd CWE-787/CWE-416) + eval subset CWE từ test set; phân tích patch đúng/sai; quay video demo 2–3 phút | Bảng case study + bảng %PP theo CWE + video | **+1** |
| **W6** | Chốt slide (ưu/nhược A7 + điểm cộng), dry-run 15 phút tính giờ, chuẩn bị Q&A (A10), backup video, nộp deliverable | Slide final + dry-run đạt ≤15 phút + video backup | 1, 2, **3**, +1 |

## 4. Milestones

- **M1 (hết W1):** hiểu paper + slide method nháp xong. *Kiểm tra:* cả nhóm giảng lại được pipeline không nhìn tài liệu (đối chiếu A3).
- **M2 (hết W2):** chạy được inference/eval tối thiểu, ra bảng %PP vs 44%. *Kiểm tra:* file CSV kết quả nhóm diff được với raw predictions paper.
- **M3 (hết W3–W4):** bảng kết quả vs paper (beam, CWE, train nếu có), **ghi lệch số + nguyên nhân**.
- **M4 (hết W5):** phân tích ưu/nhược (A7) + qualitative examples (case study PA-1).
- **M5 (đầu W6):** điểm cộng hoàn tất hoặc **quyết định bỏ** (nếu thiếu thời gian/GPU) — có biên bản quyết định.
- **M6 (cuối W6):** demo 15 phút dry-run + video backup sẵn sàng.

## 5. Reproduction matrix — chọn 1 default + điều kiện chuyển

| Phương án | Nội dung | Yêu cầu | Khi nào chọn |
|---|---|---|---|
| **A. Eval-only (DEFAULT)** | Inference + eval trên checkpoint HF, beam 50 + sweep, bảng CWE, case study | GPU ≥4 GB VRAM hoặc CPU (chậm), 0h train | **Mặc định ngay từ đầu** — chắc chắn đạt tiêu chí 3 |
| B. Subset-train | Train M1 trên subset (vd 20% train data, ít epoch) để minh họa quy trình train | GPU ≥8 GB, ~2–3h | Chuyển từ A khi có GPU và W3 trôi chảy |
| C. Full-train + baselines | Train M1 75 epochs + M2/M3 | GPU ≥8 GB, ~6–10h/model | Chuyển từ B khi W4 còn dư thời gian; luôn giữ A làm bảo hiểm |

Quy tắc: **A luôn được làm trước và giữ làm kết quả tối thiểu**; B/C là bổ sung, không được phép để B/C kéo ngã A.

## 6. Rủi ro & mitigation

| Rủi ro | Khả năng | Mitigation |
|---|---|---|
| OOM khi train/eval | Trung bình | `--train_batch_size 4`, `--eval_batch_size 1`; thuê Colab/Kaggle GPU nếu không có máy |
| Train lại không ra 44% (đã ghi nhận Issue #4: 29.5%) | Cao | Đường default là eval-only; nếu train thì dùng đúng dataset HF + split 70/10/20 + seed 123456; báo cáo trung thực "lệch X điểm % do Y" — đây chính là nội dung biện luận ăn điểm |
| Checkpoint Drive (M2–M10) chết link | Thấp–trung | Kiểm tra W1; fallback: dùng raw predictions CSV sẵn trong repo cho các bảng còn lại |
| GitHub bitrot (README link sai, M8 fork transformers xung đột) | Trung bình | Dùng repo `awsm-research/VulRepair` (không theo link repo cá nhân); M8 cài venv riêng hoặc bỏ qua |
| Môi trường cũ (torch 1.10/cu113) không chạy trên GPU mới | Trung bình | Docker image với CUDA 11.x, hoặc chạy CPU cho case study nhỏ |
| Demo fail ngay trước báo cáo | Thấp | Video quay sẵn W5 + slide bảng kết quả; máy demo cài sẵn offline |
| Data duplication ảnh hưởng uy tín kết quả | Chắc chắn bị hỏi | Chuẩn bị slide limitation + câu trả lời A10 #9; tùy chọn eval dedup làm điểm cộng |

## 7. Deliverable cuối (nộp W6)

1. Slide 15 phút (đúng storyboard A9, 1 diagram method).
2. Repo nhóm: fork VulRepair + `eval/` gồm (a) script 1-click eval `run_eval.sh` (tải checkpoint, chạy beam 50, xuất CSV), (b) bảng kết quả `results.md` (nhóm vs paper, lệch số + giải thích), (c) case study PA-1.
3. Video demo 3 phút (backup) + video/live demo 1–2 ví dụ repair.
4. Biên bản dry-run 15 phút + bảng Q&A (A10).

## 8. Definition of done — tiêu chí 3 (5đ)

- [ ] Chạy được **X script**: `run_eval.sh` trên máy nhóm (Docker, offline) — không cần mạng, không cần tài khoản.
- [ ] Ra **bảng Y**: `results.md` có ít nhất 3 bảng — (1) %PP beam 50 của nhóm vs 44% paper, (2) beam sweep 1/5/10/50 vs Fig. 8, (3) %PP theo CWE (tối thiểu Top-10) vs Table 2 paper; mỗi bảng có cột "lệch so với paper" + 1–2 dòng nguyên nhân.
- [ ] Giải thích được **lệch Z**: mọi con số lệch đều có lời giải (seed/split, phần cứng, phiên bản thư viện, hoặc chính lỗi dữ liệu đã biết của dataset).
- [ ] Biện luận ưu/nhược theo A7 có trong slide + trả lời được ≥10/15 câu A10 khi thử nội bộ.

## 9. Phụ thuộc chéo giữa các hạng mục

- Điểm cộng PA-1 phụ thuộc: (1) env inference chạy được (M2), (2) khả năng tự viết hàm toy đúng ngữ nghĩa CWE. Không phụ thuộc phần train (M3) → làm được song song với W3–W4.
- **Tradeoff:** nếu quá tải → cắt PA-2/PA-3, giữ PA-1 vì rẻ nhất (chỉ cần inference).

## Open questions cho nhóm (Plan)

1. `[THIẾU]` Ngày báo cáo đồ án GV chốt → cập nhật lại cột tuần W1…W6 thành ngày thật.
2. Nhóm có GPU gì / có mua Colab/Kaggle không → chốt matrix A/B/C ở W1.
3. Số thành viên và vai (mục 2) → chốt W1.
4. Có kinh phí API LLM cho PA-2 không (nếu muốn làm thêm điểm cộng).
5. Nộp đồ án qua kênh nào (slide + repo + video — có cần bản báo cáo Word/PDF riêng không?) → hỏi GVLT.

# PM PLAN — 3 người / ~10 giờ / deadline 9h sáng

> Engine **đã chạy** (1044 dòng, zero dependency). Việc còn lại là **nâng chất + đóng gói**, không phải build từ đầu.

---

## 0. NGUYÊN TẮC CHIA VIỆC

**Chia theo FILE, không chia theo feature.**
3 người không bao giờ sửa cùng 1 file → **zero git conflict, không cần merge, không cần code review chặn nhau.**

| | Người | Sở hữu file | Không được đụng |
|---|---|---|---|
| **P1** | AI / Prompt | `assistant.py`, `ocr_gemini.py`*, `review_gemini.py`* | `retrieve.py`, `kb.py` |
| **P2** | Data / Enrichment | `enrich.py`*, `quality_report.py`*, `build/metrics.json`* | `assistant.py` |
| **P3** | Demo / Deck | `ui/`*, deck, video, README | **toàn bộ `engine/`** |

`*` = file MỚI, chưa tồn tại → tạo mới, không đụng của ai.

**Nút thắt duy nhất đã gỡ:** `engine/gemini.py` (client dùng chung: cache đĩa + retry + batch song song) **đã viết sẵn**. P1 và P2 dùng chung, không ai chờ ai.

---

## 1. S0 — 30 PHÚT ĐẦU, CẢ 3 NGỒI CÙNG NHAU

**Bắt buộc. Đừng bỏ.** Mục đích: cả 3 tận mắt thấy engine chạy, rồi mới tách làn.

```bash
unzip tasco-poi-engine.zip && cd tasco-poi-engine
python -m engine.kb                    # ai cũng chạy
python -m engine.run_eval              # ai cũng đọc build/eval_answers.md
export GEMINI_API_KEY=xxx
python -m engine.gemini                # xác nhận key sống
python -m engine.run_eval --llm        # đọc CẢ 15 câu, cùng nhau
```

**Chốt 3 việc rồi mới tách:**
1. Key Gemini sống, quota còn → nếu chết thì đổi plan NGAY (P1 chuyển sang polish offline mode)
2. Ai đọc 15 câu trả lời `--llm`, chấm câu nào dở → đó là backlog của P1
3. `git branch` riêng cho mỗi người. Merge vào `main` ở mốc S2.

---

## 2. BA LÀN CHẠY SONG SONG

### 🟢 P1 — AI / Prompt (làn có giá trị điểm cao nhất)

| Giờ | Việc | Output |
|---|---|---|
| T+0.5 → T+2 | Đọc 15 câu `--llm`. Sửa `SYSTEM` prompt trong `assistant.py` cho từng `kind` (search / named / poi_quality / empty / not_found). Câu 8 (Comparison) và 13 (AI Summary) cần prompt riêng. | 15 câu trả lời **hay**, không chỉ đúng |
| T+2 → T+3.5 | **`ocr_gemini.py`** — dùng `gemini.gen_json()` + schema, parse `raw_ocr_text` → menu. Chạy trên 18 quán có OCR. **So với Menu Dataset → in ra accuracy %.** | Con số cho slide 6 |
| T+3.5 → T+5 | **`review_gemini.py`** — `gemini.batch()` 150 review 1 lượt (~30s). Aspect + sentiment. **So với `known_strengths/weaknesses` → accuracy %.** | Con số cho slide 6 |
| T+5 → T+6 | Chạy lại `run_eval --llm` full. Verify **L3 không chặn** (không có id bịa). Nộp số cho P3. | ✅ FREEZE |

> **Cảnh báo:** đừng đụng `retrieve.py`. Nó đã khớp 8/8 ground truth bún chả. Sửa là hỏng.

---

### 🟣 P2 — Data / Enrichment (làn "map-tech")

| Giờ | Việc | Output |
|---|---|---|
| T+0.5 → T+1.5 | Chạy `python -m engine.kb`, mở `build/kb.json`, list ra **12 quán có `gaps`**. Xác định thiếu chính xác cái gì (`ocr_menu`? `reviews`?). | Bảng gap before |
| T+1.5 → T+4 | **`enrich.py`** — với mỗi quán gap: gọi Gemini **có Google Search grounding** (`tools: [{google_search:{}}]`) tìm giờ mở / amenity / món trên web. Structured output. **Ghi `source: "web_grounded"`, `confidence < 1.0`** — không được giả vờ là data gốc. | 12 quán được lấp |
| T+4 → T+5.5 | **`quality_report.py`** — tính lại quality score sau enrich. Xuất `build/metrics.json`: `{before: 0.xx, after: 0.yy, gaps_closed: N}`. | **Ảnh before/after cho slide 6** |
| T+5.5 → T+6 | Nộp `metrics.json` cho P3. | ✅ FREEZE |

> **Nếu Google Search grounding không chạy/hết quota:** cắt luôn, chuyển sang làm **gap analysis report** (chỉ ra thiếu gì, cần enrich gì) — vẫn đủ nội dung cho slide, chỉ mất phần "before/after".

---

### 🟠 P3 — Demo / Deck (làn KHÔNG BAO GIỜ bị chặn)

**Bắt đầu ngay từ phút 0. Engine đã chạy offline — P3 không phải chờ P1/P2 một giây nào.**

| Giờ | Việc | Output |
|---|---|---|
| T+0.5 → T+3 | **UI 1 trang** (`ui/index.html`, gọi `http://localhost:8000/v1/assistant?q=`). Phải có: ô chat · kết quả · **badge nguồn + confidence** · nút *"vì sao gợi ý quán này"* (hiện `meta.why`). | Live demo |
| T+3 → T+5 | **Deck 8 slide** (khung ở `BATTLE_PLAN.md` §3). **Chừa ô trống cho số** — điền sau khi P1/P2 freeze. | Deck v1 |
| T+5 → T+6 | Chạy **Module 5 Node** (`node module5/server.js`), quay màn hình along-route. **Đừng sửa code Node.** | Clip map-tech |
| T+6 → T+7 | Điền số từ P1/P2 vào deck. Deck v2 = final. | ✅ Deck xong |
| T+7 → T+8.5 | **Quay video ≤3 phút.** Kịch bản: vấn đề (20s) → assistant trả lời (40s) → **bẫy Crystal BBQ** (30s) → enrichment before/after (30s) → **along-route** (40s) → scale (20s). | Video |
| T+8.5 → T+9 | README, dọn repo, push, nộp. | ✅ Nộp |

---

## 3. BA MỐC ĐỒNG BỘ (chỉ 3 lần, mỗi lần ≤15 phút)

| Mốc | Khi | Ai | Nội dung |
|---|---|---|---|
| **S0** | T+0 | cả 3 | Chạy engine cùng nhau. Verify key. Chia branch. **30 phút.** |
| **S1** | T+3 | cả 3 | Báo cáo 3 câu: *xong gì / kẹt gì / có cần cắt gì không*. **15 phút, đứng.** |
| **S2** | **T+6 — FREEZE** | cả 3 | P1+P2 **nộp số**. Merge vào `main`. **Sau mốc này CẤM sửa code engine.** P3 điền số, làm deck + video. |

> **T-1h: buffer. KHÔNG CODE GÌ.** Chỉ nộp bài. Ai code trong giờ này là phá hoại.

---

## 4. THỨ TỰ CẮT (khi tụt giờ — quyết định TẠI S1, không cãi nhau lúc 5h sáng)

```
1. Cắt trước:  enrichment before/after (P2)     → giữ gap analysis report
2. Cắt tiếp:   review_gemini (P1)               → offline keyword vẫn chạy
3. Cắt tiếp:   along-route clip (P3)            → tiếc, nhưng deck vẫn nói được
4. Cắt tiếp:   ocr_gemini (P1)                  → regex parser vẫn chạy
─────────────────────────────────────────────────────────────
KHÔNG BAO GIỜ CẮT:  15 câu eval · UI demo · deck · video
```

**Engine offline đã trả lời được 15/15.** Nghĩa là cắt hết Gemini vẫn nộp được bài. Đó là lưới an toàn.

---

## 5. RỦI RO & ĐỐI SÁCH (định sẵn, không ứng biến lúc 4h sáng)

| Rủi ro | Xác suất | Đối sách (làm ngay, không họp) |
|---|---|---|
| **Gemini hết quota lúc 3h sáng** | Cao | Cache đĩa đã có → **demo vẫn chạy bằng cache**. `GEMINI_CACHE=on` là mặc định. |
| Gemini trả lời dở ở 1-2 câu | Cao | P1 sửa prompt. Nếu hết giờ → để `mode=offline` cho riêng câu đó. **Đúng > hay.** |
| Google Search grounding không chạy | Trung bình | P2 cắt sang gap analysis. Slide 6 đổi thành "chúng tôi **biết** thiếu gì" thay vì "chúng tôi **lấp** được". |
| Merge conflict | **Thấp** | Chia theo file rồi → gần như không thể xảy ra. |
| Wifi hội trường chết | Trung bình | **Video quay sẵn.** Không demo live. Đây là lý do P3 quay video ở T+7. |
| Có người ngủ gật | **Cao** | Chấp nhận. Chia làn xong thì 1 người ngủ không kéo 2 người kia chết. |

---

## 6. ĐỊNH NGHĨA "XONG" (Definition of Done)

Mỗi làn chỉ được nói "xong" khi:

- **P1:** `python -m engine.run_eval --llm` chạy sạch, **15/15 grounded=True**, có 2 con số accuracy (OCR %, review %).
- **P2:** `build/metrics.json` tồn tại, có `before`/`after`, và **mọi field enrich đều có `source` + `confidence < 1.0`** (không giả vờ là data gốc).
- **P3:** Video ≤3 phút **đã export**, deck **đã có số thật** (không còn ô trống), repo push xong.

---

## 7. NẾU CHỈ CÒN 4 GIỜ (kịch bản tệ nhất)

Vứt hết. Làm đúng 3 việc:

1. `run_eval --llm` → nộp `build/eval_answers.md` (**đã có sẵn, ít đội làm cái này**)
2. Deck 8 slide, nhấn **slide 4 (3 lớp chống bịa)** và **slide 5 (3 bằng chứng trung thực)**
3. Video 3 phút quay đúng 1 cảnh: hỏi **Crystal BBQ** → engine **từ chối bịa**

Ba thứ này đủ để kể trọn câu chuyện. Phần còn lại là trang trí.

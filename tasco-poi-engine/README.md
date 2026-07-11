# Tasco POI Intelligence Engine

AI engine biến POI thô thành POI **có cấu trúc, có nguồn gốc, tìm được theo ngữ nghĩa**.
Food là vertical đầu tiên. Engine chạy được trên mọi POI trong DB Tasco.

## Chạy trong 60 giây

```bash
pip install -r requirements.txt          # thực ra không cần gì ngoài Python 3.10+

python -m engine.kb                      # 5 CSV -> build/kb.json  (S1-S4)
python -m engine.run_eval                # trả lời 15 câu, KHÔNG cần mạng
GEMINI_API_KEY=xxx python -m engine.run_eval --llm    # có Gemini, câu trả lời tự nhiên hơn

python -m engine.serve                   # HTTP :8000
```

**Không có key vẫn chạy.** Mất mạng vẫn chạy. Demo không thể sập.

## Kiến trúc

```
5 CSV ──► S1 ingest ──► S2 extract ──► S3 taxonomy ──► S4 quality ──► S5 index ──► S6 retrieve ──► S7 assistant
          entity      OCR/review     text tự do →     completeness   dish vocab   hard filter    Gemini RAG
          resolution  → structured   tag đóng         × agreement    + inverted   + 4-factor     + 3 lớp chống
                                                      × freshness                  rank           hallucination
```

| File | Stage | Việc |
|---|---|---|
| `engine/kb.py` | S1–S4 | CSV → `CanonicalPOI` (mỗi field có `source`, `confidence`, `fetched_at`), taxonomy đóng, quality score + **gap detection** |
| `engine/retrieve.py` | S5–S6 | Query → FilterSpec → hard filter → rank. **Món ăn là ràng buộc CỨNG.** |
| `engine/assistant.py` | S7 | Gemini RAG, grounded, 3 lớp chống bịa |
| `engine/run_eval.py` | — | Chạy 15 câu benchmark → `build/eval_answers.md` |

## Ba lớp chống hallucination

| Lớp | Ở đâu | Làm gì |
|---|---|---|
| **L1 Guard** | code, TRƯỚC khi gọi LLM | Tên quán không có trong KB → `not_found`. **Không gọi LLM** — không cho nó cơ hội bịa. |
| **L2 Prompt** | system prompt | Chỉ được dùng `<evidence>`. Bắt trích dẫn `RESxxx`. Cấm kiến thức ngoài. |
| **L3 Hậu kiểm** | code, SAU khi LLM trả lời | Regex mọi `RESxxx` trong output. Có id không nằm trong evidence → **vứt câu trả lời**, fallback offline. |

## Kết quả trên 2 bẫy của benchmark

| Câu | Sự thật trong data | Engine trả lời |
|---|---|---|
| **6. Crystal BBQ** | Không tồn tại trong bất kỳ dataset nào | `not_found` — *"trả lời sẽ là bịa đặt"* |
| **5. Halal TP.HCM** | Halal chỉ có RES008 (HN), RES027 (Đà Lạt) | Rỗng trung thực **+ tự nới vùng** gợi 2 quán kia |
| **9. POI thấp nhất** | **ĐỒNG HẠNG** RES004 & RES011 = 0.86 | Nêu **cả hai** + nói rõ "không thể chọn một quán duy nhất" |

Câu 9 là chỗ đa số hệ thống sẽ chọn bừa 1 quán rồi sai.

## Quyết định thiết kế đáng chú ý

**Món ăn là ràng buộc CỨNG, không phải signal mềm.**
Bản đầu để món là soft signal → hỏi *"quán nào bán Bún chả"* thì Little Korea BBQ (rating 4.2, không hề có bún chả) xếp **trên** Bún Chả Phố Cổ. Sai hoàn toàn về ý định người dùng.
Sau khi sửa: trả về **đúng 8/8** quán có bún chả, khớp tuyệt đối ground truth.

**Không tin một cột duy nhất.**
Cột `cuisine_type` trong POI CSV noisy. Engine cross-check với `dietary_tags` của menu, và hạ `confidence` xuống 0.4 khi hai nguồn mâu thuẫn.

**Gap detection, không chỉ score.**
12/30 quán không có OCR menu. Engine không chỉ chấm điểm thấp — nó nói **thiếu cái gì** (`gaps: ["ocr_menu", "reviews"]`), tức là chỉ ra đúng việc cần làm để enrich.

## Yêu cầu

Python 3.10+. Không dependency bắt buộc. `GEMINI_API_KEY` là tuỳ chọn.

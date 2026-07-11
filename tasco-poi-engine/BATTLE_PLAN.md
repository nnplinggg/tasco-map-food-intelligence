# BATTLE PLAN — T-minus tới 9h sáng mai

> Ràng buộc: **chỉ có Gemini API**. Deadline **9h sáng 12/07**.
> Với ràng buộc này tôi **tự quyết** 2 câu bạn chưa trả lời, vì không còn thời gian hỏi lại.

---

## 0. QUYẾT ĐỊNH ĐÃ CHỐT (không bàn lại)

### Q2 — Reframe? → **Có, nhưng chỉ ở tầng NARRATIVE. Code không đổi.**
Deliverable vẫn khớp 100% brief P11 (menu OCR, review, POI quality, recommendation, assistant).
Nhưng **deck + README gọi nó là POI Enrichment Engine**, food là vertical đầu tiên.
→ Chi phí: **0 giờ code**. Lợi: giám khảo thấy năng lực map, không thấy demo food thứ N.

### Q3 — Scope? → **30 quán benchmark. KHÔNG bơm OSM.**
Lý do: bơm POI ngoài = 3-4h + rủi ro sập. Không đáng khi còn <14h.
Câu chuyện "scale được" chứng minh bằng **kiến trúc** (gap detection + provenance), không bằng volume.

### Stack → **Gemini LÀ TẤT CẢ. Cắt sạch phần còn lại.**

| Thành phần | Quyết định |
|---|---|
| Gemini Flash | ✅ RAG assistant, OCR vision, query parsing |
| Gemini + Google Search grounding | ✅ enrichment (**thay TinyFish — không cần key thứ 2**) |
| TinyFish / AgentQL | ❌ **CẮT** — không có key |
| Cohere / Jina rerank | ❌ **CẮT** — 30 POI không cần rerank |
| Vector DB (Qdrant/LanceDB) | ❌ **CẮT** — 30 POI, in-memory là thừa |
| OSM Overpass ingestion | ❌ **CẮT** — rủi ro cao, giá trị thấp trong 14h |
| Entity Resolution (S1 LLM) | ❌ **CẮT** — chỉ 1 nguồn thì không có gì để resolve |

---

## 1. ĐÃ XONG (tôi build rồi, chạy được ngay)

```bash
python -m engine.kb        # 30 POI + 179 món + 150 review -> KB có provenance
python -m engine.run_eval  # 15/15 câu, KHÔNG cần mạng
python -m engine.serve     # HTTP :8000
```

| Đã có | Trạng thái |
|---|---|
| S1–S4: KB builder, taxonomy đóng, quality + **gap detection** | ✅ chạy |
| S5–S6: hybrid retrieval, **món = ràng buộc cứng** | ✅ chạy, khớp 8/8 ground truth bún chả |
| S7: assistant + **3 lớp chống hallucination** | ✅ chạy |
| 15 câu eval → `build/eval_answers.md` | ✅ 15/15 route đúng |
| Bẫy Crystal BBQ | ✅ `not_found`, không gọi LLM |
| Bẫy Halal TP.HCM | ✅ rỗng trung thực + tự nới vùng |
| Câu 9 đồng hạng RES004/RES011 | ✅ nêu cả hai |
| HTTP server + PlaceResult DTO | ✅ chạy |
| **Module 5 along-route (Node, có sẵn từ trước)** | ✅ **đã có, đừng đụng vào** |

---

## 2. LỊCH T-MINUS (giả định bây giờ ~11h đêm, còn ~10h)

| Giờ | Việc | Ai | Cắt được? |
|---|---|---|---|
| **T-10 → T-9** | Cắm `GEMINI_API_KEY`, chạy `run_eval --llm`. Đọc **cả 15 câu trả lời**. Câu nào Gemini nói dở → sửa `SYSTEM` prompt trong `assistant.py`. | Dev 1 | ❌ **KHÔNG** |
| **T-9 → T-8** | **Menu OCR bằng Gemini vision** (câu 2 benchmark). Thêm `engine/ocr_gemini.py`: raw_ocr_text → JSON menu có dấu, giá integer. So với Menu Dataset → in ra **accuracy %**. Con số này lên deck. | Dev 2 | ⚠️ có (đã có regex fallback) |
| **T-8 → T-7** | **Review → aspect bằng Gemini batch** (câu 6, 8, 13). 150 review 1 lượt. So với `known_strengths/weaknesses` → **accuracy %**. | Dev 3 | ⚠️ có |
| **T-7 → T-6** | **Enrichment demo**: 12 quán thiếu OCR → Gemini + Google Search grounding lấp gap → quality score nhảy lên. **Đây là cảnh đắt nhất của demo.** | Dev 2 | ⚠️ có, nhưng tiếc |
| **T-6 → T-5** | **UI demo** 1 trang: ô chat + kết quả + badge nguồn/confidence + nút "vì sao gợi ý quán này". Dùng luôn `/v1/assistant`. | Dev 4 | ❌ **KHÔNG** (phải có live demo) |
| **T-5 → T-4** | **Nối Module 5 along-route** vào narrative. Node server có sẵn, chỉ cần chạy + quay màn hình. | Dev 4 | ⚠️ có |
| **T-4 → T-2** | **DECK** (xem §3) | Dev 1 | ❌ **KHÔNG** |
| **T-2 → T-1** | **Quay video demo 3 phút.** Quay TRƯỚC, đừng demo live trên sân khấu. | cả team | ❌ **KHÔNG** |
| **T-1 → T-0** | Dọn repo, README, đẩy git, nộp. **Buffer 1h — đừng code gì.** | Dev 1 | ❌ **KHÔNG** |

**Nếu tụt giờ, cắt theo thứ tự:** enrichment demo → along-route → review LLM → OCR vision.
**Không bao giờ cắt:** eval 15 câu, UI demo, deck, video.

---

## 3. DECK — 8 slide, viết theo thứ tự này

| # | Slide | Nội dung |
|---|---|---|
| 1 | **Vấn đề** | *"Google Maps VN có POI nhưng POI rỗng."* 12/30 quán trong chính dataset của BTC không có menu số hoá. Không tra được "có món dưới 100k không". |
| 2 | **Insight** | Tài sản Tasco không phải data ẩm thực — là **hạ tầng bản đồ**. Nên ta không build app đồ ăn. Ta build **engine bơm ruột cho POI**. |
| 3 | **Kiến trúc** | 7 stage S1→S7. Nhấn: **mỗi field có `source` + `confidence` + `fetched_at`**. Google Maps không show cái này. |
| 4 | **Chống bịa — 3 lớp** | L1 guard (không gọi LLM), L2 prompt, L3 hậu kiểm regex `RESxxx`. **Slide này ăn điểm engineer.** |
| 5 | **Bằng chứng trung thực** | Bảng 3 dòng: Crystal BBQ → not_found. Halal HCM → rỗng + nới vùng. POI thấp nhất → **đồng hạng 2 quán**. *"Đa số hệ thống sẽ chọn bừa 1 quán và sai."* |
| 6 | **Enrichment** | 12 quán gap → Gemini lấp → quality 0.6→0.9. **Ảnh before/after.** |
| 7 | **Map-native ⭐** | Along-route search: gợi quán **phía trước**, detour tính bằng **2 lần gọi Valhalla thật**. Google Maps VN không làm được vì không có route engine trong tay. |
| 8 | **Scale** | Engine không biết gì về "nhà hàng". Nó biết "POI thiếu thông tin". Chạy được trên **toàn bộ POI DB Tasco ngày mai.** |

---

## 4. CHECKLIST NỘP BÀI (theo đúng brief §9)

- [ ] Presentation deck (8 slide trên)
- [ ] Video demo ≤3 phút (**quay sẵn**, không demo live)
- [ ] Source code repo (đã có, sạch)
- [ ] README (đã có — setup + technical + AI approach)
- [ ] Data enrichment workflow → §Kiến trúc trong README
- [ ] OCR methodology → `engine/ocr_gemini.py` + accuracy %
- [ ] Recommendation methodology → `engine/retrieve.py` + lý do món là ràng buộc cứng
- [ ] POI quality approach → `engine/kb.py` §S4 (completeness × agreement × freshness)
- [ ] **`build/eval_answers.md`** — 15 câu trả lời sẵn. **Nộp cái này.** Ít đội làm.

---

## 5. BA THỨ ĐỪNG LÀM (đêm nay)

1. **Đừng thêm vector DB / rerank.** 30 POI. Không có tác dụng. Tốn 2h.
2. **Đừng demo live.** Quay video. Wifi hội trường sẽ phản bội bạn.
3. **Đừng đụng vào Module 5 (Node).** Nó đang chạy. Chỉ cần quay màn hình.

---

## 6. CÂU BÁN HÀNG (thuộc lòng, nói trong 15 giây)

> *"Google Maps Việt Nam có POI nhưng POI rỗng — không tra được món, không tra được giá, không biết có chỗ đỗ ô tô không. Chúng tôi làm engine tự bơm ruột cho POI, mỗi trường dữ liệu đều truy được nguồn và độ tin cậy. Và vì Tasco có route engine thật trong tay, POI của Tasco tìm được **theo hành trình** — gợi quán phía trước, detour tính bằng số thật, không phải bán kính quanh một điểm. Đó là thứ Google Maps VN không làm được."*

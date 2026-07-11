# THIẾT KẾ ENGINE — BẢN ĐỀ XUẤT (chưa build, chờ confirm)

> Tasco Maps AI Hackathon — P11 Restaurant & Menu Intelligence
> Trạng thái: **PROPOSAL — chờ confirm 4 câu hỏi ở mục 6 trước khi build**
> Ngày: 11/07/2026

---

## 0. INSIGHT GỐC — reframe lại đề bài

Đây là điểm quan trọng nhất, nếu sai chỗ này thì mọi thứ sau đều lệch.

> **Tài sản của Tasco KHÔNG phải data ẩm thực. Tài sản là hạ tầng bản đồ** (Valhalla routing, Pelias geocoding, POI DB, VETC vehicle mobility).
> 30 quán trong dataset là **đồ chơi benchmark**, không phải sản phẩm.

Nên thứ ta build **không phải "app đồ ăn"**, mà là:

> ### **POI Enrichment & Retrieval Engine**
> Một layer biến *bất kỳ POI thô nào* (30 quán benchmark, hay 1 triệu POI OSM thật trong DB Tasco) thành POI **có cấu trúc + có độ tin cậy + tìm được theo ngữ nghĩa + gắn được vào route**.
>
> **Food chỉ là vertical đầu tiên để chứng minh engine chạy.**

Cái này trả lời trực tiếp yêu cầu *"focus vào cải thiện công nghệ map cho Tasco"*: giám khảo thấy không phải 1 demo food, mà là **một năng lực map mới** mà Tasco có thể apply lên toàn bộ POI DB ngày mai.

**Câu bán hàng 1 dòng:**

> *"Google Maps VN có POI nhưng POI rỗng. Chúng tôi làm engine tự bơm ruột cho POI — và vì Tasco có route engine thật, POI của Tasco tìm được theo hành trình, không chỉ theo bán kính."*

---

## 1. KIẾN TRÚC 7 TẦNG (raw data → search / recommendation)

```
S0  SOURCE REGISTRY              mọi field đều mang provenance + confidence
     ↓
S1  INGEST + ENTITY RESOLUTION   gộp cùng 1 quán từ nhiều nguồn về 1 canonical POI
     ↓
S2  EXTRACTION                   OCR menu / review→aspect / web page→structured
     ↓
S3  NORMALIZATION                taxonomy chuẩn: cuisine, segment, amenity, dietary, price tier
     ↓
S4  CONFIDENCE + QUALITY         POI Quality Score = độ đầy đủ × độ tin cậy × độ tươi
     ↓
S5  INDEXING                     hybrid: structured filter + BM25 + vector + GEO/ROUTE index
     ↓
S6  RETRIEVAL + RERANK           recall rộng → rerank → LLM re-rank (chỉ top-K)
     ↓
S7  SERVE                        /search  /nearby  /along-route  /assistant (RAG)
```

**Điểm khác biệt map-native nằm ở S5 + S7:** không ai index POI theo *route corridor*. Ta có Valhalla → ta làm được **"along-route search"** (tìm dọc tuyến, không phải quanh điểm). Đó là feature Google Maps VN không có.

---

## 2. CHI TIẾT TỪNG STAGE + API DÙNG GÌ

| Stage | Input | AI/API làm gì | API đề xuất | Fallback |
|---|---|---|---|---|
| **S1 Ingest + ER** | POI CSV Tasco + POI từ OSM/Overpass + POI scrape ngoài | Dedupe: cùng quán, khác nguồn, khác tên (`Phở Hàng Quân` vs `Pho Hang Quan 123 THĐ`) → 1 `canonical_id`. Dùng geo-distance (<50m) + name embedding similarity + LLM tie-break | **Tasco geocode/reverse-geocode**, **OSM Overpass** (free), embedding (Jina/Gemini free) | rule: haversine + fuzzy name |
| **S2a OCR menu** | ảnh/PDF menu, raw OCR text | Ảnh → JSON menu có dấu, đúng giá | **Gemini Flash vision** (free tier, đọc tiếng Việt tốt) hoặc **PaddleOCR / VietOCR** self-host | regex parser (đã spec ở SYSTEM_02) |
| **S2b Review→aspect** | 150 review + review scrape ngoài | Aspect + sentiment + quote, output JSON strict | **Groq / Cerebras** (free, cực nhanh, batch 150 review trong vài giây) | keyword dictionary |
| **S2c Web enrichment** | tên quán + địa chỉ | Agent vào web (Foody / Google / Fanpage) lấy: giờ mở, ảnh, món, review, amenity | **TinyFish / AgentQL** ← *đây là mảnh còn thiếu của Tasco*<br>+ **Tavily / Brave Search** free tier<br>+ **Jina Reader** (`r.jina.ai`, free, page → markdown) | bỏ qua, đánh dấu `enrichment_gap` |
| **S3 Normalize** | text tự do từ mọi nguồn | Map về taxonomy đóng (VD `"có chỗ để ô tô"`, `"parking"`, `"bãi xe rộng"` → `amenity:car_parking`) | LLM cheap (Gemini Flash / Groq) + **structured output** bắt buộc | dictionary mapping |
| **S4 Quality Score** | canonical POI | Không cần AI — công thức: `completeness × source_agreement × freshness` | thuần code | — |
| **S5 Index** | canonical POI | Embed `name + desc + menu + aspect` → vector; build BM25; build geo R-tree; build **route-corridor index** | **Jina embeddings v3** (multilingual, free) hoặc **Gemini embedding**; **Qdrant free 1GB** / **LanceDB local** | in-memory cosine (30 quán thì thừa sức) |
| **S6 Retrieve + Rerank** | query NL | ① LLM parse query → FilterSpec JSON<br>② hybrid recall<br>③ rerank<br>④ LLM re-rank top-10 | **Cohere Rerank** (multilingual, free trial) hoặc **Jina Reranker** (free) | công thức 4-factor đã spec |
| **S7 Serve** | HTTP | `/search`, `/nearby`, **`/along-route`**, `/assistant` (RAG) | **Tasco Valhalla route** cho along-route | — |

---

## 3. STACK API MIỄN PHÍ — đề xuất cụ thể

### LLM (structuring, parsing, rerank, assistant)
- **Google Gemini Flash** — free tier rộng, vision (OCR menu), tiếng Việt tốt, structured output → **làm xương sống**
- **Groq / Cerebras** — free, tốc độ cực cao → dùng cho **batch 150 review + 179 menu item** (chạy song song, xong trong <1 phút)
- **OpenRouter free models** — dự phòng khi rate-limit

### Embedding + Rerank
- **Jina Embeddings v3** (multilingual, free) + **Jina Reranker** (free)
- hoặc **Cohere embed-multilingual-v3 + rerank-multilingual** (free trial)

### Web / Agentic data (mảnh Tasco đang thiếu)
- **TinyFish / AgentQL** — agent query web page bằng natural language → structured
- **Jina Reader** (`r.jina.ai/<url>`) — free, page → markdown, không cần key
- **Tavily / Brave Search API** — free tier, search grounding

### Geo (bổ trợ Tasco)
- **OSM Overpass API** — free, lấy POI + amenity thật của VN (cực tốt để bù dữ liệu bãi đỗ xe)
- **Nominatim / Photon** — free geocode dự phòng

### Vector store
- **Qdrant Cloud free** / **LanceDB local** / thuần in-memory (30 POI thì không cần DB)

> ⚠️ **Cảnh báo trung thực:** free tier và danh sách sponsor thay đổi liên tục. Trước khi build sẽ **search verify** từng API còn free + còn key hay không, thay vì tin trí nhớ.

---

## 4. BA THỨ LÀM ĐÂY THÀNH "MAP TECH", KHÔNG PHẢI "FOOD APP"

Ba feature đề xuất **đóng đinh** vào demo:

### 4.1 Along-Route Search (`/v1/search/along-route`)
Query: *"tìm quán chay còn mở, detour <5 phút, trên tuyến tôi đang đi"*

→ dùng Valhalla polyline, snap POI vào corridor, tính detour thật bằng 2 lần route call.

**Google Maps VN không có. Foody không có. Chỉ Tasco có route engine để làm.**

### 4.2 POI Enrichment Pipeline (auto, scalable)
Chứng minh: đưa vào 12 quán **KHÔNG có OCR** (RES019–RES030) → engine tự đi web (TinyFish / Jina Reader) lấy menu + review → POI Quality Score nhảy từ 0.6 → 0.9 **live trên sân khấu**.

Đây là "cải thiện công nghệ map" theo nghĩa đen: **POI DB tự làm giàu chính nó.**

### 4.3 Provenance & Confidence trên từng field
Mỗi field có `{ value, source, confidence, fetched_at }`.

→ Tasco dám đưa vào production. Google Maps không show cái này. Giám khảo là engineer → cực ăn điểm.

---

## 5. DRAFT MASTER PROMPT (để drive AI code sau này)

```
ROLE: Bạn build POI Enrichment & Retrieval Engine cho Tasco Maps.

MENTAL MODEL (không được lệch):
- Đầu vào không phải "30 nhà hàng". Đầu vào là "một POI bất kỳ, thiếu thông tin".
- Đầu ra không phải "danh sách quán". Đầu ra là "POI đã được làm giàu, có provenance,
  index được, truy vấn được theo ngữ nghĩa VÀ theo hành trình".
- Mọi field phải trả lời được: giá trị này từ đâu ra, tin bao nhiêu %, lấy lúc nào.

INVARIANTS (vi phạm = fail):
1. KHÔNG hallucination. Không có data → trả not_found / empty + gap flag. Không bịa.
2. Giữ nguyên dấu tiếng Việt trong mọi output hiển thị.
3. Giá VND là integer, khớp tuyệt đối ground truth khi có.
4. Mọi LLM call phải structured output (JSON schema), không free-text parse.
5. Mọi external call: cache-first trên đĩa. Demo phải chạy được khi MẤT MẠNG.
6. Tách bạch: data benchmark (30 quán) và data enrichment ngoài KHÔNG trộn vào nhau.

PIPELINE: S1 ER → S2 Extract → S3 Normalize → S4 Score → S5 Index → S6 Retrieve → S7 Serve
(mỗi stage là 1 module thuần hàm, test được độc lập, không side effect chéo)

OUTPUT CONTRACT: PlaceResult DTO theo API doc Tasco. Field mở rộng chỉ nằm trong `meta`.
```

---

## 6. CÂU HỎI CẦN CONFIRM TRƯỚC KHI BUILD

**Không build gì cho tới khi trả lời 4 câu này** — vì trả lời sai thì code sai hướng:

### 6.1 API nào bạn THẬT SỰ có key trong Build Week?
Liệt kê giúp: TinyFish / AgentQL? Gemini? Groq? Cohere? Tavily? Credit bao nhiêu?
→ Không muốn spec một stack mà bạn không có key.

### 6.2 Reframe "POI Enrichment Engine" (mục 0) — ĐỒNG Ý hay giữ nguyên khung "food app" của P11?
Đây là quyết định chiến lược lớn nhất. Nó đổi toàn bộ narrative + deck.

### 6.3 Scope demo
30 quán benchmark thôi, hay **bơm thêm POI thật từ OSM / Tasco API** để chứng minh engine scale được?
→ Khuyến nghị: **có**, vì đó chính là "map tech".

### 6.4 Deadline & team
Còn bao nhiêu giờ? Bao nhiêu dev?
→ Sẽ cắt scope theo đó chứ không spec đồ thừa.

---

## 7. SAU KHI CONFIRM — SẼ GIAO GÌ

Trả lời 4 câu ở mục 6, sẽ dựng ngay:

1. **Spec kỹ thuật đầy đủ 7 stage** (I/O contract, pseudo-code, edge case, test case mỗi stage)
2. **Master prompt hoàn chỉnh** (bản production, dùng để drive AI code generator)
3. **Code skeleton chạy được** (S1→S7, cache-first, offline-safe)
4. **Deck narrative** (problem → engine → 3 differentiator map-native → demo flow)

---

*Tài liệu này là bản đề xuất. Chưa có dòng code nào được viết.*

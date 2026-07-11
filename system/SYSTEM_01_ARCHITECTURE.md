# SYSTEM_01_ARCHITECTURE — v2
## POI Enrichment & Retrieval Engine (thay thế v1)

> **Trạng thái:** v2 thay thế hoàn toàn SYSTEM_01 v1.
> **Lý do thay:** reframe từ "food app 5 module song song" → "POI enrichment engine 7 stage + 2 lane".
> **Còn treo:** 4 câu hỏi ở §9 chưa được confirm → các mục đánh dấu `[ASSUMPTION]` có thể đổi.
> **Ngày:** 11/07/2026

---

## 0. ĐIỀU GÌ ĐỔI SO VỚI v1

| | v1 | v2 | Lý do |
|---|---|---|---|
| Hình dạng | 5 module **song song**, độc lập data | 7 stage **nối tiếp** (pipeline), 2 lane | Enrichment vốn là pipeline: resolve → extract → normalize → score → index. Không thể song song. |
| Đơn vị dữ liệu | `POI` (record CSV phẳng) | `CanonicalPOI` — mỗi field là `{value, source, confidence, fetched_at}` | Không có provenance thì không dám đưa vào POI DB production. |
| Nguồn data | Đóng: 5 CSV | Mở: CSV + OSM + web agent + Tasco API | 12/30 quán thiếu OCR. Muốn lấp thì phải đi ra ngoài. |
| Ranking | Công thức 4-factor **là toàn bộ ranker** | 4-factor tụt xuống thành **1 signal trong S6** | Hybrid recall + rerank mạnh hơn nhiều, nhưng 4-factor vẫn là fallback tin cậy. |
| LLM | Không có | Xương sống S2/S3/S6; rule cũ thành **fallback** | OCR regex không đọc nổi menu ảnh thật. |
| Module 5 | Stretch, 0 điểm, cắt đầu tiên | **Core differentiator**: along-route search | Đây mới là "công nghệ map". Cắt nó = mất luôn lý do Tasco làm cái này. |
| Model song song | 4 dev × 4 module | **2 lane** × N dev | Xem §2. |

### Cái gì SỐNG SÓT nguyên vẹn từ v1
- `PlaceResult` DTO — vẫn là output contract duy nhất
- Công thức `0.40·rating + 0.20·pop + 0.25·match + 0.15·price_fit` → thành S6 signal + Lane A ranker
- Regex OCR parser → S2a **fallback**
- Keyword review extractor → S2b **fallback**
- POI Quality Score → S4, nhưng mở rộng (thêm `source_agreement` + `freshness`)
- 15 câu eval + 2 bẫy (Crystal BBQ, Halal HCMC) → thành **invariant xuyên suốt**
- Rule cách ly benchmark ↔ enrichment → tổng quát hoá thành **kiến trúc 2 lane**

---

## 1. MENTAL MODEL

> Đầu vào không phải "30 nhà hàng". Đầu vào là **"một POI bất kỳ, thiếu thông tin"**.
> Đầu ra không phải "danh sách quán". Đầu ra là **"POI đã làm giàu, có provenance, index được, truy vấn được theo ngữ nghĩa VÀ theo hành trình"**.
>
> Food là vertical đầu tiên. Engine phải chạy được trên mọi POI trong DB Tasco.

---

## 2. KIẾN TRÚC 2 LANE (quyết định quan trọng nhất của v2)

Pipeline nối tiếp có rủi ro chết người: **enrichment lỗi → eval chết**. Nên tách:

### Lane A — BENCHMARK (không được phép fail)
- **Input:** 5 CSV, 30 quán
- **Xử lý:** thuần code. **Không LLM. Không mạng. Không external API.**
- **Ranker:** công thức 4-factor v1
- **Trách nhiệm:** bảo đảm **15/15 điểm eval**
- **Deploy:** chạy được offline, deterministic, <100ms

### Lane B — ENRICHMENT / MAP-TECH (bán câu chuyện)
- **Input:** POI thô (OSM, Tasco POI DB, 12 quán thiếu OCR)
- **Xử lý:** S1→S7, LLM + web agent + Tasco route API
- **Trách nhiệm:** chứng minh **năng lực map mới** cho giám khảo
- **Deploy:** cache-first, offline replay khi demo

### Hợp đồng giữa 2 lane
- Chia sẻ: `lib/` (normalize, price, taxonomy, geometry) + `PlaceResult` DTO
- **Lane B fail KHÔNG kéo Lane A chết.** Không import chéo, không shared mutable state.
- Test tự động scan source: Lane A không được require bất kỳ file nào trong `laneB/`

> **Rule vàng:** nếu 30 phút trước pitch mà Lane B sập, ta vẫn demo được Lane A và vẫn có 15/15 điểm.

---

## 3. PIPELINE 7 STAGE (Lane B)

```
S1  ENTITY RESOLUTION     nhiều nguồn → 1 CanonicalPOI
     ↓
S2  EXTRACTION            ảnh/OCR/review/web page → structured
     ↓
S3  NORMALIZATION         text tự do → taxonomy đóng
     ↓
S4  CONFIDENCE + QUALITY  completeness × source_agreement × freshness
     ↓
S5  INDEXING              structured + BM25 + vector + GEO + ROUTE-CORRIDOR
     ↓
S6  RETRIEVAL + RERANK    query→FilterSpec → hybrid recall → rerank
     ↓
S7  SERVE                 /search /nearby /along-route /assistant
```

### S1 — Entity Resolution
**Vấn đề:** `Phở Hàng Quân` (CSV Tasco) và `Pho Hang Quan, 123 Trần Hưng Đạo` (OSM) là **cùng một quán**.

**Thuật toán:**
1. Blocking: geo grid, chỉ so các POI cách nhau <100m
2. Candidate score = `0.5·geo_proximity + 0.3·name_embedding_sim + 0.2·address_token_overlap`
3. Nếu score ∈ [0.6, 0.8] → **LLM tie-break** (structured output: `{same_entity: bool, reason: string}`)
4. Merge → `canonical_id`, mọi field giữ nguyên nguồn gốc

**Output:** `CanonicalPOI` với `sources[]`

**Fallback (không LLM):** haversine <50m + fuzzy name ≥0.85 → merge

---

### S2 — Extraction
| Sub | Input | Chính | Fallback |
|---|---|---|---|
| **S2a** OCR menu | ảnh menu / raw OCR text | LLM vision → JSON menu (có dấu, giá integer) | regex parser v1 |
| **S2b** Review → aspect | review text | LLM batch → `{aspect, sentiment, quote, confidence}[]` | keyword dictionary v1 |
| **S2c** Web enrichment | tên + địa chỉ | Web agent → giờ mở, amenity, món, ảnh | bỏ qua, set `enrichment_gap: true` |

**Bắt buộc:** mọi LLM call dùng **structured output / JSON schema**. Không parse free-text.

---

### S3 — Normalization
Text tự do → **taxonomy đóng**. Đây là stage v1 không có, và là lý do v1 không scale được.

```
"có chỗ để ô tô" ─┐
"parking"         ├─→ amenity:car_parking
"bãi xe rộng"     ┘

"phù hợp trẻ em" ─┐
"kid friendly"    ├─→ segment:family
"có ghế em bé"    ┘
```

**Taxonomy cần định nghĩa (đóng, versioned):**
- `cuisine.*` — vietnamese, japanese, korean, seafood, …
- `segment.*` — family, business, romantic, casual, fast_food, late_night
- `amenity.*` — car_parking, kid_friendly, wifi, aircon, outdoor, private_room
- `dietary.*` — vegetarian, vegan, halal, gluten_free
- `price_tier` — 1–5

**Fallback:** dictionary mapping tay.

---

### S4 — Confidence + Quality
```
poi_quality_score = completeness × source_agreement × freshness

completeness      = (# field bắt buộc có value) / (# field bắt buộc)
source_agreement  = 1 - disagreement_rate giữa các nguồn cho cùng 1 field
freshness         = decay(now - max(fetched_at))
```

**Khác v1:** v1 chỉ đo *completeness*. v2 đo thêm **độ đồng thuận nguồn** và **độ tươi** — đây mới là "trustworthy" theo brief.

**Demo hook:** đưa RES019–RES030 (không có OCR) qua Lane B → score nhảy từ ~0.6 → ~0.9 **live trên sân khấu**.

---

### S5 — Indexing (4 index song song)
| Index | Dùng để | Tech |
|---|---|---|
| **Structured** | filter cứng: city, segment, amenity, price, hours | in-memory map |
| **BM25** | keyword match: tên món, tên quán | lunr / thuần code |
| **Vector** | semantic: "quán yên tĩnh hợp hẹn hò" | embedding + cosine |
| **GEO + ROUTE-CORRIDOR** ⭐ | **tìm dọc tuyến, không phải quanh điểm** | Valhalla polyline + snap-to-segment |

**Route-corridor index là thứ không ai có.** Cách build:
1. Lấy polyline tuyến từ Valhalla
2. Với mỗi POI: `snap_to_polyline()` → `(progress_km, lateral_offset_m)`
3. Index theo `progress_km` → query "quán phía trước trong 40km" thành range scan O(log n)

---

### S6 — Retrieval + Rerank
```
query NL
  ↓ LLM parse (structured output)
FilterSpec {segments, amenities, price, dietary, hours, city, corridor?}
  ↓
HYBRID RECALL (union, top-50)
  ├─ structured filter  (hard constraint, loại thẳng)
  ├─ BM25              (keyword)
  ├─ vector            (semantic)
  └─ corridor range    (nếu có corridor context)
  ↓
FUSE (reciprocal rank fusion) → top-20
  ↓
RERANK
  ├─ signal 1: công thức 4-factor v1  ← v1 sống ở đây
  ├─ signal 2: poi_quality_score (S4)
  ├─ signal 3: detour cost (nếu corridor)
  └─ signal 4: cross-encoder rerank (LLM/rerank API)
  ↓
top-10 → PlaceResult[]
```

---

### S7 — Serve
| Endpoint | Lane | Mô tả |
|---|---|---|
| `GET /v1/search` | A + B | Semantic search (Lane A = 4-factor, Lane B = hybrid) |
| `GET /v1/nearby` | B | Bán kính quanh điểm |
| **`GET /v1/search/along-route`** ⭐ | B | **Tìm dọc tuyến + detour thật.** Differentiator. |
| `POST /v1/menu/parse` | A + B | OCR (A = regex, B = vision) |
| `GET /v1/reviews/analyze` | A + B | Aspect (A = keyword, B = LLM) |
| `GET /v1/poi/{id}/quality` | A + B | Quality score |
| `POST /v1/assistant` | B | RAG Q&A trên enriched POI |

---

## 4. DATA MODEL — `CanonicalPOI` (thay thế `POI` của v1)

```typescript
interface ProvenancedField<T> {
  value: T;
  source: "tasco_csv" | "osm" | "web_agent" | "llm_inferred" | "tasco_api";
  confidence: number;        // 0.0–1.0
  fetched_at: string;        // ISO 8601
}

interface CanonicalPOI {
  canonical_id: string;                        // "poi:canon:abc123"
  source_ids: string[];                        // ["tasco:res001", "osm:node/123"]

  name: ProvenancedField<string>;
  coordinates: ProvenancedField<{lat, lon}>;
  address: ProvenancedField<string>;
  city: ProvenancedField<string>;

  cuisine: ProvenancedField<string[]>;         // taxonomy đóng
  segments: ProvenancedField<string[]>;        // taxonomy đóng
  amenities: ProvenancedField<string[]>;       // taxonomy đóng
  dietary: ProvenancedField<string[]>;         // taxonomy đóng

  hours: ProvenancedField<OpeningHours>;
  price_tier: ProvenancedField<number>;

  menu: ProvenancedField<MenuItem[]>;
  aspects: ProvenancedField<Aspect[]>;

  quality: {
    score: number;
    completeness: number;
    source_agreement: number;
    freshness: number;
    gaps: string[];                            // ["menu", "hours"] — field còn thiếu
  };

  // Chỉ có khi query theo corridor
  corridor_position?: {
    corridor_id: string;
    progress_km: number;
    lateral_offset_m: number;
    detour_meters: number;
    detour_seconds: number;
  };
}
```

**Điểm mấu chốt:** mọi field trả lời được 3 câu — *từ đâu ra? tin bao nhiêu %? lấy lúc nào?*

---

## 5. INVARIANTS (vi phạm = fail)

1. **KHÔNG hallucination.** Không có data → `not_found` / `[]` + `gap flag`. Không bịa.
   - Crystal BBQ → 404
   - Halal HCMC → `200 { results: [] }` (không phải error)
2. **Giữ nguyên dấu tiếng Việt** trong mọi output hiển thị.
3. **Giá VND là integer**, khớp tuyệt đối ground truth khi có.
4. **Mọi LLM call = structured output.** Không free-text parse.
5. **Mọi external call = cache-first trên đĩa.** Demo phải chạy khi **MẤT MẠNG**.
6. **Lane A không import Lane B.** Test tự động verify.
7. **Data benchmark (30 quán) không trộn với data enrichment.** Không bao giờ.

---

## 6. PHÂN CÔNG (thay model "4 dev × 4 module" của v1)

| Người | Lane | Việc |
|---|---|---|
| Dev 1 | **A** | Lane A trọn gói: load CSV → rule extract → 4-factor rank → 15/15 eval. **Ưu tiên tuyệt đối.** |
| Dev 2 | B | S1 (entity resolution) + S2 (extraction: vision OCR, review LLM) |
| Dev 3 | B | S3 (taxonomy) + S4 (quality score) + S5 (index) |
| Dev 4 | B | S5 route-corridor index + S7 `/along-route` + demo UI |
| Dev 5 | — | `lib/` shared kernel + DTO + test harness + integration |

**Thứ tự cắt scope nếu bí giờ:** S2c (web agent) → S6 rerank → S1 LLM tie-break → toàn bộ Lane B.
**Không bao giờ cắt:** Lane A.

---

## 7. CẤU TRÚC THƯ MỤC

```
src/
├── lib/                          # shared kernel — cả 2 lane dùng
│   ├── normalize.js
│   ├── price.js
│   ├── taxonomy.js               # ⭐ mới: taxonomy đóng, versioned
│   ├── geometry.js               # polyline, haversine, snap-to-segment
│   ├── dto.js                    # PlaceResult, CanonicalPOI
│   └── ranker_4factor.js         # công thức v1 — dùng ở Lane A + S6 signal
│
├── laneA/                        # BENCHMARK — không mạng, không LLM
│   ├── load_csv.js
│   ├── extract_rule.js           # regex OCR + keyword review (fallback v1)
│   ├── quality_simple.js
│   ├── search.js                 # 4-factor rank
│   └── eval_runner.js            # 15 câu
│
├── laneB/                        # ENRICHMENT — LLM + web + Tasco API
│   ├── s1_resolve/
│   ├── s2_extract/
│   │   ├── ocr_vision.js
│   │   ├── review_llm.js
│   │   └── web_agent.js
│   ├── s3_normalize/
│   ├── s4_quality/
│   ├── s5_index/
│   │   ├── structured.js
│   │   ├── bm25.js
│   │   ├── vector.js
│   │   └── corridor.js           # ⭐ route-corridor index
│   ├── s6_retrieve/
│   ├── s7_serve/
│   └── cache/                    # cache-first, offline replay
│
└── server.js                     # router → lane A hoặc lane B
```

---

## 8. `[ASSUMPTION]` — chờ confirm

Các mục này tôi **giả định**, sẽ sửa khi bạn trả lời §9:

- `[ASSUMPTION]` LLM backbone = Gemini Flash (vision + structured output + free tier)
- `[ASSUMPTION]` Batch LLM = Groq/Cerebras (150 review + 179 menu item)
- `[ASSUMPTION]` Web agent = TinyFish/AgentQL, fallback Jina Reader
- `[ASSUMPTION]` Embedding + rerank = Jina (multilingual, free)
- `[ASSUMPTION]` Vector store = in-memory (30–500 POI thì không cần DB)
- `[ASSUMPTION]` POI ngoài = OSM Overpass (free) + Tasco nearby-search API
- `[ASSUMPTION]` Corridor demo = Hà Nội → Hạ Long (đã có cache từ v1)

---

## 9. 4 CÂU HỎI CÒN TREO

1. **API nào bạn THẬT SỰ có key trong Build Week?** (TinyFish/AgentQL? Gemini? Groq? Cohere? Tavily? credit bao nhiêu?)
2. **Reframe "POI Enrichment Engine" — ĐỒNG Ý hay giữ khung "food app" P11?**
3. **Scope demo:** 30 quán benchmark thôi, hay bơm thêm POI thật từ OSM/Tasco để chứng minh scale?
4. **Deadline & team:** còn bao nhiêu giờ, bao nhiêu dev?

---

## 10. HỆ QUẢ LÊN CÁC DOC KHÁC

| Doc | Trạng thái sau v2 |
|---|---|
| `SYSTEM_01_ARCHITECTURE.md` | ❌ **Bị thay bởi file này** |
| `SYSTEM_02_ALGORITHMS.md` | ⚠️ Còn dùng được cho **Lane A** (thuật toán v1 = Lane A). Cần **bổ sung** thuật toán S1–S6 cho Lane B. |
| `SYSTEM_03_DATA_MODELS.md` | ⚠️ `PlaceResult` giữ nguyên. Cần **thêm** `CanonicalPOI` + `ProvenancedField`. |
| `SYSTEM_04_TEST_PLAN.md` | ⚠️ Test v1 = test Lane A, giữ nguyên. Cần **thêm** test per-stage cho Lane B + test cách ly 2 lane. |
| `SYSTEM_05_BUILD_RUNBOOK.md` | ⚠️ Cần **thêm** lệnh build Lane B (cache, API key, offline replay). |

**Tôi sẽ regen 02–05 sau khi bạn trả lời §9** — regen bây giờ là lãng phí, vì answer sẽ đổi stack.

---

*v2 — 11/07/2026. Thay thế v1.*

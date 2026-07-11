# Spec 01 — Semantic Search + Filter

> Module quan trọng nhất: trả lời trực tiếp ~9/15 câu Public Evaluation
> (Food Search, Family Dining, Dietary, Halal, Budget, Late Night, Romantic, Business Dining, Menu Search).
> **Không được cắt.**

## 0. Quy ước chung (áp dụng cho cả 4 module)

- File dữ liệu (tên thật trên đĩa, khuyến nghị rename — xem Rủi ro):
  - `ai_maps_track6_dataset_participants.xlsm - Restaurant POI Dataset.csv` (30 dòng, RES001–RES030)
  - `ai_maps_track6_dataset_participants.xlsm - Menu Dataset.csv` (179 dòng, phủ đủ 30 quán)
- ID ổn định: `poi:` + `restaurant_id` viết thường → `poi:res001`. Không bao giờ sinh ID mới giữa các lần gọi.
- Giữ nguyên dấu tiếng Việt trong mọi text output. So khớp (matching) thì dùng bản bỏ dấu + lowercase, nhưng **hiển thị** luôn dùng bản gốc có dấu.
- Base URL + auth (Bearer / X-API-Key) đọc từ config/env, không hardcode (yêu cầu trong API doc trang 2).
- Lỗi trả theo format `{ "error": { "code", "message", "details" }, "requestId" }`.

### 0.1 Đối chiếu API doc — 2 tầng thật vs tự build, và phạm vi cố tình bỏ qua

So với `docs/hackathon/tasco_maps_hackathon_api_documentation.md` (bản text của PDF gốc):

- **2 tầng khác nhau, đừng nhầm lẫn:** `tasco-maps.dnpwater.vn/geocode` + `/route` là backend **thật**
  (Pelias + Valhalla) — chỉ Module 5 gọi trực tiếp vì cần dữ liệu địa lý ngoài 30 quán benchmark. Còn
  `GET /v1/search`, `GET /v1/poi/{id}`, `GET /v1/autocomplete` là **contract shape team tự implement**
  trên chính 30 POI + Menu CSV — không có backend Tasco nào sẵn "biết" `RES001` hay
  `recommended_segments`. Mock server BTC (`docs/hackathon/mock_api_server.js`) là bản tham chiếu của
  tầng contract này, không phải nguồn dữ liệu thật.

- **`GET /v1/poi/{id}` là 1 endpoint DÙNG CHUNG cho Module 2/3/4, không phải 3 endpoint riêng.** Khi gọi
  `include=menu,reviews,ai_summary` (đường gọi thật của benchmark Comparison Q8 — chạm cả 4 module trên
  2 quán), response phải gộp đủ cả 3 phần mở rộng cùng lúc:

  ```json
  {
    "poi": {
      "id": "poi:res011", "type": "poi", "name": "Sushi Sakura",
      "address": "35 Lê Lợi, Lộc Thọ, Nha Trang", "category": "restaurant",
      "coordinates": { "lat": 12.215726, "lon": 109.173122 },
      "openingHours": "10:00-02:00",
      "score": 0.74,
      "source": "dataset",
      "menu": { "ocrId": "OCR011", "items": ["...xem spec 02 mục 3"] },
      "reviewInsights": { "reviewCount": 5, "strengths": ["...xem spec 03 mục 3"] },
      "aiSummary": "...",
      "qualityScore": { "overall": 0.74, "...": "xem spec 04 mục 3" }
    }
  }
  ```

- **`openingHours` luôn có mặt trong response, KHÔNG gate theo `include=hours`** — vì logic lọc
  `open_at` ở mục 4 cần field này ngay từ bước lọc POI cơ bản, trước khi biết `include` của bất kỳ
  query nào. Đây là diễn giải khác literal text API doc (doc liệt kê `hours` như 1 lựa chọn optional
  trong `include`) — quyết định có chủ đích, ghi lại để không ai "sửa cho đúng doc" rồi làm hỏng filter.

- **`include=menu` (spec 02) mở rộng enum gốc của doc.** API doc gốc chỉ liệt kê
  `reviews,photos,hours,ai_summary` cho tham số `include` — `menu` không nằm trong đó. Team thêm giá
  trị này theo đúng tinh thần "field mở rộng được phép ở tầng response" mà doc đã cho phép (tiền lệ
  `aiSummary`, `openingHours`), áp dụng tương tự cho tham số `include`.

- **Cố tình KHÔNG implement — có lý do cụ thể, không phải bỏ sót:**
  - `include=photos` — không có Photo Dataset nào trong hackathon; response không có key `photos`
    (không lỗi, không bịa placeholder).
  - `GET /v1/autocomplete` — 0/15 câu benchmark cần gõ-dở tìm kiếm tức thời; cắt để dồn giờ cho 4 module
    core, cùng logic ưu tiên đã thống nhất ở mục 5 `00-team-brief.md`.
  - `bbox` param của `/v1/search` — 30 POI tĩnh, không cần phân trang theo viewport bản đồ.
  - `category` param của `/v1/search` — filter category đã có qua FilterSpec riêng (mục 4 bên dưới),
    không cần lặp lại qua param `category` cấp ngoài của doc.

## 1. Mục tiêu

Biến câu hỏi tiếng Việt tự nhiên ("Gia đình có trẻ nhỏ muốn ăn tối ở Hà Nội") thành kết quả nhà hàng đã lọc và xếp hạng, dựa trên tầng dữ liệu ngữ nghĩa (dietary, segment, giờ mở cửa, giá món) thay vì text-matching thô — giải quyết trực tiếp "difficult to search by dishes or preferences" trong brief.

## 2. Input schema

**Từ Restaurant POI Dataset.csv** (tên cột thật):

| Cột | Dùng để |
|---|---|
| `restaurant_id`, `restaurant_name` | ID + tên hiển thị |
| `category` | Map sang category DTO (giá trị thật: `Nhà hàng`, `Quán cà phê`, `Ăn nhanh`, `Nhà hàng chay`) |
| `city`, `district`, `address` | Lọc địa lý + address DTO |
| `latitude`, `longitude` | coordinates DTO, tính distanceMeters (haversine) nếu query có lat/lon |
| `cuisine_type` | Lọc ẩm thực (giá trị thật: `Việt Nam`, `Hải sản`, `Chay`, `Halal`, `Ý`, `Nhật`, `Hàn`, `Âu`, `Healthy`) |
| `price_level`, `avg_price_vnd` | Lọc ngân sách mức quán (giá trị thật: `Bình dân`, `Trung bình`, `Cao cấp`) |
| `rating`, `review_count`, `popularity_score` | Ranking |
| `opening_hours` | Lọc giờ (5 giá trị thật: `06:00-14:00`, `07:00-22:00`, `09:00-23:00`, `10:00-02:00`, `11:00-23:30`) |
| `amenities_raw` | Lọc tiện ích ("view đẹp", "phù hợp trẻ em", "phòng riêng"…) — chuỗi phân tách bằng `, ` |
| `recommended_segments` | Lọc segment (`Gia đình`, `Hẹn hò`, `Nhóm bạn`, `Công tác`, `Du lịch`, `Ăn chay`, `Ăn nhanh`, `Tiết kiệm`, `Cao cấp`) |
| `known_strengths` | Boost ranking khi khớp intent (vd Romantic + "view đẹp") |

**Từ Menu Dataset.csv** (join qua `restaurant_id`) — bắt buộc cho câu Budget, Menu Search, Dietary:

| Cột | Dùng để |
|---|---|
| `dish_name` | Tìm theo món ("Tôi muốn ăn Bún chả") |
| `menu_category` | Lọc "món chính" (giá trị thật: `Món chính`, `Khai vị`, `Món phụ`, `Tráng miệng`, `Đồ uống`, `Ăn nhanh`) |
| `price_vnd` | Lọc "món chính dưới 100.000 VNĐ" (số nguyên, vd `80397`) |
| `dietary_tags` | Lọc chay/halal/gluten-free (giá trị thật: rỗng, `chay`, `halal`, `gluten-free` và tổ hợp `chay, halal, gluten-free`) |

**Query input**: `q` (string, bắt buộc), `lat`/`lon` (optional), `limit` (default 10) — đúng tham số `GET /v1/search` trong API doc.

## 3. Output schema

Đúng response shape của `GET /v1/search` trong API doc, mỗi phần tử là PlaceResult DTO chuẩn:

```json
{
  "query": "Gia đình có trẻ nhỏ muốn ăn tối ở Hà Nội",
  "results": [
    {
      "id": "poi:res001",
      "type": "poi",
      "name": "Phở Bếp Nhà",
      "label": "Phở Bếp Nhà",
      "address": "2 Trần Phú, Hoàn Kiếm, Hà Nội",
      "category": "restaurant",
      "coordinates": { "lat": 21.040388, "lon": 105.844615 },
      "distanceMeters": 0,
      "score": 0.84,
      "source": "dataset",
      "tags": ["Việt Nam", "Bình dân", "Gia đình", "Phù hợp trẻ em"]
    }
  ],
  "meta": { "limit": 10, "lang": "vi", "appliedFilters": { "city": "Hà Nội", "segments": ["Gia đình"] }, "relaxed": [] }
}
```

- `category` map: `Nhà hàng`→`restaurant`, `Quán cà phê`→`cafe`, `Ăn nhanh`→`fast_food`, `Nhà hàng chay`→`vegetarian_restaurant`.
- `tags` = `[cuisine_type, price_level] + recommended_segments + amenities khớp filter`. Giữ dấu tiếng Việt.
- `score` = điểm ranking 0–1 (công thức mục 4), không phải rating sao.
- `meta.appliedFilters` + `meta.relaxed` là field mở rộng trong `meta` (API doc cho phép meta tự do), KHÔNG thêm field lạ vào PlaceResult.

## 4. Logic xử lý

Kiến trúc 2 tầng: **LLM chỉ parse intent, engine lọc/xếp hạng là code thuần** (deterministic, test được, không hallucinate).

### Tầng A — Intent Parser (LLM)

Query tiếng Việt → FilterSpec JSON:

```json
{
  "city": "Hà Nội" | null,
  "cuisine_type": "Halal" | null,
  "dish_query": "bún chả" | null,
  "dietary": "chay" | "halal" | "gluten-free" | null,
  "price_level": "Bình dân" | null,
  "max_main_dish_price_vnd": 100000 | null,
  "min_rating": 4.5 | null,
  "open_at": "23:00" | null,
  "segments": ["Gia đình"],
  "amenities": ["Phù hợp trẻ em"],
  "keywords_boost": ["view đẹp", "yên tĩnh"]
}
```

### Tầng B — Filter & Rank Engine (code thuần, pandas hoặc thuần Python)

```
1. Load POI CSV + Menu CSV một lần lúc khởi động (30 + 179 dòng, giữ trong RAM).
2. Chuẩn hoá matching: NFC → lowercase → bỏ dấu (chỉ để so khớp).
3. Lọc tuần tự trên POI:
   - city/district: so khớp bỏ dấu ("TP.HCM", "Sài Gòn" → "TP. Hồ Chí Minh" qua bảng alias cứng ~10 dòng)
   - cuisine_type, price_level: match chính xác sau chuẩn hoá
   - segments: giao khác rỗng với recommended_segments (split ", ")
   - amenities: mọi amenity yêu cầu phải có trong amenities_raw
   - open_at: parse "HH:MM-HH:MM"; nếu end < start → ca qua đêm
     → quán mở tại T nếu (start <= T < end) hoặc (end < start và (T >= start hoặc T < end)).
     QUY ƯỚC BIÊN: "mở cửa sau 23:00" nghĩa là còn phục vụ lúc 23:00 → `11:00-23:30` ĐẠT, `09:00-23:00` KHÔNG (đóng đúng 23:00), `10:00-02:00` ĐẠT.
4. Lọc theo menu (khi có dish_query / dietary / max_main_dish_price_vnd):
   - dish_query: bỏ dấu rồi substring-match với dish_name → giữ quán có ít nhất 1 món khớp
   - dietary: dish có dietary_tags chứa tag → quán đạt nếu có >= 2 món (tránh quán chỉ có "Nước suối" tag chay)
   - max_main_dish_price_vnd: quán đạt nếu có >= 1 món menu_category == "Món chính" với price_vnd <= ngưỡng
5. Ranking (mọi thành phần chuẩn hoá 0–1):
   score = 0.40*(rating/5) + 0.20*(popularity_score/100) + 0.25*match_strength + 0.15*price_fit
   - match_strength: tỉ lệ tiêu chí soft khớp (segments khớp / tổng, keywords_boost xuất hiện trong known_strengths hoặc amenities_raw)
   - price_fit: 1.0 nếu đúng price_level yêu cầu hoặc không yêu cầu; giảm dần theo bậc lệch
6. Kết quả rỗng → relaxation ladder (nới lỏng từng bước, ghi vào meta.relaxed):
   bỏ city → bỏ price → bỏ amenities. KHÔNG BAO GIỜ bịa quán.
   Ví dụ thật từ benchmark: "quán Halal tại TP.HCM" → 0 quán Halal ở TP.HCM trong dataset
   (chỉ có RES008 Hà Nội, RES027 Đà Lạt) → trả 2 quán này kèm meta.relaxed=["city"],
   assistant diễn giải "không có quán Halal tại TP.HCM trong dữ liệu, gần nhất là…".
```

## 5. Prompt LLM (Tầng A)

**System prompt:**

```
Bạn là bộ phân tích truy vấn tìm kiếm nhà hàng cho bản đồ Tasco Maps.
Nhiệm vụ: chuyển câu hỏi tiếng Việt của người dùng thành JSON FilterSpec, KHÔNG trả lời câu hỏi.
Chỉ trả về JSON hợp lệ, không markdown, không giải thích.

Schema (mọi field đều có thể null hoặc mảng rỗng):
{"city": string|null, "cuisine_type": "Việt Nam"|"Hải sản"|"Chay"|"Halal"|"Ý"|"Nhật"|"Hàn"|"Âu"|"Healthy"|null,
 "dish_query": string|null, "dietary": "chay"|"halal"|"gluten-free"|null,
 "price_level": "Bình dân"|"Trung bình"|"Cao cấp"|null, "max_main_dish_price_vnd": number|null,
 "min_rating": number|null, "open_at": "HH:MM"|null,
 "segments": ["Gia đình"|"Hẹn hò"|"Nhóm bạn"|"Công tác"|"Du lịch"|"Ăn chay"|"Ăn nhanh"|"Tiết kiệm"|"Cao cấp"],
 "amenities": string[], "keywords_boost": string[]}

Quy tắc:
- "tiếp khách", "gặp đối tác" → segments ["Công tác"], amenities ["Phòng riêng"], keywords_boost ["yên tĩnh"]
- "hẹn hò", "lãng mạn" → segments ["Hẹn hò"]
- "trẻ nhỏ", "trẻ em", "gia đình" → segments ["Gia đình"], amenities ["Phù hợp trẻ em"]
- "mở khuya", "sau 23h" → open_at "23:00"
- "dưới X VNĐ/đồng" cho món ăn → max_main_dish_price_vnd
- "chay", "thuần chay" → dietary "chay"; "halal" → dietary "halal"
- Tên món cụ thể (Phở, Bún chả, Sushi…) → dish_query
- TP.HCM = "TP. Hồ Chí Minh", Sài Gòn = "TP. Hồ Chí Minh"
- Không suy diễn field người dùng không nhắc đến.
```

**User prompt template:** `Câu hỏi: "{query}"`

**Ví dụ thật (câu số 10 trong Public Evaluation.csv):**

Input: `Câu hỏi: "Gợi ý quán ăn có món chính dưới 100.000 VNĐ và được đánh giá từ 4.5 sao trở lên."`

Expected output:
```json
{"city": null, "cuisine_type": null, "dish_query": null, "dietary": null,
 "price_level": null, "max_main_dish_price_vnd": 100000, "min_rating": 4.5,
 "open_at": null, "segments": [], "amenities": [], "keywords_boost": []}
```

## 6. Cách đo chất lượng

Ground truth **tính được bằng script** từ CSV (không cần gán nhãn tay) cho các câu deterministic:

| Câu eval | Ground truth script |
|---|---|
| Budget (Q10) | POI có `rating >= 4.5` ∩ quán có món `menu_category=="Món chính"` và `price_vnd <= 100000` |
| Late Night (Q11) | POI có `opening_hours` còn mở lúc 23:00 theo quy ước biên mục 4 ∩ segments chứa `Nhóm bạn` |
| Menu Search Bún chả (Q14) | 8 quán có `dish_name=="Bún chả"`: RES001, RES002, RES003, RES006, RES016, RES021, RES026, RES029 (đã xác minh bằng grep) |
| Halal (Q5) | Tập Halal đúng = rỗng tại TP.HCM; hệ thống phải trả relaxed + RES008/RES027, KHÔNG trả quán TP.HCM nào |
| Dietary (Q4) | POI `cuisine_type=="Chay"` hoặc quán có >= 2 món tag `chay` |

Công thức, tính trên tập kết quả trả về R so với ground truth G:

- **Precision = |R ∩ G| / |R|**, **Recall = |R ∩ G| / |G|**, F1. Mục tiêu: F1 = 1.0 cho 5 câu deterministic trên (hoàn toàn khả thi vì engine là code thuần — sai tức là bug).
- Riêng Tầng A (LLM parser): 15 câu eval + ~15 câu tự biến thể → so FilterSpec sinh ra với FilterSpec gán tay, đo **field-level accuracy** = số field đúng / tổng field. Mục tiêu >= 90%.
- Các câu ranking mềm (Family, Romantic, Business): kiểm tra top-3 đều thoả điều kiện cứng (đúng city, đúng segment) — pass/fail từng ràng buộc thay vì đo thứ tự.

## 7. Rủi ro kỹ thuật và fallback

| Rủi ro | Xử lý |
|---|---|
| LLM trả JSON hỏng / thêm markdown | Strip ```json fence → json.loads → nếu fail, retry 1 lần kèm thông báo lỗi parse → nếu vẫn fail, fallback regex-parser rút city/dish/số tiền từ query (chậm hơn về chất lượng nhưng không sập demo) |
| LLM bịa giá trị enum (vd cuisine "Trung Hoa") | Validate whitelist từng field sau parse; giá trị lạ → set null và log |
| Câu Halal-TP.HCM trả rỗng, demo bẽ mặt | Relaxation ladder mục 4 bước 6 — đây là câu benchmark thật, phải test riêng trước |
| Giờ qua đêm `10:00-02:00` lọc sai | Unit test riêng cho open_at ∈ {22:00, 23:00, 23:30, 01:00, 03:00} với cả 5 giá trị opening_hours thật |
| Người dùng gõ không dấu ("bun cha") | Mọi so khớp đều qua bước bỏ dấu; test với biến thể không dấu của 15 câu eval |
| Latency LLM làm demo chậm | Cache FilterSpec theo query đã chuẩn hoá; 15 câu eval chạy trước và cache sẵn |

## 8. Ước tính thời gian build (1 dev + Claude)

| Việc | Giờ |
|---|---|
| Data loader + chuẩn hoá + bảng alias city | 0.5 |
| Filter engine + overnight hours + menu join | 1.5 |
| Ranking + relaxation ladder | 1.0 |
| Intent parser (prompt + validate + retry + fallback) | 1.0 |
| API endpoint /v1/search đúng contract + error format | 0.5 |
| Script ground truth + chạy eval 15 câu + sửa bug | 1.5 |
| **Tổng** | **6.0** |

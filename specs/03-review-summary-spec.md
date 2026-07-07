# Spec 03 — Review Sentiment + Summary

> Trả lời trực tiếp câu eval số 6 (Review Analysis — "Crystal BBQ thường được khen/phàn nàn về điều gì?")
> và cấp strengths/weaknesses cho câu Comparison (số 8) và AI Summary (số 13).
> ⚠️ BẪY ĐÃ XÁC MINH: "Crystal BBQ" KHÔNG tồn tại trong bất kỳ dataset nào
> (grep 0 kết quả trên POI/Reviews/Menu — chỉ xuất hiện trong chính file Public Evaluation).
> Đây là câu test chống hallucination. Trả lời đúng = "không có dữ liệu", kèm error DTO chuẩn.
> Quy ước chung (ID, dấu tiếng Việt, error format, config): xem mục 0 của `01-semantic-search-spec.md`.

## 1. Mục tiêu

Cô đọng các review rời rạc thành nhận định dùng được: điểm mạnh / điểm yếu / phân bố cảm xúc / phù hợp nhóm khách nào — giải quyết trực tiếp "đánh giá người dùng rải rác, không tổng hợp thành điểm mạnh/yếu rõ ràng" trong problem statement.

## 2. Input schema

**Từ Restaurant Reviews.csv** (tên cột thật, 150 dòng = đúng 5 review/quán × 30 quán):

| Cột | Ý nghĩa / giá trị thật |
|---|---|
| `review_id` | REV0001–REV0150 |
| `restaurant_id` | Join key RES001–RES030 |
| `review_text` | Text tiếng Việt, 3 khuôn mẫu: khen ("Tôi thích X và Y…"), trung lập ("…có X, nhưng Y…"), chê ("Trải nghiệm chưa tốt vì X và Y…") |
| `sentiment_label` | `Tích cực` / `Trung lập` / `Tiêu cực` (nhãn sẵn — KHÔNG cần LLM đoán lại) |
| `rating` | 2–5 |
| `customer_type` | `Gia đình` / `Cặp đôi` / `Bạn bè` / `Công tác` / `Một mình` |
| `review_date` | 2026-01 → 2026-06 |
| `mentioned_aspects` | Chuỗi `aspect1, aspect2` — chính là ground truth aspect extraction |

**Ground truth để chấm — từ Restaurant POI Dataset.csv:** `known_strengths` (3 aspect/quán), `known_weaknesses` (2 aspect/quán).

## 3. Output schema

Gắn vào POI detail `GET /v1/poi/{id}?include=reviews,ai_summary` (đúng tham số `include` có sẵn trong API doc):

```json
{
  "poi": {
    "id": "poi:res011",
    "type": "poi",
    "name": "Sushi Sakura",
    "label": "Sushi Sakura",
    "address": "35 Lê Lợi, Lộc Thọ, Nha Trang",
    "category": "restaurant",
    "coordinates": { "lat": 12.215726, "lon": 109.173122 },
    "source": "dataset",
    "reviewInsights": {
      "reviewCount": 5,
      "sentimentBreakdown": { "positive": 1, "neutral": 2, "negative": 2 },
      "avgRating": 3.0,
      "strengths": [
        { "aspect": "khẩu vị ổn định", "mentions": 2 },
        { "aspect": "món ăn ngon", "mentions": 1 }
      ],
      "weaknesses": [
        { "aspect": "chờ món lâu giờ cao điểm", "mentions": 4 },
        { "aspect": "ít món chay", "mentions": 2 }
      ],
      "byCustomerType": { "Cặp đôi": 3, "Công tác": 2, "Một mình": 1 }
    },
    "aiSummary": "Sushi Sakura được khách đánh giá cao về khẩu vị ổn định và thực đơn đa dạng, nhưng thường xuyên bị phàn nàn về thời gian chờ món giờ cao điểm và ít lựa chọn chay."
  }
}
```

Quán không tồn tại (case Crystal BBQ) → **error DTO chuẩn, không bịa**:

```json
{
  "error": {
    "code": "not_found",
    "message": "Không tìm thấy nhà hàng 'Crystal BBQ' trong dữ liệu.",
    "details": { "query": "Crystal BBQ", "suggestion": "Kiểm tra tên hoặc xem danh sách 30 nhà hàng hiện có." }
  },
  "requestId": "<uuid>"
}
```

## 4. Logic xử lý

**Số liệu tính bằng code thuần, LLM chỉ viết văn.** Con số do code đếm thì không bao giờ hallucinate.

```
Bước 1 — Aggregate (code thuần, không LLM):
  reviews = df[df.restaurant_id == rid]           # luôn đúng 5 dòng
  sentimentBreakdown = đếm sentiment_label
  avgRating = mean(rating)
  byCustomerType = đếm customer_type

Bước 2 — Phân cực aspect (code thuần, tận dụng khuôn mẫu văn bản đã xác minh):
  for review in reviews:
      aspects = mentioned_aspects.split(", ")     # luôn 2 aspect
      if sentiment_label == "Tích cực":  cả 2 → strengths
      if sentiment_label == "Tiêu cực":  cả 2 → weaknesses
      if sentiment_label == "Trung lập": aspect trước "nhưng" trong review_text → strengths,
                                          aspect sau "nhưng" → weaknesses
        (fallback nếu không tìm thấy "nhưng": aspect[0] → strengths, aspect[1] → weaknesses —
         khớp khuôn "…có X, nhưng Y…" đã xác minh trên data thật)
  strengths/weaknesses = Counter, sort giảm dần theo mentions

Bước 3 — LLM viết aiSummary (1 call/quán):
  input: JSON kết quả bước 1+2 (KHÔNG đưa raw review — ép LLM chỉ dùng số liệu đã đếm)
  output: 2-3 câu tiếng Việt

Bước 4 — Lookup theo tên (phục vụ câu hỏi tự nhiên):
  chuẩn hoá bỏ dấu + lowercase, match với restaurant_name
  → không khớp quán nào → trả error not_found (mục 3). TUYỆT ĐỐI không "đoán quán gần giống"
    khi độ tương đồng thấp (Crystal BBQ không giống quán nào).
```

## 5. Prompt LLM (Bước 3)

**System prompt:**

```
Bạn là bộ tạo tóm tắt đánh giá nhà hàng cho bản đồ Tasco Maps.
Bạn nhận số liệu đã tổng hợp (KHÔNG phải review gốc). Viết đoạn tóm tắt tiếng Việt 2-3 câu:
- Câu 1: điểm mạnh nổi bật nhất (theo số mentions cao nhất trong strengths).
- Câu 2: điểm yếu bị nhắc nhiều nhất (theo mentions trong weaknesses).
- Câu 3 (tuỳ chọn): phù hợp nhóm khách nào (theo byCustomerType và sentiment).
Quy tắc bắt buộc:
- CHỈ dùng aspect có trong input. Không thêm nhận định mới, không suy diễn.
- Không nêu con số phần trăm tự tính. Được phép nói "4/5 review".
- Giữ nguyên từ ngữ aspect tiếng Việt trong input.
Trả về JSON: {"aiSummary": "..."}
```

**User prompt template:** `Nhà hàng: {restaurant_name}\nSố liệu: {json_bước_1_2}`

**Ví dụ thật (RES011 Sushi Sakura — REV0051–REV0055):**

Input:
```
Nhà hàng: Sushi Sakura
Số liệu: {"sentimentBreakdown":{"positive":1,"neutral":2,"negative":2},"avgRating":3.0,
"strengths":[{"aspect":"khẩu vị ổn định","mentions":2},{"aspect":"món ăn ngon","mentions":1},{"aspect":"thực đơn đa dạng","mentions":1}],
"weaknesses":[{"aspect":"chờ món lâu giờ cao điểm","mentions":4},{"aspect":"ít món chay","mentions":2}],
"byCustomerType":{"Cặp đôi":3,"Công tác":2,"Một mình":1}}
```

Expected output:
```json
{"aiSummary": "Sushi Sakura được khách khen về khẩu vị ổn định và thực đơn đa dạng. Tuy nhiên 4/5 review phàn nàn chờ món lâu giờ cao điểm, và một số khách chê ít món chay. Quán phù hợp đi cặp đôi hoặc công tác hơn là nhóm cần phục vụ nhanh."}
```

(Đối chiếu POI CSV RES011: known_strengths = "khẩu vị ổn định, thực đơn đa dạng, món ăn ngon", known_weaknesses = "chờ món lâu giờ cao điểm, ít món chay" → khớp.)

## 6. Cách đo chất lượng

Ground truth: cột `known_strengths` / `known_weaknesses` trong Restaurant POI Dataset.csv, split `", "` thành set. Chạy trên đủ 30 quán.

| Metric | Công thức | Mục tiêu |
|---|---|---|
| Strengths precision/recall | so set aspect output (mọi aspect có mentions >= 1) với set `known_strengths` — P = đúng/trả ra, R = đúng/ground truth | R >= 90% (reviews chỉ 5 dòng, có thể không phủ hết 3 strengths — báo cáo kèm coverage) |
| Weaknesses precision/recall | tương tự với `known_weaknesses` | P >= 90%, R >= 90% |
| Sentiment breakdown | exact match với đếm `sentiment_label` | 100% (code thuần, sai là bug) |
| aiSummary faithfulness | check tự động: mọi aspect xuất hiện trong aiSummary phải ∈ strengths ∪ weaknesses input (string match bỏ dấu) | 100% — vi phạm = hallucination, phải sửa prompt |
| Not-found handling | test "Crystal BBQ" + 2 tên bịa khác → phải trả error code `not_found` | 3/3 |

## 7. Rủi ro kỹ thuật và fallback

| Rủi ro | Xử lý |
|---|---|
| Hallucination khi hỏi quán không tồn tại (câu benchmark thật) | Lookup là code thuần trước khi chạm LLM; không match → error DTO, LLM không bao giờ được gọi. Test case bắt buộc trước demo |
| LLM thêm nhận định ngoài input vào aiSummary | Faithfulness check tự động (mục 6); fail → retry với reminder; fail lần 2 → dùng summary template cứng ghép từ aspect ("Khách khen X, Y; thường phàn nàn về Z") — không đẹp bằng nhưng đúng 100% |
| Review Trung lập không chứa "nhưng" (khuôn mẫu khác) | Fallback aspect[0]/aspect[1] đã ghi ở Bước 2; script eval sẽ lộ ngay nếu quy tắc sai vì so được với known_* |
| known_strengths có 3 aspect nhưng 5 review không nhắc đủ | Đo coverage thực tế bằng script trước, đặt mục tiêu recall theo mức phủ thật của data thay vì ép 100% |
| LLM trả JSON hỏng | json.loads + retry 1 lần + fallback template cứng |

## 8. Ước tính thời gian build (1 dev + Claude)

| Việc | Giờ |
|---|---|
| Aggregator + phân cực aspect (code thuần) + unit test | 1.0 |
| Name lookup + not_found path + test 3 tên bịa | 0.5 |
| Prompt aiSummary + faithfulness check + fallback template | 1.0 |
| Endpoint include=reviews,ai_summary + tích hợp POI detail | 0.5 |
| Script eval 30 quán so known_strengths/weaknesses + tune | 1.0 |
| **Tổng** | **4.0** |

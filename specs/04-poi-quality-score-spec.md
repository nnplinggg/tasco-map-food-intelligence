# Spec 04 — POI Quality Scoring & Enrichment Gap

> Trả lời trực tiếp câu eval số 9 (POI Quality — "Nhà hàng nào có POI Quality Score thấp nhất
> và cần bổ sung những thông tin gì?").
> Module rẻ nhất, KHÔNG dùng LLM cho phần tính điểm — được phép cắt trước nếu bí giờ (theo quyết định mục 5 của context).
> Quy ước chung (ID, dấu tiếng Việt, error format, config): xem mục 0 của `01-semantic-search-spec.md`.

## 1. Mục tiêu

Đo được độ đầy đủ / độ tin cậy của thông tin từng nhà hàng và chỉ ra chính xác cần bổ sung gì — giải quyết "không có cơ chế đo độ đầy đủ/tin cậy của thông tin một địa điểm" trong problem statement, và là nền cho pitch "continuously enriched POIs" của brief.

## 2. Input schema

**Phát hiện quan trọng từ data thật (đã xác minh): cả 21 cột của Restaurant POI Dataset đều được điền đủ cho cả 30 quán.** Nếu chỉ đo completeness trên 1 file này thì 30 quán đều đạt điểm tối đa — vô nghĩa. Vì vậy điểm chất lượng PHẢI đo **cross-dataset**:

| Nguồn | Cột dùng | Tín hiệu chất lượng |
|---|---|---|
| Restaurant POI Dataset.csv | tất cả cột metadata (`opening_hours`, `amenities_raw`, `description_raw`, `recommended_segments`, `known_strengths`, `known_weaknesses`) | Completeness cơ bản: field rỗng/không rỗng + độ giàu (số amenity, số segment) |
| Restaurant POI Dataset.csv | `review_count`, `rating`, `popularity_score` | Độ tin cậy thống kê (126 → 1178 review) |
| Menu Dataset.csv | đếm dòng theo `restaurant_id`; đếm món có `dietary_tags`, `description` | Quán có menu số hoá chưa, menu giàu thông tin không (5–7 món/quán) |
| OCR Menu Dataset.csv | tồn tại `restaurant_id` hay không | **Chỉ RES001–RES018 có OCR; RES019–RES030 thiếu** → đây chính là "enrichment gap" thật để demo |
| Restaurant Reviews.csv | đếm review theo `restaurant_id` (đều 5/quán) | Có dữ liệu review để phân tích chưa |
| Restaurant POI Dataset.csv | `poi_quality_score` (0.86–0.99) | **Ground truth tham chiếu** để kiểm chứng công thức — KHÔNG dùng làm input tính điểm |

## 3. Output schema

Gắn vào POI detail, đồng thời `score` trong PlaceResult của mọi kết quả search có thể lấy từ đây:

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
    "score": 0.74,
    "source": "dataset",
    "qualityScore": {
      "overall": 0.74,
      "referenceScore": 0.86,
      "breakdown": {
        "basicInfo": 1.0,
        "richness": 0.75,
        "menuCoverage": 0.85,
        "reviewTrust": 0.35,
        "ocrDigitized": 1.0
      },
      "missingFields": [],
      "enrichmentSuggestions": [
        "Số review thấp (193) — kích hoạt thu thập đánh giá từ người dùng VETC",
        "Chưa có ảnh món ăn — bổ sung từ Food Image Dataset"
      ]
    }
  }
}
```

- `overall` = điểm của công thức mình (0–1, làm tròn 2 chữ số). `referenceScore` = `poi_quality_score` gốc để đối chiếu minh bạch.
- `missingFields` = danh sách tên cột/nguồn còn thiếu (vd RES019–RES030: `["ocr_menu"]`).
- `enrichmentSuggestions` = câu tiếng Việt sinh từ rule (template), mỗi câu gắn với 1 tín hiệu đo được — trả lời trực tiếp vế "cần bổ sung những thông tin gì" của câu eval.

## 4. Logic xử lý

100% code thuần, deterministic, chạy 1 lần lúc khởi động cho cả 30 quán:

```
Trọng số (tổng = 1.0):
  basicInfo    0.25  — tỉ lệ field bắt buộc không rỗng:
                       name, address, latitude, longitude, opening_hours,
                       cuisine_type, price_level  (7 field, mỗi field 1/7)
  richness     0.20  — min(1, số amenity / 6) * 0.5 + min(1, số segment / 4) * 0.3
                       + (description_raw >= 100 ký tự ? 0.2 : 0.1)
  menuCoverage 0.20  — quán có menu? (0.5) + min(1, số món / 6) * 0.3
                       + (tỉ lệ món có dietary_tags hoặc ingredients) * 0.2
  reviewTrust  0.20  — min(1, review_count / 800) * 0.7 + (có >= 5 review text ? 0.3 : 0)
  ocrDigitized 0.15  — restaurant_id có trong OCR Menu Dataset ? 1 : 0

overall = Σ trọng_số * điểm_thành_phần

enrichmentSuggestions (rule table, không LLM):
  ocrDigitized == 0        → "Chưa có menu số hoá từ OCR — cần chụp/scan thực đơn"
  review_count < 400       → "Số review thấp (<n>) — kích hoạt thu thập đánh giá"
  số amenity < 5           → "Thông tin tiện ích còn mỏng — xác minh tại chỗ"
  tỉ lệ món có dietary < 0.5 → "Menu thiếu tag dinh dưỡng — chạy enrichment từ ingredients"
  (mỗi rule 1 dòng template, chèn số liệu thật)

Trả lời câu eval số 9 ("quán nào score thấp nhất"): trả lời theo CẢ HAI thang minh bạch:
  - Theo poi_quality_score gốc: min = 0.86 (RES004 Nhà Hàng Biển Xanh và RES011 Sushi Sakura — đồng hạng, đã xác minh)
  - Theo công thức enrichment của mình: quán RES019–RES030 nào thiếu OCR + review_count thấp sẽ tụt xuống
  → câu trả lời demo nêu quán thấp nhất theo thang gốc + danh sách enrichmentSuggestions của quán đó.
```

## 5. Prompt LLM

**Không dùng LLM cho tính điểm** — điểm số phải tái lập được và giải thích được từng thành phần (đây chính là điểm bán hàng "trustworthy" khi pitch).

Tuỳ chọn (nếu dư giờ): 1 call LLM viết lại `enrichmentSuggestions` thành đoạn văn mượt cho demo; template rule vẫn là fallback mặc định. Không ưu tiên.

## 6. Cách đo chất lượng

Ground truth tham chiếu: cột `poi_quality_score` (0.86–0.99, band hẹp, khả năng cao là synthetic — vì vậy KHÔNG kỳ vọng khớp tuyệt đối, mà đo tương quan thứ hạng):

| Metric | Công thức | Mục tiêu |
|---|---|---|
| Spearman rank correlation | giữa `overall` của mình và `poi_quality_score` trên 30 quán | >= 0.5 — nếu < 0.5, xem xét lại trọng số 1 lần; nếu vẫn thấp thì chấp nhận và trình bày như "thang đo enrichment khác mục tiêu với thang gốc" (thang mình đo cross-dataset gap, thang gốc chưa rõ phương pháp) |
| MAE | mean(|overall − poi_quality_score|) | báo cáo, không đặt ngưỡng cứng (lý do trên) |
| Determinism | chạy 2 lần → output byte-identical | bắt buộc |
| Eval Q9 dry-run | câu trả lời nêu đúng min theo thang gốc (0.86: RES004, RES011) + suggestions của các quán đó không rỗng | pass/fail |

## 7. Rủi ro kỹ thuật và fallback

| Rủi ro | Xử lý |
|---|---|
| POI CSV được điền đủ 100% → completeness thuần vô nghĩa | Đã xử lý bằng thiết kế cross-dataset (mục 2). Đây là lý do tồn tại của bảng trọng số |
| Công thức mình lệch xa poi_quality_score gốc, giám khảo hỏi | `referenceScore` luôn hiển thị cạnh `overall` + breakdown giải thích được từng phần — chủ động trình bày là 2 thang đo khác nhau, thang mình minh bạch công thức |
| Ban tổ chức kỳ vọng trả lời Q9 theo score gốc chứ không theo score mình | Trả lời theo cả hai (mục 4). Không rủi ro |
| Trọng số tuỳ ý bị bắt bẻ | Ghi rõ trong spec/README: trọng số là hyperparameter, có 1 file config; demo được việc đổi trọng số → điểm đổi theo, minh chứng "đo được, tinh chỉnh được" |
| Đồng hạng min (RES004 = RES011 = 0.86) làm câu trả lời mơ hồ | Nêu cả hai quán, phân biệt bằng breakdown (RES011 review_count 193 thấp hơn hẳn RES004 984) |

## 8. Ước tính thời gian build (1 dev + Claude)

| Việc | Giờ |
|---|---|
| Loader cross-dataset + bảng đếm menu/OCR/review theo quán | 0.5 |
| Công thức điểm + breakdown + rule suggestions | 1.0 |
| Gắn vào POI detail + score cho PlaceResult | 0.5 |
| Script Spearman/MAE + dry-run câu eval Q9 | 0.5 |
| **Tổng** | **2.5** |

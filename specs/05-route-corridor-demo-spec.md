# Spec 05 — Gợi Ý Điểm Dừng Dọc Hành Trình (VETC Route Corridor Demo)

> **Trạng thái: stretch feature, KHÔNG nằm trong 15 câu Public Evaluation.**
> Không có owner cố định — giao cho dev nào xong Module 1 sớm nhất (module này 100% dùng lại engine
> Module 1, không xây engine mới). Nếu bí giờ, đây là thứ **cắt đầu tiên**, trước cả Module 4.
> Xem quyết định cập nhật ở `00-team-brief.md` mục 3 và `CLAUDE.md` mục 4.

## 0. Vì sao module này tồn tại (bối cảnh quyết định)

Quyết định gốc là cắt hẳn route layer vì: (a) 0/15 câu benchmark liên quan route, (b) 30 quán rải
7 tỉnh không đủ mật độ dọc 1 tuyến để demo có ý nghĩa, (c) mock đầy đủ trạm sạc/thu phí + route engine
tốn 4-6h. Team xét lại và quyết định: benchmark không chấm route, nhưng phần thi có tiêu chí
"business value", "production-readiness" — và VETC (Vietnam Electronic Toll Collection) **chính là
công ty thu phí không dừng**, nên câu chuyện "biết xe vừa qua trạm thu phí → gợi ý luôn chỗ ăn gần đó"
là differentiation thật, không phải trang trí.

Cách giải quyết nút thắt (a)-(c) mà không tốn 4-6h: **không build route engine, không mock toll/sạc
đầy đủ** — chỉ mock **1 hành lang (corridor) duy nhất** với vài điểm dừng chân dọc đường, và dùng lại
100% engine lọc/xếp hạng đã có ở Module 1. Chi phí ước tính: 3.5-4h, không đụng vào route thật.

## 1. Mục tiêu

Minh hoạ (không phải sản xuất) năng lực "biết ngữ cảnh hành trình đang di chuyển qua VETC → gợi ý điểm
dừng chân phù hợp" — trả lời trực tiếp "Demonstrate a realistic path toward production deployment"
trong brief, mà không cần route engine thật hay dữ liệu route engine-grade.

## 2. Input schema

**Dữ liệu mock mới (đã tạo, không đụng vào 5 CSV gốc):**

| File | Nội dung |
|---|---|
| `mock/route_corridor_definition.json` | 1 corridor `hanoi-halong`: origin (toạ độ RES001 thật), destination (toạ độ RES005 thật), polyline 4 điểm (gồm 2 waypoint mock ước lượng), progressKm mỗi điểm |
| `mock/route_corridor_toll_stations.csv` | 2 trạm thu phí mock: `TOLL_M01` (gần Hải Dương, km 60), `TOLL_M02` (gần Uông Bí, km 115) |
| `mock/route_corridor_restaurants.csv` | 5 quán mock dọc hành lang, **CÙNG SCHEMA 21 CỘT** với Restaurant POI Dataset để tái dùng thẳng code Module 1 (parking, mở khuya, gia đình — đúng nhu cầu người đi đường dài) |

**Input runtime (giả lập ngữ cảnh chuyến đi — mock, không phải GPS thật):**

```json
{ "corridorId": "hanoi-halong", "currentProgressKm": 55, "tripContext": { "segments": ["Gia đình"], "amenities": ["Bãi đỗ xe"] } }
```

## 3. Output schema

Endpoint riêng, **KHÔNG đụng vào `/v1/search` hay `/v1/nearby-search` chính** (lý do cách ly ở mục 4):

```
GET /v1/route/rest-stops?corridorId=hanoi-halong&currentProgressKm=55
```

```json
{
  "corridor": { "id": "hanoi-halong", "label": "Hà Nội → Hạ Long", "totalKm": 155 },
  "currentProgressKm": 55,
  "results": [
    {
      "id": "poi:mockres01",
      "type": "poi",
      "name": "Quán Cơm Gia Đình Hải Dương",
      "label": "Quán Cơm Gia Đình Hải Dương",
      "address": "Quốc lộ 5, TP. Hải Dương",
      "category": "restaurant",
      "coordinates": { "lat": 20.945, "lon": 106.34 },
      "distanceMeters": null,
      "score": 0.81,
      "source": "mock",
      "tags": ["Việt Nam", "Bình dân", "Gia đình", "Bãi đỗ xe"]
    }
  ],
  "meta": {
    "note": "Dữ liệu minh hoạ (mock), không phải POI thật — dùng để trình bày khả năng mở rộng.",
    "nearestTollStation": "TOLL_M01",
    "detourInfo": [
      { "poiId": "poi:mockres01", "detourMeters": 850, "extraMinutesEstimate": 4, "progressKm": 62 }
    ]
  }
}
```

- `source: "mock"` — giá trị này **đã có sẵn trong ví dụ chính thức của API doc** (`"source": "mock"`
  trong PlaceResult mẫu), nên đúng chuẩn hợp đồng, không phải field tự chế.
- `detourInfo` là phần mở rộng trong `meta`, không nằm trong PlaceResult chuẩn — theo đúng quy tắc
  "field mở rộng chỉ thêm ở tầng chi tiết/meta" đã thống nhất.
- `meta.note` **bắt buộc phải có** — xem mục 7 (rủi ro "trình bày mock như thật").

## 4. Logic xử lý

Không dùng LLM. Toàn bộ là hình học đơn giản + tái dùng ranking engine Module 1.

```
Bước 1 — Cách ly dữ liệu (QUAN TRỌNG NHẤT của module này):
  Load 3 file mock ở trên vào 1 namespace RIÊNG, KHÔNG merge vào bảng 30 quán gốc dùng cho
  /v1/search. Endpoint /v1/route/rest-stops là đường load dữ liệu DUY NHẤT được phép đọc mock POIs.
  → Lý do: benchmark đã có ground truth đếm tay trên đúng 30 quán (vd "8 quán có Bún chả"). Nếu 5 quán
    mock lọt vào index chính, mọi phép đếm ground truth của Module 1/3/4 SẼ SAI. Đây là bug nghiêm
    trọng nhất có thể xảy ra nếu làm ẩu — phải có test cách ly (mục 6).

Bước 2 — Hình học corridor (code thuần):
  polyline = 4 điểm từ route_corridor_definition.json
  for mỗi rest-stop candidate (2 toll + 5 quán mock):
      progress_km = nội suy tuyến tính theo điểm gần nhất trên polyline (point-to-segment projection)
      detour_m = khoảng cách vuông góc từ toạ độ quán đến đoạn polyline gần nhất (haversine + hình học
                 điểm-đến-đoạn thẳng, KHÔNG dùng Valhalla, không gọi route engine thật)
      extra_minutes_estimate = detour_m / 1000 / 40kmh * 60 * 2   # ước lượng thô, khứ hồi, tốc độ đường nhánh 40km/h

Bước 3 — Lọc theo currentProgressKm:
  chỉ giữ quán có progress_km trong khoảng [currentProgressKm, currentProgressKm + 40km]
  (chỉ gợi ý điểm PHÍA TRƯỚC, trong tầm 40km — giả lập "sắp tới nơi này")

Bước 4 — Rank: TÁI DÙNG NGUYÊN engine Module 1 (mục 4 của 01-semantic-search-spec.md)
  score = 0.40*(rating/5) + 0.20*(popularity_score/100) + 0.25*match_strength(tripContext) + 0.15*price_fit
  sort theo progress_km tăng dần trước, rồi theo score giảm dần trong cùng khoảng progress
```

## 5. Prompt LLM

**Không dùng LLM.** Toàn module là hình học + rule, lý do giống Module 4: đây là phần "chứng minh
năng lực hạ tầng", cần tái lập được 100%, không cần ngôn ngữ tự nhiên tạo sinh.

(Tuỳ chọn nếu dư giờ: 1 câu LLM diễn giải "bạn đang cách Hải Dương 5km, có 2 điểm dừng phù hợp gia
đình phía trước" — chỉ là lớp trình bày, không ảnh hưởng đến việc chọn quán nào.)

## 6. Cách đo chất lượng

Không có ground truth benchmark (module này không được BTC chấm bằng Public Evaluation). Đo bằng
kiểm thử nội bộ:

| Kiểm tra | Cách làm | Mục tiêu |
|---|---|---|
| **Cách ly dữ liệu** (quan trọng nhất) | Chạy lại toàn bộ eval Module 1/3/4 sau khi thêm module 5 — so kết quả với **trước khi thêm** | Byte-identical — 0 sai lệch, xác nhận 5 quán mock không lọt vào benchmark |
| Hình học điểm-đến-đoạn | Unit test 3 case toạ độ đã biết trước đáp số tay (vuông góc giữa đoạn, ngoài 2 đầu đoạn) | Sai số < 1% so tính tay |
| Thứ tự progress_km | Kiểm tra 5 quán mock trả về đúng thứ tự tăng dần theo khoảng cách tới Hà Nội | Đúng thứ tự tuyệt đối (data tĩnh, biết trước đáp án) |
| Honesty check | `meta.note` xuất hiện trong 100% response của endpoint này | Bắt buộc, test tự động |

## 7. Rủi ro kỹ thuật và fallback

| Rủi ro | Xử lý |
|---|---|
| **5 quán mock lọt vào kết quả `/v1/search` chính, làm sai ground truth benchmark** | Bước 1 mục 4 + test cách ly mục 6. Đây là rủi ro nghiêm trọng nhất — review code trước khi merge phải check dòng load data của `/v1/search` KHÔNG import từ `mock/` |
| Giám khảo hỏi "đây có phải trạm thu phí thật không" | `meta.note` + toạ độ trong JSON đã ghi rõ "ước lượng cho demo, không phải toạ độ trạm thu phí thật" — trả lời trung thực ngay, không giả vờ đây là dữ liệu sản xuất |
| Corridor chỉ có 1 tuyến, demo trông đơn giản/dàn dựng | Đúng vậy — đây LÀ minh hoạ, không phải sản phẩm đầy đủ. Kịch bản demo nói thẳng: "phiên bản đầy đủ sẽ mở rộng ra mọi tuyến cao tốc VETC thật" |
| Hình học điểm-đến-đoạn sai (lỗi toán phổ biến: quên clamp về 2 đầu đoạn) | Unit test 3 case ở mục 6 bắt buộc trước khi tích hợp |
| Tốn giờ vượt ngân sách 3.5-4h vì mắc kẹt ở hình học | Có sẵn công thức đóng gói ở mục 4, không cần tự nghĩ lại; nếu vẫn trễ, cắt bỏ luôn (đây là module ưu tiên thấp nhất, xem mục 6 của `00-team-brief.md`) |

## 8. Ước tính thời gian build (1 dev + Claude)

| Việc | Giờ |
|---|---|
| Mock data đã soạn sẵn (file trong `mock/`, không cần làm lại) | 0 (đã xong) |
| Hình học (point-to-segment, progress_km, detour) + unit test | 1.0 |
| Tích hợp ranking engine Module 1 + endpoint `/v1/route/rest-stops` | 1.0 |
| Test cách ly (chạy lại eval Module 1/3/4, xác nhận không lệch) | 1.0 |
| Demo script + honesty note trong UI | 0.5-1.0 |
| **Tổng** | **3.5-4.0** |

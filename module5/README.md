# Module 5 — VETC Route Corridor Demo (Hà Nội → Hạ Long)

Demo minh hoạ lợi thế hạ tầng của Tasco/VETC: **vì app biết xe vừa qua trạm thu
phí trên hành trình đang chạy, nó gợi ý được điểm dừng ăn uống phù hợp phía
trước — điều Google Maps không làm được vì không biết trước lộ trình của bạn.**

## Chạy demo

```bash
# 1. (một lần, cần mạng) build corridor bundle từ Tasco Maps API thật
node module5/scripts/build_corridor.js

# 2. chạy demo — KHÔNG cần mạng, replay từ cache
node module5/server.js
# → http://localhost:8790          (UI demo)
# → http://localhost:8790/v1/route/rest-stops?corridorId=hanoi-halong&currentProgressKm=55

# 3. tests (hình học, engine, honesty, cách ly dữ liệu)
node module5/test/run_tests.js
```

Không có dependency nào ngoài Node ≥ 18. Cache đã commit sẵn trong
`module5/cache/` nên bước 1 có thể bỏ qua khi demo.

## THẬT vs MÔ PHỎNG — trình bày trung thực

| Thành phần | Nguồn | Trạng thái |
|---|---|---|
| Hình học tuyến đường, quãng đường, thời gian (158.5 km, ~93 phút) | `POST /v1/route` — Valhalla production `tasco-maps.dnpwater.vn/route` | **THẬT** |
| Toạ độ trạm thu phí (Trạm QL10, Trạm Cầu Bạch Đằng, Trạm Đồng Đăng) | `GET /v1/geocoding` + quét `GET /v1/reverse-geocoding` dọc polyline — tên và toạ độ trạm là dữ liệu OSM thật; 3 trạm đều nằm NGAY TRÊN tuyến (lệch 5 m / 9 m / 469 m) | **THẬT** |
| Danh sách quán ăn + toạ độ quanh mỗi trạm | `GET /v1/nearby-search` (Pelias, `categories=food`) | **THẬT** |
| Số liệu detour (+phút / +km) | 2 lệnh `POST /v1/route` — baseline vs có điểm dừng (xem bên dưới) | **THẬT** |
| Tên địa danh khi xe di chuyển | `GET /v1/reverse-geocoding` | **THẬT** |
| Xếp hạng quán | Engine Module 1 (`lib/module1_engine.js`, công thức spec 01 §4) | **THẬT (code thuần, tái lập 100%)** |
| **Sự kiện xe qua trạm** (`gate_name, timestamp, lat, lon, vehicle_class`) | Đồng hồ demo phát khi xe hoạt hình chạm km của trạm | **MÔ PHỎNG** — nhãn "TÍN HIỆU QUA TRẠM: MÔ PHỎNG" luôn hiển thị trên UI |
| Rating/độ phổ biến của quán ven đường | API không cung cấp → engine dùng giá trị trung tính có tài liệu (rating 3.5, popularity 50); tiện ích "Bãi đỗ xe" kiểm tra qua API parking trong 400 m, không có thì suy luận theo loại hình quán và **gắn nhãn ≈ (suy luận)** trên UI | trung thực từng field, xem `provenance` trong bundle |

Không có toạ độ, tuyến đường, hay con số detour nào được bịa hay hardcode.

## Cách tính detour (để trả lời giám khảo "con số này ở đâu ra?")

1. **Baseline**: `POST /v1/route` với `locations = [Hà Nội, Hạ Long]`
   → 158 533 m, 5 589 s.
2. **With-stop**: `POST /v1/route` với `locations = [Hà Nội, quán, Hạ Long]`
   (3 điểm, quán là waypoint giữa).
3. **Detour = with-stop − baseline**, cả mét lẫn giây; UI hiển thị phút + km
   kèm chú thích "tính qua route API (baseline vs with-stop)".

**Waypoint approach đã xác minh trực tiếp**: route API (Valhalla production)
**chấp nhận waypoint giữa và đi qua nó thật** — response trả về 2 legs (một
per cặp điểm), tổng legs = tổng summary. Vì vậy dùng 1 call 3-điểm, KHÔNG cần
fallback cộng 2 route rời (origin→quán + quán→đích). Code fallback không tồn
tại vì không cần — nếu môi trường khác không hỗ trợ waypoint, thêm fallback
trong `TascoApiClient.route()`.

Edge case có thật: đôi khi with-stop **ngắn hơn** baseline vài trăm mét
(Valhalla chọn biến thể tuyến khác qua điểm dừng nằm sát đường). Bundle giữ
số âm nguyên bản (trung thực); UI hiển thị "≈0 km".

## Tái dùng engine Module 1

`lib/module1_engine.js` hiện thực đúng spec 01 §4 Tầng B:
`score = 0.40·(rating/5) + 0.20·(popularity/100) + 0.25·match_strength + 0.15·price_fit`,
chuẩn hoá bỏ dấu NFC→lowercase, match segments/amenities/keywords. Lúc build
Module 5 chưa có code Module 1 trong repo, nên file này là hiện thực chuẩn
spec để **Module 1 import chung** — không fork công thức, không xây ranker mới.

Ngữ cảnh chuyến đi của demo: *"Gia đình có trẻ nhỏ, cần bãi đỗ xe, dừng
nhanh"* → FilterSpec `{segments: ["Gia đình"], amenities: ["Bãi đỗ xe"],
keywords_boost: ["ăn nhanh"]}`.

## Cách ly dữ liệu (bất biến quan trọng nhất — spec 05 §4 bước 1)

- Module 5 sống trọn trong `module5/` + đọc duy nhất `module5/cache/`.
- **Không file nào trong module5 đọc 5 CSV benchmark** (30 quán / menu / OCR /
  review / eval). Test tự động quét toàn bộ source và fail nếu có tham chiếu:
  `node module5/test/run_tests.js` (mục 4).
- Quán trong demo đến từ nearby-search API — không dính gì tới 30 quán RES001–RES030.
- Khi Module 1/3/4 có code: chạy lại eval của chúng trước/sau khi thêm Module 5,
  yêu cầu byte-identical (spec 05 §6). Hiện chỉ chia sẻ đúng 1 file
  `lib/module1_engine.js` thuần hàm, không side effect.

## Độ tin cậy khi demo trên sân khấu

Mọi call API bọc try/catch + **cache-first trên đĩa** (`cache/api/`, key =
hash request). Lần build đầu ghi cache; khi demo, server **không gọi mạng** —
mất mạng không thể làm sập pitch, số liệu vẫn là số thật đã bắt trước đó
(mỗi entry cache có `cachedAt`). Muốn làm mới: `TASCO_CACHE=refresh node
module5/scripts/build_corridor.js`.

Base URL + auth cấu hình qua env (`TASCO_ROUTE_BASE`, `TASCO_GEOCODE_BASE`,
`TASCO_BEARER_TOKEN`, `TASCO_API_KEY`) — không hardcode, đúng yêu cầu API doc.

## Files

```
module5/
├── lib/geometry.js          # decode polyline, haversine, snap-to-segment (unit-tested)
├── lib/tasco_api.js         # adapter 4 endpoint chuẩn API doc, cache-first
├── lib/module1_engine.js    # engine lọc/xếp hạng spec 01 §4 — DÙNG CHUNG với Module 1
├── scripts/build_corridor.js# build bundle từ API thật (route→gates→quán→detour)
├── server.js                # demo server :8790 + endpoint /v1/route/rest-stops (spec 05 §3)
├── ui/index.html            # bản đồ SVG, xe chạy, ledger VETC, thẻ gợi ý, privacy note
├── test/run_tests.js        # 23 checks: hình học, engine, honesty, CÁCH LY DỮ LIỆU
└── cache/                   # corridor_bundle.json + cache API (số thật, replay offline)
```

## Ghi chú riêng tư (hiển thị ngay trong UI)

Bản production: tín hiệu qua trạm chỉ dùng dạng tổng hợp & ẩn danh; ngưỡng cụm
tối thiểu N ≥ 5 xe / ô lưới + khung giờ (dưới ngưỡng loại bỏ); không lưu quỹ
đạo cá nhân; tuân thủ Nghị định 13/2023/NĐ-CP.

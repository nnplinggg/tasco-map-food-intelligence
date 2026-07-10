# CONTEXT — Tasco Maps AI Hackathon (P11 Restaurant & Menu Intelligence)

## 1. Bối cảnh dự án

Hackathon: Tasco Maps AI Hackathon, track Mobility, đề bài P11 "AI-Powered Restaurant & Menu Intelligence".

Ngày hack thật: 10/7/2026, 1 ngày duy nhất.

Team 5 người: 1 strategy/spec, 4 dev.

Nền tảng đích: Tasco Maps (app Flutter tên T Map trên store), tích hợp với hệ sinh thái VETC.

## 2. Problem Statement 

Thông tin nhà hàng tại Việt Nam phân mảnh, không đồng nhất, khó xác thực. Menu tồn tại chủ yếu dưới dạng ảnh/PDF, không có cấu trúc dữ liệu chuẩn để tìm theo món, giá, dinh dưỡng. Đánh giá người dùng rải rác, không tổng hợp thành điểm mạnh/yếu rõ ràng. Không có cơ chế đo độ đầy đủ/tin cậy của thông tin một địa điểm.

Hậu quả: tìm kiếm theo nhu cầu cụ thể (gia đình, ăn chay, ngân sách, giờ khuya) chậm, không chính xác, vì thiếu tầng dữ liệu ngữ nghĩa, chỉ có text-matching thô.

Vì sao là vấn đề của Tasco: Tasco Maps đã có route engine (Valhalla) và geocoding thật, phục vụ người dùng có vị trí/lộ trình thời gian thực qua VETC. Năng lực này chưa nối với dữ liệu ẩm thực. Đây là năng lực Foody hay Google Maps không có ở quy mô tích hợp hạ tầng giao thông thật.

## 3. Ground truth data đã xác nhận

| Dataset | Số dòng/đặc điểm đã xác nhận |
|---|---|
| Restaurant POI Dataset | 30 nhà hàng, rải 7 thành phố (Hà Nội, HCM, Đà Nẵng, Nha Trang, Hạ Long, Đà Lạt, Huế), có sẵn poi_quality_score (0.86-0.99), known_strengths, known_weaknesses, amenities_raw, recommended_segments |
| Menu Dataset | 179 món, phủ đủ 30 quán (5-7 món/quán), có menu_item_id, dish_name, price_vnd, dietary_tags, ingredients — ground truth để so output OCR |
| OCR Menu Dataset | raw_ocr_text dạng thô, **chỉ 18 quán RES001–RES018** (RES019–RES030 không có OCR — dùng làm enrichment gap cho Module 4) |
| Restaurant Reviews | 150 review (đúng 5/quán), có sentiment_label sẵn, mentioned_aspects là ground truth aspect |
| Public Evaluation | Đúng 15 câu, 0/15 liên quan route. Toàn bộ là Food Search, Family, Dietary, Halal, Review Analysis, Comparison, POI Quality, Budget, Late Night, Romantic, Business, Menu Search, Menu Extraction, Menu QA, AI Summary |

Kết luận bắt buộc: 15 câu này là benchmark chấm điểm thật. Toàn bộ spec tối ưu để trả lời đúng 15 dạng câu này trước, không lệch trọng tâm.

## 4. Quyết định (cập nhật 7/7): route không được benchmark chấm, nhưng có 1 demo nhẹ mang câu chuyện VETC

- 0/15 câu Eval liên quan route/hành trình lái xe → route KHÔNG ảnh hưởng điểm eval tự động.
- 30 quán rải 7 tỉnh thành, không đủ mật độ dọc 1 tuyến đường để demo detour engine đầy đủ có ý nghĩa;
  mock đủ trạm sạc/thu phí + route engine thật tốn 4-6h — không đáng.
- Nhưng: bỏ hẳn route thì mất luôn câu chuyện differentiation duy nhất gắn với VETC (công ty thu phí
  không dừng thật). Quyết định: xây **Module 5 — Gợi ý điểm dừng dọc hành trình**, một demo nhẹ
  dùng 1 corridor thật (Hà Nội → Hạ Long), tái dùng 100% engine Module 1. Xem
  `specs/05-route-corridor-demo-spec.md` cho lý do quyết định gốc.
- **CẬP NHẬT 10/7 (hack day) — ĐÃ BUILD XONG, khác spec 05 gốc theo hướng tốt hơn:** thay vì mock cả
  trạm thu phí lẫn quán ăn, Module 5 dùng thẳng **API production thật** của Tasco (Valhalla
  `tasco-maps.dnpwater.vn/route`, Pelias `.../geocode`) cho toàn bộ phần địa lý — tuyến đường, toạ độ
  trạm thu phí (geocode tên trạm thật + quét reverse-geocoding dọc tuyến), quán ăn quanh mỗi trạm, và
  số liệu detour (route 2 lần: baseline vs có điểm dừng). **Chỉ 1 thứ còn mô phỏng: sự kiện xe qua
  trạm** (thời điểm xe chạm km của trạm), luôn gắn nhãn "MÔ PHỎNG/SIMULATED" trên UI. Dữ liệu mock cũ ở
  `mock/` không còn được đọc. Chi tiết đầy đủ + cách chạy: `module5/README.md`.
- Module 5 vẫn là **stretch feature, ưu tiên thấp nhất, cắt đầu tiên nếu bí giờ** — không ảnh hưởng 4 module core.

## 5. 4 module build (độc lập dữ liệu, làm SONG SONG không tuần tự)

| Problem (nguyên văn brief) | Module giải quyết | Dataset | Phụ thuộc |
|---|---|---|---|
| "menus are unstructured, image-heavy" | Module 2: OCR-to-JSON Parser | OCR Menu Dataset | Không |
| "restaurant information is often fragmented" | Module 4: POI Quality Scoring | POI + cross-dataset | Không |
| review rời rạc, "descriptions inconsistent" | Module 3: Review Sentiment + Summary | Restaurant Reviews | Không |
| "difficult to search by dishes or preferences" | Module 1: Semantic Search + Filter | POI + Menu | Không |

Phân công: 4 dev bắt đầu cả 4 module CÙNG LÚC giờ đầu ngày 10/7. Nếu thiếu thời gian: module 1 KHÔNG được cắt (chiếm ~9/15 điểm chấm), module 4 cắt trước (rẻ nhất, ít điểm nhất).

## 6. API contract bắt buộc (từ tasco_maps_hackathon_api_documentation.pdf — đã xác minh khớp PDF)

PlaceResult DTO — không tự chế field mới ở tầng này (field mở rộng chỉ được thêm trong response POI detail hoặc `meta`, theo tiền lệ `aiSummary`, `openingHours`, `rating` trong API doc):

```json
{
  "id": "poi:xxx", "type": "poi", "name": "string", "label": "string",
  "address": "string", "category": "string",
  "coordinates": { "lat": 0.0, "lon": 0.0 },
  "distanceMeters": 0, "score": 0.0, "source": "mock", "tags": []
}
```

- Giữ nguyên dấu tiếng Việt trong mọi text. ID ổn định (`poi:res001`). WGS84 lat/lon.
- Base URL + auth (Bearer / X-API-Key) cấu hình được, không hardcode.
- Error: `{ "error": { "code", "message", "details" }, "requestId" }`.
- Mock server BTC: `http://localhost:8787` (chạy `node docs/hackathon/mock_api_server.js`), facade khuyến nghị `https://hackathon.example.com/v1`. Endpoint liên quan: `GET /v1/search`, `GET /v1/poi/{id}?include=reviews,photos,hours,ai_summary`, `GET /v1/nearby-search`.

## 7. Specs

Spec đội (giải thích đau/giá trị/ưu tiên, dùng để 4 dev thống nhất): `specs/00-team-brief.md`.

Spec kỹ thuật: `specs/01-semantic-search`, `02-ocr-parser`, `03-review-summary`, `04-poi-quality-score`
(4 module core, làm song song) và `specs/05-route-corridor-demo-spec.md` (stretch feature, ưu tiên
thấp nhất). Code viết SAU khi team review spec. Quy ước chung nằm ở mục 0 của spec 01.

Dữ liệu mock cho Module 5 nằm ở `mock/` (`route_corridor_definition.json`,
`route_corridor_toll_stations.csv`, `route_corridor_restaurants.csv`) — **tuyệt đối không merge vào
30 quán benchmark**, chỉ được đọc bởi endpoint riêng của Module 5.

## 8. Xác minh dữ liệu quan trọng (đã kiểm tra trực tiếp ngày 7/7/2026)

- **Tên file thật trên đĩa** (có prefix dài): `ai_maps_track6_dataset_participants.xlsm - Restaurant POI Dataset.csv` (tương tự cho Menu / OCR Menu / Public Evaluation / Restaurant Reviews).
- **BẪY 1 — Crystal BBQ**: câu Review Analysis hỏi về "Crystal BBQ" — quán này KHÔNG tồn tại trong bất kỳ dataset nào. Câu test chống hallucination → phải trả `not_found`, không bịa.
- **BẪY 2 — Halal TP.HCM**: câu Halal hỏi quán Halal tại TP.HCM — chỉ có RES008 (Hà Nội) và RES027 (Đà Lạt) là Halal. Không quán Halal nào ở TP.HCM → phải trả lời trung thực + gợi ý nới lỏng, không bịa.
- POI CSV được điền đủ 100% cả 21 cột → điểm chất lượng phải đo cross-dataset (thiếu OCR, review ít) mới có ý nghĩa.
- Giờ mở cửa chỉ có 5 giá trị: `06:00-14:00`, `07:00-22:00`, `09:00-23:00`, `10:00-02:00` (qua đêm!), `11:00-23:30`.
- Giá OCR dùng dấu chấm ngăn nghìn (`80.397 VND` = 80397), khớp tuyệt đối `price_vnd` trong Menu Dataset.
- OCR mất dấu một phần: `Pho bò tái`, `Bun chả`, `Com tấm sườn`.
- Bún chả có tại 8 quán: RES001, RES002, RES003, RES006, RES016, RES021, RES026, RES029.
- poi_quality_score thấp nhất: 0.86, đồng hạng RES004 (Nhà Hàng Biển Xanh) và RES011 (Sushi Sakura).
- Rating >= 4.5: RES002, RES004, RES007, RES014, RES021, RES022, RES028.

## 9. NGUYÊN VĂN BRIEF GỐC (P11, tiếng Anh, đối chiếu khi cần)

```
Mobility Track / Problem statement
P11) AI-Powered Restaurant & Menu Intelligence
Restaurant and menu information is unstructured, image-heavy, incomplete, and difficult to search by dishes or preferences.

Objective
Design and build an AI-powered platform that automatically collects, enriches, structures, and maintains restaurant and menu information to improve food discovery, local search, and dining experiences within the VETC ecosystem.

The goal is not to build another food delivery platform, but to build an AI engine that enriches restaurant information, understands menus, and improves restaurant discovery, food search, recommendations, and dining experiences.

Design principle
The proposed solution should transform unstructured restaurant information into structured, trustworthy, and continuously enriched restaurant POIs and menu knowledge.

Core capabilities
Restaurant POI Enrichment / Menu Extraction / OCR Processing / Dish Recognition / Food Search / AI Restaurant Assistant / AI Summary Generation / Recommendation Engine / POI Quality Scoring.

Expected output
Structured restaurant profile. Structured digital menu. OCR-extracted menu items and prices. Dish recognition results. AI-generated restaurant summary. Review sentiment analysis. Key strengths and weaknesses. Cuisine classification. Recommended dining occasions (Family, Business, Romantic, Casual, Fast Food). POI Quality Score. Personalized restaurant recommendations.

Expected deliverables
Restaurant Intelligence Platform. Menu Intelligence Engine (OCR, menu extraction, structuring). AI Restaurant Assistant. Recommendation Engine. Live demonstration.

Submission requirements
Presentation deck (problem, solution, architecture, business value, impact). Live demo or video. Source code repo. README (setup, technical overview, AI approach). Data enrichment workflow. OCR and extraction methodology. Dish recognition approach. Recommendation methodology. POI quality evaluation approach. Demonstration of: enrichment, menu OCR/extraction, dish recognition from images, AI summary, restaurant comparison, personalized recommendation, AI assistant Q&A.

Success criteria
Automatic enrichment of restaurant POIs. Accurate OCR menu extraction. Reliable dish recognition. AI summaries and review insights. High-quality recommendations per user need. AI assistant answering restaurant/menu questions from enriched knowledge. Scalable, production-ready architecture.
```

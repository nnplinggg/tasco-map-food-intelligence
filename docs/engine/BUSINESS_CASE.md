# BUSINESS CASE — vì sao engine này giúp Tasco Maps thắng

> Cặp với `SYSTEM_FLOW.md` (luồng kỹ thuật). File này trả lời: **ngách nào, vì sao từ góc nhìn
> Tasco (map đang build/test, chưa launch), use case gì, tiền ở đâu** — evidence-based,
> không khẩu hiệu.

---

## 1. GÓC NHÌN TASCO — bài toán thật không phải "làm app đồ ăn"

Tasco Maps đang **pre-launch**. Một map generic ra mắt năm 2026 đối đầu Google Maps sẽ chết vì
không có lý do để mở app. Bài học từ các map đi sau thành công:

- **Amap (Alibaba)**: không đấu review với Meituan/Dianping — launch **Street Stars 9/2025**,
  xếp hạng 1.6M cơ sở bằng *hành vi di chuyển thật* ("Tire-Wear Ranking" — quán người ta lái xe xa
  để đến; "Repeat Customer Ranking"), tuyên bố không thương mại hoá bảng xếp hạng để giữ lòng tin.
  **40 triệu user vào test.** Map thắng food discovery bằng tín hiệu mà nền tảng review không có.
- **Apple Maps**: không xây kho review — mua/tổng hợp từ Yelp/TripAdvisor/Foursquare, và xếp hạng
  local bằng **engagement map-native** (bao nhiêu người bấm chỉ đường tới quán).
- **Trucker Path**: chọn đúng 1 ngách tài xế + 1 field wedge (chỗ đỗ xe còn trống, crowdsource,
  có recency) → ~⅓ tài xế xe tải Bắc Mỹ dùng hàng tháng → mở rộng thành load board, fuel
  discount, fleet B2B, factoring.

**Kết luận cho Tasco:** tài sản không phải data ẩm thực (đi sau Foody 10 năm) mà là
**hạ tầng sinh tín hiệu hành vi**: điều hướng + VETC (giao dịch qua trạm của hàng triệu ô tô).
Đây là đúng loại tín hiệu Amap dùng để đánh Meituan — và ở VN chưa ai dùng.

Check cạnh tranh nội địa: Xanh SM đã có **AI menu OCR cho merchant** và Xanh SM Ngon (5/2025);
Be đầu tư AI toàn stack; ShopeeFood/GrabFood thống trị delivery đô thị. → **Menu OCR là table
stakes, delivery đô thị là biển đỏ.** Lane trống duy nhất: **ăn uống TRÊN HÀNH TRÌNH liên tỉnh**
— nơi cần route engine + trạm thu phí, thứ chỉ Tasco có.

---

## 2. NGÁCH ĐÃ CHỌN

### Primary — B. Gia đình/nhóm đi ô tô liên tỉnh (lễ, tết, cuối tuần, du lịch)

| Tiêu chí | Đánh giá |
|---|---|
| Khớp user thật của Tasco | VETC = chủ ô tô đi liên tỉnh qua trạm — **đúng persona này, khỏi acquire** |
| Khớp moat | Route/detour thật (Valhalla), meal-window push tại trạm, behavior rank — Google/Foody không copy được |
| Khớp dữ liệu + benchmark | 30 quán rải 7 thành phố du lịch; 15 câu eval toàn Family/Dietary/Budget/Late-night/Romantic — **chấm điểm cũng đang chấm đúng segment này** |
| Demo được hôm nay | Module 5 corridor HN→Hạ Long đã chạy trên API production |
| Nỗi đau có thật | Đi xa không biết quán nào **có chỗ đỗ ô tô**, hợp trẻ em, mở đúng giờ mình ngang qua; Google VN không structure các field này |

### Roadmap (năm 2) — A. Tài xế chuyên nghiệp (tải/container/đường dài)

Bằng chứng monetization mạnh nhất trong mọi ngách (Trucker Path: penetration ⅓ thị trường →
4-5 dòng doanh thu). VETC **đã thu phí mọi xe tải trên mọi cao tốc** → kênh phân phối bằng 0 đồng.
Không demo hôm nay vì benchmark không có quán cơm dọc QL — nói thẳng trong deck là phase 2.

### Không chọn
- **C. Phượt/khám phá**: giữ làm *signal layer* (buzz TikTok, đặc sản vùng — mọi segment hưởng),
  không làm segment chính — phượt đi xe máy, không chạm hạ tầng VETC.
- **D. Cơm trưa văn phòng đô thị**: đối đầu trực diện ShopeeFood/GrabFood/Xanh SM Ngon khi không
  có fleet giao hàng — lane tệ nhất. (Cơ chế repeat/explore của Meituan vẫn tái dụng bên trong B.)

**Câu chuyện 1 dòng:** *"Launch bằng wedge gia-đình-đi-ô-tô (data + demo có hôm nay), mở rộng
sang tài xế chuyên nghiệp (kinh tế học Trucker Path), chạy trên một engine duy nhất:
POI intelligence xếp hạng bằng hành vi, hiểu phương ngữ Việt, có provenance từng field."*

---

## 3. USE CASES (đúng 6 scenario đề bài, khoác ngữ cảnh hành trình)

| Scenario đề bài | Use case theo ngách B | Cơ chế trong engine |
|---|---|---|
| Restaurant Discovery | "Đang trên đường HN→Hạ Long, trưa nay ăn gì ngon gần tuyến?" | corridor recall + HARD/CTX/SOFT + behavior rank |
| Food Search | "Quán nào có bún chả, dưới 100k/người, detour <5 phút?" | menu index (Module 2) + S_route |
| Family Dining | "4 người 2 trẻ nhỏ, cần ghế em bé và chỗ đỗ ô tô" | kids>0 → family_facilities thành HARD; parking HARD khi đi ô tô |
| Dietary | "Quán chay/Halal trên tuyến" — không có thì **nói thật + đề xuất nới lỏng** | HARD gate; bẫy Halal-HCM xử lý đúng |
| AI Assistant | "Quán này có món gì đáng thử? Nguồn đâu?" | RAG + trích provenance ("theo chủ quán 10/7", "theo Foody") |
| Enrichment | Quán RES019–030 thiếu ruột → bấm nút, engine tự đi web, score 0.6→0.9 live | T2 gap-detect cascade |

Cộng 2 use case chỉ Tasco làm được: **push gợi ý tại trạm trong khung giờ bữa** (T5, Module 5 đã
build) và **"Bảng xếp hạng Bánh xe"** — top quán người-ta-lái-xe-xa-để-đến theo tuyến/tỉnh
(mô phỏng hôm nay, VETC thật sau launch; đúng playbook Amap, chưa ai làm ở VN).

---

## 4. TÀI CHÍNH — dòng tiền và chi phí, theo phase

Nguyên tắc rút từ Amap: **KHÔNG bán ranking** (pay-to-play giết lòng tin — trust là sản phẩm).
Tiền nằm ở dịch vụ xung quanh ranking.

### Phase 0 — Hackathon → pilot (bây giờ): chi phí gần 0
- Apify credit (~$1.5–4/1k places full-detail) + TinyFish credit + Gemini/Groq/Jina free tier.
- Ước enrichment: **≤ $10–15 / 1k POI** (Apify + LLM structuring) — làm giàu 100k POI food toàn VN
  cỡ **$1–1.5k một vòng**, vòng refresh theo TTL rẻ hơn (chỉ fetch field hết hạn). Con số này
  đủ nhỏ để Tasco chạy như chi phí vận hành map, không cần business case riêng.

### Phase 1 — Launch wedge B (0–12 tháng): mục tiêu là RETENTION, không phải revenue
- Giá trị đo bằng KPI test-phase (bên dưới) + **data flywheel**: mỗi chuyến đi lễ/tết sinh
  dwell/confirm data → POI giàu hơn → app đáng mở hơn. (Grab đo geofence trigger **+3% conversion**
  — citation cho giá trị của push đúng lúc.)
- Doanh thu nhẹ, không phá trust: (a) **merchant verified profile + menu digitization miễn phí →
  bán gói premium** (ảnh, ưu tiên hiển thị *ở mục quảng cáo có nhãn*, số liệu khách ghé);
  (b) **voucher/thanh toán VETC wallet tại quán** — commission trên giao dịch, khép kín vòng
  "gợi ý → ghé → trả tiền" ngay trong hệ sinh thái.

### Phase 2 — Ngách A tài xế chuyên nghiệp (năm 2): copy cấu trúc doanh thu Trucker Path
- Subscription driver pro (điểm dừng, bãi đỗ xe tải, cơm bình dân xác minh) →
  **fuel/food partnership** dọc cao tốc → **fleet B2B** (doanh nghiệp vận tải mua API điểm dừng
  + phúc lợi tài xế). VETC đã có quan hệ thanh toán với 100% xe tải qua trạm — CAC ≈ 0.
- Đây là phần làm slide finance "có đường lớn": Trucker Path chứng minh ngách này gánh được
  load-board/factoring — bản VN là hàng-hoá + trạm dừng nghỉ đang được quy hoạch lại.

### Phase 3 — Engine as a service
- POI Enrichment Engine bán ra ngoài food: xăng/sạc, sửa xe, khách sạn — cùng pipeline, đổi taxonomy.
  (Đúng reframe của ENGINE_PROPOSAL.md: food chỉ là vertical chứng minh.)

### KPI đề xuất cho giai đoạn test của Tasco Maps
| KPI | Ý nghĩa |
|---|---|
| % chuyến liên tỉnh có mở tính năng food | wedge có đúng không |
| % push tại trạm được bấm (theo khung bữa) | giá trị của meal-window gating (benchmark nội bộ: Grab +3%) |
| Số POI được enrich tự động/ngày + Δquality score | engine sống thật không |
| % field có ≥2 nguồn đồng thuận | độ tin của data (bán được cho merchant/B2B sau này) |
| Số confirm 1-tap/1000 chuyến | flywheel driver-data có quay không |

---

## 5. RỦI RO & CÁCH TRẢ LỜI

| Rủi ro | Mitigation |
|---|---|
| Scraping ToS (Google/FB) khi lên production | Hackathon: Apify credit là chấp nhận được để chứng minh cơ chế. Production: chuyển tier 3 sang **Google Places API (New) trả phí** + OSM + dữ liệu tự sinh (tier 1/2 ngày càng gánh nhiều) — cascade thiết kế sẵn cho việc swap nguồn |
| Cold start tier 1/2 (chưa có merchant/driver thật) | Wedge B tự giải: mỗi kỳ lễ là một đợt data; bot xác minh kiểu **Baidu DuIVRS** (gọi điện/Zalo tự động hỏi giờ mở + chỗ đỗ) bootstrap tier 1 không cần quán cài app |
| Tin sai từ social | Kiến trúc đã chặn: 4b không bao giờ sửa fact, chỉ reinforce; consensus ≥3; provenance công khai |
| "Google Maps làm được không?" | Tín hiệu sau trạm thu phí + detour thật + phương ngữ Việt: Google có thể xấp xỉ geofence nhưng **không có giao dịch VETC, không structure amenity ô tô ở VN, không ưu tiên thị trường này** — và Amap đã chứng minh map-behavior ranking đánh được incumbent review |

---

## 6. CẦN GÌ TỪ TASCO (3 câu hỏi quyết định scale)

1. **Telemetry**: sự kiện qua trạm + GPS dwell có mở cho engine không, khung consent thế nào?
   (quyết định tier 2 thật hay mãi mô phỏng)
2. **User base**: bao nhiêu tài khoản VETC active có thể nhận push/1-tap? (quyết định tốc độ flywheel)
3. **Data assets**: POI DB hiện có bao nhiêu record food, nguồn gốc? (quyết định điểm xuất phát coverage)

---

*Nguồn chính: [Amap Street Stars — SCMP](https://www.scmp.com/tech/big-tech/article/3325225/amap-alibabas-answer-google-maps-sees-over-40-million-users-test-new-ranking-service) ·
[iChongqing](https://www.ichongqing.info/2025/09/12/alibabas-amap-launches-worlds-first-ai-driven-consumer-ranking-based-on-user-behavior/) ·
[Trucker Path — Wikipedia](https://en.wikipedia.org/wiki/Trucker_Path) · [Trucker Path for Business](https://truckerpath.com/truckerpath-business) ·
[Meituan repeat/explore RecSys'24](https://dl.acm.org/doi/10.1145/3640457.3688119) ·
[DoorDash KDD'25](https://careersatdoordash.com/blog/doordash-kdd-llm-assisted-personalization-framework/) ·
[Baidu DuIVRS](https://dl.acm.org/doi/10.1145/3511808.3557131) · [Grab engineering](https://engineering.grab.com/) ·
[Apple Maps ranking](https://www.localseoguide.com/apple-maps-ranking-factors-2/) ·
[Xanh SM vs Grab](https://www.ainvest.com/news/high-stakes-ev-ride-hailing-play-southeast-asia-xanh-sm-dethrone-grab-2508/) ·
[VN platforms AI — Vietdata](https://www.vietdata.vn/post/applying-ai-to-ride-hailing-and-delivery-the-race-among-vietnamese-platforms) ·
[Apify Google Places](https://apify.com/compass/crawler-google-places)*

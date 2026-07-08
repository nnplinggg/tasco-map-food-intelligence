# Brief thống nhất đội — Tasco Maps AI Hackathon P11

> Chi tiết kỹ thuật từng module nằm ở `01-04-*.md`. File này chỉ trả lời: đau ở đâu, vì sao giải pháp này đúng, ai làm gì, boundary ở đâu. 

---

## 1. Vấn đề

Brief gốc viết "restaurant information is fragmented, menus are unstructured..." — nghe rất trừu tượng.
Bóc thành 4 tình huống cụ thể, mỗi tình huống ứng với đúng 1 module bên dưới, để cả team thấy được
**pain point thật, đo được bằng data thật**.

### 1.1 "Menu là ngõ cụt dữ liệu" — máy không đọc được thực đơn

Khách mở app, thấy tên quán, nhưng muốn biết "có món dưới 100k không", "có món chay không" —
**không có cách nào tra cứu**, phải gọi điện hỏi hoặc đến tận nơi xem ảnh chụp menu mờ.

- Bằng chứng: dataset có 30 quán nhưng chỉ 18 quán có bản OCR thô (RES001–RES018).
  12 quán còn lại (RES019–RES030) **không có bất kỳ dữ liệu menu số hoá nào**.
- Ngay cả 18 quán "có OCR" thì text cũng chỉ là chuỗi thô lộn xộn (`Pho bò tái .... 80.397 VND`,
  mất dấu, không phân loại) — chưa dùng được cho tìm kiếm hay lọc.
- Hậu quả: món ăn tồn tại nhưng vô hình với mọi tính năng tìm kiếm.

### 1.2 "Review là biển chữ không ai đọc hết"

150 review nằm rải rác 30 quán (5 review/quán). Muốn biết "quán này có ồn không", "phục vụ có
chậm không" — người dùng phải tự bấm vào đọc từng review, tự tổng hợp trong đầu.

- Bằng chứng: mỗi quán có sẵn cột `known_strengths`/`known_weaknesses` — tức là điểm mạnh/yếu
  **có thể tính được** từ review, nhưng hiện tại không ai tính, dữ liệu nằm chết trong text tự do.
- Hậu quả: quyết định chọn quán chậm, hoặc chọn nhầm vì chỉ nhìn số sao trung bình (không nói lên
  quán ồn hay yên tĩnh, nhanh hay chậm).

### 1.3 "Không đo được quán nào đáng tin"

Hai quán cùng 4.2 sao — quán nào thông tin đầy đủ hơn, đáng tin hơn để đề xuất? **Không ai biết**,
vì "độ đầy đủ thông tin" chưa từng được đo bằng con số.

- Bằng chứng: 30/30 quán trong POI Dataset được điền đủ 21 cột — nhìn qua tưởng "hoàn hảo", nhưng
  chỉ 18/30 có OCR menu, số review dao động 126–1178 (chênh 9 lần) — độ tin cậy thực tế rất khác nhau
  dù metadata trông giống nhau.
- Hậu quả: hệ thống đề xuất dựa vào rating thô, không phân biệt được quán "dữ liệu tốt" và quán
  "trông có vẻ đủ nhưng thực ra thiếu OCR/review".

### 1.4 "Tìm theo nhu cầu thật = đoán mò"

Câu hỏi thật của người dùng luôn là tổ hợp: *"gia đình có trẻ nhỏ, ngân sách dưới 100k, mở cửa khuya,
có chỗ đậu xe"*. Google Maps/Foody chỉ text-match tên quán hoặc 1 tiêu chí đơn lẻ, không hiểu tổ hợp
nhiều điều kiện cùng lúc.

- Bằng chứng: câu hỏi benchmark thật (`Public Evaluation.csv`) toàn là dạng tổ hợp này — Budget +
  rating, Late Night + nhóm bạn, Halal + thành phố cụ thể.
- Hậu quả: người dùng tự lọc tay qua hàng chục kết quả sai, hoặc bỏ cuộc.

**Tóm lại theo 1 câu mỗi module — đây là kim chỉ nam khi code:**

| Nỗi đau | Module | Module trả lời được câu hỏi kiểu gì |
|---|---|---|
| 1.1 Menu vô hình | **Module 2 — OCR Parser** | "Quán X có món gì, giá bao nhiêu?" |
| 1.2 Review rải rác | **Module 3 — Review Summary** | "Quán X được khen/chê gì?" |
| 1.3 Không đo được tin cậy | **Module 4 — POI Quality Score** | "Quán nào thiếu thông tin, cần bổ sung gì?" |
| 1.4 Tìm theo nhu cầu = đoán mò | **Module 1 — Semantic Search** | "Tìm quán X phù hợp Y, Z, giá W" |

### 1.5 User stories & use case cụ thể (dùng thẳng cho pitch deck)

Mỗi story dùng **nhân vật + dữ liệu thật trong dataset** (tên quán, thành phố, amenities thật)

---

**US-1 — Gia đình đi du lịch, cần quyết định nhanh** *(Module 1)*

> Là một người mẹ đang lái xe cùng chồng và 2 con nhỏ vừa tới Nha Trang sau 6 tiếng di chuyển, tôi
> muốn tìm ngay 1 nhà hàng có ghế trẻ em, bãi đỗ xe, mở cửa buổi tối, để cả nhà ăn tối mà không phải
> tấp vào từng quán hỏi thăm.

- **Trước:** gõ "nhà hàng Nha Trang" trên Google Maps → hàng chục kết quả, phải bấm vào từng quán xem
  mục "tiện ích" (nếu có) để đoán có ghế trẻ em hay không — mất 10-15 phút trong lúc cả nhà đang đói và
  mệt.
- **Sau:** gõ "gia đình có trẻ nhỏ muốn ăn tối ở Nha Trang" → hệ thống trả về ngay **Nhà Hàng Gia Đình
  Việt** (RES018, Lộc Thọ) — đúng tên, đúng thực tế: có `Phù hợp trẻ em`, `Bãi đỗ xe`, `Mở cửa khuya`,
  thuộc segment `Gia đình` — khớp 100% với câu hỏi benchmark thật số 3 (Family Dining).
- **Vì sao thuyết phục:** không phải hệ thống "đoán" ra quán phù hợp — mọi tiêu chí đều đối chiếu được
  trực tiếp với `amenities_raw` và `recommended_segments` thật trong dataset, tái lập được, không hallucination.

---

**US-2 — Chủ quán nhỏ, chỉ có 1 tờ menu photo mờ** *(Module 2)*

> Là chủ quán Gà Nướng Lá Chanh ở Đà Lạt, tôi chỉ có 1 tờ menu giấy đã ố màu, không có ngân sách thuê
> người nhập liệu, tôi muốn chụp 1 tấm ảnh và có ngay menu số hoá để khách tìm theo món, theo giá.

- **Trước:** menu tồn tại dạng chữ in mờ `Bun chả .... 107.640 VND`, mất dấu, không phân loại — khách
  hàng trên app không tìm được món này bằng từ khoá "bún chả" vì máy không "đọc" được đây là món gì.
- **Sau:** hệ thống trả về JSON sạch: `{"dishName": "Bún chả", "priceVnd": 107640, "menuCategory":
  "Món chính"}` — đúng dấu, đúng giá (đối chiếu tuyệt đối với `MENU0035` trong Menu Dataset), sẵn sàng
  hiển thị và tìm kiếm ngay lập tức, không cần ai gõ tay lại.
- **Vì sao thuyết phục:** đây đúng là quy trình thật một quán nhỏ tại Việt Nam sẽ trải qua — không có
  đội ngũ IT, chỉ có 1 chiếc điện thoại và 1 tờ menu cũ.

---

**US-3 — Cặp đôi hẹn hò, sợ chọn nhầm quán ồn ào** *(Module 3)*

> Là một người đang lên kế hoạch hẹn hò tại Phở Bếp Nhà (Hoàn Kiếm, Hà Nội), tôi muốn biết trước quán
> có ồn không, có phải chờ lâu không, mà không phải đọc hết 5-10 review dài dòng.

- **Trước:** phải tự bấm vào tab đánh giá, đọc từng dòng, tự ghép lại trong đầu "review 2 nói ồn buổi
  tối, review 5 nói chờ lâu giờ cao điểm..." — mất thời gian và dễ bỏ sót.
- **Sau:** hệ thống trả 1 câu: *"Phở Bếp Nhà được khách khen vị trí thuận tiện và phù hợp gia đình,
  nhưng thường bị nhắc đến việc ồn vào buổi tối và chờ món lâu giờ cao điểm."* — đối chiếu đúng
  `known_strengths`/`known_weaknesses` thật của RES001, tính từ chính 5 review thật.
- **Vì sao thuyết phục:** con số đứng sau câu văn (bao nhiêu review nhắc đến từng điểm) đều đếm được,
  kiểm tra lại được — không phải LLM "cảm nhận" hộ khách.

---

**US-4 — Đội vận hành nội dung Tasco, không biết nên đi thu thập dữ liệu quán nào trước** *(Module 4)*

> Là nhân viên vận hành nội dung của Tasco Maps, tôi có 30 quán cần làm giàu dữ liệu nhưng chỉ đủ nguồn
> lực đi khảo sát 5 quán trong tuần này — tôi muốn biết chính xác quán nào đang thiếu thông tin nhất.

- **Trước:** nhìn bảng 30 quán, cột nào cũng có giá trị, rating cũng đều 3.8-4.9 — trông như quán nào
  cũng "đủ dữ liệu", không có cách nào xếp ưu tiên.
- **Sau:** hệ thống chỉ thẳng: 12 quán (RES019–RES030) chưa có menu số hoá (OCR) trong khi 18 quán còn
  lại đã có, và trong nhóm đó RES011 Sushi Sakura có `review_count` chỉ 193 (thấp nhất, so với RES009
  Lẩu Nấm An Nhiên 1152) dù rating tương đương — ưu tiên rõ ràng, không phải cảm tính.
- **Vì sao thuyết phục:** đây là bài toán vận hành thật của bất kỳ nền tảng dữ liệu địa điểm nào —
  không phải tính năng "cho vui", mà là công cụ ra quyết định hàng ngày.

---

**US-5 — Tài xế đang lái xe trên cao tốc, vừa qua trạm thu phí VETC** *(Module 5 — differentiator)*

> Là một tài xế đang chở gia đình từ Hà Nội đi Hạ Long, xe vừa đi qua trạm thu phí không dừng gần Hải
> Dương, tôi đói và muốn dừng ăn tối mà không phải cầm điện thoại tra cứu trong lúc lái xe.

- **Trước:** phải tấp vào lề, mở Google Maps, gõ "nhà hàng gần đây", nhận về danh sách chung chung —
  không biết có bãi đỗ xe cho ô tô không, có phù hợp trẻ em không — mất tập trung và mất thời gian giữa
  chuyến đi.
- **Sau:** ngay tại thời điểm xe qua trạm thu phí VETC, hệ thống tự gợi ý **Quán Cơm Gia Đình Hải
  Dương** — có bãi đỗ xe, phù hợp trẻ em, cách đúng 850m khỏi lộ trình — mà không cần tự gõ tìm kiếm.
- **Vì sao thuyết phục:** đây là khoảnh khắc **chỉ Tasco/VETC có được** — Google Maps và Foody không
  biết chính xác lúc nào xe bạn vừa trả phí qua trạm. (Lưu ý: dữ liệu trạm + quán ở đây là **mock minh
  hoạ**, xem `05-route-corridor-demo-spec.md` mục 7 — kịch bản demo phải nói rõ điều này.)

---

**Use case tổng hợp — nếu ghép cả 4 module thành 1 câu hỏi thật (benchmark #8, Comparison):**

> *"So sánh Sushi Sakura và Little Korea BBQ cho nhóm bạn."*

Một câu hỏi này chạm cả 4 module cùng lúc: Module 1 (lọc 2 quán theo segment "Nhóm bạn"), Module 2
(so giá menu 2 bên), Module 3 (Sushi Sakura bị chê "chờ món lâu giờ cao điểm", Little Korea BBQ có
điểm mạnh riêng), Module 4 (Sushi Sakura có review_count thấp hơn — độ tin cậy thấp hơn). Đây là bằng
chứng rõ nhất cho giám khảo thấy 4 module không phải 4 tính năng rời rạc, mà cùng trả lời 1 câu hỏi
thật theo cách con người thực sự cần khi so sánh 2 lựa chọn.

---

## 2. Vì sao Tasco có lợi thế thật ở đây (không phải chỉ là 1 app tìm quán ăn nữa)

Tasco Maps đã có route engine thật (Valhalla) và geocode thật, phục vụ người dùng có vị trí/lộ trình
qua VETC. Đây là hạ tầng vị trí thời gian thực mà Foody/Google Maps không tích hợp sâu ở quy mô này.
Nhưng — hạ tầng đó **chưa có gì để nói** trong bộ câu hỏi chấm điểm ngày 10/7. Nên:

## 3. USP Tasco: route không được benchmark chấm, nhưng có 1 demo nhẹ mang câu chuyện VETC để giúp solution nổi bật hơn

Bản gốc định cắt hẳn route, chỉ nói trên slide. Xét lại vì: benchmark không chấm route đúng là sự
thật không đổi, nhưng nếu bỏ hẳn thì bài thi trông giống 4 module generic ai cũng build được với data
tương tự — mất đi thứ duy nhất khiến đây là **bài của Tasco/VETC** chứ không phải của bất kỳ ai. VETC
là công ty thu phí không dừng thật; "biết xe vừa qua trạm thu phí → gợi ý điểm dừng chân" là câu
chuyện differentiation thật, không phải trang trí.

| Câu hỏi | Bằng chứng | Kết luận |
|---|---|---|
| Route có được benchmark chấm không? | Đếm tay 15/15 câu — 0 câu liên quan route | Không tăng điểm ở phần eval tự động |
| Có nên build route engine đầy đủ (định tuyến thật, chi phí detour chính xác)? | 30 quán rải 7 tỉnh, không đủ mật độ 1 tuyến; mock đủ trạm sạc/thu phí tốn 4-6h | Không — quá đắt, rủi ro cao so với lợi ích |
| Có cách nào rẻ hơn để vẫn kể được câu chuyện VETC? | Chỉ cần 1 corridor thật (Hà Nội → Hạ Long) + vài điểm dừng mock + tái dùng nguyên engine Module 1, không cần route engine | **Có** — ~3.5-4h, xem `05-route-corridor-demo-spec.md` |

**Quyết định:** build 1 demo nhẹ "Gợi ý điểm dừng dọc hành trình" (Module 5) — mock, tách biệt hoàn
toàn khỏi 30 quán benchmark (xem mục 7), gắn với đúng 1 corridor thật. Đây là **stretch feature, ưu
tiên thấp nhất, cắt đầu tiên nếu bí giờ** — không ảnh hưởng đến 4 module core bên dưới.

**Toàn lực vẫn dồn vào 4 module core dưới đây trước — Module 5 chỉ làm khi 4 module core ổn.**

---

## 4. Bốn module — feature, giá trị, và vì sao thiết kế thế này là đúng

Mỗi module trả lời 3 câu: **giải quyết đau nào (mục 1) — giá trị kinh doanh 1 câu — vì sao cách làm này đúng.**

### Module 1 — Semantic Search & Filter *(không được cắt — ăn điểm nhiều nhất)*

- **Giải quyết:** đau 1.4 — tìm theo tổ hợp nhu cầu thật thay vì text-match tên quán.
- **Giá trị kinh doanh:** biến "tìm nhà hàng" thành "tìm đúng nhà hàng cho đúng tình huống" — đây là
  thứ giữ chân người dùng quay lại app, không phải danh sách quán chung chung.
- **Vì sao đúng:** tách LLM (chỉ hiểu câu hỏi → JSON điều kiện) khỏi engine lọc/xếp hạng (code thuần).
  Lý do: phần lọc/xếp hạng phải **tái lập được 100%** để test và chấm điểm — không thể để LLM tự do
  quyết định quán nào lọt vào kết quả, vì LLM có thể bịa hoặc bỏ sót.
- **Ăn điểm:** ~9/15 câu benchmark (Food Search, Family, Dietary, Halal, Budget, Late Night, Romantic,
  Business, Menu Search).
- **Chi tiết:** `01-semantic-search-spec.md` — 6h build.

### Module 2 — OCR-to-JSON Menu Parser

- **Giải quyết:** đau 1.1 — biến ảnh/text thô thành món ăn có cấu trúc (tên, giá, danh mục, dinh dưỡng).
- **Giá trị kinh doanh:** đây là "nguyên liệu thô" nuôi mọi tính năng khác (search theo món, lọc chay,
  gợi ý theo giá) — không có module này thì Module 1 không có gì để tìm theo món.
- **Vì sao đúng:** regex tách số/tên trước (không bao giờ sai định dạng vì input rất đều), LLM chỉ
  làm phần ngôn ngữ (phục hồi dấu, phân loại món). Tách vậy vì **giá tiền là thứ tuyệt đối không được
  để LLM tự đoán** — sai giá là lỗi nghiêm trọng nhất một hệ thống tìm kiếm có thể mắc.
- **Ăn điểm:** trực tiếp câu Menu Extraction, hỗ trợ Menu QA.
- **Điểm cộng khi demo:** đây là chỗ nên có ảnh menu thật (xem việc mock bên dưới) để câu chuyện
  "ảnh → dữ liệu" thuyết phục, đúng tinh thần "images contain valuable but unused information".
- **Chi tiết:** `02-ocr-parser-spec.md` — 3.5h build.

### Module 3 — Review Sentiment & Summary

- **Giải quyết:** đau 1.2 — cô đọng review rời rạc thành điểm mạnh/yếu dùng được ngay.
- **Giá trị kinh doanh:** thay vì bắt người dùng đọc 5-10 review, hệ thống nói thẳng "quán này ngon
  nhưng hay đợi lâu giờ cao điểm" — tiết kiệm thời gian quyết định, tăng tỷ lệ chốt chọn quán.
- **Vì sao đúng:** con số (bao nhiêu % tích cực, aspect nào bị nhắc mấy lần) tính bằng code thuần
  (nhãn sentiment đã có sẵn trong data). LLM chỉ được giao viết câu văn tóm tắt từ **con số đã tính
  sẵn**, không được đọc review gốc để viết — vì đó là chỗ dễ hallucination nhất.
- **Bẫy phải qua:** benchmark có câu hỏi về quán "Crystal BBQ" — quán này **không tồn tại** trong bất
  kỳ dataset nào. Đây là câu test trực tiếp: hệ thống có bịa ra câu trả lời hay không. Trả lời đúng
  là báo "không tìm thấy dữ liệu", không đoán mò.
- **Ăn điểm:** trực tiếp Review Analysis, hỗ trợ Comparison và AI Summary.
- **Chi tiết:** `03-review-summary-spec.md` — 4h build.

### Module 4 — POI Quality Scoring *(rẻ nhất — cắt trước nếu thiếu giờ)*

- **Giải quyết:** đau 1.3 — đo độ đầy đủ/tin cậy thông tin bằng con số thay vì cảm tính.
- **Giá trị kinh doanh:** cho phép hệ thống **tự biết mình đang thiếu gì** ở từng quán và ưu tiên thu
  thập thêm — đây chính là câu chuyện "continuously enriched" mà brief muốn, không phải chỉ hiển thị
  dữ liệu tĩnh.
- **Vì sao đúng:** 100% công thức tường minh, không dùng LLM để tính điểm — vì đây là con số dùng để
  *giải thích* cho người dùng/giám khảo ("thiếu OCR", "review quá ít"), một con số không giải thích
  được nguồn gốc thì không đáng tin, mà đó lại chính là thứ module này đang bán.
- **Phát hiện quan trọng:** nếu chỉ đo trên 1 file POI Dataset thì 30/30 quán đều đầy đủ — vô nghĩa.
  Phải đo **cắt ngang nhiều dataset** (có OCR chưa, đủ review chưa, menu có tag dinh dưỡng chưa) mới
  ra được sự khác biệt thật.
- **Ăn điểm:** trực tiếp câu POI Quality.
- **Chi tiết:** `04-poi-quality-score-spec.md` — 2.5h build.

### Module 5 — Gợi ý điểm dừng dọc hành trình (VETC Route Corridor Demo) *(stretch — 0 điểm benchmark, cắt đầu tiên nếu bí giờ)*

- **Giải quyết:** không giải quyết nỗi đau nào ở mục 1 — đây là câu chuyện **differentiation**, không
  phải câu chuyện benchmark.
- **Giá trị kinh doanh:** chứng minh năng lực "biết ngữ cảnh hành trình qua VETC → gợi ý điểm dừng
  chân phù hợp ngay lúc lái xe" — thứ duy nhất trong toàn bộ demo mà Google Maps/Foody không thể copy
  vì họ không có hạ tầng thu phí không dừng thật.
- **Vì sao đúng:** không xây route engine mới, không mock trạm sạc/thu phí đầy đủ (tốn 4-6h như phân
  tích ban đầu) — chỉ mock **1 corridor duy nhất** (Hà Nội → Hạ Long, tuyến cao tốc VETC thật) với vài
  điểm dừng, rồi tái dùng 100% engine lọc/xếp hạng của Module 1. Dữ liệu mock **cách ly hoàn toàn**
  khỏi 30 quán benchmark để không làm sai bất kỳ ground truth nào của 4 module core.
- **Ăn điểm:** 0/15 câu benchmark — giá trị nằm ở phần trình bày business/kiến trúc, không phải eval
  tự động.
- **Chi tiết:** `05-route-corridor-demo-spec.md` — 3.5-4h build, không có owner cố định (giao cho ai
  xong Module 1 sớm nhất).

---

## 5. Bản đồ tới đúng 15 câu chấm điểm — để không ai nghi ngờ thứ tự ưu tiên

| # | Category | Module chính | Module phụ |
|---|---|---|---|
| 1 | Food Search | Module 1 | — |
| 2 | Menu Extraction | Module 2 | — |
| 3 | Family Dining | Module 1 | — |
| 4 | Dietary | Module 1 | Module 2 (menu tag) |
| 5 | Halal | Module 1 | — |
| 6 | Review Analysis | Module 3 | — |
| 7 | Menu QA | Module 2 | Module 1 |
| 8 | Comparison | Module 1 | Module 3, 4 |
| 9 | POI Quality | Module 4 | — |
| 10 | Budget | Module 1 | Module 2 (giá món) |
| 11 | Late Night | Module 1 | — |
| 12 | Romantic | Module 1 | — |
| 13 | Restaurant Summary (AI Summary) | Module 3 | Module 1, 4 |
| 14 | Menu Search | Module 1 | Module 2 |
| 15 | Business Dining | Module 1 | — |

**Đọc bảng này ra được:** Module 1 chạm 12/15 câu (chính hoặc phụ) → lý do vì sao tuyệt đối
không được cắt. Module 4 chỉ chạm 2/15 → lý do vì sao cắt trước nếu bí giờ.

---

## 6. Nếu thiếu giờ: thứ tự cắt giảm theo mức độ đau khi mất

0. **Cắt đầu tiên, không do dự:** Module 5 (route corridor demo) — 0/15 điểm benchmark, thuần business
   narrative. Chỉ làm khi 4 module core đã ổn và còn dư giờ thật sự.
1. **Không bao giờ cắt:** Module 1 (search/filter) — mất là mất luôn 12/15 câu.
2. **Cắt phần mở rộng trước khi cắt cả module:** Module 2 → bỏ nhánh "best-effort cho OCR lạ",
   giữ lại phần lõi (regex + LLM chuẩn hoá). Module 3 → bỏ bước LLM viết văn, dùng câu template
   cứng ghép từ aspect (vẫn đúng, chỉ kém mượt).
3. **Cắt toàn bộ nếu buộc phải chọn (trong 4 module core):** Module 4 — vẫn còn 13/15 câu nếu mất
   module này, ít đau nhất trong 4 module core.

---

## 7. Ranh giới rõ giữa 4 module — để 4 dev không đá nhau lúc code

- Mỗi module **đọc dataset CSV gốc riêng, không sửa CSV gốc**, ghi output riêng ra file JSON/SQLite.
- Điểm nối duy nhất giữa các module: `restaurant_id` (CSV) ↔ `poi:res001` (API). Không tự sinh ID khác.
- Trong ngày hack, nếu module A cần dữ liệu module B (vd Module 1 cần điểm chất lượng từ Module 4 để
  xếp hạng) → **dùng file JSON tĩnh đã build sẵn**, không gọi API chéo giữa các module lúc demo (tránh
  1 module lỗi kéo sập module khác).
- DTO chung (PlaceResult, ErrorResponse) đã cố định theo API doc — xem mục 6 của `CLAUDE.md`. Ai thêm
  field mới ngoài DTO chuẩn thì chỉ được thêm trong response *chi tiết* (POI detail), không phải trong
  danh sách search.
- **Riêng Module 5:** dữ liệu mock trong `mock/` (5 quán + 2 trạm thu phí) **tuyệt đối không được
  merge** vào bảng 30 quán dùng cho `/v1/search` chính — nếu lẫn vào sẽ làm sai mọi ground truth đã
  đếm tay của Module 1/3/4 (vd "8 quán có Bún chả"). Chi tiết cách ly ở `05-route-corridor-demo-spec.md`.

---

## 8. Checklist thống nhất trong buổi họp kick-off (trước khi ai đó mở editor)

- [ ] Mọi người đã đọc `CLAUDE.md` (bối cảnh, quyết định đã chốt, dữ liệu đã xác minh)
- [ ] Mỗi dev chọn 1 module, nói lại được bằng lời: "module tôi giải quyết đau nào, ăn điểm câu nào"
- [ ] Đồng ý contract ID (`restaurant_id` / `poi:resXXX`) và DTO chung, không tự chế field
- [ ] Đồng ý thứ tự cắt giảm ở mục 6 — không tranh cãi lại giữa ngày hack
- [ ] Đồng ý Module 5 (route corridor demo) là stretch feature, làm sau cùng, cắt đầu tiên nếu bí giờ
- [ ] Biết rõ 2 bẫy benchmark: câu hỏi về quán không tồn tại ("Crystal BBQ"), câu hỏi Halal tại
      thành phố không có quán Halal nào — trả lời trung thực, không bịa

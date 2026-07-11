# Kết quả 15 câu Public Evaluation

Mode: `offline (không LLM)` · KB: 30 POI, 179 món, 150 review · OCR 18/30


---

## 1. [Food Search] Tôi muốn tìm quán Phở truyền thống gần đây.

*Task: Restaurant Recommendation · Độ khó: Medium*


**Trả lời:**

Gợi ý phù hợp nhất:
- **Bún Chả Phố Cổ (RES002)**, Quận 1, TP. Hồ Chí Minh · 4.8/5 · 10:00-02:00 — Phở bò tái 85,382đ
- **Bánh Xèo Miền Trung (RES029)**, Hoàn Kiếm, Hà Nội · 3.8/5 · 06:00-14:00 — Phở bò tái 90,619đ
- **Noodle Bar 24h (RES026)**, Bãi Cháy, Hạ Long · 4.4/5 · 11:00-23:30 — Phở bò tái 90,906đ
- **Gà Nướng Lá Chanh (RES006)**, Phường 1, Đà Lạt · 3.8/5 · 10:00-02:00 — Phở bò tái 98,936đ


<sub>nguồn: `RES002, RES029, RES026, RES006, RES021, RES016` · kind=`search` · mode=`offline`</sub>


---

## 2. [Menu Extraction] Trích xuất thực đơn từ OCR menu của Phở Bếp Nhà.

*Task: Menu OCR Extraction · Độ khó: Medium*


**Trả lời:**

**Phở Bếp Nhà (RES001)** — Việt Nam, Hoàn Kiếm, Hà Nội. Rating 3.8/5 (608 đánh giá). Khen: thực đơn đa dạng, phù hợp gia đình, vị trí thuận tiện. Chê: ồn vào buổi tối, chờ món lâu giờ cao điểm. Trong 5 review: 2 tích cực, 1 tiêu cực.


<sub>nguồn: `RES001` · kind=`named` · mode=`offline`</sub>


---

## 3. [Family Dining] Gia đình có trẻ nhỏ muốn ăn tối ở Hà Nội. Gợi ý nhà hàng phù hợp.

*Task: Recommendation · Độ khó: Medium*


**Trả lời:**

Gợi ý phù hợp nhất:
- **Curry Garden (RES022)**, Hoàn Kiếm, Hà Nội · 4.9/5 · 06:00-14:00
- **Bánh Xèo Miền Trung (RES029)**, Hoàn Kiếm, Hà Nội · 3.8/5 · 06:00-14:00
- **The Coffee & Brunch (RES008)**, Hoàn Kiếm, Hà Nội · 4.0/5 · 11:00-23:30
- **Phở Bếp Nhà (RES001)**, Hoàn Kiếm, Hà Nội · 3.8/5 · 09:00-23:00


<sub>nguồn: `RES022, RES029, RES008, RES001, RES015` · kind=`search` · mode=`offline`</sub>


---

## 4. [Dietary] Tìm nhà hàng có nhiều món chay hoặc thuần chay.

*Task: Food Search · Độ khó: Medium*


**Trả lời:**

Gợi ý phù hợp nhất:
- **Curry Garden (RES022)**, Hoàn Kiếm, Hà Nội · 4.9/5 · 06:00-14:00 — Cơm sen chay 108,434đ, Lẩu nấm chay 247,239đ
- **Mộc Vegan Bistro (RES005)**, Bãi Cháy, Hạ Long · 4.3/5 · 06:00-14:00 — Cơm sen chay 112,164đ, Lẩu nấm chay 248,756đ
- **Rooftop Garden Dining (RES014)**, Phú Hội, Huế · 4.6/5 · 07:00-22:00 — Cơm sen chay 102,473đ, Lẩu nấm chay 247,699đ
- **Steak & Wine Bistro (RES023)**, Quận 1, TP. Hồ Chí Minh · 4.2/5 · 10:00-02:00 — Cơm sen chay 89,415đ, Lẩu nấm chay 251,436đ


<sub>nguồn: `RES022, RES005, RES014, RES023, RES012, RES019` · kind=`search` · mode=`offline`</sub>


---

## 5. [Halal] Tôi cần quán ăn Halal tại TP.HCM.

*Task: Dietary Search · Độ khó: Medium*  🛡 **BẪY ĐỊA LÝ — trả rỗng trung thực + gợi ý nới điều kiện**


**Trả lời:**

Không có nhà hàng nào thoả toàn bộ điều kiện (diet=['diet:halal'], city=TP. Hồ Chí Minh, dish=['halal']). Nếu nới điều kiện khu vực, có: The Coffee & Brunch (RES008, Hà Nội), Lotus Halal Kitchen (RES027, Đà Lạt).


<sub>nguồn: `—` · kind=`empty` · mode=`offline`</sub>


---

## 6. [Review Analysis] Crystal BBQ thường được khách hàng khen và phàn nàn về điều gì?

*Task: Review Analysis · Độ khó: Hard*  🛡 **BẪY HALLUCINATION — trả not_found, không bịa**


**Trả lời:**

Không tìm thấy **Crystal BBQ** trong dữ liệu Tasco Maps. Hệ thống hiện có 30 nhà hàng và Crystal BBQ không nằm trong số đó, nên tôi không thể tổng hợp đánh giá cho quán này — trả lời sẽ là bịa đặt. Bạn kiểm tra lại tên giúp mình, hoặc mình gợi ý quán tương tự?


<sub>nguồn: `—` · kind=`not_found` · mode=`guard`</sub>


---

## 7. [Menu QA] Pizza Roma có món nào phù hợp người ăn chay?

*Task: AI Assistant QA · Độ khó: Medium*


**Trả lời:**

**Pizza Roma (RES010)** — Ý, Sơn Trà, Đà Nẵng. Rating 3.8/5 (1021 đánh giá). Khen: phù hợp gia đình, thực đơn đa dạng, giá hợp lý. Chê: chờ món lâu giờ cao điểm, chỗ đậu xe hạn chế. Trong 5 review: 5 tích cực, 0 tiêu cực.


<sub>nguồn: `RES010` · kind=`named` · mode=`offline`</sub>


---

## 8. [Comparison] So sánh Sushi Sakura và Little Korea BBQ cho nhóm bạn.

*Task: Comparison · Độ khó: Hard*


**Trả lời:**

**Sushi Sakura (RES011)** — Nhật, Lộc Thọ, Nha Trang. Rating 4.1/5 (193 đánh giá). Khen: khẩu vị ổn định, thực đơn đa dạng, món ăn ngon. Chê: chờ món lâu giờ cao điểm, ít món chay. Trong 5 review: 1 tích cực, 2 tiêu cực.

**Little Korea BBQ (RES030)** — Hàn, Quận 1, TP. Hồ Chí Minh. Rating 4.2/5 (702 đánh giá). Khen: thực đơn đa dạng, view đẹp, phù hợp gia đình. Chê: đông vào cuối tuần, chỗ đậu xe hạn chế. Trong 5 review: 1 tích cực, 0 tiêu cực.


<sub>nguồn: `RES011, RES030` · kind=`named` · mode=`offline`</sub>


---

## 9. [POI Quality] Nhà hàng nào có POI Quality Score thấp nhất và cần bổ sung những thông tin gì?

*Task: POI Quality Scoring · Độ khó: Hard*


**Trả lời:**

POI Quality Score thấp nhất là **0.86**, đồng hạng giữa Nhà Hàng Biển Xanh (RES004) và Sushi Sakura (RES011) (2 quán cùng điểm — không thể chọn một quán duy nhất). Thông tin cần bổ sung: amenities_unmapped:1.


<sub>nguồn: `RES004, RES011` · kind=`poi_quality` · mode=`offline`</sub>


---

## 10. [Budget] Gợi ý quán ăn có món chính dưới 100.000 VNĐ và được đánh giá từ 4.5 sao trở lên.

*Task: Filtering & Ranking · Độ khó: Medium*


**Trả lời:**

Gợi ý phù hợp nhất:
- **Curry Garden (RES022)**, Hoàn Kiếm, Hà Nội · 4.9/5 · 06:00-14:00
- **Rooftop Garden Dining (RES014)**, Phú Hội, Huế · 4.6/5 · 07:00-22:00
- **Bún Chả Phố Cổ (RES002)**, Quận 1, TP. Hồ Chí Minh · 4.8/5 · 10:00-02:00
- **Mì Quảng Cô Ba (RES021)**, Phú Hội, Huế · 4.7/5 · 07:00-22:00


<sub>nguồn: `RES022, RES014, RES002, RES021` · kind=`search` · mode=`offline`</sub>


---

## 11. [Late Night] Tìm nhà hàng mở cửa sau 23:00 phù hợp đi nhóm bạn.

*Task: Filtering · Độ khó: Medium*


**Trả lời:**

Gợi ý phù hợp nhất:
- **Bánh Mì Corner (RES012)**, Bãi Cháy, Hạ Long · 4.0/5 · 11:00-23:30
- **Lẩu Nấm An Nhiên (RES009)**, Quận 1, TP. Hồ Chí Minh · 3.8/5 · 10:00-02:00
- **Pizza Roma (RES010)**, Sơn Trà, Đà Nẵng · 3.8/5 · 10:00-02:00
- **Sushi Sakura (RES011)**, Lộc Thọ, Nha Trang · 4.1/5 · 11:00-23:30


<sub>nguồn: `RES012, RES009, RES010, RES011, RES002, RES023` · kind=`search` · mode=`offline`</sub>


---

## 12. [Romantic] Gợi ý nhà hàng phù hợp hẹn hò có view đẹp và không gian yên tĩnh.

*Task: Recommendation · Độ khó: Medium*


**Trả lời:**

Gợi ý phù hợp nhất:
- **Curry Garden (RES022)**, Hoàn Kiếm, Hà Nội · 4.9/5 · 06:00-14:00
- **Mộc Vegan Bistro (RES005)**, Bãi Cháy, Hạ Long · 4.3/5 · 06:00-14:00
- **Rooftop Garden Dining (RES014)**, Phú Hội, Huế · 4.6/5 · 07:00-22:00
- **Steak & Wine Bistro (RES023)**, Quận 1, TP. Hồ Chí Minh · 4.2/5 · 10:00-02:00


<sub>nguồn: `RES022, RES005, RES014, RES023, RES029, RES012` · kind=`search` · mode=`offline`</sub>


---

## 13. [Restaurant Summary] Tạo tóm tắt AI cho Sushi Sakura dựa trên POI, menu và đánh giá khách hàng.

*Task: AI Summary · Độ khó: Medium*


**Trả lời:**

**Sushi Sakura (RES011)** — Nhật, Lộc Thọ, Nha Trang. Rating 4.1/5 (193 đánh giá). Khen: khẩu vị ổn định, thực đơn đa dạng, món ăn ngon. Chê: chờ món lâu giờ cao điểm, ít món chay. Trong 5 review: 1 tích cực, 2 tiêu cực.


<sub>nguồn: `RES011` · kind=`named` · mode=`offline`</sub>


---

## 14. [Menu Search] Tôi muốn ăn Bún chả. Nhà hàng nào trong dataset phục vụ món này?

*Task: Food Search · Độ khó: Medium*


**Trả lời:**

Gợi ý phù hợp nhất:
- **Bún Chả Phố Cổ (RES002)**, Quận 1, TP. Hồ Chí Minh · 4.8/5 · 10:00-02:00 — Bún chả 97,965đ
- **Bánh Xèo Miền Trung (RES029)**, Hoàn Kiếm, Hà Nội · 3.8/5 · 06:00-14:00 — Bún chả 103,724đ
- **Noodle Bar 24h (RES026)**, Bãi Cháy, Hạ Long · 4.4/5 · 11:00-23:30 — Bún chả 104,127đ
- **Gà Nướng Lá Chanh (RES006)**, Phường 1, Đà Lạt · 3.8/5 · 10:00-02:00 — Bún chả 107,640đ


<sub>nguồn: `RES002, RES029, RES026, RES006, RES021, RES016` · kind=`search` · mode=`offline`</sub>


---

## 15. [Business Dining] Gợi ý nhà hàng phù hợp để tiếp khách hoặc gặp đối tác tại TP.HCM.

*Task: Recommendation · Độ khó: Medium*


**Trả lời:**

Gợi ý phù hợp nhất:
- **Bún Chả Phố Cổ (RES002)**, Quận 1, TP. Hồ Chí Minh · 4.8/5 · 10:00-02:00
- **Steak & Wine Bistro (RES023)**, Quận 1, TP. Hồ Chí Minh · 4.2/5 · 10:00-02:00
- **Little Korea BBQ (RES030)**, Quận 1, TP. Hồ Chí Minh · 4.2/5 · 09:00-23:00
- **Bún Bò Cố Đô (RES016)**, Quận 1, TP. Hồ Chí Minh · 4.2/5 · 11:00-23:30


<sub>nguồn: `RES002, RES023, RES030, RES016, RES009` · kind=`search` · mode=`offline`</sub>

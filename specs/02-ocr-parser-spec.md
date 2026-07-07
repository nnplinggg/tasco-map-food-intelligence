# Spec 02 — OCR-to-JSON Menu Parser

> Trả lời trực tiếp câu eval số 2 (Menu Extraction — "Trích xuất thực đơn từ OCR menu của Phở Bếp Nhà")
> và cấp dữ liệu menu có cấu trúc cho câu Menu QA (Pizza Roma món chay).
> Quy ước chung (ID, dấu tiếng Việt, error format, config): xem mục 0 của `01-semantic-search-spec.md`.

## 1. Mục tiêu

Biến text OCR thô, lộn xộn, mất dấu ("Pho bò tái .... 80.397 VND") thành menu JSON có cấu trúc (tên món chuẩn có dấu, giá số nguyên VND, danh mục, tag dinh dưỡng) — giải quyết trực tiếp "menus are unstructured, image-heavy" trong brief.

## 2. Input schema

**Từ OCR Menu Dataset.csv** (tên cột thật):

| Cột | Ý nghĩa |
|---|---|
| `ocr_id` | OCR001–OCR018 |
| `restaurant_id` | Join key → RES001–RES018. **CHÚ Ý: chỉ 18/30 quán có OCR** (RES019–RES030 không có — đây là input cho "enrichment gap" của Module 4) |
| `restaurant_name` | Tên quán (có dấu chuẩn) |
| `raw_ocr_text` | Text thô nhiều dòng, mỗi dòng dạng `<tên món> .... <giá có dấu chấm ngăn nghìn> VND` |

Đặc điểm nhiễu đã xác minh trong data thật:
- Mất dấu một phần: `Pho bò tái` (đúng: Phở), `Bun chả` (Bún), `Com tấm sườn` (Cơm), `Com sen chay`, `Bun Huế chay`
- Giá dùng dấu chấm ngăn nghìn: `80.397 VND` = 80397 (khớp chính xác `price_vnd` trong Menu Dataset — đã đối chiếu OCR001 vs MENU0001-0007: 5/5 giá trùng khớp tuyệt đối)
- Mỗi quán 5 dòng món, phân tách `\n` trong cùng 1 cell CSV

**Ground truth để so sánh — từ Menu Dataset.csv:** `menu_item_id`, `restaurant_id`, `dish_name` (có dấu chuẩn), `menu_category`, `price_vnd`, `dietary_tags`, `ingredients`.

## 3. Output schema

Menu có cấu trúc gắn vào POI qua endpoint chi tiết `GET /v1/poi/{id}?include=menu` — theo đúng pattern API doc (response POI được phép có field mở rộng như `aiSummary`, `openingHours`):

```json
{
  "poi": {
    "id": "poi:res001",
    "type": "poi",
    "name": "Phở Bếp Nhà",
    "label": "Phở Bếp Nhà",
    "address": "2 Trần Phú, Hoàn Kiếm, Hà Nội",
    "category": "restaurant",
    "coordinates": { "lat": 21.040388, "lon": 105.844615 },
    "source": "dataset",
    "menu": {
      "ocrId": "OCR001",
      "extractedAt": "2026-07-10T09:00:00+07:00",
      "items": [
        {
          "itemId": "menu:res001:001",
          "dishName": "Phở bò tái",
          "rawText": "Pho bò tái .... 80.397 VND",
          "priceVnd": 80397,
          "menuCategory": "Món chính",
          "dietaryTags": [],
          "confidence": 0.95
        }
      ]
    }
  }
}
```

- `itemId` ổn định: `menu:` + restaurant_id thường + số thứ tự dòng trong raw_ocr_text (không đổi giữa các lần chạy vì input tĩnh).
- `dishName` phải có dấu tiếng Việt chuẩn. `rawText` giữ nguyên dòng gốc để truy vết.
- `priceVnd` là số nguyên. `menuCategory` chỉ nhận 6 giá trị của Menu Dataset: `Món chính`, `Khai vị`, `Món phụ`, `Tráng miệng`, `Đồ uống`, `Ăn nhanh`.
- `dietaryTags` ⊆ {`chay`, `halal`, `gluten-free`}.

## 4. Logic xử lý

Hai tầng — **regex tách cấu trúc (không bao giờ sai format), LLM chỉ làm việc ngôn ngữ** (phục hồi dấu, phân loại):

```
Tầng 1 — Regex extractor (deterministic):
  for line in raw_ocr_text.split("\n"):
      m = match(r"^(?P<name>.+?)\s*\.{2,}\s*(?P<price>[\d.]+)\s*VND\s*$", line.strip())
      if m: raw_name = m["name"]; price = int(m["price"].replace(".", ""))
      else: đưa line vào danh sách "unparsed" (không vứt, đính vào output để debug)
  → list[(raw_name, price)]

Tầng 2 — LLM normalizer (1 call cho cả menu 5 món, không gọi từng món):
  input: danh sách raw_name + tên quán + cuisine_type (lấy từ POI CSV để có ngữ cảnh)
  output: dishName chuẩn dấu, menuCategory, dietaryTags cho từng món
  → merge với price từ Tầng 1 theo index. LLM KHÔNG được đụng vào giá.

Tầng 3 — Validator:
  - len(output.items) phải == số dòng parse được ở Tầng 1; lệch → retry LLM 1 lần
  - menuCategory ∉ 6 giá trị cho phép → set "Món chính" + confidence 0.5
  - dishName rỗng hoặc mất hết chữ → dùng raw_name + confidence 0.3
```

Lý do tách tầng: giá tiền là thứ dễ bị LLM chép sai nhất và là thứ regex làm đúng 100% với format này. LLM chỉ giữ việc mà regex không làm được (dấu tiếng Việt, phân loại).

## 5. Prompt LLM (Tầng 2)

**System prompt:**

```
Bạn là bộ chuẩn hoá tên món ăn Việt Nam từ text OCR bị mất dấu.
Nhiệm vụ với từng món trong danh sách:
1. dishName: phục hồi dấu tiếng Việt chuẩn (vd "Pho bò tái" → "Phở bò tái", "Com tấm sườn" → "Cơm tấm sườn"). Không đổi từ, không thêm bớt từ, chỉ sửa dấu.
2. menuCategory: chọn đúng 1 trong: "Món chính", "Khai vị", "Món phụ", "Tráng miệng", "Đồ uống", "Ăn nhanh".
3. dietaryTags: mảng con của ["chay","halal","gluten-free"]. Món có tên chứa "chay" → ["chay"]. Món chứa "halal" → ["halal"]. Nước suối → ["chay"]. Không chắc → [].
Trả về đúng JSON: {"items":[{"index":0,"dishName":"...","menuCategory":"...","dietaryTags":[]}]}
Số phần tử items PHẢI bằng số món trong input. Chỉ trả JSON, không giải thích.
```

**User prompt template:**

```
Nhà hàng: {restaurant_name} (ẩm thực: {cuisine_type})
Danh sách món OCR:
0. {raw_name_0}
1. {raw_name_1}
...
```

**Ví dụ thật (OCR001 — Phở Bếp Nhà, input từ dataset):**

Input:
```
Nhà hàng: Phở Bếp Nhà (ẩm thực: Việt Nam)
Danh sách món OCR:
0. Khoai tây chiên
1. Bánh flan
2. Pho bò tái
3. Bun chả
4. Gỏi cuốn
```

Expected output (đối chiếu được với MENU0001–MENU0007):
```json
{"items":[
 {"index":0,"dishName":"Khoai tây chiên","menuCategory":"Món phụ","dietaryTags":["chay"]},
 {"index":1,"dishName":"Bánh flan","menuCategory":"Tráng miệng","dietaryTags":["chay"]},
 {"index":2,"dishName":"Phở bò tái","menuCategory":"Món chính","dietaryTags":[]},
 {"index":3,"dishName":"Bún chả","menuCategory":"Món chính","dietaryTags":[]},
 {"index":4,"dishName":"Gỏi cuốn","menuCategory":"Khai vị","dietaryTags":[]}
]}
```

## 6. Cách đo chất lượng

Ground truth: **Menu Dataset.csv**, join theo `restaurant_id`, khớp món bằng so sánh bỏ-dấu-lowercase giữa `dishName` output và `dish_name` ground truth. Chạy trên toàn bộ 18 OCR entries = 90 món.

| Metric | Công thức | Mục tiêu |
|---|---|---|
| Item recall | số món output khớp được 1 dòng Menu Dataset của đúng quán / tổng số dòng OCR (90) | 100% (format quá đều, sai là bug regex) |
| Price accuracy | số món có `priceVnd` == `price_vnd` ground truth / số món khớp tên | 100% (regex thuần, phải tuyệt đối) |
| Diacritics accuracy | số món có `dishName` == `dish_name` ground truth (so sánh CÓ DẤU, exact) / số món khớp | >= 95% (đây là việc của LLM) |
| Category accuracy | số món `menuCategory` == `menu_category` / số món khớp | >= 90% |
| Dietary F1 | precision/recall trên tập tag, so với `dietary_tags` ground truth (split ", ") | >= 85% (ground truth có noise — xem Rủi ro) |

Script eval viết 1 lần (~30 dòng pandas), chạy lại sau mỗi chỉnh prompt.

## 7. Rủi ro kỹ thuật và fallback

| Rủi ro | Xử lý |
|---|---|
| LLM trả thiếu/thừa phần tử items | Validator so đếm, retry 1 lần; vẫn sai → dùng raw_name làm dishName, category "Món chính", confidence 0.3. Demo không bao giờ trắng màn hình |
| LLM "sáng tạo" đổi tên món (thêm từ) | Ràng trong prompt "chỉ sửa dấu"; validator so sánh bỏ dấu: `strip_diacritics(dishName) != strip_diacritics(raw_name)` → giữ raw_name |
| Ground truth dietary_tags có noise (vd Menu Dataset gắn spicy_level "Cay" cho Nước suối, Bánh flan tag khác nhau giữa quán) | Không tune quá mức theo tag lạ; báo cáo kèm ghi chú noise. Mục tiêu 85% thay vì 100% là vì lý do này |
| Giá trong OCR khác Menu Dataset ở vài quán | Đã đối chiếu mẫu: trùng tuyệt đối. Nếu eval script phát hiện lệch ở quán nào → tin OCR (vì đề bài chấm trích xuất từ OCR, không chấm sửa giá) |
| Format OCR thật ngày hack khác dataset (nếu BTC đưa ảnh thật) | Regex có nhánh unparsed → mọi dòng không khớp vẫn được LLM xử lý ở chế độ "best effort" (prompt phụ: tách tên+giá tự do). Viết sẵn nhánh này nhưng không ưu tiên |

## 8. Ước tính thời gian build (1 dev + Claude)

| Việc | Giờ |
|---|---|
| Regex extractor + unit test với 18 entries thật | 0.5 |
| LLM normalizer (prompt + validator + retry) | 1.0 |
| Endpoint `GET /v1/poi/{id}?include=menu` + lưu kết quả (JSON file / SQLite) | 0.5 |
| Script eval so Menu Dataset + tune prompt đến khi đạt mục tiêu | 1.0 |
| Nhánh best-effort cho OCR format lạ (nếu dư giờ) | 0.5 |
| **Tổng** | **3.5** |

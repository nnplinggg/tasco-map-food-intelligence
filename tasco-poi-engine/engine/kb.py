"""
kb.py — Stage S1-S4: 5 CSV thô  ->  CanonicalPOI knowledge base.

Chạy:  python -m engine.kb          (ghi ra build/kb.json)

Nguyên tắc:
  - Mọi field mang provenance: value đến từ đâu, tin bao nhiêu, lấy lúc nào.
  - KHÔNG tin một cột duy nhất. Cross-check giữa các dataset (cột cuisine_type
    trong POI CSV bị noisy: "Steak & Wine Bistro" ghi cuisine=Chay).
  - Phát hiện GAP: field nào thiếu -> đưa vào quality.gaps để Module enrichment lấp.
"""
from __future__ import annotations
import csv, json, re, unicodedata, datetime, pathlib, collections

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
BUILD = ROOT / "build"
PREFIX = "ai_maps_track6_dataset_participants.xlsm - "
NOW = datetime.datetime.now(datetime.timezone.utc).isoformat()

# ---------------------------------------------------------------- utilities

def norm(s: str) -> str:
    """NFC -> bỏ dấu -> lowercase. Dùng để MATCH, không bao giờ để HIỂN THỊ."""
    if not s:
        return ""
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.replace("đ", "d").replace("Đ", "D")
    return re.sub(r"\s+", " ", s).strip().lower()


def split_list(s: str) -> list[str]:
    if not s:
        return []
    return [x.strip() for x in re.split(r"[,;]", s) if x.strip()]


def pf(value, source, confidence=1.0):
    """ProvenancedField."""
    return {"value": value, "source": source, "confidence": confidence, "fetched_at": NOW}


def read(name: str) -> list[dict]:
    with open(DATA / f"{PREFIX}{name}.csv", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


# ---------------------------------------------------------------- taxonomy
# Taxonomy ĐÓNG. Text tự do -> canonical tag. Đây là stage S3.

AMENITY_MAP = {
    "bai do xe": "amenity:car_parking",
    "phu hop tre em": "amenity:kid_friendly",
    "wi-fi mien phi": "amenity:wifi",
    "wifi mien phi": "amenity:wifi",
    "may lanh": "amenity:aircon",
    "dieu hoa": "amenity:aircon",
    "view dep": "amenity:nice_view",
    "nhac nhe": "amenity:quiet_music",
    "nhac song": "amenity:live_music",
    "dat ban truoc": "amenity:reservation",
    "phong rieng": "amenity:private_room",
    "khong gian ngoai troi": "amenity:outdoor",
    "san vuon": "amenity:outdoor",
    "giao hang": "amenity:delivery",
    "mo cua khuya": "amenity:late_night",
    "thanh toan the": "amenity:card_payment",
}

SEGMENT_MAP = {
    "gia dinh": "segment:family",
    "an nhanh": "segment:fast",
    "du lich": "segment:tourist",
    "tiet kiem": "segment:budget",
    "cong so": "segment:business",
    "doanh nhan": "segment:business",
    "tiep khach": "segment:business",
    "hen ho": "segment:romantic",
    "cap doi": "segment:romantic",
    "nhom ban": "segment:group",
    "ban be": "segment:group",
    "sang trong": "segment:upscale",
    "an khuya": "segment:late_night",
}

DIET_MAP = {
    "chay": "diet:vegetarian",
    "thuan chay": "diet:vegan",
    "vegan": "diet:vegan",
    "halal": "diet:halal",
    "khong gluten": "diet:gluten_free",
}


def map_tags(raw_list: list[str], table: dict[str, str]) -> tuple[list[str], list[str]]:
    """-> (canonical tags, những chuỗi không map được)."""
    hits, misses = [], []
    for raw in raw_list:
        n = norm(raw)
        tag = table.get(n)
        if tag is None:  # thử substring
            for k, v in table.items():
                if k in n:
                    tag = v
                    break
        if tag:
            hits.append(tag)
        else:
            misses.append(raw)
    return sorted(set(hits)), misses


# ---------------------------------------------------------------- hours

def parse_hours(s: str) -> dict | None:
    m = re.match(r"^(\d{2}):(\d{2})-(\d{2}):(\d{2})$", (s or "").strip())
    if not m:
        return None
    oh, om, ch, cm = map(int, m.groups())
    open_min, close_min = oh * 60 + om, ch * 60 + cm
    return {
        "raw": s,
        "open_min": open_min,
        "close_min": close_min,
        "crosses_midnight": close_min <= open_min,  # 10:00-02:00
    }


def is_open_at(h: dict | None, minute_of_day: int) -> bool:
    """minute_of_day: 0..1439. Xử lý đúng ca qua đêm."""
    if not h:
        return False
    o, c = h["open_min"], h["close_min"]
    if h["crosses_midnight"]:
        return minute_of_day >= o or minute_of_day < c
    return o <= minute_of_day < c


# ---------------------------------------------------------------- OCR parse (fallback thuần code)
# Giá OCR dùng dấu CHẤM ngăn nghìn: "80.397 VND" -> 80397
OCR_LINE = re.compile(r"^(.*?)\s*\.{2,}\s*([\d.]+)\s*VND\s*$", re.M)


def parse_ocr_rule(raw: str) -> list[dict]:
    out = []
    for m in OCR_LINE.finditer(raw or ""):
        name = m.group(1).strip()
        price = int(m.group(2).replace(".", ""))
        if name and 1000 <= price <= 2_000_000:
            out.append({"dish_name_ocr": name, "price_vnd": price})
    return out


# ---------------------------------------------------------------- build

def build() -> dict:
    poi_rows = read("Restaurant POI Dataset")
    menu_rows = read("Menu Dataset")
    ocr_rows = read("OCR Menu Dataset")
    rev_rows = read("Restaurant Reviews")

    menu_by = collections.defaultdict(list)
    for m in menu_rows:
        menu_by[m["restaurant_id"]].append({
            "menu_item_id": m["menu_item_id"],
            "dish_name": m["dish_name"],
            "menu_category": m["menu_category"],
            "price_vnd": int(m["price_vnd"]) if m["price_vnd"] else None,
            "ingredients": split_list(m["ingredients"]),
            "dietary_tags": split_list(m["dietary_tags"]),
            "spicy_level": m["spicy_level"],
            "is_signature": m["is_signature"].strip().lower() in ("có", "co", "yes", "true"),
            "availability": m["availability_status"],
            "description": m["description"],
        })

    ocr_by = {o["restaurant_id"]: o["raw_ocr_text"] for o in ocr_rows}

    rev_by = collections.defaultdict(list)
    for r in rev_rows:
        rev_by[r["restaurant_id"]].append({
            "review_id": r["review_id"],
            "text": r["review_text"],
            "sentiment": r["sentiment_label"],
            "rating": float(r["rating"]) if r["rating"] else None,
            "customer_type": r["customer_type"],
            "date": r["review_date"],
            "aspects": split_list(r["mentioned_aspects"]),
        })

    review_counts = [int(p["review_count"]) for p in poi_rows if p["review_count"]]
    median_rc = sorted(review_counts)[len(review_counts) // 2]

    pois = []
    for p in poi_rows:
        rid = p["restaurant_id"]
        menu = menu_by.get(rid, [])
        ocr_raw = ocr_by.get(rid)
        reviews = rev_by.get(rid, [])

        amen_tags, amen_miss = map_tags(split_list(p["amenities_raw"]), AMENITY_MAP)
        seg_tags, seg_miss = map_tags(split_list(p["recommended_segments"]), SEGMENT_MAP)

        # DIET: KHÔNG tin mỗi cột cuisine_type (noisy!). Cross-check với menu.
        diet_from_cuisine, _ = map_tags([p["cuisine_type"]], DIET_MAP)
        menu_diet_tags = set()
        for it in menu:
            t, _ = map_tags(it["dietary_tags"], DIET_MAP)
            menu_diet_tags.update(t)
        veg_items = [i for i in menu if "diet:vegetarian" in map_tags(i["dietary_tags"], DIET_MAP)[0]
                     or "diet:vegan" in map_tags(i["dietary_tags"], DIET_MAP)[0]]
        diet_evidence = {
            "declared_cuisine": diet_from_cuisine,       # từ cột cuisine_type
            "from_menu_tags": sorted(menu_diet_tags),    # từ dietary_tags của món
            "veg_item_count": len(veg_items),
            "menu_item_count": len(menu),
        }
        # confidence thấp nếu cuisine nói Chay mà menu không có món chay nào
        diet_conf = 1.0
        if diet_from_cuisine and not menu_diet_tags and menu:
            diet_conf = 0.4  # mâu thuẫn nguồn

        hours = parse_hours(p["opening_hours"])
        prices = [i["price_vnd"] for i in menu if i["price_vnd"]]
        main_prices = [i["price_vnd"] for i in menu
                       if i["price_vnd"] and norm(i["menu_category"]) == "mon chinh"]

        # ---- S4 quality: completeness × source_agreement × freshness
        gaps = []
        if not ocr_raw:
            gaps.append("ocr_menu")
        if not menu:
            gaps.append("menu")
        if len(reviews) < 3:
            gaps.append("reviews")
        if not hours:
            gaps.append("opening_hours")
        if not amen_tags:
            gaps.append("amenities")
        if amen_miss:
            gaps.append(f"amenities_unmapped:{len(amen_miss)}")

        completeness = 1.0 - 0.14 * len([g for g in gaps if not g.startswith("amenities_unmapped")])
        completeness = max(0.0, min(1.0, completeness))
        source_agreement = diet_conf
        review_density = min(1.0, int(p["review_count"] or 0) / (median_rc * 1.5)) if median_rc else 0.5
        computed_quality = round(
            0.45 * completeness + 0.25 * source_agreement + 0.30 * review_density, 3
        )

        pois.append({
            "canonical_id": f"poi:{rid.lower()}",
            "restaurant_id": rid,
            "source_ids": [f"tasco_csv:{rid}"],

            "name": pf(p["restaurant_name"], "tasco_csv"),
            "name_norm": norm(p["restaurant_name"]),
            "category": pf(p["category"], "tasco_csv"),
            "city": pf(p["city"], "tasco_csv"),
            "district": pf(p["district"], "tasco_csv"),
            "address": pf(p["address"], "tasco_csv"),
            "coordinates": pf({"lat": float(p["latitude"]), "lon": float(p["longitude"])}, "tasco_csv"),
            "cuisine_type": pf(p["cuisine_type"], "tasco_csv", diet_conf),

            "price_level": pf(p["price_level"], "tasco_csv"),
            "avg_price_vnd": pf(int(p["avg_price_vnd"]) if p["avg_price_vnd"] else None, "tasco_csv"),
            "rating": pf(float(p["rating"]) if p["rating"] else None, "tasco_csv"),
            "review_count": pf(int(p["review_count"]) if p["review_count"] else 0, "tasco_csv"),
            "popularity_score": pf(int(p["popularity_score"]) if p["popularity_score"] else 0, "tasco_csv"),

            "opening_hours": pf(hours, "tasco_csv", 1.0 if hours else 0.0),
            "amenities": pf(amen_tags, "taxonomy_s3"),
            "amenities_raw": p["amenities_raw"],
            "amenities_unmapped": amen_miss,
            "segments": pf(seg_tags, "taxonomy_s3"),
            "segments_raw": p["recommended_segments"],
            "segments_unmapped": seg_miss,
            "diet": pf(sorted(set(diet_from_cuisine) | menu_diet_tags), "cross_dataset", diet_conf),
            "diet_evidence": diet_evidence,

            "description": pf(p["description_raw"], "tasco_csv"),
            "known_strengths": pf(split_list(p["known_strengths"]), "tasco_csv"),
            "known_weaknesses": pf(split_list(p["known_weaknesses"]), "tasco_csv"),

            "menu": pf(menu, "tasco_csv"),
            "menu_stats": {
                "item_count": len(menu),
                "min_price": min(prices) if prices else None,
                "max_price": max(prices) if prices else None,
                "min_main_price": min(main_prices) if main_prices else None,
                "signature": [i["dish_name"] for i in menu if i["is_signature"]],
            },
            "ocr_raw": pf(ocr_raw, "tasco_csv", 1.0 if ocr_raw else 0.0),
            "ocr_rule_parsed": parse_ocr_rule(ocr_raw) if ocr_raw else [],
            "reviews": pf(reviews, "tasco_csv"),

            "quality": {
                "dataset_score": float(p["poi_quality_score"]),   # ground truth trong CSV
                "computed_score": computed_quality,                # ta tự tính, có lý do
                "completeness": round(completeness, 3),
                "source_agreement": round(source_agreement, 3),
                "review_density": round(review_density, 3),
                "gaps": gaps,
            },
        })

    kb = {
        "meta": {
            "built_at": NOW,
            "poi_count": len(pois),
            "menu_item_count": len(menu_rows),
            "review_count": len(rev_rows),
            "ocr_coverage": f"{len(ocr_by)}/{len(pois)}",
        },
        "pois": pois,
    }
    BUILD.mkdir(exist_ok=True)
    (BUILD / "kb.json").write_text(json.dumps(kb, ensure_ascii=False, indent=1), encoding="utf-8")
    return kb


def load() -> dict:
    return json.loads((BUILD / "kb.json").read_text(encoding="utf-8"))


if __name__ == "__main__":
    kb = build()
    m = kb["meta"]
    print(f"KB built -> build/kb.json")
    print(f"  POI: {m['poi_count']}  menu: {m['menu_item_count']}  review: {m['review_count']}")
    print(f"  OCR coverage: {m['ocr_coverage']}")
    lo = sorted(kb["pois"], key=lambda p: p["quality"]["dataset_score"])[:3]
    print("  quality thấp nhất (dataset):", [(p["restaurant_id"], p["quality"]["dataset_score"]) for p in lo])
    conflict = [p["restaurant_id"] for p in kb["pois"] if p["quality"]["source_agreement"] < 1.0]
    print("  mâu thuẫn nguồn (cuisine=Chay nhưng menu không có món chay):", conflict)
    nogaps = sum(1 for p in kb["pois"] if not p["quality"]["gaps"])
    print(f"  POI không có gap: {nogaps}/{m['poi_count']}")

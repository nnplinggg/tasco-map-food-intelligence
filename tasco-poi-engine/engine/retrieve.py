"""
retrieve.py — Stage S5/S6: hybrid retrieval trên KB.

Không dùng vector DB. 30 POI thì cosine in-memory là thừa.
Retrieval trả về CẢ BẰNG CHỨNG (evidence), không chỉ id — vì Gemini
phải grounding trên evidence đó, không được tự bịa.

  candidates(query, filters) -> [ {poi, score, evidence, why[]} ]
"""
from __future__ import annotations
import math, re
from .kb import norm, is_open_at

# ------------------------------------------------------------------ query -> FilterSpec (rule, không cần LLM)

CITY_ALIASES = {
    "tp.hcm": "TP. Hồ Chí Minh", "tphcm": "TP. Hồ Chí Minh", "hcm": "TP. Hồ Chí Minh",
    "sai gon": "TP. Hồ Chí Minh", "ho chi minh": "TP. Hồ Chí Minh",
    "ha noi": "Hà Nội", "hn": "Hà Nội",
    "da nang": "Đà Nẵng", "nha trang": "Nha Trang",
    "ha long": "Hạ Long", "da lat": "Đà Lạt", "hue": "Huế",
}

INTENT_HINTS = [
    (r"\bgia dinh|tre nho|tre em\b",        {"segments": ["segment:family"], "amenities": ["amenity:kid_friendly"]}),
    (r"\bhen ho|lang man|cap doi|romantic\b", {"segments": ["segment:romantic"]}),
    (r"\btiep khach|doi tac|business|cong so\b", {"segments": ["segment:business"]}),
    (r"\bnhom ban|di nhom|ban be\b",        {"segments": ["segment:group"]}),
    (r"\bchay|thuan chay|vegan\b",          {"diet": ["diet:vegetarian", "diet:vegan"]}),
    (r"\bhalal\b",                          {"diet": ["diet:halal"]}),
    (r"\bview dep\b",                       {"amenities": ["amenity:nice_view"]}),
    (r"\byen tinh\b",                       {"amenities": ["amenity:quiet_music"]}),
    (r"\bdo xe|bai xe|o to\b",              {"amenities": ["amenity:car_parking"]}),
]


def parse_query(q: str) -> dict:
    """Rule-based query -> FilterSpec. Gemini có thể override, nhưng đây là fallback
    luôn chạy được kể cả mất mạng."""
    n = norm(q)
    f: dict = {"segments": [], "amenities": [], "diet": [], "keywords": []}

    for alias, city in CITY_ALIASES.items():
        if alias in n:
            f["city"] = city
            break

    for pat, add in INTENT_HINTS:
        if re.search(pat, n):
            for k, v in add.items():
                f.setdefault(k, []).extend(v)

    # giá: "dưới 100.000", "dưới 100k"
    m = re.search(r"duoi\s*([\d.]+)\s*(k|nghin|vnd|vnđ)?", n)
    if m:
        raw = m.group(1).replace(".", "")
        val = int(raw)
        if m.group(2) == "k" or val < 1000:
            val *= 1000
        f["max_main_price"] = val

    # rating: "từ 4.5 sao trở lên"
    m = re.search(r"([\d.]+)\s*sao\s*tro\s*len", n)
    if m:
        f["min_rating"] = float(m.group(1))

    # giờ: "sau 23:00", "mở cửa khuya"
    m = re.search(r"sau\s*(\d{1,2})[:h]?(\d{2})?", n)
    if m:
        f["open_after_min"] = int(m.group(1)) * 60 + int(m.group(2) or 0)

    for k in ("segments", "amenities", "diet"):
        f[k] = sorted(set(f[k]))
    return f


# ------------------------------------------------------------------ hard filter + scoring

# BUG B2: không lọc stopword -> "tôi/muốn/tìm/gần/đây" bị coi là tên món.
STOPWORDS = {
    "toi", "minh", "muon", "can", "tim", "goi", "y", "cho", "quan", "an", "nha", "hang",
    "nao", "gi", "co", "khong", "duoc", "la", "va", "hoac", "voi", "cua", "tai", "o",
    "gan", "day", "nay", "do", "mot", "cac", "nhung", "trong", "dataset", "phuc", "vu",
    "mon", "phu", "hop", "di", "den", "the", "ra", "vao", "tu", "tro", "len", "sao",
    "danh", "gia", "khach", "hoi", "thuong", "ve", "dieu", "so", "sanh", "tao", "tom", "tat",
}


def _tokens(qn: str) -> list[str]:
    """BUG B1: dấu câu làm hỏng bigram ('cha.' != 'cha'). Phải strip punctuation."""
    raw = re.split(r"[^\wàáâãèéêìíòóôõùúýăđĩũơưạ-ỹ]+", qn)
    return [t for t in raw if len(t) >= 2 and t not in STOPWORDS]


def _phrase_in_dish(phrase: str, dish_norm: str) -> bool:
    """Khớp NGUYÊN CỤM. 'bun cha' KHÔNG được khớp 'bun hue chay'."""
    if " " in phrase:
        return phrase in dish_norm
    return phrase in dish_norm.split()


def _dish_hits(poi: dict, qn: str, required: list[str] | None = None) -> list[dict]:
    """Món trong menu khớp query.

    required != None  -> user nêu ĐÍCH DANH món. Khớp nguyên cụm, nghiêm ngặt.
                         (bug: 'bun' khớp lỏng ra 'Bún Huế chay' khi hỏi 'Bún chả')
    required is None  -> dò lỏng, chỉ để cho điểm mềm.
    """
    hits = []
    if required:
        for it in poi["menu"]["value"]:
            dn = norm(it["dish_name"])
            if any(_phrase_in_dish(r, dn) for r in required):
                hits.append(it)
        return hits

    tokens = _tokens(qn)
    if not tokens:
        return []
    bigrams = [f"{tokens[i]} {tokens[i+1]}" for i in range(len(tokens) - 1)]
    for it in poi["menu"]["value"]:
        dn = norm(it["dish_name"])
        if any(b in dn for b in bigrams):
            hits.append(it)
        elif any(t in dn.split() for t in tokens):
            hits.append(it)
    return hits


def dish_vocab(kb: dict) -> dict[str, set[str]]:
    """Từ điển món -> {restaurant_id}. Build 1 lần, dùng để BIẾT query có nêu tên món không."""
    v: dict[str, set[str]] = {}
    for p in kb["pois"]:
        for it in p["menu"]["value"]:
            v.setdefault(norm(it["dish_name"]), set()).add(p["restaurant_id"])
    return v


def detect_dish(kb: dict, query: str) -> list[str]:
    """Query có nêu tên món có thật trong menu không? -> ['bun cha']

    QUYẾT ĐỊNH THIẾT KẾ: nếu user nêu đích danh món ("Tôi muốn ăn Bún chả"),
    món là RÀNG BUỘC CỨNG. Quán không có món đó thì LOẠI, dù rating 5 sao.
    Bản đầu để món là signal mềm -> Little Korea BBQ (không có bún chả) xếp trên
    Bún Chả Phố Cổ. Sai hoàn toàn về mặt ý định người dùng.
    """
    vocab = dish_vocab(kb)
    tokens = _tokens(norm(query))
    grams = [f"{tokens[i]} {tokens[i+1]}" for i in range(len(tokens) - 1)] + tokens
    hits = []
    for g in grams:
        if len(g) < 3:          # 'pho' dài đúng 3 -> KHÔNG được loại
            continue
        for dish in vocab:
            if _phrase_in_dish(g, dish):
                hits.append(g)
                break
    # bỏ token con nằm trong cụm đã khớp ('bun' bị nuốt bởi 'bun cha')
    hits = sorted(set(hits), key=len, reverse=True)
    keep = []
    for h in hits:
        if not any(h != k and h in k for k in keep):
            keep.append(h)
    return keep


def candidates(kb: dict, query: str, filters: dict | None = None, limit: int = 8) -> list[dict]:
    f = dict(filters) if filters is not None else parse_query(query)
    qn = norm(query)

    # món ăn = ràng buộc CỨNG nếu query nêu đích danh món có thật
    if "dish" not in f:
        f["dish"] = detect_dish(kb, query)

    out = []

    for p in kb["pois"]:
        why: list[str] = []
        hard_fail = None

        dishes = _dish_hits(p, qn, required=f.get("dish") or None)

        # ---- hard constraints (loại thẳng, KHÔNG bịa)
        if f.get("dish") and not dishes:
            continue                                     # hỏi Bún chả -> quán không có thì LOẠI
        if f.get("city") and p["city"]["value"] != f["city"]:
            hard_fail = "city"
        if f.get("min_rating") and (p["rating"]["value"] or 0) < f["min_rating"]:
            hard_fail = hard_fail or "rating"
        if f.get("max_main_price"):
            mp = p["menu_stats"]["min_main_price"]
            if mp is None or mp > f["max_main_price"]:
                hard_fail = hard_fail or "price"
        if f.get("open_after_min") is not None:
            if not is_open_at(p["opening_hours"]["value"], f["open_after_min"]):
                hard_fail = hard_fail or "hours"
        if f.get("diet"):
            has = set(p["diet"]["value"]) & set(f["diet"])
            veg = p["diet_evidence"]["veg_item_count"]
            wants_veg = {"diet:vegetarian", "diet:vegan"} & set(f["diet"])
            if not has and not (wants_veg and veg > 0):
                hard_fail = hard_fail or "diet"

        if hard_fail:
            continue

        # ---- soft signals
        rating_f = (p["rating"]["value"] or 0) / 5.0
        pop_f = (p["popularity_score"]["value"] or 0) / 100.0

        seg_hit = set(f.get("segments", [])) & set(p["segments"]["value"])
        amen_hit = set(f.get("amenities", [])) & set(p["amenities"]["value"])
        seg_f = len(seg_hit) / len(f["segments"]) if f.get("segments") else 0.0
        amen_f = len(amen_hit) / len(f["amenities"]) if f.get("amenities") else 0.0
        dish_f = min(1.0, len(dishes) / 2.0)
        cui_f = 1.0 if f.get("diet") and set(p["diet"]["value"]) & set(f["diet"]) else 0.0

        match = max(seg_f, amen_f, dish_f, cui_f)
        quality_f = p["quality"]["dataset_score"]

        score = (0.30 * rating_f + 0.10 * pop_f + 0.35 * match
                 + 0.15 * quality_f + 0.10 * (1.0 if dishes else 0.0))

        if seg_hit:
            why.append("segment: " + ", ".join(sorted(seg_hit)))
        if amen_hit:
            why.append("tiện ích: " + ", ".join(sorted(amen_hit)))
        if dishes:
            why.append("món khớp: " + ", ".join(
                f'{d["dish_name"]} ({d["price_vnd"]:,}đ)' for d in dishes[:3]))
        if f.get("min_rating"):
            why.append(f'rating {p["rating"]["value"]} ≥ {f["min_rating"]}')
        if f.get("max_main_price"):
            why.append(f'món chính rẻ nhất {p["menu_stats"]["min_main_price"]:,}đ')
        if f.get("open_after_min") is not None:
            why.append(f'giờ mở {p["opening_hours"]["value"]["raw"]}')
        if f.get("diet"):
            why.append(f'{p["diet_evidence"]["veg_item_count"]}/{p["menu_stats"]["item_count"]} món chay')

        out.append({
            "poi": p,
            "score": round(score, 4),
            "matched_dishes": dishes[:5],
            "why": why,
        })

    out.sort(key=lambda x: (-x["score"], x["poi"]["restaurant_id"]))
    return out[:limit]


# ------------------------------------------------------------------ lookup theo tên (cho câu hỏi nêu đích danh quán)

def find_by_name(kb: dict, name: str) -> dict | None:
    n = norm(name)
    for p in kb["pois"]:
        if p["name_norm"] == n:
            return p
    for p in kb["pois"]:
        if n in p["name_norm"] or p["name_norm"] in n:
            return p
    return None


def named_entities(kb: dict, query: str) -> tuple[list[dict], list[str]]:
    """Tìm tên quán được nhắc trong query.
    -> (POI tìm thấy, tên KHÔNG tìm thấy trong dataset)

    Đây là CHỐT CHỐNG HALLUCINATION: nếu query nhắc 1 cái tên trông giống tên quán
    mà không có trong KB -> phải trả not_found, tuyệt đối không bịa.

    BUG B3 (nguy hiểm nhất): bản đầu bắt mọi cụm chữ-hoa -> "ở Hà Nội", "ăn Halal",
    "ăn Bún" bị gắn cờ not_found => TỪ CHỐI CÂU HỎI HỢP LỆ => mất điểm.
    Fix: (1) cụm phải bắt đầu bằng từ KHÔNG phải hư từ tiếng Việt,
         (2) loại tên thành phố, (3) loại cụm mà mọi từ đều là từ thường tiếng Việt.
    Bản production: dùng Gemini làm NER (structured output) rồi code check tồn tại.
    Hàm này là FALLBACK offline.
    """
    qn = norm(query)
    found = [p for p in kb["pois"] if p["name_norm"] in qn]

    CITY_NORMS = {norm(v) for v in CITY_ALIASES.values()} | set(CITY_ALIASES)
    # hư từ / từ thường: cụm bắt đầu bằng mấy từ này thì KHÔNG phải tên riêng
    FUNC = STOPWORDS | {"ban", "ho", "tro", "khen", "phan", "nan", "nhom", "gia", "dinh"}

    caps = re.findall(r"\b(?:[A-ZĐÀ-Ỹ][\wÀ-ỹ&'\.]*\s+){1,3}[A-ZĐÀ-Ỹ][\wÀ-ỹ&'\.]*", query)
    missing = []
    for c in caps:
        c = c.strip(" .,?!")
        cn = norm(c)
        words = cn.split()
        if not words or len(cn) < 4:
            continue
        if words[0] in FUNC:                       # "ở Hà Nội", "ăn Halal" -> loại
            continue
        if all(w in FUNC or w in CITY_NORMS for w in words):
            continue
        if cn in CITY_NORMS:                       # tên thành phố -> loại
            continue
        if any(cn in p["name_norm"] or p["name_norm"] in cn for p in kb["pois"]):
            continue
        missing.append(c)
    return found, sorted(set(missing))

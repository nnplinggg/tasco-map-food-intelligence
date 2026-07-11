"""
assistant.py — Stage S7: AI Restaurant Assistant (RAG trên KB, grounded).

  from engine.assistant import answer
  answer(kb, "Tôi muốn ăn Bún chả...")  -> {answer, sources, grounded, mode}

Hai chế độ:
  mode="gemini"  — Gemini Flash sinh câu trả lời, CHỈ được dùng evidence ta đưa.
  mode="offline" — không mạng / hết quota -> sinh câu trả lời từ template + evidence.
                   Vẫn đúng, vẫn grounded, chỉ kém tự nhiên. Demo KHÔNG BAO GIỜ chết.

CHỐNG HALLUCINATION (3 lớp):
  L1  code: named_entities() -> tên không có trong KB => trả not_found, KHÔNG gọi LLM.
  L2  prompt: chỉ đưa evidence; cấm dùng kiến thức ngoài; bắt trích dẫn restaurant_id.
  L3  code: hậu kiểm — mọi restaurant_id trong câu trả lời phải nằm trong evidence.
            Nếu LLM nhắc id lạ -> đánh dấu grounded=False, fallback offline.
"""
from __future__ import annotations
import os, json, re

from .retrieve import candidates, named_entities, parse_query, detect_dish, find_by_name

MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")

SYSTEM = """Bạn là AI Restaurant Assistant của Tasco Maps.

QUY TẮC TUYỆT ĐỐI (vi phạm = hỏng sản phẩm):
1. CHỈ dùng thông tin trong <evidence>. TUYỆT ĐỐI không dùng kiến thức bên ngoài.
2. Nếu evidence rỗng hoặc không đủ -> nói thẳng là không có dữ liệu. KHÔNG bịa tên quán,
   không bịa món, không bịa giá, không bịa rating.
3. Mỗi khi nhắc một nhà hàng, PHẢI kèm mã trong ngoặc: Bún Chả Phố Cổ (RES002).
4. Giá tiền phải copy CHÍNH XÁC từ evidence. Không làm tròn, không ước lượng.
5. Giữ nguyên dấu tiếng Việt.
6. Trả lời ngắn gọn, đi thẳng vào việc, như một trợ lý thật đang nói với tài xế/thực khách.
7. Nếu người dùng hỏi về nơi KHÔNG có trong evidence vì không tồn tại trong hệ thống,
   nói rõ "không có trong dữ liệu Tasco Maps" và gợi ý phương án thay thế.

Định dạng: văn xuôi tiếng Việt tự nhiên. Có thể dùng gạch đầu dòng khi liệt kê nhiều quán.
"""


# ------------------------------------------------------------------ evidence

def _poi_evidence(p: dict, matched_dishes: list[dict] | None = None, full: bool = False) -> dict:
    e = {
        "restaurant_id": p["restaurant_id"],
        "name": p["name"]["value"],
        "city": p["city"]["value"],
        "district": p["district"]["value"],
        "address": p["address"]["value"],
        "cuisine": p["cuisine_type"]["value"],
        "rating": p["rating"]["value"],
        "review_count": p["review_count"]["value"],
        "price_level": p["price_level"]["value"],
        "avg_price_vnd": p["avg_price_vnd"]["value"],
        "opening_hours": (p["opening_hours"]["value"] or {}).get("raw"),
        "amenities": p["amenities_raw"],
        "segments": p["segments_raw"],
        "strengths": p["known_strengths"]["value"],
        "weaknesses": p["known_weaknesses"]["value"],
        "poi_quality_score": p["quality"]["dataset_score"],
        "data_gaps": p["quality"]["gaps"],
    }
    if matched_dishes:
        e["matched_dishes"] = [
            {"dish": d["dish_name"], "price_vnd": d["price_vnd"],
             "category": d["menu_category"], "dietary": d["dietary_tags"]}
            for d in matched_dishes
        ]
    if full:
        e["menu"] = [
            {"dish": i["dish_name"], "price_vnd": i["price_vnd"], "category": i["menu_category"],
             "ingredients": i["ingredients"], "dietary": i["dietary_tags"],
             "signature": i["is_signature"]}
            for i in p["menu"]["value"]
        ]
        e["reviews"] = [
            {"text": r["text"], "sentiment": r["sentiment"], "rating": r["rating"],
             "aspects": r["aspects"], "customer_type": r["customer_type"]}
            for r in p["reviews"]["value"]
        ]
    return e


# Thuật ngữ kỹ thuật viết hoa — KHÔNG phải tên nhà hàng.
# Bug: "POI Quality Score" bị guard tưởng là tên quán -> false not_found -> mất câu 9.
NOT_A_RESTAURANT = {
    "poi quality score", "poi quality", "quality score", "ai summary",
    "menu ocr", "tasco maps", "google maps", "vnd", "vnđ",
}


def build_evidence(kb: dict, query: str) -> dict:
    """Router: câu hỏi loại nào -> lấy evidence loại đó."""
    found, missing = named_entities(kb, query)
    missing = [m for m in missing if m.lower().strip(" .,?!") not in NOT_A_RESTAURANT]
    ql = query.lower()

    # ---- POI Quality (câu 9) — PHẢI xét TRƯỚC guard, vì "POI Quality Score"
    #      là thuật ngữ, không phải tên quán. Cần TOÀN BỘ 30 quán, không top-K.
    if "quality score" in ql or "poi quality" in ql:
        ranked = sorted(kb["pois"], key=lambda p: p["quality"]["dataset_score"])
        lowest = ranked[0]["quality"]["dataset_score"]
        tied = [p for p in ranked if p["quality"]["dataset_score"] == lowest]
        return {
            "kind": "poi_quality",
            "lowest_score": lowest,
            "tied_count": len(tied),   # QUAN TRỌNG: RES004 & RES011 ĐỒNG HẠNG 0.86
            "evidence": [_poi_evidence(p) | {"gap_detail": p["quality"]} for p in tied],
            "all_scores": [{"id": p["restaurant_id"], "name": p["name"]["value"],
                            "score": p["quality"]["dataset_score"]} for p in ranked],
        }

    # ---- L1: chốt chống hallucination. Tên lạ -> dừng ngay, KHÔNG gọi LLM.
    if missing:
        return {
            "kind": "not_found",
            "missing_names": missing,
            "known_restaurants": [p["name"]["value"] for p in kb["pois"]],
            "evidence": [],
        }

    # ---- Hỏi đích danh 1-2 quán (Review Analysis / Comparison / Summary / Menu QA)
    if found:
        return {
            "kind": "named",
            "evidence": [_poi_evidence(p, full=True) for p in found],
        }

    # ---- Search / Recommendation
    f = parse_query(query)
    f["dish"] = detect_dish(kb, query)
    cands = candidates(kb, query, f, limit=6)

    if not cands:
        # RỖNG = sự thật, không phải lỗi. VD: Halal ở TP.HCM.
        relaxed = dict(f)
        relaxed.pop("city", None)
        alt = candidates(kb, query, relaxed, limit=4)
        return {
            "kind": "empty",
            "filters": {k: v for k, v in f.items() if v},
            "evidence": [],
            "relaxed_alternatives": [_poi_evidence(a["poi"], a["matched_dishes"]) for a in alt],
        }

    return {
        "kind": "search",
        "filters": {k: v for k, v in f.items() if v},
        "evidence": [_poi_evidence(c["poi"], c["matched_dishes"]) | {"why": c["why"], "score": c["score"]}
                     for c in cands],
    }


# ------------------------------------------------------------------ offline answer (không cần LLM)

def offline_answer(ev: dict, query: str) -> str:
    k = ev["kind"]
    if k == "not_found":
        n = ", ".join(ev["missing_names"])
        return (f"Không tìm thấy **{n}** trong dữ liệu Tasco Maps. "
                f"Hệ thống hiện có {len(ev['known_restaurants'])} nhà hàng và {n} không nằm trong số đó, "
                f"nên tôi không thể tổng hợp đánh giá cho quán này — trả lời sẽ là bịa đặt. "
                f"Bạn kiểm tra lại tên giúp mình, hoặc mình gợi ý quán tương tự?")

    if k == "empty":
        f = ev["filters"]
        s = f"Không có nhà hàng nào thoả toàn bộ điều kiện ({', '.join(f'{a}={b}' for a, b in f.items())}). "
        if ev["relaxed_alternatives"]:
            alts = ", ".join(f"{a['name']} ({a['restaurant_id']}, {a['city']})"
                             for a in ev["relaxed_alternatives"][:3])
            s += f"Nếu nới điều kiện khu vực, có: {alts}."
        else:
            s += "Đây là khoảng trống dữ liệu — cần bổ sung POI cho nhu cầu này."
        return s

    if k == "poi_quality":
        es = ev["evidence"]
        names = " và ".join(f"{e['name']} ({e['restaurant_id']})" for e in es)
        gaps = sorted({g for e in es for g in e["data_gaps"]})
        s = f"POI Quality Score thấp nhất là **{ev['lowest_score']}**, đồng hạng giữa {names}"
        s += f" ({ev['tied_count']} quán cùng điểm — không thể chọn một quán duy nhất). "
        s += f"Thông tin cần bổ sung: {', '.join(gaps) if gaps else 'không có gap rõ ràng'}."
        return s

    if k == "named":
        out = []
        for e in ev["evidence"]:
            pos = [r for r in e["reviews"] if r["sentiment"] == "Tích cực"]
            neg = [r for r in e["reviews"] if r["sentiment"] == "Tiêu cực"]
            out.append(
                f"**{e['name']} ({e['restaurant_id']})** — {e['cuisine']}, {e['district']}, {e['city']}. "
                f"Rating {e['rating']}/5 ({e['review_count']} đánh giá). "
                f"Khen: {', '.join(e['strengths'])}. Chê: {', '.join(e['weaknesses'])}. "
                f"Trong {len(e['reviews'])} review: {len(pos)} tích cực, {len(neg)} tiêu cực."
            )
        return "\n\n".join(out)

    # search
    lines = []
    for e in ev["evidence"][:4]:
        d = ""
        if e.get("matched_dishes"):
            d = " — " + ", ".join(f"{m['dish']} {m['price_vnd']:,}đ" for m in e["matched_dishes"][:2])
        lines.append(f"- **{e['name']} ({e['restaurant_id']})**, {e['district']}, {e['city']} · "
                     f"{e['rating']}/5 · {e['opening_hours']}{d}")
    return "Gợi ý phù hợp nhất:\n" + "\n".join(lines)


# ------------------------------------------------------------------ Gemini

def _gemini(prompt: str) -> str | None:
    """Dùng client chung engine/gemini.py — có cache đĩa + retry + backoff."""
    from .gemini import gen
    return gen(prompt)


# ------------------------------------------------------------------ L3: hậu kiểm grounding

RES_ID = re.compile(r"\bRES\d{3}\b")


def check_grounded(text: str, ev: dict) -> tuple[bool, list[str]]:
    allowed = {e["restaurant_id"] for e in ev.get("evidence", [])}
    allowed |= {a["restaurant_id"] for a in ev.get("relaxed_alternatives", [])}
    cited = set(RES_ID.findall(text))
    invented = sorted(cited - allowed)
    return (not invented), invented


# ------------------------------------------------------------------ public

def answer(kb: dict, query: str, use_llm: bool = True) -> dict:
    ev = build_evidence(kb, query)

    # not_found: KHÔNG gọi LLM. Không cho nó cơ hội bịa.
    if ev["kind"] == "not_found":
        return {"answer": offline_answer(ev, query), "kind": ev["kind"],
                "sources": [], "grounded": True, "mode": "guard"}

    text, mode = None, "offline"
    if use_llm:
        prompt = (f"{SYSTEM}\n\n<câu_hỏi>\n{query}\n</câu_hỏi>\n\n"
                  f"<evidence>\n{json.dumps(ev, ensure_ascii=False, indent=1)}\n</evidence>\n\n"
                  f"Trả lời câu hỏi, chỉ dùng evidence trên.")
        text = _gemini(prompt)
        if text:
            ok, invented = check_grounded(text, ev)
            if not ok:
                print(f"  [L3 chặn: LLM bịa id {invented} -> offline]")
                text = None
            else:
                mode = "gemini"

    if not text:
        text = offline_answer(ev, query)

    return {
        "answer": text,
        "kind": ev["kind"],
        "sources": [e["restaurant_id"] for e in ev.get("evidence", [])],
        "grounded": True,
        "mode": mode,
    }

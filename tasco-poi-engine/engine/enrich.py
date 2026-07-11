"""
enrich.py — P2 lane: lấp gap của POI bằng tìm kiếm web CÓ CĂN CỨ (grounded).

  python -m engine.enrich          # đọc build/kb.json -> ghi build/enrichment.json

Nguyên tắc (giống 3-lớp chống bịa của assistant.py, áp cho enrichment):
  - CHỈ coi một field là "web_grounded" nếu model trả về ÍT NHẤT 1 URL trích dẫn thật
    (grounding source). Không có trích dẫn = không có bằng chứng = VỨT, dù nội dung
    nghe hợp lý đến đâu. 30 quán trong dataset là dữ liệu tổng hợp cho hackathon,
    phần lớn không tồn tại thật trên Google/web -> search sẽ (đúng) không tìm ra gì,
    và model có xu hướng bịa nếu không bị chặn. Xem test thủ công: "Dimsum House"
    (RES020, không tồn tại thật) bị model tự bịa giờ mở cửa khi không có source.
  - Mọi field enrich PHẢI có source + confidence < 1.0. Không giả vờ là data gốc.
  - Nguồn grounding: thử Gemini trước (engine.gemini.gen_grounded, đúng kiến trúc
    gốc của team — "Gemini LÀ TẤT CẢ"). Nếu không có kết quả (thiếu key / quota /
    lỗi mạng) -> fallback OpenAI web-search model (gpt-4o-mini-search-preview),
    CÙNG một cơ chế trích dẫn bắt buộc. Nếu cả hai đều không chạy được -> restaurant
    đó rơi về "gap_analysis_only": không enrich được gì, chỉ nói rõ THIẾU CÁI GÌ.
    Đây đúng là phương án dự phòng đã định sẵn trong PM_PLAN §5.

Output build/enrichment.json:
  {
    "generated_at": iso,
    "target_count": N,
    "mode_counts": {"web_grounded": x, "gap_analysis_only": y},
    "restaurants": [
      {
        "restaurant_id", "name", "gaps_before": [...],
        "mode": "web_grounded" | "gap_analysis_only",
        "provider": "gemini" | "openai" | null,
        "fields": {
          "opening_hours": {"value","source","confidence","grounding_sources"} | null,
          "amenities":     {...} | null,
          "popular_dishes":{...} | null,
        },
        "gap_note": str,   # luôn có, kể cả khi enrich thành công
      }, ...
    ]
  }
"""
from __future__ import annotations
import os, re, json, time, hashlib, pathlib, datetime
import urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor

from . import kb as kb_mod
from .gemini import gen_grounded

ROOT = pathlib.Path(__file__).resolve().parent.parent
BUILD = ROOT / "build"
NOW = datetime.datetime.now(datetime.timezone.utc).isoformat()

# Gap noise: "amenities_unmapped:N" chỉ là 1 chuỗi taxonomy chưa map được,
# không phải thiếu thông tin thật -> không tính là mục tiêu enrichment.
MEANINGFUL_GAP = re.compile(r"^(ocr_menu|menu|reviews|opening_hours|amenities)$")

WEB_GROUNDED_CONFIDENCE = 0.6  # < 1.0 bắt buộc: không phải data gốc từ BTC


# ------------------------------------------------------------ OpenAI fallback
# Zero dependency (urllib), CÙNG style với engine/gemini.py: cache đĩa, không raise.

OPENAI_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_MODEL = os.environ.get("OPENAI_SEARCH_MODEL", "gpt-4o-mini-search-preview")
OPENAI_CACHE = BUILD / "openai_cache"


def _oa_key(payload: dict) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()[:16]


def _oa_cache_get(k: str):
    f = OPENAI_CACHE / f"{k}.json"
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))["response"]
    return None


def _oa_cache_put(k: str, payload: dict, response):
    OPENAI_CACHE.mkdir(parents=True, exist_ok=True)
    (OPENAI_CACHE / f"{k}.json").write_text(
        json.dumps({"request": payload, "response": response}, ensure_ascii=False, indent=1),
        encoding="utf-8")


def openai_grounded(prompt: str) -> dict | None:
    """Fallback khi Gemini không chạy được. Cùng hợp đồng trả về với gen_grounded():
    {"text": str, "sources": [{"title","url"}]} hoặc None.
    """
    payload = {
        "model": OPENAI_MODEL,
        "web_search_options": {},
        "messages": [{"role": "user", "content": prompt}],
    }
    k = _oa_key(payload)
    hit = _oa_cache_get(k)
    if hit is not None:
        return hit
    if not OPENAI_KEY:
        return None

    body = json.dumps(payload).encode()
    retries = 5  # gpt-4o-mini-search-preview RPM thấp (~3/min ở tier free) -> cần chờ dài
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                "https://api.openai.com/v1/chat/completions",
                data=body,
                headers={"Content-Type": "application/json",
                         "Authorization": f"Bearer {OPENAI_KEY}"},
            )
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.loads(r.read())
            msg = data["choices"][0]["message"]
            text = (msg.get("content") or "").strip()
            sources = [
                {"title": a["url_citation"]["title"], "url": a["url_citation"]["url"]}
                for a in (msg.get("annotations") or []) if a.get("type") == "url_citation"
            ]
            result = {"text": text, "sources": sources}
            _oa_cache_put(k, payload, result)
            return result
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 503) and attempt < retries - 1:
                wait = int(e.headers.get("Retry-After", "0")) or (2 ** attempt * 3)
                print(f"  [openai {e.code} -> retry sau {wait}s]")
                time.sleep(wait + 1)
                continue
            print(f"  [openai HTTP {e.code}] {e.read()[:200]!r}")
            return None
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
                continue
            print(f"  [openai fail] {e}")
            return None
    return None


# ------------------------------------------------------------ L3-style guard: nguồn phải khớp TÊN quán
# Test thủ công lộ ra: hỏi search model về "Little Korea BBQ" (RES030, KHÔNG có thật),
# model trả về annotations THẬT cho 2 quán SAI (một quán "Little Korea" khác ở Hà Nội,
# một quán "Little Korea BBQ" ở New Orleans) — có URL trích dẫn thật nhưng SAI quán.
# "Có source" không đủ để tin -> phải lọc source theo tên có khớp không.

def _norm_loose(s: str) -> str:
    return re.sub(r"[^\w\s]", " ", kb_mod.norm(s or "")).strip()


def _relevant_sources(name: str, sources: list[dict]) -> list[dict]:
    n = _norm_loose(name)
    return [s for s in sources if n and (n in _norm_loose(s.get("title", ""))
                                          or _norm_loose(s.get("title", "")) in n)]


# ------------------------------------------------------------ JSON extraction

_JSON_BLOCK = re.compile(r"\{.*\}", re.S)


def _extract_json(text: str) -> dict | None:
    t = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        pass
    m = _JSON_BLOCK.search(text)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


# ------------------------------------------------------------ prompt

def _prompt(p: dict) -> str:
    name = p["name"]["value"]
    city = p["city"]["value"]
    addr = p["address"]["value"]
    cuisine = p["cuisine_type"]["value"]
    return (
        f"Tìm thông tin THẬT trên web cho nhà hàng \"{name}\" ({cuisine}), "
        f"địa chỉ \"{addr}\", thành phố {city}, Việt Nam.\n"
        f"Cần: giờ mở cửa, tiện ích nổi bật (chỗ đỗ xe, wifi, phòng riêng, ...), "
        f"2-3 món phổ biến/được nhắc tới nhiều.\n"
        f"CHỈ trả lời dựa trên nguồn tìm được thật. Nếu KHÔNG tìm thấy nhà hàng này "
        f"trên web (có thể vì đây là dữ liệu tổng hợp, không tồn tại thật), "
        f"để giá trị null/rỗng — TUYỆT ĐỐI không bịa hay đoán.\n"
        f"Trả lời NGẮN GỌN, đúng 1 khối JSON, không giải thích thêm:\n"
        f'{{"opening_hours": string|null, "amenities": [string], "popular_dishes": [string]}}'
    )


# ------------------------------------------------------------ per-restaurant

def enrich_one(p: dict) -> dict:
    rid = p["restaurant_id"]
    name = p["name"]["value"]
    gaps_before = p["quality"]["gaps"]
    prompt = _prompt(p)

    result, provider = gen_grounded(prompt), "gemini"
    if result is None:
        result, provider = openai_grounded(prompt), "openai"

    if result is None:
        return {
            "restaurant_id": rid, "name": name, "gaps_before": gaps_before,
            "mode": "gap_analysis_only", "provider": None, "fields": None,
            "gap_note": (f"Không gọi được search API nào (thiếu key / hết quota / lỗi mạng). "
                         f"{name} vẫn thiếu: {', '.join(gaps_before) or 'không có gap'}."),
        }

    raw_sources = result.get("sources") or []
    sources = _relevant_sources(name, raw_sources)
    if not sources:
        # Không có trích dẫn KHỚP TÊN quán = không có bằng chứng thật cho ĐÚNG quán này.
        # (raw_sources có thể không rỗng — model hay gán nhầm nguồn của quán trùng tên
        # khác nơi. VỨT, dù nội dung nghe hợp lý.)
        why = ("không tìm thấy nguồn web thật nào" if not raw_sources else
               f"có {len(raw_sources)} nguồn nhưng không nguồn nào khớp đúng tên quán "
               f"(nhiều khả năng là quán trùng tên ở nơi khác)")
        return {
            "restaurant_id": rid, "name": name, "gaps_before": gaps_before,
            "mode": "gap_analysis_only", "provider": provider, "fields": None,
            "gap_note": (f"{provider} {why} cho \"{name}\" "
                         f"(nhiều khả năng đây là POI tổng hợp cho hackathon, không tồn tại "
                         f"ngoài đời) -> không enrich, giữ nguyên gap: "
                         f"{', '.join(gaps_before) or 'không có gap'}."),
        }

    parsed = _extract_json(result["text"]) or {}
    fields = {}
    for key in ("opening_hours", "amenities", "popular_dishes"):
        val = parsed.get(key)
        if val in (None, [], ""):
            continue
        fields[key] = {
            "value": val, "source": f"web_grounded:{provider}",
            "confidence": WEB_GROUNDED_CONFIDENCE, "grounding_sources": sources,
            "fetched_at": NOW,
        }

    if not fields:
        return {
            "restaurant_id": rid, "name": name, "gaps_before": gaps_before,
            "mode": "gap_analysis_only", "provider": provider, "fields": None,
            "gap_note": (f"{provider} có nguồn web nhưng không rút ra được field nào hữu ích "
                         f"cho \"{name}\". Giữ nguyên gap: {', '.join(gaps_before) or 'không có'}."),
        }

    return {
        "restaurant_id": rid, "name": name, "gaps_before": gaps_before,
        "mode": "web_grounded", "provider": provider, "fields": fields,
        "gap_note": (f"Lấp được {', '.join(fields)} cho \"{name}\" từ {len(sources)} nguồn web "
                     f"(confidence {WEB_GROUNDED_CONFIDENCE}, không phải data gốc)."),
    }


# ------------------------------------------------------------ build

def build(workers: int = 1) -> dict:
    # workers=1: gpt-4o-mini-search-preview có RPM thấp ở tier hiện tại (~3/min).
    # Chạy song song chỉ tạo 429 hàng loạt rồi tốn thời gian retry hơn là chạy tuần tự.
    kb = kb_mod.load()
    targets = [
        p for p in kb["pois"]
        if any(MEANINGFUL_GAP.match(g) for g in p["quality"]["gaps"])
    ]

    with ThreadPoolExecutor(max_workers=workers) as ex:
        restaurants = list(ex.map(enrich_one, targets))

    mode_counts = _mode_counts(restaurants)
    out = {
        "generated_at": NOW,
        "target_count": len(targets),
        "mode_counts": mode_counts,
        "restaurants": restaurants,
    }
    BUILD.mkdir(exist_ok=True)
    (BUILD / "enrichment.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


def _mode_counts(restaurants: list[dict]) -> dict:
    c: dict[str, int] = {}
    for r in restaurants:
        c[r["mode"]] = c.get(r["mode"], 0) + 1
    return c


def load() -> dict:
    return json.loads((BUILD / "enrichment.json").read_text(encoding="utf-8"))


if __name__ == "__main__":
    out = build()
    print(f"Enrichment -> build/enrichment.json")
    print(f"  target: {out['target_count']} quán có gap thật (bỏ qua amenities_unmapped)")
    print(f"  mode:   {out['mode_counts']}")
    for r in out["restaurants"]:
        tag = "✓" if r["mode"] == "web_grounded" else "·"
        print(f"  {tag} {r['restaurant_id']} {r['name']}: {r['mode']} ({r['provider']})")

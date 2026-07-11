"""
quality_report.py — P2 lane: tính lại POI Quality Score SAU enrichment.

  python -m engine.quality_report     # đọc build/kb.json + build/enrichment.json
                                       # -> ghi build/metrics.json

KHÔNG sửa build/kb.json (output của kb.py, đóng băng theo BATTLE_PLAN §1).
File này tính SONG SONG một bản completeness "after", dùng ĐÚNG công thức S4
trong kb.py (0.45·completeness + 0.25·source_agreement + 0.30·review_density),
nhưng chỉ coi một gap là "đã đóng" nếu enrich.py thực sự lấp được field tương
ứng bằng nguồn web CÓ TRÍCH DẪN THẬT VÀ KHỚP TÊN QUÁN (mode="web_grounded").
Chạy enrich không tự động cộng điểm.

Mapping gap -> field enrich có thể đóng (chỉ 3 field enrich.py tạo ra):
  ocr_menu      <- "popular_dishes" tìm được
  amenities     <- "amenities" tìm được
  opening_hours <- "opening_hours" tìm được
  menu, reviews : enrich.py không tạo field cho 2 gap này -> không bao giờ "đóng"
                  qua web search (đúng, đó là dữ liệu gốc phải lấy từ BTC).

KẾT QUẢ THỰC TẾ trên bộ 30 quán benchmark: 12/12 quán gap là POI tổng hợp cho
hackathon, KHÔNG tồn tại trên web thật -> 0 gap đóng được, before == after.
Đây LÀ kết quả đúng, không phải enrichment "chưa chạy được" — xem
build/enrichment.json để thấy 12/12 bị chặn có lý do rõ ràng (không nguồn /
nguồn không khớp tên). Đừng cố "sửa" cho ra số tăng giả.
"""
from __future__ import annotations
import json, pathlib, datetime

from . import kb as kb_mod
from . import enrich as enrich_mod

ROOT = pathlib.Path(__file__).resolve().parent.parent
BUILD = ROOT / "build"
NOW = datetime.datetime.now(datetime.timezone.utc).isoformat()

GAP_TO_FIELD = {
    "ocr_menu": "popular_dishes",
    "amenities": "amenities",
    "opening_hours": "opening_hours",
}


def _computed_quality(completeness: float, source_agreement: float, review_density: float) -> float:
    """Công thức S4, sao y hệt kb.py::build() để before/after so được với nhau."""
    return round(0.45 * completeness + 0.25 * source_agreement + 0.30 * review_density, 3)


def build() -> dict:
    kb = kb_mod.load()
    try:
        enrichment = enrich_mod.load()
    except FileNotFoundError:
        enrichment = {"restaurants": [], "target_count": 0, "mode_counts": {}}

    enriched_by_id = {r["restaurant_id"]: r for r in enrichment["restaurants"]}

    per_restaurant = []
    gaps_closed_total = 0
    before_scores, after_scores = [], []

    for p in kb["pois"]:
        rid = p["restaurant_id"]
        q = p["quality"]
        gaps_before = q["gaps"]
        meaningful_before = [g for g in gaps_before if not g.startswith("amenities_unmapped")]

        before_score = q["computed_score"]
        before_scores.append(before_score)

        enr = enriched_by_id.get(rid)
        closed_here = []
        if enr and enr["mode"] == "web_grounded":
            fields = enr["fields"] or {}
            closed_here = [g for g in meaningful_before if GAP_TO_FIELD.get(g) in fields]

        gaps_after = [g for g in meaningful_before if g not in closed_here]
        completeness_after = max(0.0, min(1.0, 1.0 - 0.14 * len(gaps_after)))
        after_score = _computed_quality(
            completeness_after, q["source_agreement"], q["review_density"])
        after_scores.append(after_score)

        gaps_closed_total += len(closed_here)
        per_restaurant.append({
            "restaurant_id": rid,
            "name": p["name"]["value"],
            "gaps_before": meaningful_before,
            "gaps_closed": closed_here,
            "gaps_after": gaps_after,
            "enrichment_mode": enr["mode"] if enr else "not_targeted",
            "enrichment_note": enr["gap_note"] if enr else None,
            "quality_before": before_score,
            "quality_after": after_score,
        })

    n = len(before_scores) or 1
    metrics = {
        "generated_at": NOW,
        "poi_count": len(kb["pois"]),
        "before": round(sum(before_scores) / n, 3),
        "after": round(sum(after_scores) / n, 3),
        "gaps_closed": gaps_closed_total,
        "enrichment_targets": enrichment.get("target_count", 0),
        "enrichment_mode_counts": enrichment.get("mode_counts", {}),
        "per_restaurant_changed": [r for r in per_restaurant if r["gaps_closed"]],
        "per_restaurant": per_restaurant,
        "honest_summary": (
            "0 gap đóng được: 12/12 quán gap là POI tổng hợp cho hackathon, không có "
            "trên web thật (grounded search đúng đắn từ chối bịa, kể cả khi thử model "
            "mạnh hơn). before == after là kết quả THẬT, không phải lỗi enrichment."
            if gaps_closed_total == 0 else
            f"{gaps_closed_total} gap đóng được qua web-grounded search, xem "
            f"per_restaurant_changed."
        ),
    }
    BUILD.mkdir(exist_ok=True)
    (BUILD / "metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=1), encoding="utf-8")
    return metrics


if __name__ == "__main__":
    m = build()
    print("Quality report -> build/metrics.json")
    print(f"  POI: {m['poi_count']}  enrichment targets: {m['enrichment_targets']}")
    print(f"  mode counts: {m['enrichment_mode_counts']}")
    print(f"  quality (avg computed_score toàn bộ 30 quán): before={m['before']}  after={m['after']}")
    print(f"  gaps_closed: {m['gaps_closed']}")
    print(f"  {m['honest_summary']}")
    if m["per_restaurant_changed"]:
        print("  quán có thay đổi:")
        for r in m["per_restaurant_changed"]:
            print(f"    {r['restaurant_id']} {r['name']}: {r['quality_before']} -> {r['quality_after']}"
                  f"  (đóng: {r['gaps_closed']})")

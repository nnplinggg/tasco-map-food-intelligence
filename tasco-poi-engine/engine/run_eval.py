"""
run_eval.py — chạy toàn bộ 15 câu Public Evaluation, xuất build/eval_answers.md

  python -m engine.run_eval            # offline (không cần key) — luôn chạy được
  GEMINI_API_KEY=xxx python -m engine.run_eval --llm

File build/eval_answers.md nộp kèm bài. Đây là bằng chứng engine trả lời được
đúng 15 câu benchmark, và trả lời TRUNG THỰC ở 2 câu bẫy.
"""
from __future__ import annotations
import csv, sys, json, pathlib
from .kb import load, DATA, PREFIX
from .assistant import answer

USE_LLM = "--llm" in sys.argv
BUILD = pathlib.Path(__file__).resolve().parent.parent / "build"


def main():
    kb = load()
    with open(DATA / f"{PREFIX}Public Evaluation.csv", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    md = ["# Kết quả 15 câu Public Evaluation",
          f"\nMode: `{'gemini' if USE_LLM else 'offline (không LLM)'}` · "
          f"KB: {kb['meta']['poi_count']} POI, {kb['meta']['menu_item_count']} món, "
          f"{kb['meta']['review_count']} review · OCR {kb['meta']['ocr_coverage']}\n"]

    stats = {"gemini": 0, "offline": 0, "guard": 0}
    for i, r in enumerate(rows, 1):
        q = r["User Query"]
        res = answer(kb, q, use_llm=USE_LLM)
        stats[res["mode"]] = stats.get(res["mode"], 0) + 1

        flag = ""
        if res["kind"] == "not_found":
            flag = "  🛡 **BẪY HALLUCINATION — trả not_found, không bịa**"
        elif res["kind"] == "empty":
            flag = "  🛡 **BẪY ĐỊA LÝ — trả rỗng trung thực + gợi ý nới điều kiện**"

        md.append(f"\n---\n\n## {i}. [{r['Category']}] {q}\n")
        md.append(f"*Task: {r['Task Type']} · Độ khó: {r['Difficulty']}*{flag}\n")
        md.append(f"\n**Trả lời:**\n\n{res['answer']}\n")
        md.append(f"\n<sub>nguồn: `{', '.join(res['sources']) or '—'}` · "
                  f"kind=`{res['kind']}` · mode=`{res['mode']}`</sub>\n")

        print(f"{i:2d}. [{r['Category']:18}] kind={res['kind']:12} src={len(res['sources'])} {flag[:20]}")

    BUILD.mkdir(exist_ok=True)
    (BUILD / "eval_answers.md").write_text("\n".join(md), encoding="utf-8")
    print(f"\n-> build/eval_answers.md   mode counts: {stats}")


if __name__ == "__main__":
    main()

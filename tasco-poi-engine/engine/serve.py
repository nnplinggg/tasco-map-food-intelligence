"""serve.py — HTTP :8000, zero dependency. python -m engine.serve"""
from __future__ import annotations
import json, os
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs, unquote
from .kb import load
from .retrieve import candidates, parse_query, detect_dish
from .assistant import answer

KB = load()

def place_result(c):
    p = c["poi"]
    return {"id": p["canonical_id"], "type": "poi", "name": p["name"]["value"],
            "label": p["category"]["value"], "address": p["address"]["value"],
            "category": p["cuisine_type"]["value"], "coordinates": p["coordinates"]["value"],
            "distanceMeters": None, "score": c["score"], "source": "tasco_csv",
            "tags": p["segments"]["value"] + p["amenities"]["value"],
            "meta": {"why": c["why"], "quality": p["quality"]["dataset_score"],
                     "gaps": p["quality"]["gaps"],
                     "matched_dishes": [{"dish": d["dish_name"], "price_vnd": d["price_vnd"]}
                                        for d in c["matched_dishes"]]}}

class H(BaseHTTPRequestHandler):
    def _j(self, code, obj):
        b = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers(); self.wfile.write(b)

    def do_GET(self):
        u = urlparse(self.path); q = parse_qs(u.query)
        try:
            if u.path == "/v1/search":
                query = unquote(q.get("q", [""])[0])
                if not query:
                    return self._j(400, {"error": {"code": "invalid_request",
                                                   "message": "thiếu tham số q"}})
                f = parse_query(query); f["dish"] = detect_dish(KB, query)
                cs = candidates(KB, query, f, limit=int(q.get("limit", ["8"])[0]))
                return self._j(200, {"results": [place_result(c) for c in cs],
                                     "meta": {"query": query,
                                              "filters": {k: v for k, v in f.items() if v},
                                              "count": len(cs)}})
            if u.path == "/v1/assistant":
                query = unquote(q.get("q", [""])[0])
                use = os.environ.get("GEMINI_API_KEY") is not None
                return self._j(200, answer(KB, query, use_llm=use))
            if u.path == "/v1/poi":
                rid = q.get("id", [""])[0].upper()
                p = next((x for x in KB["pois"] if x["restaurant_id"] == rid), None)
                if not p:
                    return self._j(404, {"error": {"code": "not_found",
                                                   "message": f"không có {rid}"}})
                return self._j(200, p)
            if u.path == "/health":
                return self._j(200, {"status": "ok", **KB["meta"]})
            self._j(404, {"error": {"code": "not_found", "message": u.path}})
        except Exception as e:
            self._j(500, {"error": {"code": "internal_error", "message": str(e)}})

    def log_message(self, *a): pass

if __name__ == "__main__":
    print("http://localhost:8000/health")
    print("http://localhost:8000/v1/search?q=Bún chả")
    print("http://localhost:8000/v1/assistant?q=Crystal BBQ có gì ngon")
    HTTPServer(("0.0.0.0", 8000), H).serve_forever()

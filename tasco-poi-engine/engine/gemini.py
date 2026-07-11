"""
gemini.py — Gemini client DÙNG CHUNG. Zero dependency (urllib stdlib).

Đây là NÚT THẮT DUY NHẤT của team: P1 và P2 đều cần file này.
Nó đã viết sẵn -> KHÔNG AI PHẢI CHỜ AI. Bắt đầu song song ngay từ phút 0.

  from engine.gemini import gen, gen_json, gen_vision, batch

Tính năng:
  - gen()        text -> text
  - gen_json()   text -> dict, ÉP JSON schema (không parse free-text)
  - gen_vision() ảnh  -> text/dict
  - batch()      chạy song song N prompt (thread), có retry + backoff
  - CACHE ĐĨA    mọi call cache theo hash. Chạy lần 2 = 0 giây, 0 quota.
                 -> Demo trên sân khấu KHÔNG gọi mạng. Wifi hội trường không giết được bạn.

Env:
  GEMINI_API_KEY   bắt buộc (nếu thiếu -> gen() trả None, caller fallback offline)
  GEMINI_MODEL     mặc định gemini-2.0-flash
  GEMINI_CACHE     'on' (mặc định) | 'off' | 'refresh'
"""
from __future__ import annotations
import os, json, time, hashlib, pathlib, base64
import urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor

MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
KEY = os.environ.get("GEMINI_API_KEY")
CACHE_MODE = os.environ.get("GEMINI_CACHE", "on")
CACHE = pathlib.Path(__file__).resolve().parent.parent / "build" / "gemini_cache"
BASE = "https://generativelanguage.googleapis.com/v1beta/models"


def _key(payload: dict) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()[:16]


def _cache_get(k: str):
    if CACHE_MODE != "on":
        return None
    f = CACHE / f"{k}.json"
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))["response"]
    return None


def _cache_put(k: str, payload: dict, response):
    if CACHE_MODE == "off":
        return
    CACHE.mkdir(parents=True, exist_ok=True)
    (CACHE / f"{k}.json").write_text(
        json.dumps({"request": payload, "response": response,
                    "cached_at": time.strftime("%Y-%m-%dT%H:%M:%S")},
                   ensure_ascii=False, indent=1), encoding="utf-8")


def _call(payload: dict, retries: int = 3):
    """Trả về text, hoặc None nếu hỏng. KHÔNG BAO GIỜ raise — caller phải fallback được."""
    k = _key(payload)
    hit = _cache_get(k)
    if hit is not None:
        return hit
    if not KEY:
        return None

    url = f"{BASE}/{MODEL}:generateContent?key={KEY}"
    body = json.dumps(payload).encode()

    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                url, data=body, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.loads(r.read())
            text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            _cache_put(k, payload, text)
            return text
        except urllib.error.HTTPError as e:
            code = e.code
            if code in (429, 500, 503) and attempt < retries - 1:
                wait = 2 ** attempt * 2          # 2s, 4s, 8s
                print(f"  [gemini {code} -> retry sau {wait}s]")
                time.sleep(wait)
                continue
            print(f"  [gemini HTTP {code}] {e.read()[:200]!r}")
            return None
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
                continue
            print(f"  [gemini fail] {e}")
            return None
    return None


# ------------------------------------------------------------------ public

def gen(prompt: str, temperature: float = 0.2, max_tokens: int = 1200) -> str | None:
    return _call({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens},
    })


def gen_json(prompt: str, schema: dict, temperature: float = 0.0) -> dict | list | None:
    """ÉP structured output. Không bao giờ parse free-text bằng regex.

    schema ví dụ:
      {"type":"ARRAY","items":{"type":"OBJECT","properties":{
         "dish_name":{"type":"STRING"},"price_vnd":{"type":"INTEGER"}},
         "required":["dish_name","price_vnd"]}}
    """
    txt = _call({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": 4096,
            "responseMimeType": "application/json",
            "responseSchema": schema,
        },
    })
    if not txt:
        return None
    try:
        return json.loads(txt)
    except json.JSONDecodeError:
        # Gemini thi thoảng bọc ```json — gỡ ra
        t = txt.strip().removeprefix("```json").removeprefix("```").removesuffix("```")
        try:
            return json.loads(t.strip())
        except Exception:
            print(f"  [gen_json: không parse được] {txt[:120]!r}")
            return None


def gen_vision(prompt: str, image_path: str, mime: str = "image/jpeg",
               schema: dict | None = None):
    """Ảnh menu -> text hoặc JSON. Dùng cho câu 2 benchmark (Menu Extraction)."""
    b64 = base64.b64encode(pathlib.Path(image_path).read_bytes()).decode()
    cfg = {"temperature": 0.0, "maxOutputTokens": 4096}
    if schema:
        cfg |= {"responseMimeType": "application/json", "responseSchema": schema}
    txt = _call({
        "contents": [{"parts": [
            {"inline_data": {"mime_type": mime, "data": b64}},
            {"text": prompt},
        ]}],
        "generationConfig": cfg,
    })
    if txt and schema:
        try:
            return json.loads(txt)
        except Exception:
            return None
    return txt


def batch(prompts: list[str], workers: int = 6, schema: dict | None = None) -> list:
    """Chạy song song. 150 review / 179 món xong trong ~30 giây thay vì 10 phút.

    Cache-first nên chạy lại lần 2 là 0 giây, 0 quota.
    """
    fn = (lambda p: gen_json(p, schema)) if schema else gen
    with ThreadPoolExecutor(max_workers=workers) as ex:
        return list(ex.map(fn, prompts))


def cache_stats() -> dict:
    n = len(list(CACHE.glob("*.json"))) if CACHE.exists() else 0
    return {"cached_calls": n, "mode": CACHE_MODE, "model": MODEL, "key_set": bool(KEY)}


if __name__ == "__main__":
    print("gemini client:", cache_stats())
    if KEY:
        print("test:", gen("Trả lời đúng 3 từ: bạn có hoạt động không?"))
    else:
        print("GEMINI_API_KEY chưa set -> mọi call trả None, hệ thống tự fallback offline.")

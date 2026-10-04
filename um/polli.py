"""Game assets from pollinations (https://gen.pollinations.ai): plain REST, no SDK needed.

Default recipes are the FREE-TIER image + 3d ones (no paid pollen):
    um polli image  "a rusty scrap drone enemy, side view facing left, 16-bit pixel art" --aspect 1:1
    um polli sprite "a rusty scrap drone enemy" --name drone
    um polli edit   "same drone, rotors blurred, second animation frame" --ref assets/gen/drone.png
    um polli 3d     assets/gen/drone.png --name drone          # -> textured GLB (microsoft/trellis-2)
    um polli rmbg   in.png                                     # transparent PNG (free, no pollen)
    um polli upscale in.png                                    # free, no pollen

Audio + video bill the PAID wallet, so they are OFF by default. They need an explicit
spend gate plus a pollen cap:
    um polli sfx   "laser rifle shot, sci-fi, punchy" --seconds 1.5 --yes-spend
    um polli music "tense boss battle, chiptune, 140 bpm" --seconds 30 --yes-spend --max-pollen 0.2
    um polli voice "You dare challenge the Mothership?" --voice-id Adam --yes-spend
    um polli video assets/gen/drone.png "camera orbits the boss" --seconds 4 --yes-spend --max-pollen 0.5

Model ids: `um polli models [--category image]`. Defaults: image/sprite/edit = openai/gpt-image-2,
3d = microsoft/trellis-2, sfx/music/voice = elevenlabs, video = bytedance/seedance-2.5.
Pass `--model google/gemini-3.1-flash-image` (or the alias `gemini`) to switch image models.

Key: env POLLINATIONS_API_KEY, else the 'pollinations' entry in the opencode auth.json.
Every call appends a line to <out>/polli_manifest.jsonl so an asset can be traced.
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from um.common import die

BASE = "https://gen.pollinations.ai"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) HeadlessChrome/150.0.0.0 Safari/537.36"

MODELS = {
    "image": "openai/gpt-image-2",
    "sprite": "openai/gpt-image-2",
    "edit": "openai/gpt-image-2",
    "3d": "microsoft/trellis-2",
    "sfx": "elevenlabs/eleven-text-to-sound-v2",
    "music": "elevenlabs/music-v2.5",
    "voice": "elevenlabs/eleven-v3",
    "video": "bytedance/seedance-2.5",
}
ALIASES = {
    "gpt-image-2": "openai/gpt-image-2", "gpt-image": "openai/gpt-image-2",
    "gemini": "google/gemini-3.1-flash-image", "gemini-flash": "google/gemini-3.1-flash-image",
    "gemini-3.1-flash-image": "google/gemini-3.1-flash-image", "nano-banana-2": "google/gemini-3.1-flash-image",
    "trellis": "microsoft/trellis-2", "trellis-2": "microsoft/trellis-2",
    "rodin": "hyper3d/rodin-2.5", "hyper3d": "hyper3d/rodin-2.5",
    "asset-harvester": "nvidia/asset-harvester",
    "seedance": "bytedance/seedance-2.5", "seedance-2.5": "bytedance/seedance-2.5",
    "eleven": "elevenlabs/eleven-v3", "eleven-v3": "elevenlabs/eleven-v3",
}
SPRITE_STYLE = ("a single game sprite, the whole subject in frame and centered, clean readable silhouette, "
                "no text, no watermark, no ground shadow, no background scenery, on a plain flat white background")
ASPECT = {"1:1": (1024, 1024), "16:9": (1344, 768), "9:16": (768, 1344), "4:3": (1152, 864),
          "3:4": (864, 1152), "3:2": (1216, 832), "2:3": (832, 1216), "21:9": (1536, 640)}
# flat pollen estimates (pollen ~ usd); only used to gate spending, never to block free recipes
COST_PER_SEC = {"sfx": 0.002, "music": 0.0025, "video": 0.1028}

FREE_TOOLS = {
    "rmbg": {"host": "bgeraser.com", "up": "/api/bgeraser/legacy/upload", "st": "/api/bgeraser/legacy/status",
             "fields": {"type": "4", "mattValue": "0"}, "page": "https://bgeraser.com", "status_body": "codes"},
    "upscale": {"host": "imgupscaler.com", "up": "/api/legacy/upload", "st": "/api/legacy/status",
                "fields": {"type": "4"}, "page": "https://imgupscaler.com", "status_body": "taskId"},
}


# --------------------------------------------------------------------------- key

def polli_key(required: bool = True) -> str | None:
    k = os.environ.get("POLLINATIONS_API_KEY") or os.environ.get("POLLINATIONS_KEY")
    if not k:
        home = Path.home()
        xdg = Path(os.environ.get("XDG_DATA_HOME", home / ".local" / "share"))
        candidates = [
            xdg / "opencode" / "auth.json",
            Path(os.environ.get("APPDATA", "")) / "opencode" / "auth.json",
            Path(os.environ.get("LOCALAPPDATA", "")) / "opencode" / "auth.json",
        ]
        for c in candidates:
            try:
                data = json.loads(Path(c).read_text(encoding="utf-8"))
                entry = data.get("pollinations") or data.get("pollinations_enter") or data.get("pollinations_api_key")
                k = entry.get("key") if isinstance(entry, dict) else entry
                if k:
                    break
            except Exception:
                pass
    if not k and required:
        die("no pollinations key. set POLLINATIONS_API_KEY, or add a 'pollinations' key to the opencode auth.json")
    return k


# --------------------------------------------------------------------------- http + files

def _req(method: str, url: str, key: str | None = None, body=None, headers=None, timeout: int = 600, retries: int = 3):
    h = {"User-Agent": "universal-modder", "Accept": "*/*", **(headers or {})}
    if key:
        h["Authorization"] = "Bearer " + key
    data = body
    if isinstance(body, dict):
        data = json.dumps(body).encode()
        h.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read(), dict(r.headers)
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")[:1500]
            if e.code in (429, 500, 502, 503, 504) and attempt < retries:
                time.sleep(2 * (attempt + 1))
                continue
            die(f"pollinations {method} {url.split('?')[0]} -> HTTP {e.code}: {detail}")
        except urllib.error.URLError as e:
            if attempt < retries:
                time.sleep(2 * (attempt + 1))
                continue
            die(f"pollinations {method} {url.split('?')[0]}: {e.reason}")


def _multipart(fields: dict, files: list):
    boundary = "----um" + os.urandom(12).hex()
    out = bytearray()
    for k, v in fields.items():
        out += f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
    for name, fn, ct, data in files:
        out += f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"; filename="{fn}"\r\nContent-Type: {ct}\r\n\r\n'.encode()
        out += data + b"\r\n"
    out += f"--{boundary}--\r\n".encode()
    return boundary, bytes(out)


def sniff_ext(b: bytes) -> str:
    if b[:3] == b"\xff\xd8\xff":
        return ".jpg"
    if b[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png"
    if b[:4] == b"RIFF" and b[8:12] == b"WEBP":
        return ".webp"
    if b[:4] == b"GIF8":
        return ".gif"
    if b[:4] == b"glTF":
        return ".glb"
    if b[:4] == b"RIFF" and b[8:12] == b"WAVE":
        return ".wav"
    if b[:3] == b"ID3" or b[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"):
        return ".mp3"
    if b[4:8] == b"ftyp":
        return ".mp4"
    return ".bin"


def save_bytes(data: bytes, out, stem: str, ext: str | None = None) -> Path:
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    ext = ext or sniff_ext(data)
    p = out / f"{stem}{ext}"
    n = 1
    while p.exists():
        n += 1
        p = out / f"{stem}_{n}{ext}"
    p.write_bytes(data)
    return p


def manifest(out, rec: dict):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    rec = {"t": time.strftime("%Y-%m-%dT%H:%M:%S"), **rec}
    with open(out / "polli_manifest.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")


def _norm_urls(d) -> list:
    if isinstance(d, list):
        return [str(u).strip() for u in d if u and str(u).strip()]
    if isinstance(d, dict):
        return [str(u).strip() for u in d.values() if u and str(u).strip()]
    return []


# --------------------------------------------------------------------------- upload (for 3d / video refs)

def upload_litterbox(p: Path) -> str:
    mime = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
    boundary, body = _multipart({"reqtype": "fileupload", "time": "1h"},
                                [("fileToUpload", p.name, mime, p.read_bytes())])
    res, _ = _req("POST", "https://litterbox.catbox.moe/resources/internals/api.php", body=body,
                  headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}, timeout=180)
    url = res.decode(errors="replace").strip()
    if not url.startswith("http"):
        die(f"litterbox upload failed: {url[:200]}")
    return url


def to_url(v: str) -> str:
    if re.match(r"^https?://", v):
        return v
    p = Path(v)
    if not p.is_file():
        die(f"no such file: {p}")
    print(f"  uploading {p.name} -> litterbox...", file=sys.stderr)
    return upload_litterbox(p)


# --------------------------------------------------------------------------- generators

def _name(args, fallback: str) -> str:
    if getattr(args, "name", None):
        return args.name
    words = re.sub(r"[^a-z0-9 ]", "", fallback.lower()).split()[:5]
    return "_".join(words) or "asset"


def _kv(pairs) -> dict:
    out = {}
    for p in pairs or []:
        if ":=" in p:
            k, v = p.split(":=", 1)
            out[k] = json.loads(v)
        elif "=" in p:
            k, v = p.split("=", 1)
            out[k] = v
        else:
            die(f"bad --set {p!r}: use K=V or K:=json")
    return out


def _wh(args) -> tuple:
    if getattr(args, "width", None) and getattr(args, "height", None):
        return args.width, args.height
    return ASPECT.get(getattr(args, "aspect", "1:1"), (1024, 1024))


def _gate(args, est: float, what: str):
    if not getattr(args, "yes_spend", False):
        die(f"{what} bills your PAID pollinations wallet (est ~{est:.4f} pollen).\n"
            f"  re-run with --yes-spend once you are ok with it, e.g. add:  --yes-spend --max-pollen {max(est, 0.05):.2f}")
    cap = getattr(args, "max_pollen", None)
    if cap is not None and est > cap:
        die(f"{what}: estimated {est:.4f} pollen exceeds --max-pollen {cap}. lower the request or raise the cap.")
    print(f"  spending ~{est:.4f} pollen ({what})...", file=sys.stderr)


def gen_image(prompt: str, model: str, out, name: str, w: int, h: int, seed, extra: dict, key: str, n: int = 1):
    for i in range(n):
        params = {"model": model, "width": str(w), "height": str(h), "nologo": "true", "private": "true"}
        if seed is not None:
            params["seed"] = str(seed + i if n > 1 else seed)
        for k, v in extra.items():
            params[k] = str(v)
        url = f"{BASE}/image/{urllib.parse.quote(prompt)}?{urllib.parse.urlencode(params)}"
        data, headers = _req("GET", url, key=key, timeout=600)
        ext = sniff_ext(data)
        if ext not in (".jpg", ".png", ".webp", ".gif"):
            die(f"image: unexpected bytes {data[:16]!r}")
        p = save_bytes(data, out, name if n == 1 else f"{name}_{i + 1}", ext)
        print(p)
        manifest(out, {"recipe": "image", "model": headers.get("x-model-used") or model,
                       "prompt": prompt, "seed": params.get("seed"), "file": str(p), "input": params})


def gen_edit(prompt: str, refs: list, model: str, out, name: str, seed, key: str):
    urls = [to_url(r) for r in refs]
    params = {"model": model, "image": ",".join(urls), "nologo": "true", "private": "true"}
    if seed is not None:
        params["seed"] = str(seed)
    url = f"{BASE}/image/{urllib.parse.quote(prompt)}?{urllib.parse.urlencode(params)}"
    data, headers = _req("GET", url, key=key, timeout=600)
    ext = sniff_ext(data)
    if ext not in (".jpg", ".png", ".webp", ".gif"):
        die(f"edit: unexpected bytes {data[:16]!r}")
    p = save_bytes(data, out, name, ext)
    print(p)
    manifest(out, {"recipe": "edit", "model": headers.get("x-model-used") or model,
                   "prompt": prompt, "refs": urls, "file": str(p)})


def gen_3d(image: str, model: str, out, name: str, resolution: str, seed, key: str):
    url_in = to_url(image)
    params = {"model": model, "resolution": resolution, "nologo": "true", "private": "true", "image": url_in}
    if seed is not None:
        params["seed"] = str(seed)
    url = f"{BASE}/3d/{urllib.parse.quote('3d model')}?{urllib.parse.urlencode(params)}"
    print("  generating GLB (trellis-2 can take a minute)...", file=sys.stderr)
    data, headers = _req("GET", url, key=key, timeout=1800)
    if data[:4] != b"glTF":
        die(f"3d: expected GLB, got {data[:16]!r}")
    p = save_bytes(data, out, name, ".glb")
    print(p)
    manifest(out, {"recipe": "3d", "model": headers.get("x-model-used") or model,
                   "image": url_in, "resolution": resolution, "file": str(p)})


def gen_audio(kind: str, prompt: str, model: str, out, name: str, seconds, voice, key: str):
    params = {"model": model, "nologo": "true", "private": "true"}
    if kind == "music":
        params["duration"] = str(int(seconds))
    elif kind == "sfx":
        params["duration"] = str(seconds)
    elif kind == "voice":
        params["voice"] = voice or "Adam"
    url = f"{BASE}/audio/{urllib.parse.quote(prompt)}?{urllib.parse.urlencode(params)}"
    data, headers = _req("GET", url, key=key, timeout=600)
    ext = sniff_ext(data)
    if ext not in (".mp3", ".wav", ".ogg"):
        die(f"{kind}: unexpected bytes {data[:16]!r}")
    p = save_bytes(data, out, name, ext)
    print(p)
    manifest(out, {"recipe": kind, "model": headers.get("x-model-used") or model,
                   "prompt": prompt, "file": str(p), "input": params})


def gen_video(prompt: str, model: str, out, name: str, seconds: float, image, w: int, h: int, key: str):
    params = {"model": model, "nologo": "true", "private": "true",
              "duration": str(seconds), "width": str(w), "height": str(h)}
    if image:
        params["image"] = to_url(image)
    url = f"{BASE}/video/{urllib.parse.quote(prompt)}?{urllib.parse.urlencode(params)}"
    print("  generating video (this can take a while)...", file=sys.stderr)
    data, headers = _req("GET", url, key=key, timeout=1800)
    ext = sniff_ext(data)
    if ext != ".mp4":
        die(f"video: expected mp4, got {data[:16]!r}")
    p = save_bytes(data, out, name, ext)
    print(p)
    manifest(out, {"recipe": "video", "model": headers.get("x-model-used") or model,
                   "prompt": prompt, "file": str(p), "input": params})


# --------------------------------------------------------------------------- free tools (rmbg / upscale)

def free_image_tool(tool: str, image: str, out, name: str):
    t = FREE_TOOLS[tool]
    p = Path(image)
    if not p.is_file():
        die(f"no such file: {p}")
    mime = mimetypes.guess_type(p.name)[0] or "image/jpeg"
    boundary, body = _multipart(t["fields"], [("file", p.name, mime, p.read_bytes())])
    hdrs = {"User-Agent": UA, "Origin": f"https://{t['host']}", "Referer": t["page"],
            "Content-Type": f"multipart/form-data; boundary={boundary}"}
    print(f"  {tool}: uploading {p.name}...", file=sys.stderr)
    res, _ = _req("POST", f"https://{t['host']}{t['up']}", body=body, headers=hdrs, timeout=120)
    j = json.loads(res)
    urls = _norm_urls(j.get("downloadUrls"))
    if not urls:
        code = j.get("code") or j.get("taskId") or j.get("taskCode") or (j.get("data") or {}).get("code")
        if not code:
            die(f"{tool}: no task code in {str(j)[:200]}")
        hdrs2 = {"User-Agent": UA, "Origin": f"https://{t['host']}", "Referer": t["page"],
                 "Content-Type": "application/json"}
        for _ in range(30):
            time.sleep(5)
            sbody = {"type": 4, "codes": [str(code)]} if t["status_body"] == "codes" else {"taskId": str(code)}
            res2, _ = _req("POST", f"https://{t['host']}{t['st']}", body=json.dumps(sbody).encode(),
                           headers=hdrs2, timeout=60)
            st = json.loads(res2)
            urls = _norm_urls(st.get("downloadUrls"))
            if urls:
                break
            if st.get("status") == "failed":
                die(f"{tool} failed: {str(st)[:200]}")
    if not urls:
        die(f"{tool}: timed out waiting for a result")
    u = urls[0]
    if not u.startswith("http"):
        u = f"https://{t['host']}/{u.lstrip('/')}"
    data, _ = _req("GET", u, timeout=300)
    p2 = save_bytes(data, out, name, ".png")
    print(p2)
    manifest(out, {"recipe": tool, "provider": t["host"], "file": str(p2)})


# --------------------------------------------------------------------------- commands

def list_models(category, filt):
    data, _ = _req("GET", f"{BASE}/models", timeout=60)
    models = json.loads(data)
    if isinstance(models, dict):
        models = models.get("data", [])
    for m in models:
        if category and m.get("category") != category:
            continue
        hay = f"{m.get('name', '')} {m.get('title', '')}"
        if filt and filt.lower() not in hay.lower():
            continue
        print(f"{m.get('name', ''):48} {m.get('category', ''):10} {m.get('title', '')}")


def cmd(args):
    r = args.recipe
    out = getattr(args, "out", "assets/gen")
    extra = _kv(getattr(args, "set", None))
    model = getattr(args, "model", None)
    model = ALIASES.get(model, model) if model else None

    if r == "balance":
        print(json.dumps(get_balance(polli_key(True)), indent=2))
        return
    if r == "models":
        list_models(getattr(args, "category", None), getattr(args, "filter", None))
        return

    key = polli_key(True)
    if r == "image":
        w, h = _wh(args)
        gen_image(args.prompt, model or MODELS["image"], out, _name(args, args.prompt), w, h, args.seed, extra, key, args.n)
    elif r == "sprite":
        w, h = _wh(args)
        gen_image(f"{args.prompt}. {SPRITE_STYLE}", model or MODELS["sprite"], out, _name(args, args.prompt), w, h,
                  args.seed, extra, key, args.n)
    elif r == "edit":
        gen_edit(args.prompt, args.ref, model or MODELS["edit"], out, _name(args, args.prompt), args.seed, key)
    elif r == "3d":
        gen_3d(args.image, model or MODELS["3d"], out, args.name or Path(args.image).stem, args.resolution, args.seed, key)
    elif r in ("rmbg", "upscale"):
        free_image_tool(r, args.image, out, args.name or f"{Path(args.image).stem}_{r}")
    elif r == "sfx":
        est = COST_PER_SEC["sfx"] * args.seconds
        _gate(args, est, "sfx")
        gen_audio("sfx", args.prompt, model or MODELS["sfx"], out, _name(args, args.prompt), args.seconds, None, key)
    elif r == "music":
        est = COST_PER_SEC["music"] * args.seconds
        _gate(args, est, f"music (~{args.seconds:g}s; duration support varies by model)")
        gen_audio("music", args.prompt, model or MODELS["music"], out, _name(args, args.prompt), args.seconds, None, key)
    elif r == "voice":
        est = max(len(args.text) / 4, 1) * 0.0001
        _gate(args, est, "voice")
        gen_audio("voice", args.text, model or MODELS["voice"], out, _name(args, args.text), None, args.voice_id, key)
    elif r == "video":
        est = COST_PER_SEC["video"] * args.seconds
        _gate(args, est, "video")
        w, h = ASPECT.get(args.aspect, (1920, 1080))
        gen_video(args.prompt, model or MODELS["video"], out, args.name or "video", args.seconds, args.image, w, h, key)


def get_balance(key):
    try:
        b, _ = _req("GET", f"{BASE}/account/balance", key=key, timeout=30)
        return json.loads(b)
    except SystemExit:
        return None


def register(sub):
    p = sub.add_parser("polli", help="generate game assets with pollinations (image, 3d, audio, video)",
                       description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    rs = p.add_subparsers(dest="recipe", metavar="<recipe>")

    def recipe(name, help_, *positional, out=True, spend=False):
        q = rs.add_parser(name, help=help_)
        for pos in positional:
            q.add_argument(pos)
        if out:
            q.add_argument("--out", default="assets/gen", help="output folder (default assets/gen)")
            q.add_argument("--name", help="output file stem")
            q.add_argument("--model", help="override the model (alias or full id)")
            q.add_argument("--set", action="append", metavar="K=V", help="extra model input (repeatable; K:=json)")
        if spend:
            q.add_argument("--yes-spend", action="store_true", help="confirm this bills the PAID wallet")
            q.add_argument("--max-pollen", type=float, help="refuse if the cost estimate exceeds this")
        q.set_defaults(func=cmd)
        return q

    b = rs.add_parser("balance", help="show pollen balance"); b.set_defaults(func=cmd)
    m = rs.add_parser("models", help="list pollinations models")
    m.add_argument("--category"); m.add_argument("--filter"); m.set_defaults(func=cmd)

    q = recipe("image", "text -> image (openai/gpt-image-2 by default; free tier)", "prompt")
    q.add_argument("--aspect", default="1:1"); q.add_argument("--width", type=int); q.add_argument("--height", type=int)
    q.add_argument("--seed", type=int); q.add_argument("--n", type=int, default=1)
    q = recipe("sprite", "text -> game sprite on a flat background (gpt-image-2)", "prompt")
    q.add_argument("--aspect", default="1:1"); q.add_argument("--width", type=int); q.add_argument("--height", type=int)
    q.add_argument("--seed", type=int); q.add_argument("--n", type=int, default=1)
    q = recipe("edit", "edit / make variants from reference image(s)", "prompt")
    q.add_argument("--ref", action="append", required=True, help="reference image path or url (repeatable)")
    q.add_argument("--seed", type=int)
    q = recipe("3d", "image -> textured GLB (microsoft/trellis-2)", "image")
    q.add_argument("--resolution", default="low", choices=["low", "medium", "high"]); q.add_argument("--seed", type=int)
    q = recipe("rmbg", "remove the background -> transparent PNG (free, no pollen)", "image")
    q = recipe("upscale", "upscale an image (free, no pollen)", "image")

    q = recipe("sfx", "sound effect (PAID)", "prompt", spend=True); q.add_argument("--seconds", type=float, default=1.5)
    q = recipe("music", "music track (PAID)", "prompt", spend=True); q.add_argument("--seconds", type=float, default=30)
    q = recipe("voice", "text -> speech (PAID)", "text", spend=True); q.add_argument("--voice-id", default="Adam")
    q = recipe("video", "image + text -> video (PAID)", "image", "prompt", spend=True)
    q.add_argument("--seconds", type=float, default=4); q.add_argument("--aspect", default="16:9")

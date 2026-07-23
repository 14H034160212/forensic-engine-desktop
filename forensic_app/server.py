#!/usr/bin/env python3
"""
Forensic Engine — real web application.
Upload a pitch deck (PDF/DOCX/text) → the blind 2-pass prosecution + unit-economics
engine runs live on local hardware → polished interactive report. Cross-document
conflict detection, run history, and PDF export. Zero external calls.

Run:  cd forensic_app && uvicorn server:app --host 127.0.0.1 --port 8800
Open: http://127.0.0.1:8800/   (SSH-tunnel the port for a private remote demo)
"""
import os, sys, json, time, threading, datetime, io, queue, subprocess, re
# Resource dir (read-only bundled files) vs data dir (writable). Frozen-aware so the same
# server runs from source AND inside a PyInstaller/Tauri native bundle.
if getattr(sys, "frozen", False):
    HERE = os.path.join(sys._MEIPASS, "forensic_app")                 # bundled resources
    _DATA = os.path.join(os.path.expanduser("~"), ".forensic_engine") # user-writable
else:
    HERE = os.path.dirname(os.path.abspath(__file__))
    _DATA = HERE
sys.path.insert(0, os.path.join(HERE, "..", "local_engine"))
import prosecution_engine as E
import reasoning_excavation as RE
import trigger_packs as T
import parsing

from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import (HTMLResponse, JSONResponse, StreamingResponse,
                               Response, FileResponse)

RUNS = os.path.join(_DATA, "runs")
os.makedirs(RUNS, exist_ok=True)
RUN_LOCK = threading.Lock()
_RUN_AT = [0.0]                 # when the current holder acquired it
RUN_STALE_SECS = 900           # a run holding the lock longer than this is presumed dead → reclaim it
def _acquire_run():
    """Non-blocking acquire with a stale-lock safety net: if a previous run hung/died without releasing
    (e.g. a stalled Ollama call), don't lock the app out forever — reclaim the lock once it's clearly stale."""
    import time as _t
    if RUN_LOCK.acquire(blocking=False):
        _RUN_AT[0] = _t.time(); return True
    if _t.time() - _RUN_AT[0] > RUN_STALE_SECS:      # held too long → previous run is dead; steal it
        try: RUN_LOCK.release()
        except RuntimeError: pass
        if RUN_LOCK.acquire(blocking=False):
            _RUN_AT[0] = _t.time(); return True
    return False
MODELS = [m.strip() for m in os.environ.get(
    "MODELS", "qwen2.5-coder:7b,qwen2.5-coder:32b,L3370B:latest").split(",") if m.strip()]

# Routed domain trigger-packs (the encoded-expertise rulebook) lift recall from ~15% to ~75% on the
# internal benchmark and are the Core IP. Gated by USE_PACKS (default OFF so source behaviour is
# unchanged); the packaged app's entry.py sets USE_PACKS=1. Router-gated + precision-guarded, so safe.
USE_PACKS = os.environ.get("USE_PACKS", "0").strip().lower() not in ("0", "false", "no", "")

def _set_model(model):
    """Select the engine model and its matching native-thinking mode. Routing rule shared with the eval
    harness via prosecution_engine.wants_thinking (single source of truth)."""
    E.LLM = model
    os.environ["OLLAMA_THINK"] = "true" if E.wants_thinking(model) else "false"

app = FastAPI(title="Forensic Engine")

# ----------------------------------------------------------------- helpers
def _coerce(fs):
    for f in fs:
        v = f.get("load_bearing")
        f["load_bearing"] = (v.strip().lower() in ("true", "yes", "1")) if isinstance(v, str) else (v is True)
    return fs

def verify_excavation(res, on_stage=None):
    """Re-check the LLM-proposed Step-3 contradiction bonds with the NLI logic verifier and
    tag each one real / duplicate / weak. Graceful no-op if the verifier can't load (e.g. a
    laptop with no torch) — then the raw bonds are shown as before. The heavy AMR-LDA
    equivalence layer stays OFF here (USE_AMR unset); this is the fast CPU/GPU NLI pass only."""
    bonds = res.get("contradictions") or []
    if not bonds:
        return
    try:
        import logic_verifier as LV
    except Exception:
        res["verified"] = False
        return
    if on_stage:
        on_stage("verify", f"Verifying {len(bonds)} contradiction bonds (logic NLI)...")
    try:
        r = LV.verify_contradictions(res)
    except Exception:
        res["verified"] = False
        return
    vmap = {(p["from"], p["to"]): p for p in r["pairs"]}
    for b in bonds:
        p = vmap.get((b.get("from"), b.get("to")))
        if p:
            b["verifier"] = p["verifier"]
            b["verdict"] = ("real" if p["confirmed"] else
                            "duplicate" if p["verifier"] == "equivalent" else "weak")
    res["verified"] = True
    res["verification"] = {"confirmed": r["verifier_confirmed"],
                           "rejected": r["false_positives"],
                           "duplicates": r["of_which_duplicates"]}

def _save_run(result):
    rid = datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + \
          "".join(c for c in (result.get("label") or "run").lower() if c.isalnum())[:20]
    result["id"] = rid
    result["created"] = datetime.datetime.now().isoformat(timespec="seconds")
    json.dump(result, open(os.path.join(RUNS, rid + ".json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return rid

# ----------------------------------------------------------------- pages
@app.get("/", response_class=HTMLResponse)
def index():
    return open(os.path.join(HERE, "static", "index.html"), encoding="utf-8").read()

@app.get("/report", response_class=HTMLResponse)
def report():
    return open(os.path.join(HERE, "static", "report.html"), encoding="utf-8").read()

@app.get("/laptop", response_class=HTMLResponse)
def laptop():
    return open(os.path.join(HERE, "static", "laptop.html"), encoding="utf-8").read()

@app.get("/leaderboard", response_class=HTMLResponse)
def leaderboard():
    return open(os.path.join(HERE, "static", "leaderboard.html"), encoding="utf-8").read()

@app.get("/api/setup")
def setup_status():
    """First-run auto-setup progress (Ollama install + default-model pull), written by entry.py."""
    try:
        return json.load(open(os.path.join(_DATA, "setup.json"), encoding="utf-8"))
    except Exception:
        return {"stage": "unknown", "done": True}

@app.get("/laptop.pdf")
def laptop_pdf():
    html = open(os.path.join(HERE, "static", "laptop.html"), encoding="utf-8").read()
    try:
        from weasyprint import HTML
        return Response(HTML(string=html).write_pdf(), media_type="application/pdf",
                        headers={"Content-Disposition": 'attachment; filename="laptop-feasibility.pdf"'})
    except Exception as e:
        return HTMLResponse(html + f"<!-- pdf unavailable: {e} -->")

@app.get("/local_deploy.zip")
def local_deploy_zip():
    """The full local-deploy bundle (app + engine + samples + launchers + CLAUDE.md)."""
    p = os.path.join(HERE, "download", "local_deploy.zip")
    if not os.path.exists(p):
        return JSONResponse({"error": "bundle not built"}, status_code=404)
    return FileResponse(p, media_type="application/zip", filename="local_deploy.zip")

# fixed upstream that publishes the latest build (this same demo server)
UPDATE_SOURCE = os.environ.get("UPDATE_SOURCE", "https://chivalry-premises-ferocity.ngrok-free.dev")

def _local_version():
    try:
        return open(os.path.join(HERE, "VERSION"), encoding="utf-8").read().strip()
    except Exception:
        return "unknown"

@app.get("/api/version")
def version():
    """This install's version — also the source-of-truth 'latest' when hit on the demo server."""
    return {"version": _local_version(), "source": UPDATE_SOURCE}

@app.get("/api/update-check")
def update_check():
    """Ask the upstream demo server for the latest version and compare. Graceful when offline:
    returns available=False / latest=None rather than erroring."""
    cur = _local_version()
    if UPDATE_SOURCE.rstrip("/").endswith("chivalry-premises-ferocity.ngrok-free.dev") and _is_self():
        return {"current": cur, "latest": cur, "available": False, "self": True}
    latest = None
    try:
        import urllib.request
        req = urllib.request.Request(UPDATE_SOURCE.rstrip("/") + "/api/version",
                                     headers={"ngrok-skip-browser-warning": "1"})
        with urllib.request.urlopen(req, timeout=4) as r:
            latest = json.loads(r.read().decode()).get("version")
    except Exception:
        return {"current": cur, "latest": None, "available": False, "offline": True}
    return {"current": cur, "latest": latest,
            "available": bool(latest and latest != cur and latest != "unknown"),
            "zip": UPDATE_SOURCE.rstrip("/") + "/local_deploy.zip"}

@app.get("/api/ollama")
def ollama_status():
    """Is the local Ollama reachable, and does it have any usable model? Drives the onboarding
    banner in the native app so a user who hasn't installed/started Ollama is told what to do."""
    base = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
    try:
        import urllib.request
        with urllib.request.urlopen(base + "/api/tags", timeout=2) as r:
            tags = json.loads(r.read().decode())
        have = [m.get("name", "") for m in tags.get("models", [])]
        wanted = [m for m in MODELS if any(h == m or h.startswith(m.split(":")[0]) for h in have)]
        return {"running": True, "models": have, "has_wanted": bool(wanted or have)}
    except Exception:
        return {"running": False, "models": [], "has_wanted": False,
                "install": "https://ollama.com/download"}

def _is_self():
    """True when this process IS the upstream (demo server) — no point checking itself."""
    return os.environ.get("IS_UPSTREAM", "").strip() in ("1", "true", "yes")

@app.get("/download", response_class=HTMLResponse)
def download():
    """Landing page: download the bundle + a copy-paste prompt to let local Claude Code deploy it."""
    return """<meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>Forensic Engine — local deploy</title>
<style>body{font-family:system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif;max-width:720px;
margin:0 auto;padding:40px 22px;line-height:1.6;color:#15212B;background:#EDF1F3}
h1{font-family:Georgia,serif;font-weight:600;font-size:28px;margin:0 0 4px}
.sub{color:#5A6B78;margin:0 0 24px}
a.btn{display:inline-block;background:#0E6E78;color:#fff;text-decoration:none;padding:12px 22px;
border-radius:8px;font-weight:600;margin:8px 0 22px}
ol{padding-left:22px} li{margin:0 0 10px}
pre{background:#10333A;color:#E7EEF0;padding:14px 16px;border-radius:8px;overflow-x:auto;font-size:13px;white-space:pre-wrap}
code{background:#dde7ea;padding:1px 6px;border-radius:3px;font-size:13px}
.zh{color:#5A6B78;font-size:14px}</style>
<a href="/" style="display:inline-block;margin-bottom:12px;font-family:ui-monospace,Menlo,Consolas,monospace;font-size:13px;color:#0E6E78;text-decoration:none">&#8592; Back to the app</a>
<h1>Forensic Engine — run it on your own laptop</h1>
<p class=sub>Downloads a self-contained bundle. Everything runs locally; nothing leaves your machine.<br>
<span class=zh>下载一个自包含部署包,整套在本机运行,数据不出你的电脑。</span></p>
<a class=btn href="/local_deploy.zip">⬇ Download local_deploy.zip</a>
<ol>
<li><b>Unzip</b> it. / <span class=zh>解压。</span></li>
<li><b>Open the <code>local_deploy</code> folder in Claude Code</b> (<code>cd local_deploy &amp;&amp; claude</code>),
then paste the prompt below. It reads <code>CLAUDE.md</code> and installs + launches everything for you.<br>
<span class=zh>用 Claude Code 打开 <code>local_deploy</code> 文件夹,粘贴下面这句话,它会读 <code>CLAUDE.md</code> 自动安装并启动。</span></li>
</ol>
<pre>Read CLAUDE.md and follow it to install and launch this Forensic Engine locally on my machine. Detect my OS, install Ollama and the Python deps if needed, start it, and open the browser. 请读 CLAUDE.md 并照做:在我本机安装并启动这个取证引擎。</pre>
<p class=sub>Prefer no AI? Follow <code>forensic_app/LAPTOP.md</code> (English) or <code>forensic_app/LAPTOP.zh.md</code> (中文) by hand — it's 4 steps.</p>"""

@app.get("/api/models")
def models():
    return {"models": MODELS}

PROFILE_LABELS = [("pitch", "Pitch deck"), ("report", "Report / analysis"),
                  ("essay", "Essay / argument"), ("proposal", "Proposal / plan"),
                  ("generic", "Generic document")]

@app.get("/api/profiles")
def profiles():
    return {"profiles": [{"id": k, "label": v} for k, v in PROFILE_LABELS]}

# --- self-calibrating time estimates -----------------------------------------------------------
# tok/s is measured on THIS machine and cached per model; workload size (tokens) is a per-kind prior.
# est ≈ expected_tokens / measured_tok_s + model-load time. A model never run here is estimated by
# scaling a measured model's speed by relative size; a totally fresh machine gets a rough accel band.
CALIB = os.path.join(_DATA, "calib.json")
TYP_TOKENS = {"deck": 4500, "excavation": 5500, "excavation_deep": 12000, "crossdoc": 3000}
# Relative runtime weight (~ time per token). MoE gpt-oss:20b runs ~3.6B active, so it's weighted
# well below its 20B nominal; dense models track their parameter count.
SPEED_WEIGHT = {"llama3.2:3b": 3, "qwen2.5-coder:7b": 7, "qwen2.5-coder:32b": 32,
                "gpt-oss:20b": 8, "gemma4:26b": 26, "L3370B:latest": 70, "deepseek-r1:32b": 32}

def _read_calib():
    try: return json.load(open(CALIB, encoding="utf-8"))
    except Exception: return {}

def _write_calib(model, kind, stats, wall_s, accel):
    try:
        c = _read_calib()
        c[model] = {"tok_s": stats["tok_s"], "gen_tokens": stats["gen_tokens"],
                    "wall_s": round(wall_s), "load_s": stats["load_seconds"],
                    "kind": kind, "accel": accel,
                    "at": datetime.datetime.now().isoformat(timespec="seconds")}
        json.dump(c, open(CALIB, "w", encoding="utf-8"), indent=2)
    except Exception:
        pass

def _fmt_dur(sec):
    if sec >= 5400: return f"~{sec/3600:.1f} h"
    if sec >= 90:   return f"~{round(sec/60)} min"
    return f"~{max(5, int(round(sec/5)*5))}s"

def _accel_from_ollama():
    """Ask Ollama what it is ACTUALLY running on — the cross-vendor truth, unlike nvidia-smi.
    A loaded model reports size_vram: >0 means it's on a GPU, ==0 means pure CPU (e.g. an AMD/Intel
    iGPU that Ollama can't offload to). Returns 'gpu' | 'cpu' | 'unknown' (nothing loaded yet)."""
    import urllib.request
    base = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
    try:
        with urllib.request.urlopen(base + "/api/ps", timeout=3) as r:
            models = json.loads(r.read().decode()).get("models", [])
        if not models:
            return "unknown", None
        vram = sum(m.get("size_vram", 0) for m in models)
        return ("gpu" if vram > 0 else "cpu"), vram
    except Exception:
        return "unknown", None

def _resolve_accel():
    """Best call on GPU- vs CPU-bound inference, CONSERVATIVE on ambiguity. Ollama's loaded-model
    size_vram is authoritative; before any model loads we fall back to platform + NVIDIA presence and
    — the fix for the AMD/no-dGPU case — default to 'cpu' rather than an optimistic 'gpu'/'unknown'
    when no accelerator is detectable. Better to over-estimate time than promise a wrong fast one."""
    a, vram = _accel_from_ollama()
    if a != "unknown":
        return a, vram
    if sys.platform == "darwin":
        return "gpu", vram                       # Apple Silicon → Metal, always GPU-accelerated
    import shutil
    if shutil.which("nvidia-smi"):
        return "gpu", vram                       # NVIDIA present → GPU
    return "cpu", vram                           # no NVIDIA on Win/Linux → almost certainly CPU-only

@app.get("/api/gpu")
def gpu():
    """Two jobs. On the shared demo server: live NVIDIA load (reflects all users). On a local laptop
    (often no NVIDIA GPU): report the real acceleration Ollama is using, WITHOUT crashing when
    nvidia-smi is absent — a missing nvidia-smi is normal (AMD/Intel/Apple), not an error. The two
    used to be one bug: nvidia-smi threw on AMD, so the app never learned it was CPU-only and showed
    GPU-calibrated time estimates that were 10–20× optimistic."""
    accel, vram = _resolve_accel()
    base = {"accel": accel, "vram_bytes": vram, "platform": sys.platform, "nvidia": False}
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5).stdout.strip()
        gpus = []
        for line in out.splitlines():
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 3:
                gpus.append({"util": int(float(parts[0])),
                             "mem_used": int(float(parts[1])),
                             "mem_total": int(float(parts[2]))})
        n = len(gpus) or 1
        free = sum(1 for g in gpus if g["util"] < 25 and g["mem_used"] < 8000)
        avg_util = round(sum(g["util"] for g in gpus) / n)
        if free >= 2:   level, status = "light", "plenty free"
        elif free == 1: level, status = "moderate", "getting busy"
        else:           level, status = "heavy", "busy"
        base.update({"gpus": len(gpus), "free": free, "level": level,
                     "status": status, "avg_util": avg_util, "nvidia": True,
                     "accel": "gpu" if accel == "unknown" else accel})
        return base
    except FileNotFoundError:
        pass                          # no NVIDIA tooling → laptop/AMD/Apple; not an error
    except Exception:
        pass
    # No NVIDIA GPU. Report acceleration so the UI can warn + show CPU-realistic estimates.
    base.update({"gpus": 0, "free": 0, "level": None, "status": "no NVIDIA GPU"})
    return base

@app.get("/api/estimate")
def estimate(model: str, kind: str = "deck", depth: str = "fast"):
    """Machine-specific time estimate for a run. Priority: (1) this exact model measured here before
    → precise; (2) another model measured here → scale by relative size; (3) nothing measured → a
    rough band from whether Ollama is on GPU or CPU. Always says which, so the number is never a
    false promise. Self-improving: every completed run rewrites calib.json."""
    accel, _ = _resolve_accel()
    calib = _read_calib()
    tok_key = "excavation_deep" if (kind == "excavation" and depth == "deep") else kind
    tokens = TYP_TOKENS.get(tok_key, 4500)
    # NOMINAL size (from the name), independent of the GPU MoE speed-weight: on CPU a 20B+ model is
    # slow regardless of active-param tricks (gpt-oss:20b measured ~3 tok/s on CPU), so flag it honestly.
    nominal_big = model.endswith(":latest") or any(t in model.lower()
                    for t in ("20b", "26b", "27b", "30b", "32b", "70b"))

    def band():
        if accel == "cpu":
            if nominal_big:
                return {"est_s": None, "text": "impractical on CPU (tens of minutes) — prefer a 3B/7B model", "source": "band-cpu", "accel": accel}
            lo = tokens / (10 if SPEED_WEIGHT.get(model, 7) <= 3 else 5)   # conservative CPU tok/s (~3B vs ~7B)
            return {"est_s": round(lo), "text": _fmt_dur(lo) + "+ on CPU (no GPU detected)", "source": "band-cpu", "accel": accel}
        return {"est_s": None, "text": None, "source": "band-gpu", "accel": accel}

    # (1) exact model measured here — always most accurate, even for a big model the user chose to run
    c = calib.get(model)
    if c and c.get("tok_s"):
        ts = c["tok_s"]
        if c.get("kind") == kind and c.get("wall_s"):
            est = c["wall_s"]
        else:
            est = tokens / ts + (c.get("load_s") or 0)
        return {"est_s": round(est), "text": _fmt_dur(est), "tok_s": ts,
                "source": "measured", "accel": c.get("accel", accel)}
    # A big model on CPU that hasn't been measured yet → be honest before the user commits to a 40-min run
    if accel == "cpu" and nominal_big:
        return {"est_s": None, "text": "impractical on CPU (tens of minutes) — prefer a 3B/7B model",
                "source": "band-cpu", "accel": accel, "refines": True}
    # (2) scale from the fastest model measured here
    ref = None
    for m, cc in calib.items():
        if cc.get("tok_s") and m in SPEED_WEIGHT and model in SPEED_WEIGHT:
            if ref is None or cc["tok_s"] > calib[ref]["tok_s"]:
                ref = m
    if ref:
        pred = calib[ref]["tok_s"] * SPEED_WEIGHT[ref] / SPEED_WEIGHT[model]
        est = tokens / pred + 8
        return {"est_s": round(est), "text": _fmt_dur(est) + f" (estimated from your {ref} speed)",
                "tok_s": round(pred, 1), "source": "scaled", "ref": ref, "accel": accel}
    # (3) nothing measured yet
    b = band(); b["refines"] = True
    return b

# ----------------------------------------------------------------- Heuristic Override demo (why-it-works)
# A live before/after: the SAME model on the SAME question, once asked plainly and once asked to first
# enumerate the implicit feasibility constraint (the engine's core mechanism). Data: HOB (Li et al. 2026,
# MIT). This is an explainer of WHY the approach works — a third-party benchmark, distinct from the product.
_HOB_PATH = os.path.join(HERE, "hob_samples.json")

def _hob_chat(model, prompt):
    import urllib.request
    base = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
    body = {"model": model, "stream": False,
            "options": {"temperature": 0, "num_ctx": 4096, "num_predict": 400},
            "messages": [{"role": "user", "content": prompt}]}
    data = json.dumps(body).encode()
    for attempt in range(3):
        try:
            req = urllib.request.Request(base + "/api/chat", data=data, headers={"Content-Type": "application/json"})
            r = json.load(urllib.request.urlopen(req, timeout=300))
            c = (r.get("message") or {}).get("content", "")
            if c and c.strip():
                return c
        except Exception:
            pass
        time.sleep(0.5 * (attempt + 1))
    return ""

def _hob_pick(text, a, b):
    m = re.findall(r"ANSWER:\s*\(?\s*([AB])\b", text or "", re.I)
    letter = (m[-1].upper() if m else None)
    if not letter:
        low = (text or "").lower(); ai, bi = low.rfind(a.lower()), low.rfind(b.lower())
        if ai != bi: letter = "A" if ai > bi else "B"
    return letter

@app.get("/api/hob/samples")
def hob_samples():
    try:
        return {"samples": json.load(open(_HOB_PATH, encoding="utf-8"))}
    except Exception:
        return {"samples": []}

@app.post("/api/hob/run")
def hob_run(payload: dict):
    """Run one heuristic-override item through the SAME model twice (plain vs constraint-enumeration)."""
    model = payload.get("model") or MODELS[0]
    goal = (payload.get("goal") or "").strip()
    q = (payload.get("question") or "").strip()
    gold = (payload.get("gold_answer") or "").strip()
    sc = (payload.get("shortcut_answer") or "").strip()
    if not (q and gold and sc):
        return JSONResponse({"error": "need question, gold_answer, shortcut_answer"}, status_code=400)
    import random as _r
    opts = [gold, sc]; _r.Random(q).shuffle(opts); a, b = opts
    head = f"{q}\n\nTwo options:\n(A) {a}\n(B) {b}\n"
    p_plain = head + f"\nWhich option achieves the stated goal \"{goal}\"? Reply with ONLY: ANSWER: A  (or)  ANSWER: B"
    p_con = (head + f"\nFirst, in one line, state the implicit real-world constraint the goal \"{goal}\" "
             f"actually requires (what must physically/logically be true). Then decide. "
             f"Final line EXACTLY: ANSWER: A  (or)  ANSWER: B")
    def one(prompt):
        raw = _hob_chat(model, prompt)
        letter = _hob_pick(raw, a, b)
        chosen = a if letter == "A" else b if letter == "B" else None
        return {"raw": raw, "choice": chosen, "correct": (chosen == gold) if chosen else None}
    plain, con = one(p_plain), one(p_con)
    return {"model": model, "gold": gold, "shortcut": sc,
            "hidden_constraint": payload.get("hidden_constraint", ""),
            "explanation": payload.get("explanation", ""),
            "plain": plain, "constraint": con}

# ----------------------------------------------------------------- Decision Graph (Tarski 2 preview)
# Turn a document into the SMALLEST navigable reasoning landscape: decision + claims + the assumptions
# they rest on + dependencies + contradictions. Rendered client-side (no server graphviz), so it works
# identically in the hosted demo and the fully-local app.
_GRAPH_SYS = ("You are a reasoning-graph extractor for a Deep Reasoning Engine. Given a document, output "
    "the SMALLEST graph that captures its load-bearing reasoning — the core decision or thesis, the key "
    "claims, the assumptions they depend on, and the dependencies and contradictions between them. "
    "Favour clarity over completeness: at most 12 nodes. Surface any SINGLE assumption that several "
    "branches secretly share (a hidden single point of failure). Output STRICT JSON only, no prose.")

def _graph_prompt(text):
    return (f"DOCUMENT:\n{text[:12000]}\n\n"
        "Return STRICT JSON with this shape:\n"
        '{"decision":"<the core decision/thesis in one line>",'
        '"nodes":[{"id":"n1","label":"<=6 words","kind":"decision|claim|assumption|risk",'
        '"detail":"one sentence, quoting the document where possible"}],'
        '"edges":[{"from":"n1","to":"n2","type":"depends|supports|contradicts"}]}\n'
        "Rules: exactly one node with kind 'decision'. 'depends'/'supports' edges point FROM the "
        "supporting claim/assumption TO what it supports (ending at the decision). 'contradicts' edges "
        "join two nodes in genuine tension (e.g. a stated comfort vs a disclosed fact). Include the "
        "load-bearing dependencies and every clear internal contradiction. 8-12 nodes is ideal.")

def _clean_graph(g):
    nodes = [n for n in (g.get("nodes") or []) if isinstance(n, dict) and n.get("id")][:16]
    ids = {n["id"] for n in nodes}
    for n in nodes:
        n["kind"] = n.get("kind") if n.get("kind") in ("decision", "claim", "assumption", "risk") else "claim"
        n["label"] = str(n.get("label") or n["id"])[:64]
        n["detail"] = str(n.get("detail") or "")[:280]
    edges = [e for e in (g.get("edges") or [])
             if isinstance(e, dict) and e.get("from") in ids and e.get("to") in ids
             and e.get("from") != e.get("to")]
    for e in edges:
        e["type"] = e.get("type") if e.get("type") in ("depends", "supports", "contradicts") else "depends"
    # mark shared-dependency single points of failure (a node ≥2 outgoing depend/support edges)
    from collections import Counter
    out = Counter(e["from"] for e in edges if e["type"] in ("depends", "supports"))
    for n in nodes:
        n["spof"] = out.get(n["id"], 0) >= 2 and n["kind"] in ("assumption", "risk")
    return {"decision": str(g.get("decision") or "")[:200], "nodes": nodes, "edges": edges}

@app.post("/api/graph/build")
def graph_build(payload: dict):
    text = (payload.get("deck") or payload.get("text") or "").strip()
    model = payload.get("model") or MODELS[0]
    if not text:
        return JSONResponse({"error": "empty document"}, status_code=400)
    if not _acquire_run():
        return JSONResponse({"error": "another analysis is running — try again in a moment"}, status_code=409)
    try:
        _set_model(model)
        for _e in _pull_events(model):
            pass
        g = E.chat_json(_GRAPH_SYS, _graph_prompt(text))
        if not isinstance(g, dict) or not g.get("nodes"):
            return JSONResponse({"error": "could not extract a graph from this document"}, status_code=422)
        out = _clean_graph(g); out["model"] = model
        return out
    finally:
        RUN_LOCK.release()

DECKS_DIR = os.path.join(HERE, "..", "local_engine", "decks")
SAMPLES = [("QuickBite", "quickbite", "Anonymised deck of a company that raised $1B and failed"),
           ("Human & the Engine", "human_and_the_engine", "An essay/argument document (not a deck) — good for the report profile")]

@app.get("/api/samples")
def samples():
    out = []
    for label, fn, desc in SAMPLES:
        p = os.path.join(DECKS_DIR, fn + ".txt")
        if os.path.exists(p):
            out.append({"label": label, "desc": desc,
                        "text": open(p, encoding="utf-8").read().strip()})
    return {"samples": out}

# ----------------------------------------------------------------- upload/parse
@app.post("/api/parse")
async def parse_files(files: list[UploadFile] = File(...)):
    out = []
    for f in files:
        data = await f.read()
        try:
            text = parsing.parse(f.filename, data)
        except Exception as e:
            text = ""
            out.append({"filename": f.filename, "error": str(e)[:200], "chars": 0, "text": ""})
            continue
        out.append({"filename": f.filename, "chars": len(text), "text": text})
    return {"documents": out}

def _pull_events(model):
    """Ensure `model` is present locally; if not, pull it, yielding {stage,msg} progress dicts.
    Keeps the one-click promise — the user never runs `ollama pull` by hand and never sees a bare
    404. A model the dropdown offers but that was never downloaded (only the default is auto-pulled
    at setup) used to fail Step 0 with 'HTTP Error 404: Not Found'; now it downloads on first use.
    Raises RuntimeError with a clear message on a genuine pull failure."""
    import urllib.request, urllib.error
    base = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
    try:
        with urllib.request.urlopen(base + "/api/tags", timeout=4) as r:
            have = [m.get("name", "") for m in json.loads(r.read().decode()).get("models", [])]
        if any(h == model or h == model + ":latest" or h.split(":")[0] == model for h in have):
            return                                   # already downloaded → nothing to do
    except Exception:
        return                                       # Ollama unreachable → let the engine surface it
    yield {"stage": "pull", "msg": f"First use of {model} — downloading it now (one-time). The size and "
                                   f"a live speed / time-remaining estimate appear below; you can leave this "
                                   f"running. A large model on a slow connection can take a while."}
    req = urllib.request.Request(base + "/api/pull",
        data=json.dumps({"model": model, "stream": True}).encode(),
        headers={"Content-Type": "application/json"})

    def _fmt_eta(sec):
        if sec >= 5400:  return f"~{sec/3600:.1f} h left"
        if sec >= 90:    return f"~{round(sec/60)} min left"
        return f"~{max(1, round(sec))} s left"

    t0 = done0 = None; last_emit = 0.0; last_pct = -1
    try:
        with urllib.request.urlopen(req, timeout=7200) as r:
            for raw in r:
                raw = raw.strip()
                if not raw:
                    continue
                try: d = json.loads(raw.decode())
                except Exception: continue
                if d.get("error"):
                    raise RuntimeError(f"Could not download {model}: {d['error']}")
                total, done = d.get("total") or 0, d.get("completed") or 0
                if total and done:
                    now = time.time()
                    if t0 is None:                       # anchor speed at the first byte-bearing sample
                        t0, done0 = now, done
                    pct = int(done * 100 / total)
                    # update in place at most ~once/2s (or on each 1% change) so speed/ETA refresh live
                    if pct != last_pct or now - last_emit >= 2:
                        last_pct, last_emit = pct, now
                        elapsed = now - t0
                        rate = (done - done0) / elapsed if elapsed > 0.5 else 0     # bytes/s since anchor
                        tail = ""
                        if rate > 0:
                            mbps = rate / (1 << 20)
                            tail = f"  ·  {mbps:.1f} MB/s  ·  {_fmt_eta((total - done) / rate)}"
                        yield {"stage": "pull",
                               "msg": f"Downloading {model} — {pct}%  ·  {done>>20} / {total>>20} MB{tail}"}
                elif d.get("status"):
                    yield {"stage": "pull", "msg": f"{model}: {d['status']}"}
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Could not download '{model}' (HTTP {e.code}). Check the model name is correct.")
    yield {"stage": "pulldone", "msg": f"{model} is ready — starting the analysis now."}

# ----------------------------------------------------------------- live run (SSE)
@app.post("/api/run")
def run_stream(payload: dict):
    deck = (payload.get("deck") or "").strip()
    model = payload.get("model") or MODELS[0]
    profile = payload.get("profile") or "pitch"
    label = (payload.get("label") or "Untitled deck").strip()[:60]

    def gen():
        def ev(o): return "data: " + json.dumps(o) + "\n\n"
        if not deck:
            yield ev({"error": "empty deck"}); return
        if not _acquire_run():
            yield ev({"error": "another analysis is running — try again in a moment"}); return
        try:
            _set_model(model)
            E.PROFILE = profile
            yield ev({"stage": "start", "msg": f"Engine starting · {model} · {profile} · blind · local, zero egress"})
            for e in _pull_events(model):            # auto-download the model on first use
                yield ev(e)
            E.reset_gen(); t0 = time.time()          # start machine-speed calibration clock

            yield ev({"stage": "p1", "msg": "Pass 1 — reviewing the document..."})
            p1 = _coerce(E.pass_one(deck).get("findings", []))
            yield ev({"stage": "p1done", "msg": f"Pass 1 — {len(p1)} surface charges", "t": round(time.time()-t0)})

            yield ev({"stage": "dec", "msg": "Excavating hidden assumptions..."})
            claims = E.decompose(deck).get("claims", [])
            yield ev({"stage": "decdone", "msg": f"Excavated {len(claims)} Level-2 assumptions", "t": round(time.time()-t0)})

            yield ev({"stage": "p2", "msg": "Pass 2 — structural contradictions..."})
            p2 = _coerce(E.pass_two(deck, p1, claims).get("findings", []))
            npin = sum(1 for f in p2 if f.get("type") == "pincer")
            yield ev({"stage": "p2done", "msg": f"Pass 2 — {len(p2)} new ({npin} pincers)", "t": round(time.time()-t0)})

            packs, routed = [], []
            if USE_PACKS:
                yield ev({"stage": "rules", "msg": "Applying the routed domain rulebook..."})
                try:
                    packs, routed = T.run(deck)
                except Exception:
                    packs, routed = [], []
                packs = _coerce([f for f in packs if isinstance(f, dict)])
                yield ev({"stage": "rulesdone",
                          "msg": f"Rulebook — {len(packs)} domain charges "
                                 f"({', '.join(routed) if routed else 'no pack matched — out of domain'})",
                          "t": round(time.time()-t0)})

            yield ev({"stage": "econ", "msg": "Computing unit economics from the deck's own numbers..."})
            econ = E.compute_economics(E.figures_for(deck))   # LLM + deterministic regex overlay
            yield ev({"stage": "econdone", "msg": f"{len(econ['metrics'])} metrics · {econ['danger_count']} red flags", "t": round(time.time()-t0)})

            yield ev({"stage": "integ", "msg": "Integrating the case..."})
            integ = E.integrate(deck, p1, p2)
            yield ev({"stage": "integdone", "msg": "Case integrated", "t": round(time.time()-t0)})

            result = {"label": label, "model": model, "profile": profile,
                      "blind": True, "local_zero_egress": True, "source_text": deck,
                      "pass1": p1, "level2_claims": claims, "pass2": p2, "economics": econ,
                      "integration": integ,
                      "rulebook": packs, "routed_packs": routed,
                      "stats": {"pass1_count": len(p1), "level2_count": len(claims),
                                "pass2_count": len(p2), "pass2_pincers": npin,
                                "rulebook_count": len(packs),
                                "load_bearing": sum(1 for f in p1+p2+packs if f.get("load_bearing")),
                                "econ_metrics": len(econ["metrics"]),
                                "econ_red_flags": econ["danger_count"],
                                "seconds": round(time.time()-t0)}}
            rid = _save_run(result)
            result["id"] = rid
            gs = E.gen_stats()                       # record this machine's real speed for next time
            _write_calib(model, "deck", gs, time.time() - t0, _accel_from_ollama()[0])
            yield ev({"stage": "result", "result": result})
        except Exception as e:
            yield ev({"error": str(e)[:300]})
        finally:
            RUN_LOCK.release()

    return StreamingResponse(gen(), media_type="text/event-stream")

# ----------------------------------------------------------------- cross-document
@app.post("/api/crossdoc")
def crossdoc(payload: dict):
    docs = payload.get("documents") or []
    model = payload.get("model") or MODELS[0]
    docs = [{"label": d.get("label") or f"Doc {i+1}", "text": (d.get("text") or "").strip()}
            for i, d in enumerate(docs) if (d.get("text") or "").strip()]
    if len(docs) < 2:
        return {"conflicts": [], "note": "Provide at least two documents."}
    if not _acquire_run():
        return JSONResponse({"error": "another analysis is running"}, status_code=409)
    try:
        _set_model(model)
        for _e in _pull_events(model):              # auto-download the model on first use
            pass
        t0 = time.time()
        res = E.cross_document(docs)
        res["docs"] = [d["label"] for d in docs]
        res["source_docs"] = docs
        res["model"] = model
        res["seconds"] = round(time.time() - t0)
        res["label"] = "Cross-document: " + " vs ".join(d["label"] for d in docs)
        res["kind"] = "crossdoc"
        _save_run(res)
        return res
    finally:
        RUN_LOCK.release()

# ----------------------------------------------------------------- reasoning excavation (SSE)
@app.post("/api/excavate")
def excavate_stream(payload: dict):
    text = (payload.get("deck") or payload.get("text") or "").strip()
    model = payload.get("model") or MODELS[0]
    label = (payload.get("label") or "Untitled document").strip()[:80]
    batch = 1 if payload.get("depth") == "deep" else 4   # deep = per-category (~16 calls)

    def gen():
        def ev(o): return "data: " + json.dumps(o) + "\n\n"
        if not text:
            yield ev({"error": "empty document"}); return
        if not _acquire_run():
            yield ev({"error": "another analysis is running — try again shortly"}); return
        q = queue.Queue()
        holder = {}
        def worker():
            try:
                _set_model(model)
                for e in _pull_events(model):        # auto-download the model on first use
                    q.put(e)
                E.reset_gen(); holder["t0"] = time.time()   # machine-speed calibration clock
                holder["res"] = RE.excavate(text, label, batch=batch,
                                            on_stage=lambda s, m: q.put({"stage": s, "msg": m}))
                verify_excavation(holder["res"], on_stage=lambda s, m: q.put({"stage": s, "msg": m}))
            except Exception as e:
                holder["err"] = str(e)[:300]
            finally:
                q.put(None)
        th = threading.Thread(target=worker, daemon=True); th.start()
        try:
            yield ev({"stage": "start", "msg": f"Reasoning excavation · {model} · {'deep' if batch==1 else 'fast'} · blind · local"})
            while True:
                item = q.get()
                if item is None:
                    break
                yield ev(item)
            if "err" in holder:
                yield ev({"error": holder["err"]}); return
            res = holder["res"]; res["kind"] = "excavation"; res["source_text"] = text
            _save_run(res)
            if holder.get("t0"):                    # record this machine's real speed for next time
                _write_calib(model, "excavation", E.gen_stats(), time.time() - holder["t0"], _accel_from_ollama()[0])
            yield ev({"stage": "result", "result": res})
        finally:
            RUN_LOCK.release()

    return StreamingResponse(gen(), media_type="text/event-stream")

# ----------------------------------------------------------------- history
@app.get("/api/history")
def history():
    items = []
    for fn in sorted(os.listdir(RUNS), reverse=True):
        if not fn.endswith(".json"):
            continue
        try:
            d = json.load(open(os.path.join(RUNS, fn), encoding="utf-8"))
        except Exception:
            continue
        items.append({"id": d.get("id", fn[:-5]), "label": d.get("label", "—"),
                      "created": d.get("created", ""), "model": d.get("model", ""),
                      "kind": d.get("kind", "deck"),
                      "stats": d.get("stats", {}),
                      "conflicts": len(d.get("conflicts", [])) if d.get("kind") == "crossdoc" else None})
    return {"runs": items}

@app.get("/api/history/{rid}")
def get_run(rid: str):
    p = os.path.join(RUNS, rid + ".json")
    if not os.path.exists(p):
        return JSONResponse({"error": "not found"}, status_code=404)
    return json.load(open(p, encoding="utf-8"))

@app.delete("/api/history/{rid}")
def del_run(rid: str):
    p = os.path.join(RUNS, rid + ".json")
    if os.path.exists(p):
        os.remove(p)
    return {"ok": True}

# ----------------------------------------------------------------- export PDF
@app.get("/api/export/{rid}")
def export_pdf(rid: str):
    p = os.path.join(RUNS, rid + ".json")
    if not os.path.exists(p):
        return JSONResponse({"error": "not found"}, status_code=404)
    d = json.load(open(p, encoding="utf-8"))
    html = _report_html(d)
    try:
        from weasyprint import HTML
        pdf = HTML(string=html).write_pdf()
        return Response(pdf, media_type="application/pdf",
                        headers={"Content-Disposition": f'attachment; filename="{rid}.pdf"'})
    except Exception as e:
        # fall back to printable HTML if weasyprint hits a system-lib issue
        return HTMLResponse(html + f"<!-- pdf export unavailable: {e} -->")

def _report_html(d):
    import html as H
    def esc(x): return H.escape(str(x if x is not None else ""))
    S = d.get("stats", {}); I = d.get("integration", {}); econ = d.get("economics", {})
    rows = ""
    for m in econ.get("metrics", []):
        flag = " ⚑" if m.get("danger") else ""
        rows += f"<tr><td><b>{esc(m['metric'])}</b>{flag}<br><small>{esc(m.get('note',''))}</small></td><td>{esc(m['value'])}</td><td><small>{esc(m['derivation'])}</small></td></tr>"
    def findings(title, fs):
        s = f"<h3>{esc(title)}</h3>"
        for f in fs:
            tags = []
            if f.get("type") == "pincer": tags.append("pincer")
            if f.get("load_bearing"): tags.append("load-bearing")
            s += f"<div class='f'><b>{esc(f.get('id'))} · {esc(f.get('name'))}</b> <span class='sev'>{esc(f.get('severity'))}</span> {' '.join('['+t+']' for t in tags)}<br>{esc(f.get('charge'))}</div>"
        return s
    reg = "".join(f"<tr><td>{esc(r.get('rank'))}</td><td>{esc(r.get('title'))}</td><td>{esc(r.get('severity'))}</td><td>{esc(r.get('why_it_matters'))}</td></tr>" for r in I.get("ranked_register", []))
    if d.get("kind") == "excavation":
        amap = {a["id"]: a.get("text", "") for a in d.get("atoms", [])}
        s0 = d.get("step0", {})
        cats = "".join(f"<tr><td>{esc(c)}</td><td>{n}</td></tr>" for c, n in sorted((d.get("atoms_by_category") or {}).items(), key=lambda x: -x[1]))
        _vb = {"real": "✓ verified", "duplicate": "♻ duplicate", "weak": "✗ unverified"}
        def vbadge(b):
            v = b.get("verdict")
            return f" <span class='sev'>{_vb[v]}</span>" if v in _vb else ""
        contra = "".join(
            f"<div class='f'><b>{esc(b.get('from'))} ✕ {esc(b.get('to'))}</b>{vbadge(b)}<br>"
            f"{esc(amap.get(b.get('from'),''))}<br>{esc(amap.get(b.get('to'),''))}<br><i>{esc(b.get('note',''))}</i></div>"
            for b in d.get("contradictions", []))
        vsum = ""
        if d.get("verified") and d.get("verification"):
            vf = d["verification"]
            vsum = (f" — <span style='font-size:13px;color:#5A6B78'>logic verifier: "
                    f"{vf['confirmed']} verified, {vf['rejected']} rejected "
                    f"({vf['duplicates']} duplicates)</span>")
        rd = "".join(f"<li>{esc(x)}</li>" for x in s0.get("reader_takeaways", []))
        ai = "".join(f"<li>{esc(x)}</li>" for x in s0.get("author_intent", []))
        body = (f"<h3>Step 0 — what a reader takes away</h3><ul>{rd}</ul>"
                f"<h3>Step 0 — inferred author intent</h3><ul>{ai}</ul>"
                f"<h3>Reasoning atom register — {len(d.get('atoms', []))} atoms</h3>"
                f"<table><tr><th>Category</th><th>Atoms</th></tr>{cats}</table>"
                f"<h3>Step 3 — contradiction bonds ({len(d.get('contradictions', []))}){vsum}</h3>{contra}")
    elif d.get("kind") == "crossdoc":
        body = "<h2>Cross-document conflicts</h2>" + "".join(
            f"<div class='f'><b>{esc(c.get('topic'))}</b> <span class='sev'>{esc(c.get('severity'))}</span><br>"
            f"<b>{esc(c.get('doc_a'))}:</b> {esc(c.get('claim_a'))}<br><b>{esc(c.get('doc_b'))}:</b> {esc(c.get('claim_b'))}<br>"
            f"<i>{esc(c.get('why'))}</i></div>" for c in d.get("conflicts", []))
    else:
        pitch = (d.get("profile") or "pitch") == "pitch"
        vlab = "Blind predictive verdict" if pitch else "Overall assessment"
        reglab = "Ranked prosecution register" if pitch else "Ranked issue register"
        p1lab = "Pass 1 — surface charges" if pitch else "Pass 1 — surface findings"
        p2lab = "Pass 2 — deeper charges" if pitch else "Pass 2 — deeper findings"
        body = (f"<p class='sum'>{esc(I.get('executive_summary'))}</p>"
                f"<div class='verdict'><b>{vlab}:</b> {esc(I.get('predictive_failure_judgement'))}</div>"
                + (f"<h3>Unit economics (computed from the document)</h3><table><tr><th>Metric</th><th>Value</th><th>Derivation</th></tr>{rows}</table>" if rows else "")
                + (f"<h3>{reglab}</h3><table><tr><th>#</th><th>Charge</th><th>Severity</th><th>Why</th></tr>{reg}</table>" if reg else "")
                + (findings(f"Domain rulebook — routed expert charges ({', '.join(d.get('routed_packs') or [])})", d.get("rulebook", [])) if d.get("rulebook") else "")
                + findings(p2lab, d.get("pass2", []))
                + findings(p1lab, d.get("pass1", [])))
    # appendix: the original document(s) analysed, so the report is self-contained
    def _src(title, text):
        return (f"<h3 style='page-break-before:always'>Appendix — {esc(title)}</h3>"
                f"<div style='white-space:pre-wrap;font-family:monospace;font-size:10.5px;"
                f"line-height:1.45;color:#333'>{esc(text)}</div>")
    appendix = ""
    if d.get("kind") == "crossdoc":
        for sd in d.get("source_docs", []):
            appendix += _src("Source: " + str(sd.get("label", "")), sd.get("text", ""))
    elif d.get("source_text"):
        appendix += _src("Original document analysed", d.get("source_text", ""))
    return f"""<meta charset="utf-8"><style>
      body{{font-family:Georgia,serif;color:#15212B;max-width:780px;margin:0 auto;padding:24px;line-height:1.5}}
      h1{{font-size:24px;margin:0 0 2px}} h2{{font-size:19px}} h3{{font-size:15px;margin-top:20px;border-bottom:1px solid #ccc;padding-bottom:3px}}
      .meta{{font-family:monospace;font-size:11px;color:#666;margin-bottom:16px}}
      .sum{{font-size:15px}} .verdict{{background:#10333A;color:#E7EEF0;padding:12px 14px;border-radius:5px;font-size:13px;margin:10px 0}}
      table{{width:100%;border-collapse:collapse;font-size:12px;margin:6px 0}} td,th{{border:1px solid #ddd;padding:5px 7px;text-align:left;vertical-align:top}}
      .f{{font-size:12.5px;margin:7px 0;padding-left:10px;border-left:3px solid #B3261E}} .sev{{font-family:monospace;font-size:10px;background:#eee;padding:1px 5px;border-radius:3px}}
      small{{color:#666}}
    </style>
    <h1>{esc(d.get('label'))}</h1>
    <div class="meta">Forensic Engine Forensic Engine · {esc(d.get('model'))} · blind · local, zero egress · {esc(d.get('created'))} · runtime {esc(S.get('seconds'))}s</div>
    {body}
    {appendix}
    <hr><div class="meta">Decision-support, not legal/financial advice. Confidential — do not distribute.</div>"""

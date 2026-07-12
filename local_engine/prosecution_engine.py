#!/usr/bin/env python3
"""
Automated 2-Pass Blind Forensic Prosecution Engine
==================================================
Reproduces, in code, Kerry's manual two-stage method:

  Pass 1  – prosecutor reads the SURFACE deck text and catalogues every weakness,
            error, misleading statement, internal contradiction and execution risk.
  Decompose – excavate the deck's implied claims, hidden assumptions and
            combination-inferences (the "Level-2" statements that underpin the slides).
  Pass 2  – prosecutor subjects the excavated Level-2 statements to the same scrutiny
            and reports ONLY what is NEW vs Pass 1 (esp. structural "pincer" contradictions).
  Integrate – merge into a ranked prosecution register + load-bearing collapse map
            + an executive summary, and a blind predictive failure judgement.

BLIND BY CONSTRUCTION: the engine is given ONLY the (anonymised) deck text. It has no
web access and is instructed to use no outside identification or outcome knowledge —
every finding must be derivable from the deck's own claims, numbers and internal logic.

FULLY LOCAL / ZERO EGRESS: runs entirely against a local Ollama daemon. No third-party
API, nothing sent off the machine — the privacy moat is the architecture.

Usage:
  LLM_MODEL=deepseek-r1:32b python3 prosecution_engine.py decks/psyscale.txt PsyScale
"""
import json, urllib.request, os, sys, time, re

OLLAMA = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
LLM    = os.environ.get("LLM_MODEL", "deepseek-r1:32b")

# Single source of truth for per-model native-thinking routing (measured 2026-07-10): reasoning-native
# models score best with thinking ON; hybrid-toggle (qwen3) and plain models score best with it OFF.
# Shared by the app (server.py) and the eval harness so the two never diverge.
THINK_ON_FRAGMENTS = ("gpt-oss", "qwq", "deepseek-r1", "magistral")
def wants_thinking(model):
    return any(f in (model or "").lower() for f in THINK_ON_FRAGMENTS)

def post(path, payload, timeout=1200):
    req = urllib.request.Request(OLLAMA + path,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=timeout))

def strip_think(c):
    return (c.split("</think>")[-1] if "</think>" in c else c).strip()

def chat(system, user, temperature=0.2):
    # num_ctx: Ollama defaults to only 2048, which truncates long docs + long JSON replies
    # (especially on small models) → unparseable output. num_predict caps the reply generously.
    body = {
        "model": LLM, "stream": False,
        "options": {"temperature": temperature,
                    "num_ctx": int(os.environ.get("NUM_CTX", "8192")),
                    "num_predict": int(os.environ.get("NUM_PREDICT", "4096"))},
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}]}
    # Hybrid "thinking" models (qwen3/qwen3.5/...) spend their whole token budget inside a
    # <think> block and never emit the JSON → the stage degrades to empty and scores unfairly.
    # OLLAMA_THINK=false sends Ollama's native think toggle to disable it. Default: unset →
    # body unchanged, so existing models (qwen2.5-coder:32b, the product path) are untouched.
    think = os.environ.get("OLLAMA_THINK")
    if think is not None:
        body["think"] = think.strip().lower() not in ("0", "false", "no", "off")
    try:
        r = post("/api/chat", body)
    except Exception:
        # model/server doesn't accept the think field → retry without it
        if "think" in body:
            body.pop("think"); r = post("/api/chat", body)
        else:
            raise
    _record_gen(r)
    return strip_think(r["message"]["content"])

# --- machine-speed accounting (self-calibrating ETA) -------------------------------------------
# Ollama returns per-call eval_count / eval_duration. Accumulating them over a run gives the REAL
# tokens/sec on THIS laptop for THIS model — the only honest basis for a time estimate, since a
# static number can't span an M-series Mac, a Ryzen iGPU box, and an old dual-core i5. Reset at the
# start of a run; snapshot at the end to write the calibration the /api/estimate endpoint reads.
_GEN = {"tokens": 0, "ns": 0, "prompt_tokens": 0, "load_ns": 0}
def reset_gen():
    _GEN.update({"tokens": 0, "ns": 0, "prompt_tokens": 0, "load_ns": 0})
def _record_gen(r):
    try:
        _GEN["tokens"]        += int(r.get("eval_count") or 0)
        _GEN["ns"]            += int(r.get("eval_duration") or 0)
        _GEN["prompt_tokens"] += int(r.get("prompt_eval_count") or 0)
        _GEN["load_ns"]        = max(_GEN["load_ns"], int(r.get("load_duration") or 0))
    except Exception:
        pass
def gen_stats():
    ns = _GEN["ns"]
    return {"gen_tokens": _GEN["tokens"],
            "gen_seconds": round(ns / 1e9, 1),
            "tok_s": round(_GEN["tokens"] / (ns / 1e9), 2) if ns else 0,
            "prompt_tokens": _GEN["prompt_tokens"],
            "load_seconds": round(_GEN["load_ns"] / 1e9, 1)}

def _salvage_json(txt):
    """Best-effort recovery of a TRUNCATED JSON reply (common on small models): cut at the last
    safe point (end of a string / element / after a comma) and close the open brackets."""
    safe = 0; stack = 0; in_str = False; esc = False
    for i, ch in enumerate(txt):
        if in_str:
            if esc: esc = False
            elif ch == "\\": esc = True
            elif ch == '"': in_str = False; safe = i + 1
            continue
        if ch == '"': in_str = True
        elif ch in "{[": stack += 1
        elif ch in "}]": stack -= 1; safe = i + 1
        elif ch == ",": safe = i + 1
    s = txt[:safe].rstrip().rstrip(",")
    # recompute the closers needed for the trimmed string
    st = []; in_str = False; esc = False
    for ch in s:
        if in_str:
            if esc: esc = False
            elif ch == "\\": esc = True
            elif ch == '"': in_str = False
            continue
        if ch == '"': in_str = True
        elif ch == "{": st.append("}")
        elif ch == "[": st.append("]")
        elif ch in "}]":
            if st: st.pop()
    try:
        return json.loads(s + "".join(reversed(st)))
    except Exception:
        return None

def chat_json(system, user, temperature=0.2, retries=2):
    """Ask for JSON, parse robustly (strip prose / code fences / think blocks). On persistent
    failure, salvage a truncated reply; if that also fails, return {} rather than crashing the
    whole analysis — a degraded stage beats a dead run."""
    hint = ("\n\nRespond with ONLY valid JSON — no preamble, no markdown fences, "
            "no commentary before or after.")
    raw = ""
    for attempt in range(retries + 1):
        raw = chat(system, user + hint, temperature)
        txt = raw.strip()
        if txt.startswith("```"):
            txt = re.sub(r"^```[a-zA-Z]*\n?", "", txt)
            txt = re.sub(r"\n?```$", "", txt).strip()
        # grab the outermost JSON object/array
        m = re.search(r"(\{.*\}|\[.*\])", txt, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                pass
        user = (user + "\n\nYour previous reply was not parseable JSON. "
                "Return STRICT JSON only.")
    # last resort: salvage a truncated reply, else degrade to {} (don't crash the run)
    salvaged = _salvage_json(txt if txt.startswith(("{", "[")) else raw)
    if isinstance(salvaged, (dict, list)):
        sys.stderr.write("[chat_json] recovered a truncated JSON reply\n")
        return salvaged
    sys.stderr.write("[chat_json] could not parse JSON after retries; degrading this stage\n")
    return {}

# ----------------------------------------------------------------------------- #
# Document-type profiles — calibrate the framing so an essay/report isn't prosecuted
# as if it were a fundraising pitch. Set PROFILE (module global) before running.
PROFILES = {
    "pitch":    {"noun": "pitch deck",
                 "persona": "the Prosecutor in a hearing, and the startup behind it is the defendant",
                 "case": "the investment thesis it asks an investor to believe",
                 "extra": "Pay attention to market sizing, unit economics, traction claims, team credentials, competitive positioning and regulatory status."},
    "report":   {"noun": "report",
                 "persona": "a ruthless critical reviewer",
                 "case": "the report's conclusions and recommendations",
                 "extra": "Check whether the conclusions actually follow from the stated evidence, and surface hidden assumptions, cherry-picked data and unstated limitations."},
    "essay":    {"noun": "argument (an essay / position paper)",
                 "persona": "a ruthless critical reader",
                 "case": "the argument the document makes",
                 "extra": "Check whether each claim is actually supported; expose hidden assumptions, overclaims, leaps of logic, and rhetoric standing in for evidence. This is NOT a fundraising pitch — do NOT invent commercial, market-traction or financial-solvency concerns it does not itself raise, and treat the author's own coined terms and names as intentional, not as 'misleading'."},
    "proposal": {"noun": "proposal / plan",
                 "persona": "a critical reviewer",
                 "case": "the plan it asks you to approve",
                 "extra": "Check feasibility, sequencing, dependencies, resourcing, and the risks the plan omits."},
    "generic":  {"noun": "document",
                 "persona": "a skeptical forensic analyst",
                 "case": "the case the document makes",
                 "extra": ""},
}
PROFILE = os.environ.get("PROFILE", "pitch")

def _prof():
    return PROFILES.get(PROFILE, PROFILES["generic"])

def _system():
    p = _prof()
    return (
        f"You are {p['persona']}. The exhibit is the {p['noun']} under review. Your job is to "
        "forensically find every weakness, error, unsupported claim, misleading statement, "
        "internal contradiction and execution risk in it. Be a ruthless, exhaustive investigator.\n\n"
        "STRICT BLINDING RULES:\n"
        "- Work ONLY from the text supplied. Do NOT identify or guess the real author/company. "
        "Do NOT use outside knowledge of its history, launch, press or outcome. Do NOT invent "
        "external facts.\n"
        f"- Every finding must be derivable from the document's own claims, numbers, logic and "
        f"internal consistency. The test is whether the document itself supports {p['case']} — "
        "NOT whether hindsight proves it wrong.\n"
        "- A finding is LOAD-BEARING if, like a support under a bridge or a link in a chain, its "
        "failure alone brings the central case down."
        + (("\n" + p["extra"]) if p["extra"] else ""))

def _wrap(obj, key):
    """Normalise model output: small/quantised models often return a bare array
    instead of the requested {key:[...]}. Always return a dict with key -> list."""
    if isinstance(obj, list):
        return {key: obj}
    if isinstance(obj, dict):
        if not isinstance(obj.get(key), list):
            obj[key] = obj.get(key) if isinstance(obj.get(key), list) else []
        return obj
    return {key: []}

def pass_one(deck):
    usr = (
        "Here is the document:\n\n<document>\n" + deck + "\n</document>\n\n"
        "PASS ONE — surface review. Catalogue every issue in the explicit text. For each "
        "issue return an object with:\n"
        '  "id": "P1-01" style id,\n'
        '  "name": short title,\n'
        '  "charge": the finding (2-4 sentences, grounded in the document),\n'
        '  "load_bearing": a JSON boolean true or false (REQUIRED on every item),\n'
        '  "severity": one of "Fatal","Severe","Material","Minor".\n'
        "Return JSON: {\"findings\": [ ... ]}. Be exhaustive — return AT LEAST 16 distinct "
        "findings (more if warranted). Every finding MUST include the load_bearing boolean.")
    return _wrap(chat_json(_system(), usr), "findings")

def decompose(deck):
    sys_p = (
        "You are a forensic analyst. You take a document and excavate the LEVEL-2 statements "
        "beneath its surface: the hidden assumptions, implied claims, and combination-"
        "inferences the reader must silently accept for its case to hold. Work only from the "
        "text; do not identify the author or use outside facts.")
    usr = (
        "Here is the document:\n\n<document>\n" + deck + "\n</document>\n\n"
        "Enumerate the hidden assumptions and implied claims that underpin this document — "
        "the things it never states but needs the reader to believe. "
        "Return JSON: {\"claims\": [\"...\", \"...\"]}. Be exhaustive — return AT LEAST "
        "35 crisp statements (one assumption each).")
    d = _wrap(chat_json(sys_p, usr), "claims")
    if isinstance(d, dict) and isinstance(d.get("claims"), list):
        d["claims"] = [_as_text(c) for c in d["claims"]]   # small models sometimes return dicts
    return d

def _as_text(c):
    """A claim may come back as a plain string OR a dict (small models vary) — coerce to text."""
    if isinstance(c, str):
        return c
    if isinstance(c, dict):
        for k in ("text", "claim", "statement", "assumption", "content"):
            if isinstance(c.get(k), str):
                return c[k]
        return json.dumps(c, ensure_ascii=False)
    return str(c)

def pass_two(deck, p1_findings, claims):
    p1_titles = "; ".join((f.get("name", "") if isinstance(f, dict) else str(f)) for f in p1_findings)
    usr = (
        "Here is the document:\n\n<document>\n" + deck + "\n</document>\n\n"
        "PASS ONE already found these issues (do NOT merely repeat them):\n" +
        p1_titles + "\n\n"
        "Here are the excavated LEVEL-2 statements:\n- " +
        "\n- ".join(_as_text(c) for c in claims) + "\n\n"
        "PASS TWO — subject these Level-2 statements to the same forensic scrutiny. "
        "Report ONLY what is NEW or materially STRENGTHENED vs Pass One. Pay special "
        "attention to STRUCTURAL CONTRADICTIONS ('pincers'): pairs of claims/promises that "
        "cannot both be true at once. For each return:\n"
        '  "id": "P2-01" style,\n'
        '  "name": short title,\n'
        '  "charge": the new finding (grounded in the document),\n'
        '  "type": "new" or "strengthened" or "pincer",\n'
        '  "load_bearing": a JSON boolean true or false (REQUIRED on every item),\n'
        '  "severity": "Fatal","Severe","Material","Minor".\n'
        "Return JSON: {\"findings\": [ ... ]}. Return AT LEAST 8 NEW findings, including "
        "at least 3 of type \"pincer\" where the document contains such tensions. Every "
        "finding MUST include the load_bearing boolean.")
    return _wrap(chat_json(_system(), usr), "findings")

# --------------------------------------------------------------------------- #
#  ARITHMETIC / UNIT-ECONOMICS MODULE
#  The LLM only *extracts* the figures the deck states. Every damaging ratio is
#  then computed in Python — deterministic, re-checkable, no model arithmetic.
#  The core flags (capital already spent, content as % of revenue, subscriber
#  spread) need NO external data — they are pure internal-consistency attacks.
# --------------------------------------------------------------------------- #
def to_number(x):
    """Coerce '$496.5M', '1.2 billion', '8,500', 4.99 -> float (or None)."""
    if x is None: return None
    if isinstance(x, (int, float)): return float(x)
    s = str(x).strip().lower().replace("$", "").replace(",", "").replace("usd", "").strip()
    if not s or s in ("null", "none", "n/a"): return None
    mult = 1.0
    for suf, m in (("billion", 1e9), ("bn", 1e9), ("b", 1e9),
                   ("million", 1e6), ("mn", 1e6), ("m", 1e6), ("k", 1e3)):
        if s.endswith(suf):
            s = s[:-len(suf)].strip(); mult = m; break
    try: return float(s) * mult
    except ValueError: return None

def find_secured_capital(deck):
    """Deterministic regex fallback: scan the deck for a stated secured/raised figure."""
    pats = [
        r"\$?\s*([\d.,]+)\s*(b|bn|billion|m|mn|million)\+?\s+(?:secured|raised|committed|in\s+funding)",
        r"(?:secured|raised|committed)\s*[:\-]?\s*\$?\s*([\d.,]+)\s*(b|bn|billion|m|mn|million)",
        r"\$?\s*([\d.,]+)\s*(b|bn|billion|m|mn|million)\+?\s+(?:in\s+)?(?:capital|investment|funding)\s+secured",
    ]
    for p in pats:
        m = re.search(p, deck, re.IGNORECASE)
        if m:
            return to_number(m.group(1) + m.group(2))
    return None

def deterministic_figures(deck):
    """Pull standard financial figures from the text by regex — no LLM. Reliable for the
    numbers a document states, so small/quantised models don't lose the unit-economics
    red flags. Validated to match the 70B extraction on the QuickBite deck."""
    def gU(pat):
        m = re.search(pat, deck, re.IGNORECASE)
        return (m.group(1) + m.group(2)) if m else None
    def g(pat):
        m = re.search(pat, deck, re.IGNORECASE)
        return m.group(1) if m else None
    fig = {"content_spend": {}, "subscribers": {}}
    fig["content_spend"]["pre_launch"] = gU(r"\$?([\d.]+)\s*([MB])\s+pre-?launch")
    fig["content_spend"]["year1"]      = gU(r"\$?([\d.]+)\s*([MB])\s+(?:in\s+)?year\s*one")
    fig["content_spend"]["year5_base"] = gU(r"\$?([\d.]+)\s*([MB])\s+(?:by\s+)?year\s*five\s*\(base")
    fig["episodes_year1"]              = g(r"([\d,]+)\s*episodes")
    fig["minutes_per_episode_low"]     = g(r"(\d+)\s*[–-]\s*\d+\s*-?\s*minute")
    fig["minutes_per_episode_high"]    = g(r"\d+\s*[–-]\s*(\d+)\s*-?\s*minute")
    fig["subscribers"]["downside"]     = gU(r"[Dd]ownside\s*\$?([\d.]+)\s*([MB])")
    fig["subscribers"]["base"]         = gU(r"base\s*case\s*\$?([\d.]+)\s*([MB])")
    fig["subscribers"]["upside"]       = gU(r"upside\s*\$?([\d.]+)\s*([MB])")
    prices = re.findall(r"\$?([\d.]+)\s*/\s*month", deck)
    if prices:
        fig["price_monthly_low"]  = min(prices, key=float)
        fig["price_monthly_high"] = max(prices, key=float)
    fig["capital_secured"] = find_secured_capital(deck)
    return fig

def figures_for(deck, model_figures=None):
    """LLM extraction with a deterministic regex overlay: regex wins where it found a
    stated value, so weak models still recover the red flags. Pure Python — laptop-safe."""
    llm = model_figures if model_figures is not None else extract_figures(deck)
    det = deterministic_figures(deck)
    if not isinstance(llm, dict):
        llm = {}
    def merge(d_llm, d_det):
        out = dict(d_llm)
        for k, v in d_det.items():
            if isinstance(v, dict):
                out[k] = merge(d_llm.get(k, {}) if isinstance(d_llm.get(k), dict) else {}, v)
            elif v is not None:
                out[k] = v                      # deterministic value wins when present
            else:
                out.setdefault(k, d_llm.get(k))
        return out
    return merge(llm, det)

def extract_figures(deck):
    sys_p = ("You are a financial analyst. Extract ONLY the numbers the deck explicitly "
             "states. Do not infer or invent. Use null for anything not stated.")
    usr = (
        "<deck>\n" + deck + "\n</deck>\n\n"
        "Return this exact JSON, filling values the deck states (null otherwise). "
        "Give raw numbers (you may keep suffixes like 496.5M):\n"
        "{\n"
        '  "content_spend": {"pre_launch": null, "year1": null, "year5_base": null, "year5_upside": null},\n'
        '  "episodes_year1": null,\n'
        '  "minutes_per_episode_low": null, "minutes_per_episode_high": null,\n'
        '  "subscribers": {"downside": null, "base": null, "upside": null},\n'
        '  "price_monthly_low": null, "price_monthly_high": null,\n'
        '  "capital_secured": null,   // any stated secured/raised/committed funding, e.g. "$1B+ secured"\n'
        '  "ads_presold": null\n'
        "}\n(Read every slide for a secured/raised funding figure — it is often on a "
        "'backed by' or traction slide.)")
    try:
        return chat_json(sys_p, usr)
    except Exception as e:
        print("  (figure extraction failed:", e, ")"); return {}

# industry-neutral benchmarks (clearly labelled; not tied to any company)
APP_STORE_CUT = (0.15, 0.30)
PREMIUM_PER_MIN = (80000, 500000)   # premium scripted $/min, general industry context

def compute_economics(fig):
    cs = fig.get("content_spend", {}) or {}
    subs = fig.get("subscribers", {}) or {}
    pre   = to_number(cs.get("pre_launch"))
    y1    = to_number(cs.get("year1"))
    y5b   = to_number(cs.get("year5_base"))
    eps   = to_number(fig.get("episodes_year1"))
    mlo   = to_number(fig.get("minutes_per_episode_low"))
    mhi   = to_number(fig.get("minutes_per_episode_high"))
    sb    = to_number(subs.get("base"))
    sd    = to_number(subs.get("downside"))
    su    = to_number(subs.get("upside"))
    plo   = to_number(fig.get("price_monthly_low"))
    phi   = to_number(fig.get("price_monthly_high"))
    secured = to_number(fig.get("capital_secured"))

    M = []  # each: {metric, value, derivation, danger, note, external}
    def usd(n): return ("$%.2fB" % (n/1e9)) if n >= 1e9 else ("$%.0fM" % (n/1e6)) if n >= 1e6 else ("$%.0fK" % (n/1e3)) if n >= 1e3 else ("$%.2f" % n)

    # 1) capital already committed before launch (pure internal)
    if pre is not None and y1 is not None and secured:
        committed = pre + y1
        M.append({"metric": "Content capital committed before launch",
                  "value": usd(committed),
                  "derivation": f"pre-launch {usd(pre)} + year-1 content {usd(y1)} = {usd(committed)}",
                  "danger": committed > secured,
                  "note": (f"Already exceeds the {usd(secured)} 'secured' — and that is content "
                           "ALONE, before marketing, tech, distribution, operations or acquisition."
                           if committed > secured else "within secured capital"),
                  "external": False})

    # 2) cost per episode / per minute (internal; per-minute compared to benchmark)
    if y1 is not None and eps:
        per_ep = y1 / eps
        row = {"metric": "Content cost per episode (year 1)", "value": usd(per_ep),
               "derivation": f"year-1 content {usd(y1)} ÷ {int(eps):,} episodes = {usd(per_ep)}/episode",
               "danger": False, "note": "", "external": False}
        M.append(row)
        if mlo and mhi:
            pm_hi = per_ep / mlo   # fewer minutes -> higher $/min
            pm_lo = per_ep / mhi
            M.append({"metric": "Content cost per minute",
                      "value": f"{usd(pm_lo)}–{usd(pm_hi)} / min",
                      "derivation": f"{usd(per_ep)}/episode ÷ {mlo:.0f}–{mhi:.0f} min/episode",
                      "danger": pm_hi < PREMIUM_PER_MIN[0],
                      "note": (f"Premium scripted norms run ~{usd(PREMIUM_PER_MIN[0])}–{usd(PREMIUM_PER_MIN[1])}/min "
                               "(general industry benchmark) — the slate is priced like reality TV, not 'premium'."),
                      "external": True})

    # 3) content cost per subscriber vs revenue (internal)
    if y5b is not None and sb:
        cost_sub = y5b / sb
        rev_lo = (plo * 12) if plo else None
        rev_hi = (phi * 12) if phi else None
        note = ""
        danger = False
        if rev_lo:
            pct_hi = cost_sub / rev_lo * 100   # cheapest price -> worst ratio
            pct_lo = cost_sub / rev_hi * 100 if rev_hi else pct_hi
            danger = pct_hi > 40
            note = (f"Content alone is {pct_lo:.0f}–{pct_hi:.0f}% of subscription revenue "
                    f"({usd(rev_hi or rev_lo)}–{usd(rev_lo)}/yr) — before the typical "
                    f"{int(APP_STORE_CUT[0]*100)}–{int(APP_STORE_CUT[1]*100)}% app-store cut and all other costs.")
        M.append({"metric": "Content cost per subscriber / year (base case)",
                  "value": usd(cost_sub) + "/sub",
                  "derivation": f"year-5 base content {usd(y5b)} ÷ {int(sb):,} subscribers = {usd(cost_sub)}/sub",
                  "danger": danger, "note": note, "external": False})

    # 4) subscriber-scenario spread (pure internal)
    if sd and su:
        spread = su / sd
        M.append({"metric": "Subscriber-scenario spread (upside ÷ downside)",
                  "value": f"{spread:.1f}×",
                  "derivation": f"{int(su):,} upside ÷ {int(sd):,} downside = {spread:.1f}×",
                  "danger": spread >= 3,
                  "note": ("A multi-fold spread with no CAC, churn, conversion or payback behind it "
                           "signals placeholder numbers, not a model." if spread >= 3 else ""),
                  "external": False})

    return {"figures": fig, "metrics": M,
            "danger_count": sum(1 for m in M if m["danger"]),
            "internal_only": all(not m["external"] for m in M if m["danger"])}

SEV_RANK = {"Fatal": 4, "Severe": 3, "Material": 2, "Minor": 1}

def _first_sentence(t):
    parts = re.split(r"(?<=[.!?])\s", (t or "").strip())
    return parts[0] if parts and parts[0] else (t or "")

def integrate(deck, p1, p2):
    """Robust integration. The model writes only the two prose blocks (easy, no nested
    JSON to mangle); the ranked register and collapse map are assembled deterministically
    from the model's own findings — so a late JSON slip can never lose the whole run."""
    p = _prof()
    sys_p = _system() + "\n\nYou are writing the integrated closing assessment."
    def brief(fs):
        return "\n".join(f"- [{f.get('id')}] {f.get('name')} "
                         f"(LB={f.get('load_bearing')}, {f.get('severity')})" for f in fs)
    verdict_ask = ("rate the venture's risk and name the credible collapse paths"
                   if PROFILE == "pitch" else
                   f"assess how robustly {p['case']} holds up and where it is most likely to fail")
    txt = chat(sys_p,
        "PASS ONE findings:\n" + brief(p1) + "\n\nPASS TWO findings:\n" + brief(p2) +
        "\n\nWrite exactly TWO blocks, each starting on its own line with the exact prefix:\n"
        f"SUMMARY: <3-5 sentences on how well {p['case']} holds up and where it is weakest>\n"
        "VERDICT: <2-4 sentence blind, document-only overall assessment — " + verdict_ask +
        ", WITHOUT invoking any real-world identity or outcome>\n"
        "No other text, no JSON.")
    summary, verdict = "", ""
    for line in txt.splitlines():
        s = line.strip()
        if s.upper().startswith("SUMMARY:"): summary = s[8:].strip()
        elif s.upper().startswith("VERDICT:"): verdict = s[8:].strip()
    if not summary:
        summary = txt.strip()[:700]

    allf = p1 + p2
    ranked = sorted(allf, key=lambda f: (f.get("load_bearing") is True,
                                         SEV_RANK.get(f.get("severity"), 0)), reverse=True)
    register = [{"rank": i + 1, "title": f.get("name"), "severity": f.get("severity"),
                 "why_it_matters": f.get("charge") or ""} for i, f in enumerate(ranked[:10])]
    lb = [f for f in allf if f.get("load_bearing")]
    collapse = [{"issue": f.get("name"), "if_it_falls": _first_sentence(f.get("charge"))}
                for f in lb[:8]]
    return {"executive_summary": summary, "predictive_failure_judgement": verdict,
            "ranked_register": register, "load_bearing_collapse_map": collapse}

# ----------------------------------------------------------------------------- #
def cross_document(docs):
    """docs = [{"label","text"}]. Find claims across documents that cannot both be
    true. Blind/internal: judges only on what the documents themselves assert."""
    if len(docs) < 2:
        return {"conflicts": [], "note": "need at least two documents"}
    blob = "\n\n".join(f"=== DOCUMENT: {d['label']} ===\n{d['text']}" for d in docs)
    sys_p = (
        "You are a forensic analyst comparing several documents from the same matter. "
        "Find statements that CONTRADICT across documents — pairs that cannot both be "
        "true (different numbers/dates/status/ownership for the same thing), or where "
        "one document's claim undercuts another's. Use ONLY what the documents assert; "
        "do not use outside facts. Each conflict must name both documents and quote/"
        "paraphrase the conflicting claims.")
    usr = (
        blob + "\n\nReturn JSON {\"conflicts\":[ {"
        '"topic": short label, '
        '"doc_a": document name, "claim_a": its claim, '
        '"doc_b": document name, "claim_b": the conflicting claim, '
        '"why": why they cannot both be true, '
        '"severity": "Fatal"/"Severe"/"Material"/"Minor" } ]}. Only include genuine '
        "contradictions; return an empty list if there are none.")
    try:
        r = chat_json(sys_p, usr)
        if isinstance(r, list):                 # some models return a bare array
            r = {"conflicts": r}
        if not isinstance(r, dict):
            r = {"conflicts": []}
        r.setdefault("conflicts", [])
        return r
    except Exception as e:
        return {"conflicts": [], "error": str(e)[:200]}

def run(deck_path, label):
    def coerce(fs):
        for f in fs:
            v = f.get("load_bearing")
            if isinstance(v, str):
                f["load_bearing"] = v.strip().lower() in ("true", "yes", "1")
            elif not isinstance(v, bool):
                f["load_bearing"] = False
        return fs
    def _list(obj, key):
        # tolerate small models that return a bare array instead of {key:[...]}
        if isinstance(obj, list): return obj
        if isinstance(obj, dict):
            v = obj.get(key)
            return v if isinstance(v, list) else []
        return []
    deck = open(deck_path).read().strip()
    out = {"label": label, "deck_path": deck_path, "model": LLM,
           "blind": True, "local_zero_egress": True}
    t0 = time.time()
    print(f"[{LLM}] PASS 1 — surface prosecution ...", flush=True)
    p1 = coerce(_list(pass_one(deck), "findings"))
    print(f"  -> {len(p1)} findings ({time.time()-t0:.0f}s)", flush=True)

    print("DECOMPOSE — excavating Level-2 statements ...", flush=True)
    claims = _list(decompose(deck), "claims")
    print(f"  -> {len(claims)} hidden claims ({time.time()-t0:.0f}s)", flush=True)

    print("PASS 2 — deep prosecution of Level-2 ...", flush=True)
    p2 = coerce(_list(pass_two(deck, p1, claims), "findings"))
    print(f"  -> {len(p2)} NEW findings ({time.time()-t0:.0f}s)", flush=True)

    print("ARITHMETIC — extracting figures + computing unit economics ...", flush=True)
    econ = compute_economics(figures_for(deck))
    print(f"  -> {len(econ['metrics'])} metrics, {econ['danger_count']} red flags "
          f"({time.time()-t0:.0f}s)", flush=True)

    print("INTEGRATE — ranked register + collapse map ...", flush=True)
    integ = integrate(deck, p1, p2)
    print(f"  -> done ({time.time()-t0:.0f}s)", flush=True)

    out.update({"pass1": p1, "level2_claims": claims, "pass2": p2,
                "economics": econ, "integration": integ,
                "stats": {"pass1_count": len(p1), "level2_count": len(claims),
                          "pass2_count": len(p2),
                          "pass2_pincers": sum(1 for f in p2 if f.get("type") == "pincer"),
                          "load_bearing": sum(1 for f in p1 + p2 if f.get("load_bearing")),
                          "econ_metrics": len(econ["metrics"]),
                          "econ_red_flags": econ["danger_count"],
                          "seconds": round(time.time() - t0)}})
    return out

if __name__ == "__main__":
    deck_path = sys.argv[1] if len(sys.argv) > 1 else "decks/psyscale.txt"
    label = sys.argv[2] if len(sys.argv) > 2 else os.path.basename(deck_path).split(".")[0]
    result = run(deck_path, label)
    os.makedirs("prosecution_out", exist_ok=True)
    fn = f"prosecution_out/{label}_prosecution.json"
    json.dump(result, open(fn, "w"), indent=2, ensure_ascii=False)
    print("\nSaved:", fn)
    print(json.dumps(result["stats"], indent=2))

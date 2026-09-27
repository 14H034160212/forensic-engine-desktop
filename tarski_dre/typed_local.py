"""
Tarski DRE — local "System One" decision backend (zero external dependency).

Reproduces Jev's Choice primitive entirely on the app's own bundled local model, via Ollama's
constrained / structured decoding: the model is FORCED to emit one of the valid coverage states
(and, where relevant, one valid judgement) through a JSON-schema `format` with `enum`. This
guarantees a valid typed answer — which is exactly what small local models fail at with free-form
JSON (they emit unparseable text → 0/0 constructs). No cloud API, no key, fully offline.

Confidence: the model reports a 0..1 confidence per decision. True token-logprob calibration (the
ideal) is not exposed by Ollama 0.5.x; when the local runtime gains logprobs, swap `_conf_band` to
read them — the rest of the pipeline is unchanged.

Same interface as dre_reason.reason_domain, so it drops straight into the backend switch:
  DRE_DECISION_BACKEND=local_typed
"""
import os, json, urllib.request, time

COV = ["COV.RELEVANT_FOUND", "COV.RELEVANT_INSUFFICIENT", "COV.NO_OPPORTUNITY",
       "COV.NOT_RELEVANT", "COV.NO_MATERIAL_FINDING"]
JDG = ["JDG.CONCERN", "JDG.MIXED", "JDG.SUPPORTIVE", "JDG.STRONG", "JDG.NA"]

_SCHEMA = {
    "type": "object",
    "properties": {"constructs": {"type": "array", "items": {
        "type": "object",
        "properties": {
            "index": {"type": "integer"},
            "coverage": {"type": "string", "enum": COV},
            "confidence": {"type": "number"},
            "judgement": {"type": "string", "enum": JDG},
            "basis": {"type": "string"},
        },
        "required": ["index", "coverage", "confidence", "judgement", "basis"],
    }}},
    "required": ["constructs"],
}

SYS = (
 "You are the Tarski Deep Reasoning Engine's coverage classifier. For each construct, decide — from "
 "the evidence ONLY — one coverage state. Discipline: copy != understanding; exposure != comprehension; "
 "sequence != causation; AI assistance != substitution. In a single naturalistic episode EXPECT most "
 "constructs to be COV.NO_OPPORTUNITY or COV.NOT_RELEVANT; use COV.RELEVANT_FOUND only when concrete "
 "evidence demonstrates the construct, COV.RELEVANT_INSUFFICIENT when touched but too thin to judge. "
 "Give a judgement (JDG.*) only when coverage is COV.RELEVANT_FOUND; otherwise JDG.NA. confidence is 0..1."
)

def _host(): return os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
def _model(): return os.environ.get("DRE_MODEL", "mistral-small:latest")

def _chat_structured(user, timeout=300):
    body = {"model": _model(), "stream": False, "format": _SCHEMA,
            "options": {"temperature": 0, "num_ctx": 16384},
            "messages": [{"role": "system", "content": SYS}, {"role": "user", "content": user}]}
    if any(f in _model().lower() for f in ("gpt-oss", "qwq", "deepseek-r1", "qwen3", "magistral")):
        body["think"] = False
    for attempt in range(3):
        try:
            req = urllib.request.Request(_host() + "/api/chat", data=json.dumps(body).encode(),
                                         headers={"Content-Type": "application/json"})
            r = json.load(urllib.request.urlopen(req, timeout=timeout))
            c = (r.get("message") or {}).get("content", "")
            if c.strip():
                return json.loads(c)   # constrained → valid JSON by construction
        except Exception:
            time.sleep(2 * (attempt + 1))
    return None

def _band(x):
    try: x = float(x)
    except Exception: return None
    return "high" if x >= 0.75 else "moderate" if x >= 0.5 else "low"

def classify_domain(dom, constructs, brief):
    """Constrained per-construct coverage classification. Returns the SAME shape as reason_domain."""
    clist = "\n".join(f"  [{i}] {c['id']} — {c['name']} (era {c['era']}): {c['guidepost']}"
                      for i, c in enumerate(constructs))
    user = (f"DOMAIN {dom['id']} — {dom['name']}\nCore question: {dom.get('question','')}\n\n"
            f"CONSTRUCTS (return exactly one item per construct, echoing its [index]):\n{clist}\n\n"
            f"EVIDENCE:\n{brief}")
    j = _chat_structured(user)
    if not j:
        return {"domain_relevance": "(local_typed: no response)", "constructs": []}
    out = []
    items = j.get("constructs", [])
    # map by echoed index; fall back to positional order
    by_index = {}
    for it in items:
        idx = it.get("index")
        if isinstance(idx, int) and 0 <= idx < len(constructs):
            by_index[idx] = it
    for i, c in enumerate(constructs):
        it = by_index.get(i, items[i] if i < len(items) and not by_index else None)
        if not it:
            out.append({"id": c["id"], "coverage": "COV.NO_OPPORTUNITY",
                        "basis": "no decision returned", "judgement": None,
                        "confidence": None, "evidence": "", "confounds": None})
            continue
        jdg = it.get("judgement")
        cov = it.get("coverage")
        out.append({"id": c["id"], "coverage": cov,
                    "basis": it.get("basis", ""),
                    "judgement": (jdg if (jdg and jdg != "JDG.NA" and cov == "COV.RELEVANT_FOUND") else None),
                    "confidence": _band(it.get("confidence")),
                    "evidence": "constrained typed decision over the evidence brief",
                    "confounds": None,
                    "typed_confidence": it.get("confidence")})
    return {"domain_relevance": "classified per-construct via constrained typed decoding", "constructs": out}

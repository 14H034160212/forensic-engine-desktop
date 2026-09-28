"""
Tarski DRE — optional Jev (TypeSafe "System One") decision backend.

The DRE's coverage traversal is, structurally, a classification problem: for each taxonomy construct,
pick ONE coverage state (a 5-way Choice) and, where relevant, ONE judgement (a 4-way Choice), each with
a confidence. That is exactly what TypeSafe's Jev is built for — typed probabilistic decisions with
calibrated confidence, ~200x faster / ~400x cheaper than an LLM on classification, and (critically) it
GUARANTEES a valid typed answer, where small local LLMs often emit unparseable JSON.

This backend is OPT-IN and isolated to the classification step. Report SYNTHESIS always stays on the
local LLM (Jev does not generate text). Default remains fully local, so the privacy/offline promise is
untouched unless the operator explicitly turns Jev on.

Config (env):
  DRE_DECISION_BACKEND = local | jev          (default local)
  TYPESAFE_API_KEY     = <key>                (required for jev; never written to disk/repo)
  JEV_ENDPOINT         = https://api.typesafe.ai/v1/systemone   (override if needed)
  JEV_MODEL            = typesafe/jev-1.13

NOTE: the exact Choice request/response shape is verified live via probe() — the public tutorial points
to the Playground request-preview for the canonical schema, and mirror sites disagree on the endpoint.
The request builder and response parser are deliberately tolerant; probe() dumps the raw response so the
shape can be pinned against the real API before a full run.
"""
import os, json, time, urllib.request, urllib.error

COV_OPTIONS = ["COV.RELEVANT_FOUND", "COV.RELEVANT_INSUFFICIENT", "COV.NO_OPPORTUNITY",
               "COV.NOT_RELEVANT", "COV.NO_MATERIAL_FINDING"]
JDG_OPTIONS = ["JDG.CONCERN", "JDG.MIXED", "JDG.SUPPORTIVE", "JDG.STRONG"]

def endpoint():  return os.environ.get("JEV_ENDPOINT", "https://api.typesafe.ai/v1/systemone").rstrip("/")
def model():     return os.environ.get("JEV_MODEL", "typesafe/jev-1.13")
def api_key():   return os.environ.get("TYPESAFE_API_KEY", "").strip()
def available(): return bool(api_key())

def _post(body, timeout=60):
    req = urllib.request.Request(endpoint(), data=json.dumps(body).encode(),
                                 headers={"Authorization": "Bearer " + api_key(),
                                          "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)

def _choice_question(instructions, options):
    """Build one Choice question. The /v1/systemone contract (TypeSafe, and self-hosted servers like
    jeff/Kev) takes the option set as `criteria` — a dict of option -> optional description; we also
    send `options`/`choices` lists so we are robust across server variants. probe() confirms the exact
    shape against whichever live service JEV_ENDPOINT points at."""
    return {"type": "choice", "instructions": instructions,
            "criteria": {o: None for o in options},
            "options": options, "choices": options}

def probe():
    """Send one minimal Choice request and return the RAW response, to pin the exact schema live."""
    body = {"model": model(),
            "state": "A learner asked several specific follow-up questions and revised their own notes.",
            "questions": {"q_probe": _choice_question(
                "Did the learner show initiative? Pick the coverage state.", COV_OPTIONS)}}
    t0 = time.time()
    raw = _post(body)
    return {"elapsed_s": round(time.time() - t0, 2), "request": body, "response": raw}

def _parse_answer(ans, options):
    """Tolerant extraction of (chosen_option, confidence, per_option_probs) from one answer object,
    across the shapes the docs/mirrors describe: {choice, confidence, probabilities:{opt:p}} |
    {choice: opt} | a bare string | {label, score}."""
    if ans is None:
        return None, None, {}
    if isinstance(ans, str):
        return (ans if ans in options else None), None, {}
    if isinstance(ans, dict):
        probs = ans.get("probabilities") or ans.get("probs") or {}
        conf = ans.get("confidence")
        choice = ans.get("choice") or ans.get("label") or ans.get("answer") or ans.get("value")
        if choice is None and isinstance(probs, dict) and probs:
            choice = max(probs, key=probs.get)
        if conf is None and isinstance(probs, dict) and choice in probs:
            conf = probs[choice]
        return (choice if choice in options else choice), conf, (probs if isinstance(probs, dict) else {})
    return None, None, {}

def _conf_band(c):
    if c is None: return None
    try: c = float(c)
    except Exception: return None
    return "high" if c >= 0.75 else "moderate" if c >= 0.5 else "low"

def classify_domain(dom, constructs, brief):
    """Jev counterpart of dre_reason.reason_domain: assign a coverage state (and, where RELEVANT_FOUND,
    a judgement) to each construct via typed Choice calls. Returns the SAME shape reason_domain returns."""
    # one Choice per construct for coverage (batched into a single request via the questions dict)
    qs, idmap = {}, {}
    for i, c in enumerate(constructs):
        qid = "cov_%d" % i; idmap[qid] = c
        instr = (f"Construct {c['id']} — {c['name']}: {c['guidepost']}\n"
                 f"Given ONLY the evidence in the state, which coverage state does it support? "
                 f"Most constructs in a single episode have NO opportunity — do not over-claim.")
        qs[qid] = _choice_question(instr, COV_OPTIONS)
    body = {"model": model(), "state": brief, "questions": qs}
    try:
        raw = _post(body, timeout=120)
    except urllib.error.HTTPError as e:
        return {"domain_relevance": f"(jev http {e.code})", "constructs": [], "_error": e.read().decode("utf-8","replace")[:300]}
    except Exception as e:
        return {"domain_relevance": f"(jev error {e})", "constructs": []}
    answers = raw.get("answers") or raw.get("results") or {}
    out = []
    need_jdg = []
    for qid, c in idmap.items():
        cov, conf, probs = _parse_answer(answers.get(qid), COV_OPTIONS)
        rec = {"id": c["id"], "coverage": cov, "basis": "jev typed decision",
               "judgement": None, "confidence": _conf_band(conf),
               "evidence": "coverage classified by Jev over the evidence brief",
               "confounds": None, "jev_confidence": conf, "jev_probabilities": probs}
        out.append(rec)
        if cov == "COV.RELEVANT_FOUND":
            need_jdg.append((c, rec))
    # second pass: judgement only for RELEVANT_FOUND constructs
    if need_jdg:
        jqs, jmap = {}, {}
        for i, (c, rec) in enumerate(need_jdg):
            qid = "jdg_%d" % i; jmap[qid] = rec
            jqs[qid] = _choice_question(
                f"Construct {c['id']} — {c['name']}. The evidence is relevant. What is the judgement?",
                JDG_OPTIONS)
        try:
            jraw = _post({"model": model(), "state": brief, "questions": jqs}, timeout=120)
            janswers = jraw.get("answers") or jraw.get("results") or {}
            for qid, rec in jmap.items():
                jdg, jconf, _ = _parse_answer(janswers.get(qid), JDG_OPTIONS)
                rec["judgement"] = jdg
                if jconf is not None: rec["confidence"] = _conf_band(jconf)
        except Exception:
            pass
    return {"domain_relevance": "assessed per-construct via Jev typed decisions", "constructs": out}

if __name__ == "__main__":
    import sys
    if not available():
        print("TYPESAFE_API_KEY not set — export it first (never commit it)."); sys.exit(1)
    print(f"endpoint={endpoint()} model={model()}")
    print(json.dumps(probe(), indent=2)[:3000])

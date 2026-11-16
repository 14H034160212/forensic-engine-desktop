"""
Compact-vs-full evaluation harness.

Measures, for any Tarski Telemetry episode, what is gained by reasoning over a COMPACT learner-side view
instead of the full evidence stream — the two things Kerry asked for:
  (1) LLM INPUT-TOKEN REDUCTION  — how much less the DRE has to read, measured from the model's own
      prompt_eval_count (not estimated), summed over every call.
  (2) FINDING PRESERVATION       — does the compact run still surface the important findings the full run
      produced? Compared by canonical construct id (D##.NAME), plus kept / lost / compact-only sets.

The compact view here is a deterministic reduction (drop the AI reply bodies, keep the learner's prompts,
edits, copies and pastes), standing in for the Ingester when its own output is not available; point --compact
at a real Ingester file to score that instead. temperature is forced to 0 so the only variable is the input.

This is a MEASUREMENT tool, not part of the shipped app. It changes no engine behaviour.

Usage:
  python3 compact_vs_full_eval.py --episode EP.jsonl --taxonomy TAX.md [--model mistral-small:latest]
                                  [--compact COMPACT.jsonl] [--out DIR] [--ollama http://127.0.0.1:11434]
Needs an Ollama serving --model. Prints a summary and writes <out>/compact_vs_full_report.json.
"""
import argparse, json, os, re, sys, tempfile, time, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dre_core, dre_reason

AI_REPLY_KINDS = {"AI_RESPONSE", "AI_RESPONSE_AMENDED", "AI_MESSAGE_OBSERVED"}
_TOK = {"n": 0, "prompt": 0, "eval": 0}


def _instrument():
    """Replace dre_reason._chat with a temperature-0, token-counting version (same request otherwise)."""
    def _chat(system, user, temperature=0.0, num_predict=4096):
        body = {"model": dre_reason.MODEL, "stream": False,
                "options": {"temperature": 0, "num_ctx": 16384, "num_predict": num_predict},
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
        if any(f in dre_reason.MODEL.lower() for f in ("gpt-oss", "qwq", "deepseek-r1", "qwen3", "magistral")):
            body["think"] = False
        data = json.dumps(body).encode()
        for attempt in range(3):
            try:
                req = urllib.request.Request(dre_reason.OLLAMA + "/api/chat", data=data,
                                             headers={"Content-Type": "application/json"})
                r = json.load(urllib.request.urlopen(req, timeout=600))
                _TOK["n"] += 1
                _TOK["prompt"] += int(r.get("prompt_eval_count") or 0)
                _TOK["eval"] += int(r.get("eval_count") or 0)
                c = (r.get("message") or {}).get("content", "")
                if c.strip():
                    return c
            except Exception:
                pass
            time.sleep(2 * (attempt + 1))
        return ""
    dre_reason._chat = _chat


def _constructs(report):
    ids = set()
    for f in report.get("findings", []):
        ids |= set(re.findall(r"\b(D\d{2}\.[A-Z_]+)\b", json.dumps(f)))
    return ids


def _run(events_path, taxonomy, tag):
    _TOK.update(n=0, prompt=0, eval=0)
    tax, ep, obs = dre_core.load_all(events_path, taxonomy)
    outdir = tempfile.mkdtemp()
    t0 = time.time()
    internal, report = dre_reason.run(tax, ep, obs, outdir)
    secs = int(time.time() - t0)
    res = {"tag": tag, "events": ep["n_events"], "input_tokens": _TOK["prompt"], "calls": _TOK["n"],
           "n_findings": len(report.get("findings", [])), "constructs": sorted(_constructs(report)),
           "headline": report.get("headline", ""), "secs": secs}
    print(f"[{tag}] events={res['events']} input_tokens={res['input_tokens']} (calls {res['calls']}) "
          f"findings={res['n_findings']} constructs={len(res['constructs'])} {secs}s")
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--episode", required=True, help="full TT episode (.jsonl / folder / manifest)")
    ap.add_argument("--taxonomy", required=True)
    ap.add_argument("--compact", help="a ready compact file (e.g. Ingester output); default: derive it here")
    ap.add_argument("--model", default=os.environ.get("DRE_MODEL", "mistral-small:latest"))
    ap.add_argument("--ollama", default=os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434"))
    ap.add_argument("--out", default=tempfile.mkdtemp())
    a = ap.parse_args()
    os.environ["OLLAMA_HOST"] = a.ollama
    dre_reason.OLLAMA = a.ollama.rstrip("/")
    dre_reason.MODEL = a.model
    os.environ["DRE_INGEST_ADAPTER"] = os.environ.get("DRE_INGEST_ADAPTER", "auto")
    _instrument()
    os.makedirs(a.out, exist_ok=True)

    full = _run(a.episode, a.taxonomy, "FULL")

    if a.compact:
        compact_path = a.compact
        red_note = f"supplied compact file {os.path.basename(a.compact)}"
    else:
        events = dre_core.load_events(a.episode)
        reduced = [e for e in events if e.get("kind") not in AI_REPLY_KINDS]
        compact_path = os.path.join(a.out, "student_actions_only.jsonl")
        with open(compact_path, "w", encoding="utf-8") as f:
            for e in reduced:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")
        rb = sum(len(json.dumps(e)) for e in events) or 1
        cb = sum(len(json.dumps(e)) for e in reduced)
        red_note = f"derived: dropped AI reply bodies, {len(events)}->{len(reduced)} events, {100*cb/rb:.1f}% of source bytes"
    print("reduction:", red_note)
    compact = _run(compact_path, a.taxonomy, "COMPACT")

    fc, cc = set(full["constructs"]), set(compact["constructs"])
    tok_red = round(100 * (1 - compact["input_tokens"] / full["input_tokens"]), 1) if full["input_tokens"] else None
    out = {"model": a.model, "episode": a.episode, "reduction": red_note,
           "input_token_reduction_pct": tok_red,
           "full": full, "compact": compact,
           "findings_kept": sorted(fc & cc), "findings_lost": sorted(fc - cc),
           "findings_compact_only": sorted(cc - fc),
           "preservation": f"{len(fc & cc)}/{len(fc)} full constructs kept" if fc else "n/a"}
    json.dump(out, open(os.path.join(a.out, "compact_vs_full_report.json"), "w", encoding="utf-8"), indent=2)
    print("\n========== RESULT ==========")
    print(f"INPUT-TOKEN REDUCTION: {full['input_tokens']} -> {compact['input_tokens']} = {tok_red}% fewer")
    print(f"FINDING PRESERVATION: {out['preservation']}; lost {out['findings_lost']}; compact-only {out['findings_compact_only']}")
    print(f"report -> {os.path.join(a.out, 'compact_vs_full_report.json')}")
    print("\nNOTE: token reduction is only representative on a LARGE episode where AI replies dominate the "
          "stream; on a tiny episode the DRE already reads little AI text, so the saving is near zero.")


if __name__ == "__main__":
    main()

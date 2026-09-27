"""
Tarski DRE — deterministic core: taxonomy loader, telemetry evidence ingest, and the
analytical-observation layer (raw evidence -> analytical observations, evidence-graded,
with pointers back to source events). No interpretation/judgement here — that is the
reasoning layer. Honours the canonical evidence rules: TT evidence is immutable; every
derivation preserves its basis and pointers; OBSERVED/DERIVED/INFERRED/EVALUATED are distinct;
missing evidence is preserved as a capture gap, never converted into certainty.
"""
import json, re, hashlib, os
from collections import Counter, defaultdict

# ----------------------------------------------------------------- taxonomy
def load_taxonomy(md_path):
    raw = open(md_path, "rb").read()
    sha = hashlib.sha256(raw).hexdigest()
    text = raw.decode("utf-8")
    ver = (re.search(r'taxonomy_version:\s*"?([^"\n]+)"?', text) or [None, "?"])[1]
    domains, constructs, vocab = {}, {}, defaultdict(dict)
    cur_domain = None
    for block in re.split(r'\n(?=#{1,3} )', text):
        h = block.splitlines()[0].strip()
        m_dom = re.match(r'# (D\d\d) — (.+)', h)
        m_con = re.match(r'## (D\d\d\.[A-Z_]+)', h)
        m_voc = re.match(r'### ([A-Z]+\.[A-Z0-9_]+)', h)
        if m_dom:
            cur_domain = m_dom.group(1)
            q = (re.search(r'\*\*Question:\*\*\s*(.+)', block) or [None, ""])[1].strip()
            domains[cur_domain] = {"id": cur_domain, "name": m_dom.group(2).strip(), "question": q}
        elif m_con:
            cid = m_con.group(1)
            name = (re.search(r'\*\*Name:\*\*\s*(.+)', block) or [None, ""])[1].strip()
            era = (re.search(r'\*\*Era:\*\*\s*(.+)', block) or [None, ""])[1].strip()
            guide = (re.search(r'\*\*Guidepost:\*\*\s*(.+)', block) or [None, ""])[1].strip()
            constructs[cid] = {"id": cid, "domain": cid.split(".")[0], "name": name,
                               "era": era, "guidepost": guide}
        elif m_voc:
            vid = m_voc.group(1); fam = vid.split(".")[0]
            label = (re.search(r'\*\*Label:\*\*\s*(.+)', block) or [None, ""])[1].strip()
            vocab[fam][vid] = label
    return {"version": ver, "sha256": sha, "domains": domains,
            "constructs": constructs, "vocab": dict(vocab), "md_path": md_path}

# ----------------------------------------------------------------- evidence ingest
def load_events(jsonl_path):
    return [json.loads(l) for l in open(jsonl_path, encoding="utf-8") if l.strip()]

def _g(e, *ks, default=""):
    for k in ks:
        if e.get(k) not in (None, ""):
            return e[k]
    return default

def ingest(events):
    by_kind = defaultdict(list)
    for e in events:
        by_kind[e.get("kind")].append(e)
    start = (by_kind.get("SESSION_START") or [{}])[0]
    ep = {
        "episode_id": _g(start, "episode_id") or (events[0].get("episode_id") if events else ""),
        "episode_name": _g(start, "episode_name"),
        "author_label": _g(start, "author_label"),
        "recorder_version": _g(start, "recorder_version", default=events[0].get("recorder_version","")),
        "started_at": _g(start, "observed_at", default=events[0].get("observed_at","")),
        "ended_at": events[-1].get("observed_at", "") if events else "",
        "n_events": len(events),
        "kinds": dict(Counter(e.get("kind") for e in events)),
        "grades": dict(Counter(e.get("evidence_grade") for e in events)),
    }
    baseline = by_kind.get("DOCUMENT_BASELINE") or []
    ep["baselines"] = [{"doc": _g(b, "document_name"), "chars": _g(b, "chars", default=0),
                        "text": _g(b, "text")} for b in baseline]
    ep["baseline_text"] = (baseline[0].get("text") if baseline else "") or ""
    fin = by_kind.get("DOCUMENT_FINAL_TEXT") or []
    ep["final_text"] = (fin[0].get("text") if fin else "") or ""
    ep["final_chars"] = int(_g(fin[0], "chars", default=0)) if fin else 0

    # AI turns: prompts and responses, paired loosely by conversation + ordinal/sequence
    prompts = by_kind.get("AI_PROMPT") or []
    responses = by_kind.get("AI_RESPONSE") or []
    resp_started = by_kind.get("AI_RESPONSE_STARTED") or []
    turns = []
    for p in prompts:
        turns.append({"role": "prompt", "seq": int(_g(p, "global_sequence", default=0)),
                      "provider": _g(p, "provider"), "chars": _g(p, "chars", default=0),
                      "full_text_present": p.get("full_text_present"),
                      "text": _g(p, "text"), "event_id": p.get("event_id"),
                      "observed_at": _g(p, "observed_at")})
    for r in responses:
        turns.append({"role": "response", "seq": int(_g(r, "global_sequence", default=0)),
                      "provider": _g(r, "provider"), "chars": _g(r, "chars", default=0),
                      "full_text_present": r.get("full_text_present"),
                      "completion_state": _g(r, "completion_state"),
                      "text": _g(r, "text"), "event_id": r.get("event_id"),
                      "observed_at": _g(r, "observed_at")})
    turns.sort(key=lambda t: t["seq"])
    ep["ai_turns"] = turns
    ep["providers"] = sorted({t["provider"] for t in turns if t["provider"]})

    # doc changes
    inserts = by_kind.get("DOC_INSERT") or []
    ep["doc_inserts"] = [{"chars": _g(i, "chars", default=0), "classification": _g(i, "classification"),
                          "classification_basis": _g(i, "classification_basis"),
                          "text": _g(i, "text"), "event_id": i.get("event_id"),
                          "seq": int(_g(i, "global_sequence", default=0))} for i in inserts]
    ep["doc_edits"] = len(by_kind.get("DOC_EDIT") or [])
    ep["doc_whitespace"] = len(by_kind.get("DOC_WHITESPACE_CHANGE") or [])

    # transfers (AI/source -> document)
    ep["copies"] = len(by_kind.get("COPY") or [])
    ep["pastes"] = len(by_kind.get("PASTE") or [])
    ep["transfers"] = len(by_kind.get("TRANSFER_EVIDENCE") or [])

    # exposure / reading (cap each segment; raw visible_ms double-counts re-exposures)
    exp = by_kind.get("SOURCE_SEGMENT_EXPOSURE") or []
    CAP = 30000  # 30s per segment cap to avoid inflated totals from re-exposure/duplicates
    capped = sum(min(int(_g(x, "visible_ms", default=0) or 0), CAP) for x in exp)
    ep["exposure"] = {"segments": len(exp), "approx_read_seconds_capped": capped // 1000,
                      "providers": dict(Counter(_g(x, "provider", default="?") for x in exp)),
                      "note": "per-segment capped at 30s; raw visible time double-counts re-exposures."}

    # capture gaps (the known limitation: some AI replies not fully present)
    n_started, n_resp = len(resp_started), len(responses)
    missing_responses = max(0, n_started - n_resp)   # responses that began but were not fully captured
    cap_lim = by_kind.get("CAPTURE_LIMITATION") or []
    conn_gaps = by_kind.get("CONNECTOR_GAP_START") or []
    ep["capture_gaps"] = {
        "responses_started_not_fully_captured": missing_responses,
        "response_started_events": n_started, "response_events": n_resp,
        "capture_limitation_events": len(cap_lim), "connector_gap_events": len(conn_gaps),
        "note": "Browser capture was still being hardened; ~{} ChatGPT replies began but were not "
                "captured in full. Missing evidence is preserved, not reconstructed; reasoning over "
                "those turns must keep uncertainty.".format(missing_responses)}
    return ep

# ----------------------------------------------------------------- observation layer
def derive_observations(ep):
    """Raw evidence -> analytical observations. Each carries evidence grade + pointers +
    time window + capture limitations. Deterministic; no judgement about the learner."""
    obs = []
    def add(oid, grade, text, pointers, **extra):
        o = {"observation_id": oid, "evidence_grade": grade, "text": text,
             "evidence_pointers": pointers, "capture_limitations": ""}
        o.update(extra); obs.append(o)

    # O1 — session shape
    add("OBS.SESSION_SHAPE", "DERIVED",
        f"Self-directed session by {ep['author_label']}. {len(ep['ai_turns'])} AI interaction events "
        f"({sum(1 for t in ep['ai_turns'] if t['role']=='prompt')} prompts, "
        f"{sum(1 for t in ep['ai_turns'] if t['role']=='response')} responses) with provider(s) "
        f"{', '.join(ep['providers']) or 'n/a'}; {len(ep['doc_inserts'])} document inserts, "
        f"{ep['doc_edits']} edits. Working document: "
        f"{', '.join(b['doc'] for b in ep['baselines']) or 'n/a'}.",
        pointers=["SESSION_START"], derived_from="kinds")

    # O2 — transcription vs original authorship (the key AI-era signal)
    ins = ep["doc_inserts"]
    tot = sum(i["chars"] or 0 for i in ins)
    transfer = sum((i["chars"] or 0) for i in ins if "TRANSFER" in (i["classification"] or "").upper())
    original = tot - transfer
    frac = (transfer / tot) if tot else 0.0
    add("OBS.TRANSCRIPTION_VS_AUTHORSHIP", "DERIVED",
        f"Of {tot} characters inserted into the document, {transfer} ({frac:.0%}) are classified "
        f"TRANSFER_CORRELATED (moved from an AI/source via copy-paste) and {original} ({1-frac:.0%}) "
        f"were entered without a correlated transfer. (Copy≠understanding; this is a provenance signal, "
        f"not a judgement of learning.)",
        pointers=[i["event_id"] for i in ins][:40],
        transfer_chars=transfer, original_chars=original, transfer_fraction=round(frac, 3))

    # O3 — reading / exposure to AI output
    ex = ep["exposure"]
    add("OBS.AI_OUTPUT_EXPOSURE", "DERIVED",
        f"AI/source content was on screen across {ex['segments']} exposed segments (~{ex['approx_read_seconds_capped']}s "
        f"capped visible time; providers: {ex['providers']}). Exposure≠comprehension.",
        pointers=["SOURCE_SEGMENT_EXPOSURE"], **{k: ex[k] for k in ('segments','approx_read_seconds_capped','providers')})

    # O4 — prompting behaviour (texts preserved for the reasoning layer)
    proms = [t for t in ep["ai_turns"] if t["role"] == "prompt" and t.get("text")]
    add("OBS.PROMPTS", "OBSERVED",
        f"{len(proms)} learner prompts captured with full text (lengths "
        f"{[p['chars'] for p in proms][:12]}). Texts preserved for capability reasoning.",
        pointers=[p["event_id"] for p in proms][:40],
        prompt_texts=[{"seq": p["seq"], "chars": p["chars"], "text": p["text"]} for p in proms])

    # O5 — capture gaps preserved
    g = ep["capture_gaps"]
    add("OBS.CAPTURE_GAPS", "OBSERVED",
        f"~{g['responses_started_not_fully_captured']} AI responses began but were not captured in full "
        f"({g['response_started_events']} started vs {g['response_events']} fully captured); "
        f"{g['capture_limitation_events']} explicit capture-limitation events. Preserved as missing "
        f"evidence; not reconstructed.",
        pointers=["AI_RESPONSE_STARTED", "CAPTURE_LIMITATION"],
        capture_limitations="Reasoning over these turns must preserve uncertainty.")

    # O6 — revision / execution activity
    add("OBS.REVISION_ACTIVITY", "DERIVED",
        f"{ep['doc_edits']} edit events and {ep['doc_whitespace']} whitespace changes beyond initial "
        f"insertion; {ep['copies']} copies, {ep['pastes']} pastes, {ep['transfers']} transfer-evidence links.",
        pointers=["DOC_EDIT", "COPY", "PASTE", "TRANSFER_EVIDENCE"])
    return obs

# ----------------------------------------------------------------- convenience
def load_all(events_path, taxonomy_md, artifact_docx=None):
    tax = load_taxonomy(taxonomy_md)
    ep = ingest(load_events(events_path))
    # Prefer the artifact text captured in the telemetry itself (authoritative, in-episode).
    ep["artifact_text"] = ep.get("final_text", "")
    if not ep["artifact_text"] and artifact_docx and os.path.exists(artifact_docx):
        try:
            import docx
            d = docx.Document(artifact_docx)
            ep["artifact_text"] = "\n".join(p.text for p in d.paragraphs if p.text.strip())
        except Exception as ex:
            ep["artifact_error"] = str(ex)
    obs = derive_observations(ep)
    return tax, ep, obs

if __name__ == "__main__":
    import sys
    RES = os.path.join(os.path.dirname(__file__), "resources")
    tax, ep, obs = load_all(
        os.path.join(RES, "sample_episode.jsonl"),
        os.path.join(RES, "demo_taxonomy.md"))
    print(f"TAXONOMY v{tax['version']}  sha256={tax['sha256'][:16]}…  "
          f"{len(tax['domains'])} domains, {len(tax['constructs'])} constructs, "
          f"vocab families={list(tax['vocab'])}")
    print(f"\nEPISODE {ep['episode_name']}  author={ep['author_label']}  "
          f"events={ep['n_events']}  providers={ep['providers']}")
    print(f"  kinds={ep['kinds']}")
    print(f"  artifact_text chars={len(ep.get('artifact_text',''))}")
    print("\nANALYTICAL OBSERVATIONS:")
    for o in obs:
        print(f"\n[{o['evidence_grade']}] {o['observation_id']}")
        print("  " + o["text"])

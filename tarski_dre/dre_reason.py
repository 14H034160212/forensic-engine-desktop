"""
Tarski DRE — reasoning + reporting layer (Passes 1-7).
Walks the canonical domains, assigns a coverage state to every construct (coarse-to-fine),
evaluates the constructs genuinely in play, then synthesises a small, significant teacher/student
report. Honours the taxonomy contract: controlled-vocabulary identifiers are authoritative;
no forced score; missing evidence preserves uncertainty; copy != understanding, exposure !=
comprehension; every finding is stamped with construct_id + taxonomy_version + taxonomy SHA-256.
LLM backend = Ollama (configurable). Internal reasoning is preserved in full; the report is selective.
"""
import json, os, re, time, urllib.request
from collections import Counter

OLLAMA = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
MODEL = os.environ.get("DRE_MODEL", "mistral-small:latest")

def _chat(system, user, temperature=0.2, num_predict=4096):
    body = {"model": MODEL, "stream": False,
            "options": {"temperature": temperature, "num_ctx": 16384, "num_predict": num_predict},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    if any(f in MODEL.lower() for f in ("gpt-oss", "qwq", "deepseek-r1", "qwen3", "magistral")):
        body["think"] = False   # keep reasoning out of the JSON body for reasoning-native models
    data = json.dumps(body).encode()
    for attempt in range(3):
        try:
            req = urllib.request.Request(OLLAMA + "/api/chat", data=data,
                                         headers={"Content-Type": "application/json"})
            r = json.load(urllib.request.urlopen(req, timeout=600))
            c = (r.get("message") or {}).get("content", "")
            if c.strip():
                return c
        except Exception:
            pass
        time.sleep(2 * (attempt + 1))
    return ""

def _json(txt):
    m = re.search(r"\{.*\}", txt or "", re.S)
    if not m: return None
    try: return json.loads(m.group(0))
    except Exception:
        s = m.group(0)
        # light salvage: strip trailing commas
        s = re.sub(r",\s*([}\]])", r"\1", s)
        try: return json.loads(s)
        except Exception: return None

def evidence_brief(ep, obs):
    proms = next((o for o in obs if o["observation_id"] == "OBS.PROMPTS"), {})
    ptexts = "\n".join(f"  P{p['seq']}: {p['text'][:400]}" for p in proms.get("prompt_texts", [])[:25])
    lines = ["ANALYTICAL OBSERVATIONS (deterministic, evidence-graded):"]
    for o in obs:
        lines.append(f"- [{o['evidence_grade']}] {o['observation_id']}: {o['text']}")
    brief = "\n".join(lines)
    base = (ep.get("baseline_text", "") or "")[:1500]
    fin = (ep.get("artifact_text", "") or "")[:3000]
    return (f"EPISODE: {ep['episode_name']} · learner {ep['author_label']} · provider(s) {ep['providers']}\n\n"
            f"{brief}\n\n"
            f"LEARNER PROMPTS (verbatim):\n{ptexts}\n\n"
            f"PRE-EXISTING DOCUMENT (baseline, before the session):\n{base}\n\n"
            f"FINAL DOCUMENT (learner artifact after the session):\n{fin}\n\n"
            f"CAPTURE LIMITATION: {ep['capture_gaps']['note']}")

SYS = (
 "You are the Tarski Deep Reasoning Engine, reasoning over verifiable learning telemetry against a "
 "canonical taxonomy of learning capabilities. Follow this contract exactly:\n"
 "- Reason broadly; the taxonomy is your search landscape, not a checklist. Most constructs will have "
 "NO meaningful opportunity in a single naturalistic episode — that is a valid, expected result, never a weakness.\n"
 "- Use ONLY these coverage identifiers: COV.RELEVANT_FOUND, COV.RELEVANT_INSUFFICIENT, COV.NO_OPPORTUNITY, "
 "COV.NOT_RELEVANT, COV.NO_MATERIAL_FINDING. Judgement (only when COV.RELEVANT_FOUND): JDG.CONCERN, JDG.MIXED, "
 "JDG.SUPPORTIVE, JDG.STRONG.\n"
 "- Evidence discipline: copy != understanding; exposure != comprehension; temporal sequence != causation; "
 "AI assistance != AI substitution. Missing/incomplete evidence stays uncertain — never convert a capture gap "
 "into certainty in either direction. Each observation has ONE primary construct home; do not double-count it.\n"
 "- No forced score. Judge only where evidence is genuinely adequate. Give a one-line basis for EVERY coverage state.\n"
 "- SELECTIVITY: in a single naturalistic episode, EXPECT the majority of constructs to be "
 "COV.NO_OPPORTUNITY or COV.NOT_RELEVANT. Only use COV.RELEVANT_FOUND when concrete provenance evidence "
 "(a specific prompt, insert, transfer or artifact passage) actually demonstrates the construct; use "
 "COV.RELEVANT_INSUFFICIENT when it is touched but too thin to judge. Do not mark a construct in play "
 "merely because it is plausible.\n"
 "Output STRICT JSON only.")

def reason_domain(dom, constructs, brief):
    clist = "\n".join(f"  {c['id']} — {c['name']} (era {c['era']}): {c['guidepost']}" for c in constructs)
    user = (f"DOMAIN {dom['id']} — {dom['name']}\nCore question: {dom['question']}\n\n"
            f"CONSTRUCTS (assign a coverage state to EACH):\n{clist}\n\n"
            f"EVIDENCE:\n{brief}\n\n"
            "Return STRICT JSON:\n"
            '{"domain_relevance":"<=1 line: is this domain in play here, and why>",'
            '"constructs":[{"id":"'+dom['id']+'.XXX","coverage":"COV.*","basis":"<=1 line",'
            '"judgement":"JDG.* or null (only if COV.RELEVANT_FOUND)","confidence":"low|moderate|high or null",'
            '"evidence":"which observations/prompt-refs support this","confounds":"alternatives / capture limits or null"}]}')
    out = _chat(SYS, user)
    j = _json(out)
    return j or {"domain_relevance": "(parse failed)", "constructs": [], "_raw": out[:400]}

def synthesise(tax, ep, findings_in_play, brief):
    fl = "\n".join(f"- {f['id']} [{f.get('coverage')}/{f.get('judgement')}] {f.get('basis','')} "
                   f"(evidence: {f.get('evidence','')})" for f in findings_in_play[:40])
    user = (f"You have completed a broad coverage walk of the taxonomy for this episode. The constructs "
            f"genuinely in play, with episode judgements, are:\n{fl}\n\nEVIDENCE CONTEXT:\n{brief}\n\n"
            "Now write the SELECTIVE teacher-facing report. Report only what a thoughtful teacher most "
            "needs to notice — usually 3-6 findings ranked by educational significance, in plain language. "
            "Developmental change may outrank absolute level; avoid turning every mixed signal into a warning; "
            "do not list the dark taxonomy. Return STRICT JSON:\n"
            '{"headline":"<=1 sentence overall impression of THIS episode (not the learner as a person)",'
            '"findings":[{"finding":"plain-language, cite the construct in brackets e.g. [D10.COGNITIVE_LOAD_OFFLOADING]",'
            '"significance":"why a teacher should care now","evidence":"the provenance basis","confidence":"low|moderate|high"}],'
            '"strength_to_leverage":"a demonstrated capability to build on, or null",'
            '"next_learning_opportunity":"the smallest useful next task/prompt/condition",'
            '"how_the_learner_used_ai":"1-2 plain sentences",'
            '"important_uncertainty":"what the capture gaps or thin evidence prevent us from claiming"}')
    return _json(_chat(SYS, user, num_predict=3000)) or {"headline": "(synthesis parse failed)"}

def synthesise_student(ep, teacher_report, brief):
    tf = json.dumps(teacher_report)[:2500]
    user = (f"Here is the internal teacher analysis of {ep['author_label']}'s learning session:\n{tf}\n\n"
            "Rewrite it as a short, warm, encouraging note TO THE LEARNER (second person, plain language, "
            "no jargon, no construct codes). Be specific and honest, affirm what they genuinely did well, "
            "and give ONE concrete next step. Keep it to a few short paragraphs. Return STRICT JSON:\n"
            '{"note":"the full learner-facing note as a few short paragraphs",'
            '"you_did_well":["2-4 short plain bullets"],"one_next_step":"one concrete thing to try next"}')
    return _json(_chat(SYS, user, num_predict=1800)) or {"note": "(student synthesis parse failed)"}

def run(tax, ep, obs, outdir, progress=None):
    """progress(stage, done, total, note) — optional callback so a UI can show live progress.
    stage is 'domain' during the coverage walk, then 'synthesise'/'student'/'done'."""
    def _p(stage, done, total, note=""):
        if progress:
            try: progress(stage, done, total, note)
            except Exception: pass
    os.makedirs(outdir, exist_ok=True)
    brief = evidence_brief(ep, obs)
    stamp = {"construct id stamped per finding": True, "taxonomy_version": tax["version"],
             "taxonomy_sha256": tax["sha256"]}
    # Pass 1-3: coverage traversal + evaluation, domain by domain (coarse-to-fine)
    domain_results = {}
    all_constructs_by_dom = {}
    for c in tax["constructs"].values():
        all_constructs_by_dom.setdefault(c["domain"], []).append(c)
    findings_in_play = []
    CHUNK = 12   # cap constructs per LLM call so the JSON reply is never truncated (fixes large domains like D06)
    dom_ids = sorted(tax["domains"])
    ndoms = len(dom_ids)
    for di, did in enumerate(dom_ids):
        dom = tax["domains"][did]
        cons = all_constructs_by_dom.get(did, [])
        _p("domain", di, ndoms, f"{did} — {dom['name']}")
        merged = {"domain_relevance": "", "constructs": []}
        for i in range(0, len(cons), CHUNK):
            part = reason_domain(dom, cons[i:i+CHUNK], brief)
            if part.get("domain_relevance") and not merged["domain_relevance"]:
                merged["domain_relevance"] = part["domain_relevance"]
            merged["constructs"].extend(part.get("constructs", []))
        res = merged
        # stamp every construct finding
        for cf in res.get("constructs", []):
            cf["construct_id"] = cf.get("id")
            cf["taxonomy_version"] = tax["version"]
            cf["taxonomy_sha256"] = tax["sha256"]
            if cf.get("coverage") in ("COV.RELEVANT_FOUND", "COV.RELEVANT_INSUFFICIENT"):
                findings_in_play.append(cf)
        domain_results[did] = res
        in_play_n = sum(1 for c in res.get('constructs',[]) if c.get('coverage') in ('COV.RELEVANT_FOUND','COV.RELEVANT_INSUFFICIENT'))
        print(f"  {did} {dom['name'][:34]:34} — in play: {in_play_n}/{len(res.get('constructs',[]))}", flush=True)
        _p("domain", di + 1, ndoms, f"{did} in play {in_play_n}/{len(res.get('constructs',[]))}")
    # Pass 6-7: significance synthesis + teacher report + student report
    _p("synthesise", ndoms, ndoms, "Writing the teacher report")
    report = synthesise(tax, ep, findings_in_play, brief)
    _p("student", ndoms, ndoms, "Writing the student reflection")
    student = synthesise_student(ep, report, brief)

    internal = {"episode": {k: ep[k] for k in ("episode_id","episode_name","author_label","recorder_version",
                                               "started_at","ended_at","providers","capture_gaps")},
                "taxonomy": {"version": tax["version"], "sha256": tax["sha256"]},
                "observations": obs, "coverage_walk": domain_results,
                "constructs_in_play": findings_in_play}
    json.dump(internal, open(os.path.join(outdir, "internal_consideration.json"), "w"), indent=2)
    json.dump(report, open(os.path.join(outdir, "report.json"), "w"), indent=2)
    json.dump(student, open(os.path.join(outdir, "student.json"), "w"), indent=2)
    _write_report_md(tax, ep, obs, findings_in_play, report, os.path.join(outdir, "teacher_report.md"))
    _write_student_md(tax, ep, student, os.path.join(outdir, "student_report.md"))
    # coverage summary for quick audit
    cov = Counter()
    for d in domain_results.values():
        for c in d.get("constructs", []): cov[c.get("coverage")] += 1
    internal["coverage_summary"] = dict(cov)
    json.dump(internal, open(os.path.join(outdir, "internal_consideration.json"), "w"), indent=2)
    _p("done", ndoms, ndoms, "Reports ready")
    return internal, report

def _write_report_md(tax, ep, obs, in_play, report, path):
    L = []
    L.append(f"# Tarski DRE — Learning Report")
    L.append(f"*Episode: {ep['episode_name']} · learner: {ep['author_label']} · "
             f"taxonomy v{tax['version']} (sha256 {tax['sha256'][:12]}…)*\n")
    L.append(f"**{report.get('headline','')}**\n")
    L.append("## Most important findings")
    for f in report.get("findings", []):
        L.append(f"- **{f.get('finding','')}**  \n  _Why it matters:_ {f.get('significance','')}  "
                 f"_Evidence:_ {f.get('evidence','')} · _confidence:_ {f.get('confidence','')}")
    if report.get("strength_to_leverage"):
        L.append(f"\n**Strength to leverage:** {report['strength_to_leverage']}")
    if report.get("next_learning_opportunity"):
        L.append(f"\n**Next useful learning opportunity:** {report['next_learning_opportunity']}")
    if report.get("how_the_learner_used_ai"):
        L.append(f"\n**How the learner used AI:** {report['how_the_learner_used_ai']}")
    if report.get("important_uncertainty"):
        L.append(f"\n**Important uncertainty:** {report['important_uncertainty']}")
    L.append(f"\n---\n_Coverage walk: {len(tax['constructs'])} constructs across {len(tax['domains'])} "
             f"domains considered; {len(in_play)} in play. Full reasoning and evidence preserved in "
             f"`internal_consideration.json` (drill-down + audit). Reason broadly · Report selectively · "
             f"Preserve everything underneath._")
    open(path, "w").write("\n".join(L))

def _write_student_md(tax, ep, student, path):
    L = [f"# Your learning session — a quick reflection",
         f"*{ep['episode_name']} · generated by the Tarski Deep Reasoning Engine*\n"]
    L.append(student.get("note", ""))
    if student.get("you_did_well"):
        L.append("\n**What you did well**")
        for b in student["you_did_well"]:
            L.append(f"- {b}")
    if student.get("one_next_step"):
        L.append(f"\n**One thing to try next:** {student['one_next_step']}")
    L.append("\n---\n_This reflection is based only on what the session recorded, and some of the AI's "
             "replies weren't fully captured — so treat it as a helpful mirror, not a final verdict._")
    open(path, "w").write("\n".join(L))

if __name__ == "__main__":
    import dre_core
    RES = os.path.join(os.path.dirname(__file__), "resources")
    tax, ep, obs = dre_core.load_all(
        os.path.join(RES, "sample_episode.jsonl"),
        os.path.join(RES, "demo_taxonomy.md"))
    print(f"DRE reasoning · model={MODEL} · taxonomy v{tax['version']} · {len(tax['constructs'])} constructs")
    t0 = time.time()
    internal, report = run(tax, ep, obs, os.path.join(os.path.dirname(__file__), "out"))
    print(f"\nDONE in {int(time.time()-t0)}s → out/teacher_report.md + out/internal_consideration.json")
    print("\n===== TEACHER REPORT =====")
    print(open(os.path.join(os.path.dirname(__file__), "out", "teacher_report.md")).read())
    print("\n===== STUDENT REPORT =====")
    print(open(os.path.join(os.path.dirname(__file__), "out", "student_report.md")).read())

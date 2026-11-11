"""
Tarski DRE — evidence selection.

The naive brief truncates every message to a few hundred characters and sends the same blob to every
domain. On a large Episode (the Market Analysis Episode carries ~875k characters of evidence against a
16k context) that silently hides most of the learner's own text and produces *plausible clean
negatives* — the engine reports a capability absent when the evidence for it simply never reached the
model. That failure is believed precisely because the run looks clean.

This module builds a FOCUSED, BUDGETED brief PER DOMAIN instead:
  * the deterministic analytical observations are always included (compact, high-signal);
  * the learner's own text is prioritised — every prompt in full, then document inserts/edits — because
    that is what a capability claim about the learner must rest on (and what truncation hides first);
  * AI responses and remaining inserts are RANKED by lexical relevance to the domain's own constructs
    (name + guidepost + the domain question) and packed until the budget is reached;
  * each item keeps its event id / sequence so a finding can still cite it.

It is deterministic and dependency-free. It does not read the taxonomy's answer key or any baseline —
it selects from the Episode evidence only. Relevance is a transparent term-overlap score, not a model,
so selection cannot hallucinate or leak.
"""
import re
from collections import OrderedDict

_STOP = set("the a an and or of to in on for with at by from is are was were be been being this that "
            "these those it its as into than then so such not no do does did has have had will would "
            "can could should may might must about over under their they them his her our your you i we "
            "he she but if when while which who whom whose what where how why all any each more most some "
            "one two use used using given only also may within per via".split())


def _terms(*texts):
    out = set()
    for t in texts:
        for w in re.findall(r"[a-zA-Z][a-zA-Z\-]{2,}", (t or "").lower()):
            if w not in _STOP:
                out.add(w)
    return out


def _score(item_text, dom_terms):
    toks = _terms(item_text[:800])
    return len(toks & dom_terms)


# Domain-agnostic markers of the HIGH-VALUE reasoning moments. A learner prompt that corrects, rejects,
# or asks the AI to restate is where counterexamples, caught regressions and gated regeneration live —
# and term-overlap ranks those no higher than routine prompts. We surface them on salience, for every
# domain, independent of any answer key.
_CRITIQUE = re.compile(
    r"\b(lost|lose|missing|removed?|dropped?|wrong|incorrect|mistake|error|instead|actually|should have|"
    r"shouldn'?t|redo|re-?do|re-?work|again|restate|tell me back|summaris|summariz|before you|don'?t|"
    r"why did|you (changed|removed|lost|missed)|not what|revise|revisit|reconsider|but |however|"
    r"doesn'?t|isn'?t|no longer|used to|previously|earlier)\b", re.I)


def _is_critique(text):
    t = text or ""
    return bool(_CRITIQUE.search(t[:1200]))


def _wordfreq(text):
    c = {}
    for w in re.findall(r"[a-zA-Z][a-zA-Z\-]{3,}", (text or "").lower()):
        if w not in _STOP:
            c[w] = c.get(w, 0) + 1
    return c


def change_cards(ep, max_cards=8):
    """Deterministic 'delta scaffold'. Between consecutive AI deliverables, surface prominent structural
    terms (repeated headers/columns) whose presence DROPS sharply in the later one — a concrete
    'lost-capability' signal — and flag when the learner references that term afterwards (the catch).

    This makes a GLOBAL_RECHECK / lost-then-restored finding reachable without the model having to spot
    it unaided across two very long deliverables. Blind and evidence-only: it compares Episode text,
    never an answer key; each card cites its events so a finding can still be grounded."""
    turns = sorted(ep.get("ai_turns", []), key=lambda t: t.get("seq") or 0)
    # the MAJOR deliverables, in time order (not every medium conversational turn)
    major = sorted([t for t in turns if t["role"] == "response" and len((t.get("text") or "")) >= 2500],
                   key=lambda t: len(t.get("text") or ""), reverse=True)[:6]
    major = sorted(major, key=lambda t: t.get("seq") or 0)
    prompts = [t for t in turns if t["role"] == "prompt" and t.get("text")]
    common = _STOP | set("there here work project step task please note yes okay sure thanks good "
                         "model chat answer response above below section point number list first second "
                         "next make made give given".split())
    seen, cards = set(), []
    for ia in range(len(major)):
        for ib in range(ia + 1, len(major)):
            a, b = major[ia], major[ib]
            fa, fb = _wordfreq(a["text"]), _wordfreq(b["text"])
            for w, na in fa.items():
                if na < 6 or len(w) < 5 or w in common or w in seen:
                    continue
                nb = fb.get(w, 0)
                if nb > na * 0.25:
                    continue
                # keep only drops the LEARNER then references (the 'catch' signal) — high precision
                later = next((p for p in prompts if (p.get("seq") or 0) > (b.get("seq") or 0)
                              and w in (p.get("text") or "").lower()), None)
                if not later:
                    continue
                seen.add(w)
                cards.append(f"- A repeated element '{w}' appears {na}× in AI deliverable #{a.get('seq')} "
                             f"but only {nb}× in the later #{b.get('seq')}, and the learner then referenced "
                             f"'{w}' in prompt #{later.get('seq')} — consider a caught regression / restore.")
                if len(cards) >= max_cards:
                    return cards
    return cards


def brief_for_domain(ep, obs, dom, constructs, budget=9000):
    """Domain-targeted, budgeted evidence brief. Returns (brief_text, included_event_seqs).

    Selection has two tiers: a SALIENCE pack included for every domain (the learner's own text, plus the
    critique/correction moments and the AI deliverables they act on — where the intellectual findings
    live), then a term-overlap fill of whatever budget remains. The returned seq list is the per-domain
    evidence manifest: what actually reached the reasoner, so a miss can be attributed to selection vs
    reasoning rather than guessed from a sparse report."""
    dom_terms = _terms(dom.get("name", ""), dom.get("question", ""),
                       *[c.get("name", "") for c in constructs],
                       *[c.get("guidepost", "") for c in constructs])
    included = []

    obs_lines = ["ANALYTICAL OBSERVATIONS (deterministic, evidence-graded):"]
    for o in obs:
        obs_lines.append(f"- [{o['evidence_grade']}] {o['observation_id']}: {o['text']}")
    obs_block = "\n".join(obs_lines)

    turns = sorted(ep.get("ai_turns", []), key=lambda t: t.get("seq") or 0)
    prompts = [t for t in turns if t["role"] == "prompt" and t.get("text")]
    responses = [t for t in turns if t["role"] == "response" and t.get("text")]
    for p in prompts:
        included.append(p.get("seq"))
    pblock = "\n".join(f"  P#{p.get('seq')}{' [CRITIQUE/CORRECTION]' if _is_critique(p['text']) else ''}: {p['text']}"
                       for p in prompts)

    # SALIENCE pack: the AI deliverables (longest responses) + the AI response immediately before each
    # critique prompt (what the learner is acting on). Included for every domain, ahead of the fill.
    salient_seqs = set()
    for r in sorted(responses, key=lambda t: len(t.get("text") or ""), reverse=True)[:3]:
        salient_seqs.add(r.get("seq"))
    crit_prompts = [p for p in prompts if _is_critique(p["text"])]
    for cp in crit_prompts:
        prior = [r for r in responses if (r.get("seq") or 0) < (cp.get("seq") or 0)]
        if prior:
            salient_seqs.add(prior[-1].get("seq"))   # the response just before the critique
    salient = [r for r in responses if r.get("seq") in salient_seqs]
    sal_lines, used = [], 0
    for r in sorted(salient, key=lambda t: t.get("seq") or 0):
        text = r["text"]
        snip = text if len(text) <= 3000 else text[:3000] + " …[deliverable truncated]"
        line = f"  [AI_DELIVERABLE #{r.get('seq')} {r.get('provider') or ''}]: {snip}"
        sal_lines.append(line); used += len(line); included.append(r.get("seq"))
    sal_block = "\n".join(sal_lines) if sal_lines else "  (none detected)"

    # term-overlap fill of the remaining budget: inserts + remaining responses
    pool = []
    for i in ep.get("doc_inserts", []):
        if i.get("text"):
            pool.append(("INSERT", i.get("seq"), i.get("classification") or "", i["text"]))
    for r in responses:
        if r.get("seq") not in salient_seqs:
            pool.append(("AI_RESPONSE", r.get("seq"), r.get("provider") or "", r["text"]))
    ranked = sorted(pool, key=lambda it: _score(it[3], dom_terms), reverse=True)
    picked = []
    for kind, seq, tag, text in ranked:
        if _score(text, dom_terms) == 0:
            break
        snippet = text if len(text) <= 1000 else text[:1000] + " …[truncated]"
        line = f"  [{kind} #{seq}{(' ' + tag) if tag else ''}]: {snippet}"
        if used + len(line) > budget:
            continue
        picked.append(line); used += len(line); included.append(seq)
        if used >= budget:
            break
    ev_block = "\n".join(picked) if picked else "  (no further domain-specific evidence)"

    try:
        cards = change_cards(ep)
    except Exception:
        cards = []
    change_block = ("\n".join(cards) if cards
                    else "  (no structural element detected as dropped between deliverables)")

    base = (ep.get("baseline_text", "") or "")[:800]
    fin = (ep.get("artifact_text", "") or "")[:3000]
    brief = (f"EPISODE: {ep['episode_name']} · learner {ep['author_label']} · provider(s) {ep['providers']}\n"
             f"DOMAIN IN FOCUS: {dom['id']} — {dom.get('name','')}\n\n"
             f"{obs_block}\n\n"
             f"DETECTED CHANGES ACROSS AI DELIVERABLES (deterministic; an element present in an earlier "
             f"deliverable that is largely gone from a later one — consider whether the learner noticed "
             f"and restored it, i.e. a global re-check / caught regression):\n{change_block}\n\n"
             f"LEARNER PROMPTS (verbatim, all; critique/correction moments flagged):\n{pblock}\n\n"
             f"AI DELIVERABLES THE LEARNER ACTED ON (so before/after changes are visible):\n{sal_block}\n\n"
             f"FURTHER EVIDENCE RELEVANT TO THIS DOMAIN (ranked; each cites its event):\n{ev_block}\n\n"
             f"PRE-EXISTING DOCUMENT (baseline):\n{base}\n\n"
             f"FINAL DOCUMENT (learner artifact):\n{fin}\n\n"
             f"CAPTURE LIMITATION: {ep['capture_gaps']['note']}\n"
             f"NOTE: this is a selection from a much larger Episode; absence here is NOT absence in the "
             f"Episode — keep coverage uncertain where the selector may not have surfaced the evidence.")
    return brief, [s for s in included if s is not None]

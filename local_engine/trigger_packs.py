#!/usr/bin/env python3
"""
Domain trigger-packs (candidate optimisation — ISOLATED, opt-in, ROUTED).

The Felix benchmark proved that some fatal flaws are DOMAIN-KNOWLEDGE-BOUND: the facts that make
the plan impossible are NOT in the document (a blind engine of any size cannot recover them). This
module injects encoded expert knowledge — a rulebook — but only AFTER a router confirms the pack
is relevant (so it never raises clinical-trial concerns on an unrelated SaaS deck).

Flow:
  route(deck) -> which packs apply (LLM classifier, conservative)
  run_pack(deck, pack) -> for each rule, does the document's plan VIOLATE / IGNORE it? -> findings

Findings come back in pass_two shape so scoring/rendering is unchanged. Reuses engine chat_json.
Enable in the engine only after it beats the gold benchmark without regressing on non-domain docs.
"""
import prosecution_engine as E

# Shared PRECISION PRINCIPLE — injected into both the holistic and per-rule prompts. Measured
# 2026-07-10: the medical_regulatory + trial_feasibility packs over-fired on genuinely CLEAN clinical
# documents (a sound biotech update drew 2-18 false charges across models), because they charged the
# mere ABSENCE of detail, or matched a rule keyword ("treat", small sample) while ignoring that the
# document had already ADDRESSED the point (explicit power calculation, explicit not-approved /
# investigational disclaimer, properly-hedged endpoint). This guard fixes that without touching recall.
_PRECISION = (
    "PRECISION PRINCIPLE (critical): only charge a DEFECT IN A CLAIM THE DOCUMENT ACTUALLY MAKES. "
    "Do NOT charge the mere absence of information in a document that is not overclaiming. Specifically, "
    "treat a rule as SATISFIED (do not flag) when the document already: (a) states a sample-size / power "
    "justification appropriate to its stated endpoint (do not impose a generic effect-size rule over the "
    "document's own power calculation); (b) explicitly discloses the product is investigational / not yet "
    "approved and makes no present efficacy or 'treats' claim beyond a stated trial endpoint (a described "
    "indication like 'for the treatment of X' under an explicit investigational disclaimer is NOT a "
    "regulatory overclaim); (c) appropriately hedges (scenario/conditional language, 'if the trial "
    "meets its endpoint', stated assumptions and uncertainties); or (d) already describes the "
    "safety/oversight structure the rule asks about. A properly-hedged, honestly-caveated statement is "
    "NOT a violation. Reserve charges for concrete claims the document's own text actually contradicts "
    "or cannot support."
)

# ---- Pack: comparative / outcome trial feasibility (encodes the expertise in Kerry's takedown) ----
TRIAL_FEASIBILITY = {
    "id": "trial_feasibility",
    "when": "the document proposes or relies on a clinical / comparative / outcome trial or study "
            "(efficacy, pre/post outcomes, comparison arms, health or mental-health improvement)",
    "rules": [
        {"id": "TF-power", "rule": "A comparative SUPERIORITY outcome trial needs a statistically "
         "powered sample — roughly 64 per arm to detect a moderate effect (d=0.5) at 80% power, and "
         "175+ per arm for small effects (d=0.3). Cohorts around 20 per arm are underpowered unless "
         "the advantage is very large."},
        {"id": "TF-sustained", "rule": "A claim of SUSTAINED or durable improvement requires follow-up "
         "of at least 3-6 months. A short endpoint (e.g. 8-10 weeks) can only measure the state at that "
         "point; it cannot establish durability or that improvement outlasts a comparator."},
        {"id": "TF-comparator", "rule": "Comparing against an ACTIVE comparator (e.g. a generic LLM/AI "
         "coach) is a far harder bar than a waitlist or no-treatment control, because active AI tools "
         "already produce measurable short-term symptom improvement. Detecting an incremental advantage "
         "over an active comparator needs a larger sample, not a smaller one."},
        {"id": "TF-safety", "rule": "Recruiting subjects with genuine (mental-)health conditions triggers "
         "informed consent, risk/suicidality screening, escalation pathways, adverse-event logging, "
         "clinical-referral rules and data governance — all of which must be in place BEFORE the first "
         "participant, not bolted on mid-trial."},
        {"id": "TF-build", "rule": "A trial cannot validly test an intervention or product that does not "
         "yet exist or is still being built, rewritten, or manually patched during the trial. If the "
         "tool must first be built (a trial-ready v0.1 plausibly takes 3+ months with staff), the trial "
         "window cannot simultaneously contain the build — especially with no budget for staff."},
        {"id": "TF-halo", "rule": "Short-window efficacy is inflated by novelty, attention, expectation "
         "and measurement effects (the 'halo' effect). An early endpoint exaggerates apparent benefit and "
         "cannot distinguish durable change from short-term engagement."},
        {"id": "TF-recruit", "rule": "Real outcome subjects must have measurable baseline conditions and "
         "be advertised-to, screened, consented, baseline-tested and allocated to comparable arms — not "
         "enthusiastic product testers. Dropout in digital mental-health trials runs 26-48%, so enrolled "
         "numbers must substantially exceed the required completers."},
        {"id": "TF-distributed", "rule": "Beware a comparative-superiority trial claim that is never stated "
         "in one place but is DISTRIBUTED across separate reasonable-sounding phrases (proof package, "
         "controlled cohort, pre/post measures, generic-wrapper comparison, measurable improvement, "
         "outcome deltas). Recombined, these commit to a powered comparative trial far stronger than a "
         "feasibility sprint — and the timeline that is fine for a sprint is impossible for the trial."},
    ],
}
# ---- Pack: medical / regulatory claim scrutiny (general — applies to ANY health/medical pitch) ----
MEDICAL_REGULATORY = {
    "id": "medical_regulatory",
    "when": "the document markets a medical / health / mental-health product, claims to treat, "
            "diagnose or clinically improve a condition, or claims regulatory clearance (FDA, CE, "
            "Class I/II medical device)",
    "rules": [
        {"id": "MR-future", "rule": "Regulatory clearance that is a FUTURE target (e.g. 'CE Class IIa "
         "by Q4 next year') must not be presented as a present fact. Any present-tense 'treats / is a "
         "regulated medical device' claim is invalid until clearance actually exists."},
        {"id": "MR-treat", "rule": "Marketing that a product 'treats' or 'cures' a medical condition "
         "without the corresponding clearance is a live regulatory / legal exposure (FDA/FTC, state "
         "bans, wrongful-death liability) that transfers to the investor."},
        {"id": "MR-first", "rule": "A category-ownership claim ('world's first AI clinic', 'first "
         "medically-cleared treatment') is refutable — check whether already-cleared competitors "
         "exist (e.g. Limbic Class IIa, Wysa FDA Breakthrough, Woebot). If they do, the claim is false."},
        {"id": "MR-learning", "rule": "A model advertised as continuously 'learning / personalising' "
         "conflicts with a FROZEN, certified medical-device specification — a certified device cannot "
         "keep changing its behaviour and remain within its certified spec."},
        {"id": "MR-supervision", "rule": "'Clinically supervised' and 'dramatically cheaper at scale' "
         "form a pincer: clinical supervision is a per-user human cost that scales linearly and "
         "contradicts the low marginal cost the scale/economics claim needs."},
        {"id": "MR-safety-chars", "rule": "A safety-critical component (e.g. crisis/suicidality "
         "flagging) needs stated operating characteristics — false-positive/false-negative rates and "
         "human-review load. Their absence, especially where safety and scale are coupled, is a red flag."},
        {"id": "MR-minors", "rule": "Targeting minors with a mental-health product requires an explicit "
         "safeguarding, consent and age-appropriate-care architecture. Its absence converts commercial "
         "risk into existential legal/safety risk."},
        {"id": "MR-evidence", "rule": "Generic clinical evidence (e.g. 'CBT works') must not be laundered "
         "into product-specific efficacy for this particular conversational AI; and a device class "
         "(Class IIa) proves a safety pathway, not efficacy, adoption, trust or commercial pull."},
        {"id": "MR-whitelabel", "rule": "A white-label distribution model creates a clinician-of-record "
         "and clinical-liability gap, and white-label invisibility contradicts any 'category-owning "
         "clinic/brand' claim."},
        {"id": "MR-stage", "rule": "Mature-company claims (regulated clinic, world-first) on early-stage "
         "substance (no ask, no financials, no runway, no projections, almost no team) is a stage-vs-"
         "claims gulf."},
        {"id": "MR-tam", "rule": "A headline market-size (TAM) or CAGR that is inflated or internally "
         "inconsistent with the document's own narrower market listing (e.g. a headline dozens of times "
         "larger than the segment it actually serves) is not credible."},
        {"id": "MR-treat-recur", "rule": "A 'treat then discharge / step back' clinical model is a pincer "
         "against a recurring-revenue subscription business — you cannot both discharge cured users and "
         "book their ongoing subscriptions."},
        {"id": "MR-founder", "rule": "Founder/team credentials stated as achievements (inflated titles, "
         "'scaled X to a unicorn', logo-laundering) overstate causal credit; 'patent-pending' does not "
         "establish defensibility. Check for gold-plating vs verifiable contribution."},
        {"id": "MR-systemic", "rule": "Watch three systemic techniques: FUTURE-STATUS LAUNDERING (selling "
         "a target status as present), CLAIMS-BY-OMISSION (letting silence be read as a positive answer "
         "on financials/team/safety), and the PINCER PATTERN (paired promises that cannot co-exist)."},
    ],
}
# ---- Pack: investor / go-to-market claim scrutiny (general — any startup fundraising deck) ----
GTM_INVESTOR = {
    "id": "gtm_investor",
    "when": "the document is a startup pitch / investment memo / fundraising deck making market, "
            "traction, business-model, growth or go-to-market claims",
    "rules": [
        {"id": "GTM-demand", "rule": "A large market/opportunity claim with NO demand evidence (no "
         "pilot, waitlist that converted, paying users, or willingness-to-pay data) is 'build it and "
         "they will come'. Flag especially if the deck itself concedes it lacks user-adoption data."},
        {"id": "GTM-flywheel", "rule": "A growth 'flywheel' or loop with no ignition — no initial "
         "capital, users, or content to start it — cannot start. Watch for circular dependencies where "
         "each part is cited to de-risk the other (e.g. ad money that is itself audience-contingent)."},
        {"id": "GTM-unitecon", "rule": "Revenue/subscriber projections with no CAC, churn, conversion "
         "or payback mean LTV>CAC cannot even be computed; a wide scenario spread (e.g. 3-6x) with no "
         "model behind it is a phantom, unfalsifiable model."},
        {"id": "GTM-capital-seq", "rule": "Capital committed to supply/build BEFORE or WITHOUT funding "
         "demand/go-to-market is mis-sequenced — it funds the product but not the customers, forcing a "
         "fresh raise just to find demand. Check whether committed spend already exceeds capital secured."},
        {"id": "GTM-wedge", "rule": "A differentiation/tech 'wedge' claimed as a moat where the document "
         "provides ZERO evidence it drives demand or is defensible. Do NOT flag if the document shows "
         "any supporting evidence (data curve, retention/expansion, a concrete mechanism competitors "
         "lack) — only flag a bare, unsupported assertion."},
        {"id": "GTM-reach", "rule": "A distribution/format choice that DEMONSTRABLY excludes a major "
         "segment the document itself claims to serve (e.g. 'mass-market/household' positioning but "
         "mobile-only, one login per user). Do NOT flag a deliberate, coherent niche/channel choice "
         "(e.g. B2B web+API for a whole team) — only flag a concrete reach/positioning contradiction."},
        {"id": "GTM-chain", "rule": "The document's success requires SEVERAL specific, named things to "
         "ALL succeed with no fallback, AND at least one of them is explicitly unfunded, unproven, or "
         "circular. Do NOT flag merely because a plan has sequential steps — only flag a concrete "
         "single-point-of-failure the document's own content exposes."},
        {"id": "GTM-premium", "rule": "A 'premium' or 'new-category' positioning contradicted by the "
         "deck's own numbers (budget per unit, cadence, specs) that actually place it in a commodity "
         "tier collapses the differentiation claim."},
    ],
}
PACKS = [TRIAL_FEASIBILITY, MEDICAL_REGULATORY, GTM_INVESTOR]

def route(deck):
    """Conservatively decide which packs apply — so we never inject clinical rules into unrelated docs."""
    applied = []
    for p in PACKS:
        sysp = "You are a strict router. Answer only about whether a specific analysis pack is relevant."
        usr = (f"DOCUMENT:\n<document>\n{deck[:6000]}\n</document>\n\n"
               f"Is this pack relevant? Pack applies when: {p['when']}.\n"
               'Return JSON: {"relevant": true/false}.')
        r = E.chat_json(sysp, usr)
        if isinstance(r, dict) and r.get("relevant"):
            applied.append(p)
    return applied

def _holistic(deck, pack):
    """One holistic pass — lets the model connect distributed evidence across rules (better for
    subtle/distributed violations that no single rule cleanly names)."""
    rules = "\n".join(f"- [{r['id']}] {r['rule']}" for r in pack["rules"])
    sysp = ("You are a forensic analyst applying an encoded expert RULEBOOK to a document. For each "
            "rule the document VIOLATES or IGNORES, report a finding grounded in the document's own "
            "claims. Do not invent issues the document does not raise.\n\n" + _PRECISION)
    usr = (f"DOCUMENT:\n<document>\n{deck}\n</document>\n\nEXPERT RULES:\n{rules}\n\n"
           "For every rule, first ask whether the document already ADDRESSES it (per the precision "
           "principle); include a finding ONLY for rules the document genuinely violates. "
           'For every violated rule return {"id","name","charge","severity"}. '
           'Return JSON: {"findings":[ ... ]}.')
    d = E.chat_json(sysp, usr)
    fs = d.get("findings", []) if isinstance(d, dict) else (d if isinstance(d, list) else [])
    for f in fs:
        if isinstance(f, dict):
            f.setdefault("type", "pincer"); f["trigger_pack"] = pack["id"]
    return [f for f in fs if isinstance(f, dict)]

def run_pack(deck, pack):
    """Union of a holistic pass (connects distributed evidence) and per-rule checks (forces full
    rule coverage). More correct findings only helps recall; the router already gates domain
    relevance, and a precision/dedup layer (NLI verifier) can prune later."""
    out = _holistic(deck, pack)
    seen = {f.get("id") for f in out}
    for r in pack["rules"]:
        sysp = ("You are a careful forensic analyst applying ONE expert rule to a document. Your "
                "priority is to AVOID false alarms: many documents ADEQUATELY satisfy a rule, and "
                "flagging those is a serious error. Only report a violation that is concrete, specific, "
                "and grounded in the document's own text.\n\n" + _PRECISION)
        usr = (f"DOCUMENT:\n<document>\n{deck}\n</document>\n\n"
               f"RULE [{r['id']}]: {r['rule']}\n\n"
               "Step 1: state briefly whether the document ADEQUATELY addresses this rule — e.g. does "
               "it already provide the evidence/data/mechanism the rule asks about? "
               "Step 2: mark violated=true ONLY if there is a concrete, specific gap the document does "
               "NOT address. If the document reasonably satisfies the rule, mark violated=false.\n"
               'Return JSON: {"addressed": "what the doc says about this", "violated": true/false, '
               '"name": "short title", "charge": "the specific claim + exactly how it violates the rule", '
               '"severity": "Fatal|Severe|Material|Minor"}.')
        d = E.chat_json(sysp, usr)
        if isinstance(d, dict) and d.get("violated") and r["id"] not in seen:
            out.append({"id": r["id"], "name": d.get("name", r["id"]), "charge": d.get("charge", ""),
                        "type": "pincer", "load_bearing": True,
                        "severity": d.get("severity", "Material"), "trigger_pack": pack["id"]})
    return out

def run(deck):
    """Route, then run every applicable pack. Returns (findings, applied_pack_ids)."""
    packs = route(deck)
    out = []
    for p in packs:
        out += run_pack(deck, p)
    return out, [p["id"] for p in packs]

if __name__ == "__main__":
    import sys, json
    deck = open(sys.argv[1] if len(sys.argv) > 1 else "/tmp/kerry_deck.txt").read().strip()
    fs, applied = run(deck)
    print("applied packs:", applied, "| findings:", len(fs))
    print(json.dumps(fs, ensure_ascii=False, indent=2))

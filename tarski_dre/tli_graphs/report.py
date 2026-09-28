"""The Intellectual Journey Report.

Two rules govern the rendering:

1. Deterministic figures and model characterisations never share a paragraph.
   Anything computed by arithmetic over the chain is stated plainly. Anything a
   model concluded is labelled EVALUATED and carries its citations.

2. The report states its own limits before anyone else can. The coverage section
   is not an appendix; a teacher who reads only the first page and the coverage
   section should still not be misled.
"""

from __future__ import annotations

from .ingest import Episode, STRUCTURAL_LIMITATIONS
from .ledger import Ledger, PLAUSIBLE_READ_MAX_WPS, STUDIED_MAX_WPS
from .graphs import Graphs

BAND_TEXT = {
    "SLOW_ENOUGH_TO_HAVE_BEEN_STUDIED":
        f"on screen slowly enough to have been studied (<= {STUDIED_MAX_WPS} words/sec)",
    "CONSISTENT_WITH_READING":
        f"on screen at a rate consistent with reading (<= {PLAUSIBLE_READ_MAX_WPS} words/sec)",
    "TOO_FAST_TO_HAVE_BEEN_READ":
        f"on screen too briefly to have been read (> {PLAUSIBLE_READ_MAX_WPS} words/sec)",
    "PARTIALLY_EXPOSED":
        "less than half of the answer was ever scrolled into view",
    "UNKNOWN_NO_TELEMETRY":
        "no exposure telemetry for this answer",
}

KIND_TEXT = {
    "CORRECTED": "replaced an earlier belief of the learner's",
    "ORIGINATED": "first appears in the learner's own writing, with no traced source",
    "VOICED_IN_PROMPT": "appears only in what the learner asked the AI, not in their "
                        "own writing",
    "RESTATED": "re-expressed by the learner in their own writing",
    "APPLIED": "used by the learner to go further",
    "TRANSFERRED_VERBATIM": "present in the document as traced transferred text, "
                            "not as the learner's own expression",
    "UNATTRIBUTABLE_AFTER_COPY": "written shortly after a copy from an AI answer "
                                 "that never landed in a document — the chain "
                                 "cannot say whose words these are",
    "ENCOUNTERED": "presented to the learner",
}

AXIS_TEXT = {
    "THINK_CRITICALLY": "Think critically",
    "REASON_LOGICALLY": "Reason logically",
    "BE_CREATIVE": "Be creative",
    "SUPERVISE_AI": "Supervise AI",
    "EXERCISE_EPISTEMIC_JUDGEMENT": "Exercise epistemic judgement",
}


def _cites(seqs: list[int]) -> str:
    return " ".join(f"#{s}" for s in seqs) if seqs else "-"


def markdown(ep: Episode, led: Ledger, g: Graphs) -> str:
    start = next((e for e in ep.events if e.get("kind") == "SESSION_START"), {})
    name = start.get("episode_name") or ep.manifest.get("episode_name") or ep.path.name
    author = start.get("author_label") or ep.manifest.get("author_label") or "(unlabelled)"

    L: list[str] = []
    add = L.append

    add(f"# Intellectual Journey Report\n")
    add(f"**Learner label:** {author}  ")
    add(f"**Episode:** {name}  ")
    add(f"**Session length:** {led.duration_minutes:.0f} minutes  ")
    add(f"**AI assistants used:** {', '.join(led.providers) or 'none observed'}  ")
    add(f"**Recorder:** {ep.recorder_version}\n")

    # ---------------------------------------------------------------- integrity
    add("## Evidence integrity\n")
    if ep.aborted:
        add("> **This episode was aborted at start and contains no learner evidence.** "
            "No conclusions may be drawn from it.\n")
        return "\n".join(L)
    state = "intact" if ep.integrity.chain_ok else "**BROKEN**"
    add(f"The provenance chain is {state}: {ep.integrity.detail}. The closing hash "
        f"{'matches' if ep.integrity.manifest_hash_matches else '**does not match**'} "
        f"the episode manifest.\n")
    add(f"*Strength of that guarantee:* {ep.integrity.caveat}\n")
    if not ep.integrity.chain_ok:
        add("> Because the chain is broken, everything below is provisional.\n")

    # ---------------------------------------------------------------- narrative
    add("## The journey\n")
    if g.narrative:
        add(f"{g.narrative}\n")
        add("*(This narrative is an EVALUATED characterisation produced by the reasoning "
            "engine from the cited events. The figures in the next section are computed "
            "arithmetically and do not depend on it.)*\n")
    else:
        add("*No narrative available.*\n")

    # ---------------------------------------------------------------- ledger
    add("## What came from where\n")
    for d in led.documents:
        add(f"### {d.document}\n")
        add(f"- Document already held **{d.baseline_chars} characters** when recording "
            f"started (origin: {d.baseline_origin.replace('_', ' ').lower()}).")
        add(f"- Final observed length: **{d.final_chars} characters**.")
        add(f"- Of the {d.accounted_inserted} characters inserted during the session:")
        srcs = ", ".join(f"{k} ({v} chars)" for k, v in sorted(d.transfer_sources.items()))
        add(f"    - **{d.transferred_chars}** were correlated to an observed copy from "
            f"a source{': ' + srcs if srcs else ''} — **{d.transferred_share:.0%}** of "
            f"inserted text;")
        add(f"    - **{d.below_threshold_chars}** were short inserts below the "
            f"correlation threshold;")
        add(f"    - **{d.no_correlated_transfer_chars}** had **no correlated source "
            f"transfer**. That means no source was traced. It is *not* evidence that "
            f"the learner composed them unaided.")
        if d.transferred_excerpts:
            add("")
            add("**Text in this document that was traced to a source** — this is "
                "transferred content, not the learner's own expression:")
            for x in d.transferred_excerpts:
                add(f"    - from {x['provider']} ({x['chars']} chars) {x['citation']}: "
                    f"\"{x['text']}\"")
            add("")
        if d.deleted_chars or d.rewrites:
            add(f"- Revision activity: {d.deleted_chars} characters deleted, "
                f"{d.rewrites} rewrites.")
        add(f"- Evidence: {' '.join(d.citations[:12])}\n")

    # ---------------------------------------------------------------- attention
    add("## Attention to what the AI said\n")
    if led.attention:
        add("| AI answer | Words | Visible | Rate | Re-reads | Reading of the evidence |")
        add("|---|---|---|---|---|---|")
        for a in led.attention:
            add(f"| {a.provider} {a.citation} | {a.words} | "
                f"{a.active_visible_ms / 1000:.0f}s | "
                f"{a.words_per_second if a.words_per_second is not None else '-'} w/s | "
                f"{a.revisits or '-'} | {BAND_TEXT.get(a.band, a.band)} |")
        add("")
        add("*Bands are fixed thresholds over active visible time, not a judgement of "
            "comprehension. Time on screen is an upper bound on attention.*\n")
    else:
        add("*No exposure telemetry in this episode.*\n")

    # ---------------------------------------------------------------- prompts
    add("## What the learner asked for\n")
    for t in led.turns:
        atts = (" + attached " + ", ".join(a.get("name", "?") for a in t.attachments)
                if t.attachments else "")
        add(f"- **#{t.seq} → {t.provider}**{atts}: \"{t.prompt}\"")
    add("")

    # -------------------------------------------------------- shadowed writing
    if led.shadowed_inserts:
        add("## Writing the chain cannot attribute\n")
        add("Each passage below is untraced writing that appeared shortly after text "
            "was copied out of an AI answer and never pasted into a document. Both "
            "facts are observed; the link between them is not. This is neither a "
            "finding of copying nor a credit for original work — it marks where the "
            "evidence runs out, and a teacher who needs to know should ask the "
            "learner.\n")
        for x in led.shadowed_inserts:
            add(f"- **{x.document}**, {x.chars} chars `[OBSERVED]` #{x.seq}, written "
                f"{x.seconds_after_copy:.0f}s after an uncorrelated copy from "
                f"{x.copy_provider} (#{x.copy_seq}): \"{x.text}\"")
        add("")

    # ------------------------------------------------------- uncorrelated copies
    if led.uncorrelated_copies:
        add("## Text copied but never traced into a document\n")
        add("The recorder observed these copies leave a source, and observed no "
            "matching arrival in a monitored document. That is all it observed. The "
            "text may have been discarded, pasted somewhere not being monitored, or "
            "reworked far enough that the correlator could not match it — the chain "
            "does not say which, and neither does this report.\n")
        for c in led.uncorrelated_copies:
            add(f"- from {c.provider} ({c.chars} chars) `[OBSERVED]` {c.citation}: "
                f"\"{c.text}\"")
        add("")

    # ------------------------------------------------------------ where they read
    if led.web_visits:
        add("## Where the learner looked\n")
        for v in led.web_visits:
            q = v.get("search_query")
            if q:
                add(f"- searched **\"{q}\"** on {v.get('host')} `[OBSERVED]` "
                    f"{v.get('citation')}")
            else:
                add(f"- {v.get('title') or v.get('url')} ({v.get('host')}) "
                    f"`[OBSERVED]` {v.get('citation')}")
        add("")

    # ---------------------------------------------------------------- graphs
    add("## Understanding graph\n")
    if g.understanding_nodes:
        for n in sorted(g.understanding_nodes,
                        key=lambda x: list(KIND_TEXT).index(x.kind)
                        if x.kind in KIND_TEXT else 99):
            add(f"- **{n.label}** — {KIND_TEXT.get(n.kind, n.kind.lower())}. "
                f"{n.detail} `[{n.grade}]` {_cites(n.evidence)}")
        add("")
        if g.understanding_edges:
            add("**Relations the learner's work supports:**\n")
            for e in g.understanding_edges:
                add(f"- {e.source} —{e.relation}→ {e.target} `[{e.grade}]` "
                    f"{_cites(e.evidence)}")
            add("")
    else:
        add("*No concept survived citation checking.*\n")

    add("## Reasoning graph\n")
    x = led.expression
    add(f"**Measured before any interpretation:** this session contains {x.summary}. "
        f"`[DERIVED]`\n")
    if x.no_untraced_writing:
        add("> Because no writing in the document was untraced to a source, there is "
            "little learner-authored material for the axes below to rest on. Read an "
            "empty axis as *the session did not evidence it*, not as a judgement of "
            "the learner's ability.\n")
    seen = {o.axis for o in g.reasoning}
    for axis in AXIS_TEXT:
        obs = [o for o in g.reasoning if o.axis == axis]
        shown = [o for o in obs if o.polarity == "EVIDENCED"]
        absent = [o for o in obs if o.polarity != "EVIDENCED"]
        status = ("evidenced" if shown else
                  "**not evidenced in this session**" if absent else "no finding")
        add(f"**{AXIS_TEXT[axis]}** — {status}")
        for o in shown:
            add(f"- {o.observation} `[{o.grade}]` {_cites(o.evidence)}")
        for o in absent:
            add(f"- *What the session shows instead:* {o.observation} "
                f"`[{o.grade}]` {_cites(o.evidence)}")
        if not obs:
            add("- *Nothing citable either way.* Not a negative finding about the "
                "learner; this session did not exercise it observably.")
        add("")
    _ = seen

    # ---------------------------------------------------------------- coverage
    add("## What this report cannot tell you\n")
    add("Read this section before acting on anything above.\n")
    if led.gaps:
        add("**Gaps in this specific episode**\n")
        for gap in led.gaps:
            add(f"- {gap.detail} `[{gap.grade}]` {gap.citation}")
        add("")
    if ep.limitations:
        add(f"**Known limits of recorder {ep.recorder_version}**\n")
        for lim in ep.limitations:
            add(f"- {lim['id']}: {lim['effect']} *Applied rule:* {lim['dre_rule']}")
        add("")
    add("**Limits that hold for any desktop recording**\n")
    for s in STRUCTURAL_LIMITATIONS:
        add(f"- {s}")
    add("")

    # ---------------------------------------------------------------- provenance
    add("## Provenance of this report\n")
    final_hash = ep.events[-1].get("event_hash") if ep.events else "-"
    add(f"- Episode chain closing hash: `{final_hash}`")
    add(f"- Events read: {len(ep.events)}; independently re-verified: "
        f"{ep.integrity.events_verified}")
    add(f"- Semantic layer: `{g.model}`"
        f"{' (unavailable — deterministic sections only)' if not g.llm_available else ''}, "
        f"temperature 0, run locally with no network egress")
    add(f"- Model claims discarded for failing citation checks: {len(g.dropped)}")
    for d in g.dropped:
        add(f"    - {d['what']} \"{d['label']}\": {d['why']}")
    add(f"- Model labels corrected against the deterministic role of their cited "
        f"events: {len(g.corrections)}")
    for c in g.corrections:
        add(f"    - \"{c['label']}\": {c['correction']}")
    add("")
    return "\n".join(L)

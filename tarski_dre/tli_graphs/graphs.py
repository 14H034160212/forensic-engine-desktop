"""The two knowledge graphs, and the calibration gate that keeps them honest.

The model's job here is narrow: given an evidence digest of numbered events, say
what kind of understanding and what kind of reasoning the evidence shows. It is
not allowed to produce a number, and it is not allowed to make an assertion it
cannot attach to specific event sequence numbers.

`_validate` is the part that matters. Every claim the model returns is checked:
  * cited sequence numbers must exist in this episode, or the claim is dropped;
  * a claim about the learner's own contribution may only cite events that
    actually evidence learner action, or it is dropped;
  * surviving claims are graded EVALUATED and inherit the weakest grade among
    the events they cite.

So the failure mode of a hallucinating model is a *missing* finding, never a
fabricated one presented to a teacher as fact.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any

from .ingest import Episode, weakest
from .ledger import Ledger

ENGINE_HOST = os.environ.get("ENGINE_HOST", "http://127.0.0.1:11455")
LLM_MODEL = os.environ.get("LLM_MODEL", "gpt-oss:20b")
TIMEOUT = int(os.environ.get("DRE_TIMEOUT", "600"))

# The five reasoning axes, verbatim from the TLI summary.
REASONING_AXES = [
    "THINK_CRITICALLY",
    "REASON_LOGICALLY",
    "BE_CREATIVE",
    "SUPERVISE_AI",
    "EXERCISE_EPISTEMIC_JUDGEMENT",
]

# Event kinds that evidence the learner doing something, as opposed to the AI or
# the browser doing something. A claim about the learner must cite one of these.
LEARNER_ACTION_KINDS = {
    "AI_PROMPT", "DOC_INSERT", "DOC_DELETE", "DOC_REWRITE", "COPY", "CUT",
    "PASTE", "SELECTION", "DOCUMENT_SAVED", "ATTACHMENT_ADDED",
    "SOURCE_REVISIT", "SOURCE_SEGMENT_EXPOSURE", "SCROLL_SUMMARY",
    "WEB_NAVIGATION", "FILE_DOWNLOADED",
}

# ----------------------------------------------------------------- event roles
# Checking that a citation *exists* is not enough. A model will happily label the
# learner's own typed synthesis as "presented to the learner", or call a verbatim
# copy "re-expressed in their own words" -- both observed in the first run of this
# engine, and the second is the single most damaging error an integrity product can
# make. So each event is given a deterministic role, and a claim whose label
# contradicts the role of every event it cites is corrected or dropped.
ROLE_AI_PRESENTED = "AI_PRESENTED"
ROLE_SOURCE_PRESENTED = "SOURCE_PRESENTED"
ROLE_LEARNER_ORIGINATED = "LEARNER_ORIGINATED"
ROLE_LEARNER_TRANSFERRED = "LEARNER_TRANSFERRED"
ROLE_LEARNER_ATTENDED = "LEARNER_ATTENDED"
ROLE_LEARNER_SHORT_EDIT = "LEARNER_SHORT_EDIT"
ROLE_LEARNER_UNATTRIBUTABLE = "LEARNER_UNATTRIBUTABLE"
ROLE_LEARNER_ASKED = "LEARNER_ASKED"
ROLE_OTHER = "OTHER"


def event_role(e: dict[str, Any], shadowed: set[int] | None = None) -> str:
    """What this event evidences, decided by field values rather than by prose.

    `shadowed` carries the sequence numbers of untraced inserts the ledger found in
    the shadow of a copy that never landed anywhere. Those cannot support a claim
    about the learner's own expression: the chain saw AI text reach the clipboard
    and untraced text appear shortly after, and cannot say whose words they are.
    """
    kind = str(e.get("kind") or "")
    if (shadowed and kind == "DOC_INSERT"
            and int(e.get("global_sequence") or 0) in shadowed):
        return ROLE_LEARNER_UNATTRIBUTABLE
    if kind in ("AI_RESPONSE", "AI_RESPONSE_AMENDED", "AI_MESSAGE_PRELOADED"):
        return ROLE_AI_PRESENTED
    if kind == "AI_PROMPT":
        return ROLE_LEARNER_ASKED
    if kind == "DOC_INSERT":
        cls = str(e.get("classification") or "")
        # Text the correlator traced to a copy is transferred content, whatever it
        # reads like. Only an insert with no traced source can carry a claim about
        # the learner's own expression -- and even then only as "no source traced".
        if cls == "TRANSFER_CORRELATED":
            return ROLE_LEARNER_TRANSFERRED
        if cls == "BELOW_THRESHOLD":
            # BELOW_THRESHOLD means "too short to correlate", not "came from a
            # source". In 2.6.0c an exact short paste is promoted to
            # TRANSFER_CORRELATED by the exact_whole_clipboard rule, so what is
            # left here is untraced -- but it is a handful of characters, enough
            # to evidence acting on advice and not enough to originate a concept.
            return ROLE_LEARNER_SHORT_EDIT
        return ROLE_LEARNER_ORIGINATED
    if kind in ("COPY", "CUT", "PASTE", "TRANSFER_EXACT", "TRANSFER_FUZZY",
                "TRANSFER_EVIDENCE", "ATTACHMENT_TRANSFER", "BASELINE_TRANSFER",
                "DOWNLOAD_OPENED_IN_WORD", "FILE_DOWNLOADED"):
        return ROLE_LEARNER_TRANSFERRED
    if kind in ("DOC_DELETE", "DOC_REWRITE", "DOCUMENT_SAVED", "ATTACHMENT_ADDED",
                "SELECTION"):
        return ROLE_LEARNER_ORIGINATED
    if kind in ("EXPOSURE_SUMMARY", "SOURCE_SEGMENT_EXPOSURE", "SOURCE_REVISIT",
                "SCROLL_SUMMARY"):
        return ROLE_LEARNER_ATTENDED
    if kind == "WEB_NAVIGATION":
        return ROLE_SOURCE_PRESENTED
    return ROLE_OTHER


# Quantities *about the session* are the engine's arithmetic, never the model's.
# Subject-matter numbers are fine -- "the oil window is 60-120 degrees Celsius" is
# content, not a measurement of the learner -- so the rule is keyed on the units a
# session measurement would carry, not on digits.
SESSION_QUANTITY = re.compile(
    r"\b\d[\d,.]*\s*(?:%|percent|characters?|chars?|words?|"
    r"seconds?|secs?|minutes?|mins?|turns?|prompts?|messages?|times?)\b",
    re.IGNORECASE,
)


def session_quantities(text: str) -> list[str]:
    return [m.group(0) for m in SESSION_QUANTITY.finditer(text or "")]


PRESENTED_ROLES = {ROLE_AI_PRESENTED, ROLE_SOURCE_PRESENTED}
LEARNER_ROLES = {ROLE_LEARNER_ORIGINATED, ROLE_LEARNER_TRANSFERRED,
                 ROLE_LEARNER_ATTENDED, ROLE_LEARNER_ASKED,
                 ROLE_LEARNER_SHORT_EDIT, ROLE_LEARNER_UNATTRIBUTABLE}

# Roles that carry the learner's own expression, and can therefore support a
# positive claim about their thinking. Telemetry and traced transfers cannot.
LEARNER_EXPRESSION_ROLES = {ROLE_LEARNER_ORIGINATED, ROLE_LEARNER_ASKED,
                            ROLE_LEARNER_SHORT_EDIT}


@dataclass
class Node:
    label: str
    kind: str
    detail: str
    evidence: list[int]
    grade: str
    dropped_reason: str | None = None


@dataclass
class Edge:
    source: str
    target: str
    relation: str
    evidence: list[int]
    grade: str


@dataclass
class ReasoningObservation:
    axis: str
    observation: str
    evidence: list[int]
    grade: str
    # EVIDENCED  = the session shows the learner doing this.
    # NOT_EVIDENCED = the session shows the opposite, or shows nothing.
    # Rendered separately, because a negative finding printed under a bare axis
    # heading reads to a skimming teacher as a credit.
    polarity: str = "EVIDENCED"


@dataclass
class Graphs:
    understanding_nodes: list[Node] = field(default_factory=list)
    understanding_edges: list[Edge] = field(default_factory=list)
    reasoning: list[ReasoningObservation] = field(default_factory=list)
    narrative: str = ""
    dropped: list[dict[str, Any]] = field(default_factory=list)
    corrections: list[dict[str, Any]] = field(default_factory=list)
    model: str = LLM_MODEL
    llm_available: bool = True


# --------------------------------------------------------------------------- LLM
def _chat(prompt: str, system: str) -> dict[str, Any]:
    body = json.dumps({
        "model": LLM_MODEL,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": prompt}],
        "stream": False,
        "format": "json",
        "options": {"temperature": 0, "num_ctx": 16384},
    }).encode()
    req = urllib.request.Request(f"{ENGINE_HOST}/api/chat", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        payload = json.loads(r.read().decode())
    content = (payload.get("message") or {}).get("content") or "{}"
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        start, end = content.find("{"), content.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(content[start:end + 1])
            except json.JSONDecodeError:
                pass
        return {}


# ------------------------------------------------------------------- digest
def digest(ep: Episode, led: Ledger) -> str:
    """Numbered, quoted evidence the model is permitted to cite. Nothing else."""
    lines: list[str] = []
    # The ledger already resolved which responses an amendment superseded; the
    # model must see that too, or it will quote a provider progress stub as the
    # answer the learner engaged with.
    shadow_seqs = {x.seq for x in led.shadowed_inserts}
    kept = {t.response_seq for t in led.turns}
    superseded = {str(e.get("event_id")) for e in
                  ep.by_kind("AI_RESPONSE", "AI_RESPONSE_INCOMPLETE")
                  if e.get("global_sequence") not in kept
                  and any(a.get("message_id") == e.get("message_id")
                          for a in ep.by_kind("AI_RESPONSE_AMENDED"))}
    for e in ep.events:
        seq, kind, grade = e.get("global_sequence"), e.get("kind"), e.get("evidence_grade")
        if kind == "AI_PROMPT":
            atts = ", ".join(a.get("name", "?") for a in (e.get("attachments") or []))
            extra = f" [attachments: {atts}]" if atts else ""
            lines.append(f'{seq} [{grade}] LEARNER_PROMPT to {e.get("provider") or "?"}'
                         f'{extra}: "{e.get("text")}"')
        elif kind in ("AI_RESPONSE", "AI_RESPONSE_AMENDED"):
            label = ("AI_ANSWER_SUPERSEDED_BY_A_LATER_AMENDMENT"
                     if str(e.get("event_id")) in superseded else "AI_ANSWER")
            lines.append(f'{seq} [{grade}] {label} from '
                         f'{e.get("provider") or "?"}: "{e.get("text")}"')
        elif kind == "DOC_INSERT":
            shadow = ("  [WARNING: written shortly after a copy from an AI answer "
                      "that never landed in a document; whose words these are is "
                      "unknown]" if seq in shadow_seqs else "")
            lines.append(f'{seq} [{grade}] LEARNER_INSERTED_TEXT '
                         f'({e.get("chars")} chars, {e.get("classification")}): '
                         f'"{(e.get("text") or e.get("inserted_text") or "")[:400]}"'
                         f'{shadow}')
        elif kind == "DOC_DELETE":
            lines.append(f'{seq} [{grade}] LEARNER_DELETED_TEXT ({e.get("chars")} chars): '
                         f'"{(e.get("text") or "")[:200]}"')
        elif kind == "COPY":
            ctx = e.get("source_context") or {}
            lines.append(f'{seq} [{grade}] LEARNER_COPIED from '
                         f'{ctx.get("provider") or ctx.get("host") or "?"}: '
                         f'"{(e.get("text") or "")[:200]}"')
        elif kind == "TRANSFER_EXACT":
            lines.append(f'{seq} [{grade}] LINK: copied text was inserted into the document '
                         f'(match {e.get("match_method")})')
        elif kind == "EXPOSURE_SUMMARY":
            if str(e.get("role") or "") == "assistant":
                lines.append(f'{seq} [{grade}] ATTENTION: AI answer of '
                             f'{e.get("response_words")} words was visible '
                             f'{int(e.get("active_visible_ms") or 0)/1000:.0f}s, '
                             f'exposure {e.get("segment_exposure_fraction")}, '
                             f'{e.get("response_words_per_active_visible_second")} words/sec')
            else:
                lines.append(f'{seq} [{grade}] ATTENTION: page {e.get("page_title")} '
                             f'visible {int(e.get("active_visible_ms") or 0)/1000:.0f}s')
        elif kind == "SOURCE_REVISIT":
            lines.append(f'{seq} [{grade}] LEARNER_RETURNED to an earlier AI answer '
                         f'(visit {e.get("revisit_ordinal")})')
        elif kind == "SCROLL_SUMMARY":
            lines.append(f'{seq} [{grade}] SCROLLED {e.get("delta_y")}px in '
                         f'{e.get("interval_ms")}ms on {e.get("host")}')
        elif kind == "WEB_NAVIGATION":
            lines.append(f'{seq} [{grade}] VISITED {e.get("page_title")} ({e.get("host")})')
        elif kind == "ATTACHMENT_ADDED":
            lines.append(f'{seq} [{grade}] LEARNER_ATTACHED file {e.get("name")} to '
                         f'{e.get("provider")}')
        elif kind == "ATTACHMENT_TRANSFER":
            lines.append(f'{seq} [{grade}] LINK: the uploaded file is the learner\'s own '
                         f'monitored document')
        elif kind == "FILE_DOWNLOADED":
            lines.append(f'{seq} [{grade}] DOWNLOADED {e.get("name")}')
        elif kind == "DOCUMENT_FINAL_TEXT":
            lines.append(f'{seq} [{grade}] FINAL_DOCUMENT_TEXT: '
                         f'"{(e.get("final_text") or e.get("text") or "")[:1500]}"')
        elif kind == "WEB_EXCLUDED_ACTIVITY":
            lines.append(f'{seq} [{grade}] UNOBSERVABLE_GAP: '
                         f'{int(e.get("duration_ms") or 0)/1000:.0f}s on an excluded host, '
                         f'no content captured')
    return "\n".join(lines)


SYSTEM = (
    "You analyse a provenance chain from a learning session and report what the "
    "evidence shows about a learner's understanding and reasoning.\n"
    "Hard rules:\n"
    "1. Every claim must cite the sequence numbers of the events that evidence it, "
    "in an 'evidence' array. A claim you cannot cite must be omitted entirely.\n"
    "2. Never state or estimate a quantity, percentage, duration or count. Those are "
    "computed elsewhere.\n"
    "3. Text an event marks NO_CORRELATED_TRANSFER was not traced to a source. Do not "
    "describe it as typed from memory or as the learner's own knowledge; describe only "
    "what it says and does.\n"
    "4. Do not speculate about anything in an UNOBSERVABLE_GAP.\n"
    "5. Reply with JSON only."
)

UNDERSTANDING_PROMPT = """Build the learner's UNDERSTANDING GRAPH for this session.

Nodes are concepts that appear in the session. Edges are relations between them
that the evidence supports.

For each node give:
  "label": short concept name
  "kind": one of ENCOUNTERED (only presented to the learner, by an AI or a page),
          ORIGINATED (the concept first appears in the learner's own writing,
                      with no traced source),
          VOICED_IN_PROMPT (it appears only in something the learner asked, not
                      in their own writing),
          RESTATED (the learner re-expressed something they were told, in their
                    own words rather than by copying),
          CORRECTED (it replaced an earlier wrong belief of the learner's),
          APPLIED (the learner used it to do something further)
  "detail": one sentence
  "evidence": [sequence numbers]

For each edge give "source", "target", "relation" (one of IS_A, PART_OF, CAUSES,
CONTRADICTS, REFINES, PREREQUISITE_OF), and "evidence".

Return {"nodes": [...], "edges": [...]}.

EVIDENCE
--------
%s
"""

REASONING_PROMPT = """Build the learner's REASONING GRAPH for this session, on these
five axes exactly: %s.

For each observation give:
  "axis": one of the five
  "polarity": "EVIDENCED" if the session shows the learner doing this, or
              "NOT_EVIDENCED" if the session shows the opposite or shows nothing
  "observation": one or two sentences on what the evidence shows
  "evidence": [sequence numbers]

A NOT_EVIDENCED observation is a legitimate and useful finding -- report it when
the session genuinely lacks the behaviour. Never write a NOT_EVIDENCED finding as
though it were a positive one. Prefer few, well-cited observations over many weak
ones, and omit an axis entirely if you have nothing citable either way.

Do not accuse the learner of dishonesty, cheating or misconduct, and do not
recommend any consequence. Report what the evidence shows and stop there.

Return {"observations": [...]}.

EVIDENCE
--------
%s
"""

NARRATIVE_PROMPT = """Write the teacher-facing narrative of this learner's intellectual
journey through the session: where they started, what changed, and what they did with
what they were told. Three short paragraphs at most.

Cite sequence numbers inline in the form (#7) for each substantive statement. Do not
give any quantities. Do not describe anything in an UNOBSERVABLE_GAP.

Return {"narrative": "..."}.

EVIDENCE
--------
%s
"""


# --------------------------------------------------------------------- validation
def _validate_evidence(ep: Episode, cited: Any) -> tuple[list[int], str, str | None]:
    """Returns (valid seqs, inherited grade, drop reason)."""
    if not isinstance(cited, list) or not cited:
        return [], "INFERRED", "no evidence cited"
    seqs: list[int] = []
    for c in cited:
        try:
            seqs.append(int(c))
        except (TypeError, ValueError):
            continue
    events = [(s, ep.by_seq(s)) for s in seqs]
    missing = [s for s, e in events if e is None]
    if missing:
        return [], "INFERRED", f"cites events not in this episode: {missing}"
    grades = [str(e.get("evidence_grade") or "INFERRED") for _, e in events]
    return seqs, weakest(*grades), None


def _roles(ep: Episode, seqs: list[int],
           shadowed: set[int] | None = None) -> set[str]:
    return {event_role(ep.by_seq(s) or {}, shadowed) for s in seqs}


def _reconcile_kind(ep: Episode, kind: str, seqs: list[int],
                    shadowed: set[int] | None = None) -> tuple[str | None, str]:
    """Reconcile the model's label against the deterministic role of its citations.

    Returns (kind, note). A None kind means the claim must be dropped. A non-empty
    note means the label was corrected, and the report shows that it was.
    """
    roles = _roles(ep, seqs, shadowed)
    presented = roles & PRESENTED_ROLES
    unattributable = ROLE_LEARNER_UNATTRIBUTABLE in roles
    # A prompt is text the learner authored, so it counts as their own expression
    # alongside untraced document writing. (A prompt the learner pasted in from
    # elsewhere would carry its own COPY event, which is graded as a transfer.)
    transferred = ROLE_LEARNER_TRANSFERRED in roles
    short_edit = ROLE_LEARNER_SHORT_EDIT in roles
    written = ROLE_LEARNER_ORIGINATED in roles
    asked = ROLE_LEARNER_ASKED in roles
    asked_only = asked and not written and not presented and not transferred
    originated = written or asked

    if kind == "ENCOUNTERED":
        if unattributable and not (presented or transferred or short_edit or written):
            return "UNATTRIBUTABLE_AFTER_COPY", (
                "relabelled ENCOUNTERED -> UNATTRIBUTABLE_AFTER_COPY")
        if presented or transferred or short_edit:
            return "ENCOUNTERED", ""
        if asked_only:
            return "VOICED_IN_PROMPT", ("relabelled ENCOUNTERED -> VOICED_IN_PROMPT: "
                                        "the only citation is the learner's own prompt")
        if originated:
            # The concept only appears in the learner's own writing. Calling that
            # "presented to the learner" silently transfers credit away from them.
            return "ORIGINATED", ("relabelled ENCOUNTERED -> ORIGINATED: every cited "
                                  "event is the learner's own writing, not a source")
        return None, "ENCOUNTERED cites neither a source nor learner writing"

    if kind == "ORIGINATED":
        if unattributable and not written:
            return "UNATTRIBUTABLE_AFTER_COPY", (
                "relabelled ORIGINATED -> UNATTRIBUTABLE_AFTER_COPY: the cited "
                "writing followed a copy from an AI answer that never landed in a "
                "document, so the chain cannot say whose words these are")
        if written:
            return "ORIGINATED", ""
        if asked_only:
            # Naming a topic in a request is not a contribution to the work. The
            # distinction matters: a learner who only asked for 300 words on a
            # subject must not read as having originated the subject matter.
            return "VOICED_IN_PROMPT", ("relabelled ORIGINATED -> VOICED_IN_PROMPT: "
                                        "the concept appears only in the learner's "
                                        "request, not in their own writing")
        if presented:
            return "ENCOUNTERED", ("relabelled ORIGINATED -> ENCOUNTERED: the cited "
                                   "events are a source presenting it")
        if transferred:
            return "TRANSFERRED_VERBATIM", ("relabelled ORIGINATED -> "
                                            "TRANSFERRED_VERBATIM: cited events are "
                                            "traced transfers")
        return None, "ORIGINATED cites neither learner writing nor a prompt"

    if kind == "RESTATED":
        if unattributable and not written:
            return "UNATTRIBUTABLE_AFTER_COPY", (
                "relabelled RESTATED -> UNATTRIBUTABLE_AFTER_COPY: the cited writing "
                "followed an uncorrelated copy from an AI answer, so calling it the "
                "learner's own words is a claim the chain does not support")
        if written:
            return "RESTATED", ""
        if transferred:
            # The most damaging possible mislabel: verbatim transferred text
            # reported to a teacher as the learner's own words.
            return "TRANSFERRED_VERBATIM", ("relabelled RESTATED -> "
                                            "TRANSFERRED_VERBATIM: the only learner "
                                            "events cited are traced transfers, so "
                                            "the text was moved, not re-expressed")
        return None, "RESTATED cites no learner writing"

    if kind == "CORRECTED":
        if not (roles & LEARNER_ROLES):
            return None, "CORRECTED cites no learner action"
        if not presented and not transferred:
            if not (written or asked):
                return None, ("CORRECTED cites neither the information arriving nor "
                              "the learner expressing anything")
            return ("ORIGINATED" if written else "VOICED_IN_PROMPT"), (
                "relabelled CORRECTED: no cited event shows the correcting "
                "information arriving")
        return "CORRECTED", ""

    if kind == "APPLIED":
        if roles & LEARNER_ROLES:
            return "APPLIED", ""
        return None, "APPLIED cites no learner action"

    return "ENCOUNTERED", f"unknown kind {kind!r} treated as ENCOUNTERED"


def _cites_learner_action(ep: Episode, seqs: list[int]) -> bool:
    return any((ep.by_seq(s) or {}).get("kind") in LEARNER_ACTION_KINDS for s in seqs)


def analyse(ep: Episode, led: Ledger) -> Graphs:
    ev = digest(ep, led)
    out = Graphs()
    shadowed = {x.seq for x in led.shadowed_inserts}

    try:
        understanding = _chat(UNDERSTANDING_PROMPT % ev, SYSTEM)
        reasoning = _chat(REASONING_PROMPT % (", ".join(REASONING_AXES), ev), SYSTEM)
        narrative = _chat(NARRATIVE_PROMPT % ev, SYSTEM)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        out.llm_available = False
        out.narrative = (
            f"[Semantic layer unavailable: {exc}. The deterministic ledger below is "
            "unaffected and complete.]"
        )
        return out

    labels: set[str] = set()
    for n in (understanding.get("nodes") or []):
        label = str(n.get("label") or "").strip()
        if not label:
            continue
        seqs, grade, reason = _validate_evidence(ep, n.get("evidence"))
        kind = str(n.get("kind") or "ENCOUNTERED").upper()
        if reason:
            out.dropped.append({"what": "understanding_node", "label": label, "why": reason})
            continue
        kind, correction = _reconcile_kind(ep, kind, seqs, shadowed)
        if kind is None:
            out.dropped.append({"what": "understanding_node", "label": label,
                                "why": correction})
            continue
        if correction:
            out.corrections.append({"what": "understanding_node", "label": label,
                                    "correction": correction})
        bad = session_quantities(str(n.get("detail") or ""))
        if bad:
            out.dropped.append({"what": "understanding_node", "label": label,
                                "why": f"model stated a session quantity {bad}; "
                                       "quantities are the ledger's, not the model's"})
            continue
        labels.add(label)
        out.understanding_nodes.append(Node(
            label=label, kind=kind, detail=str(n.get("detail") or ""),
            evidence=seqs, grade=weakest(grade, "EVALUATED"),
        ))

    # Some models return edge endpoints as positional numbers rather than labels.
    # Resolving those is safe -- it is a naming convention, not a claim -- provided
    # the number lands unambiguously on a node that survived. Evidence citations are
    # still validated exactly as before. Without this, one formatting choice by the
    # model silently costs the entire relation graph, which is what happened on the
    # held-out episode's first run.
    returned = [str(n.get("label") or "") for n in (understanding.get("nodes") or [])]

    def resolve(ref: str) -> str:
        if ref in labels:
            return ref
        try:
            i = int(ref)
        except (TypeError, ValueError):
            return ref
        for idx in (i - 1, i):          # 1-based first, then 0-based
            if 0 <= idx < len(returned) and returned[idx] in labels:
                return returned[idx]
        return ref

    for e in (understanding.get("edges") or []):
        raw_src, raw_tgt = str(e.get("source") or ""), str(e.get("target") or "")
        src, tgt = resolve(raw_src), resolve(raw_tgt)
        if (src, tgt) != (raw_src, raw_tgt) and src in labels and tgt in labels:
            out.corrections.append({
                "what": "understanding_edge", "label": f"{raw_src} -> {raw_tgt}",
                "correction": f"model referenced nodes positionally; resolved to "
                              f"{src} -> {tgt}",
            })
        if src not in labels or tgt not in labels:
            out.dropped.append({"what": "understanding_edge",
                                "label": f"{raw_src} -> {raw_tgt}",
                                "why": "endpoint is not a surviving node"})
            continue
        seqs, grade, reason = _validate_evidence(ep, e.get("evidence"))
        if reason:
            out.dropped.append({"what": "understanding_edge",
                                "label": f"{src} -> {tgt}", "why": reason})
            continue
        out.understanding_edges.append(Edge(
            source=src, target=tgt, relation=str(e.get("relation") or "RELATED"),
            evidence=seqs, grade=weakest(grade, "EVALUATED"),
        ))

    for o in (reasoning.get("observations") or []):
        axis = str(o.get("axis") or "").upper()
        if axis not in REASONING_AXES:
            out.dropped.append({"what": "reasoning", "label": axis, "why": "unknown axis"})
            continue
        seqs, grade, reason = _validate_evidence(ep, o.get("evidence"))
        if reason:
            out.dropped.append({"what": "reasoning", "label": axis, "why": reason})
            continue
        if not _cites_learner_action(ep, seqs):
            out.dropped.append({"what": "reasoning", "label": axis,
                                "why": "cites no learner action"})
            continue
        bad = session_quantities(str(o.get("observation") or ""))
        if bad:
            out.dropped.append({"what": "reasoning", "label": axis,
                                "why": f"model stated a session quantity {bad}; "
                                       "quantities are the ledger's, not the model's"})
            continue
        polarity = str(o.get("polarity") or "EVIDENCED").upper()
        if polarity not in ("EVIDENCED", "NOT_EVIDENCED"):
            polarity = "EVIDENCED"
        # A positive claim about the learner's own thinking has to rest on the
        # learner's own expression -- their writing, their question, or their act
        # of submitting work for critique. Transfers and telemetry alone cannot
        # carry it, however plausible the sentence sounds.
        if polarity == "EVIDENCED":
            roles = _roles(ep, seqs, shadowed)
            if not (roles & LEARNER_EXPRESSION_ROLES):
                # The model wrote this as a credit. The citations cannot carry one.
                # Flipping the polarity while keeping the model's approving prose
                # produces a bullet that says "not evidenced" and then praises the
                # learner anyway -- worse than silence, because a teacher reads the
                # sentence, not the label. Drop it: a missing finding is the
                # acceptable failure, a contradictory one is not.
                out.dropped.append({
                    "what": "reasoning", "label": axis,
                    "why": ("model claimed this as evidenced, but every cited event "
                            "is a transfer, telemetry or unattributable writing; a "
                            "credit cannot rest on those, and its wording cannot be "
                            "salvaged as a negative finding"),
                })
                continue
        out.reasoning.append(ReasoningObservation(
            axis=axis, observation=str(o.get("observation") or ""),
            evidence=seqs, grade=weakest(grade, "EVALUATED"), polarity=polarity,
        ))

    text = str(narrative.get("narrative") or "").strip()
    for bad in session_quantities(text):
        text = text.replace(bad, "[figure removed — see the measured sections]")
        out.corrections.append({
            "what": "narrative", "label": bad,
            "correction": "removed a session quantity the model stated; the measured "
                          "sections carry the figures",
        })
    out.narrative = text
    return out

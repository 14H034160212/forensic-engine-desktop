"""Deterministic measurement over the chain. No language model touches this file.

Everything a teacher report says about *quantity* -- how much text came from an
AI, how long a response was on screen, how many turns the learner drove -- is
computed here by arithmetic over cited events. The language model is only ever
allowed to characterise *what kind of thinking* the evidence shows, never to
produce a number.

That split is deliberate. It is the same architecture that made the forensic
engine reproducible on a laptop: deterministic arithmetic for the load-bearing
figures, a model for structure and language.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .ingest import Episode, weakest

# Reading-rate bands, in words per second of active visible time. Stated as
# constants because a report that classifies a learner's attention must be able
# to name the threshold it used.
STUDIED_MAX_WPS = 2.0
PLAUSIBLE_READ_MAX_WPS = 8.0

# How close an uncorrelated copy has to be, in seconds, for untraced text that
# follows it to be reported as unattributable rather than as the learner's own.
# The held-out episode showed why this matters: a learner copied an AI answer,
# never pasted it, and wrote a heavy paraphrase instead. The engine reported the
# paraphrase as the learner "re-expressing an idea in their own writing" -- the
# single worst thing an integrity report can get wrong. The chain cannot tell whose
# words they are, so the report must not pick a side.
COPY_SHADOW_SECONDS = 300


@dataclass
class DocLedger:
    document: str
    doc_id: str
    baseline_chars: int
    baseline_origin: str
    final_chars: int
    transferred_chars: int
    below_threshold_chars: int
    no_correlated_transfer_chars: int
    deleted_chars: int
    rewrites: int
    transfer_sources: dict[str, int] = field(default_factory=dict)
    citations: list[str] = field(default_factory=list)
    # The actual transferred passages. A character count tells a teacher how much
    # came from an AI; only the text tells them which part of the work it is.
    transferred_excerpts: list[dict[str, Any]] = field(default_factory=list)

    @property
    def accounted_inserted(self) -> int:
        return (self.transferred_chars + self.below_threshold_chars
                + self.no_correlated_transfer_chars)

    @property
    def transferred_share(self) -> float:
        total = self.accounted_inserted
        return (self.transferred_chars / total) if total else 0.0


@dataclass
class Attention:
    provider: str
    message_id: str
    words: int
    active_visible_ms: int
    words_per_second: float | None
    exposure_fraction: float | None
    revisits: int
    band: str
    citation: str


@dataclass
class Turn:
    seq: int
    at: str
    provider: str
    prompt: str
    prompt_chars: int
    attachments: list[dict[str, Any]]
    response_seq: int | None
    response: str
    actor_basis: str


@dataclass
class ShadowedInsert:
    """Untraced text written soon after a copy that never landed anywhere.

    Not an accusation and not a credit. Two facts sit next to each other -- text
    left an AI answer onto the clipboard, and untraced text appeared shortly
    afterwards -- and the chain does not join them. The report states both and
    declines to attribute the writing.
    """
    document: str
    chars: int
    text: str
    seq: int
    copy_seq: int
    copy_provider: str
    seconds_after_copy: float


@dataclass
class UncorrelatedCopy:
    """A copy taken from a source that no insert was ever correlated to.

    This is evidence, not an accusation: the recorder observed text leave a source
    onto the clipboard, and observed no matching arrival in a monitored document.
    It can mean the learner discarded it, pasted it somewhere unmonitored, or
    reworked it past the correlator's similarity floor. The report must say the
    copy happened and must not pick one of those explanations.
    """
    provider: str
    chars: int
    text: str
    at: str
    citation: str


@dataclass
class Gap:
    kind: str
    detail: str
    grade: str
    citation: str


@dataclass
class Expression:
    """How much of the session is the learner's own expression, by arithmetic.

    Whether a learner contributed anything is not a judgement call and must not
    be delegated to a model: an untraced insert is either there or it is not. A
    report that leaves this section empty is ambiguous between "nothing happened"
    and "the engine did not look", so the engine states it either way.
    """
    untraced_chars: int
    prompt_count: int
    prompt_chars: int
    follow_up_prompts: int
    critique_submissions: int
    ai_answer_revisits: int

    @property
    def no_untraced_writing(self) -> bool:
        return self.untraced_chars == 0

    @property
    def summary(self) -> str:
        parts = []
        if self.untraced_chars:
            parts.append(f"{self.untraced_chars} characters of writing with no traced "
                         f"source")
        else:
            parts.append("no writing at all that was not traced to a source")
        parts.append(f"{self.prompt_count} request(s) to an AI"
                     + (f", {self.follow_up_prompts} of them follow-ups"
                        if self.follow_up_prompts else ", none of them follow-ups"))
        if self.critique_submissions:
            parts.append(f"{self.critique_submissions} submission(s) of the learner's "
                         f"own file for AI critique")
        if self.ai_answer_revisits:
            parts.append(f"{self.ai_answer_revisits} return(s) to an earlier AI answer")
        return "; ".join(parts)


@dataclass
class Ledger:
    documents: list[DocLedger]
    attention: list[Attention]
    turns: list[Turn]
    gaps: list[Gap]
    excluded_ms: int
    duration_minutes: float
    providers: list[str]
    web_visits: list[dict[str, Any]]
    expression: Expression
    uncorrelated_copies: list[UncorrelatedCopy]
    shadowed_inserts: list[ShadowedInsert]


def _band(wps: float | None, fraction: float | None) -> str:
    if wps is None:
        return "UNKNOWN_NO_TELEMETRY"
    if fraction is not None and fraction < 0.5:
        return "PARTIALLY_EXPOSED"
    if wps <= STUDIED_MAX_WPS:
        return "SLOW_ENOUGH_TO_HAVE_BEEN_STUDIED"
    if wps <= PLAUSIBLE_READ_MAX_WPS:
        return "CONSISTENT_WITH_READING"
    return "TOO_FAST_TO_HAVE_BEEN_READ"


def _transfer_provider(ep: Episode, link: dict[str, Any]) -> str:
    """Resolve a TRANSFER_* link back to the provider it was copied from."""
    src_id = link.get("source_event_id")
    for e in ep.events:
        if e.get("event_id") == src_id:
            ctx = e.get("source_context") or {}
            return str(ctx.get("provider") or ctx.get("host") or ctx.get("source_type")
                       or "UNKNOWN_SOURCE")
    return "UNKNOWN_SOURCE"


def build(ep: Episode) -> Ledger:
    # ---------------------------------------------------------------- documents
    docs: dict[str, DocLedger] = {}
    for e in ep.by_kind("DOCUMENT_DISCOVERED"):
        did = str(e.get("document_id") or e.get("doc_id") or e.get("event_id"))
        docs[did] = DocLedger(
            document=str(e.get("document_name") or e.get("name") or "(unnamed)"),
            doc_id=did, baseline_chars=0,
            baseline_origin="UNKNOWN_AT_DISCOVERY",
            final_chars=0, transferred_chars=0, below_threshold_chars=0,
            no_correlated_transfer_chars=0, deleted_chars=0, rewrites=0,
            citations=[ep.cite(e)],
        )

    def doc_for(e: dict[str, Any]) -> DocLedger | None:
        did = str(e.get("document_id") or e.get("doc_id") or "")
        if did in docs:
            return docs[did]
        return next(iter(docs.values())) if len(docs) == 1 else None

    for e in ep.by_kind("DOCUMENT_BASELINE"):
        d = doc_for(e)
        if d:
            d.baseline_chars = int(e.get("chars") or 0)
            d.citations.append(ep.cite(e))

    # A baseline that a BASELINE_TRANSFER links to an AI message did not start blank.
    for e in ep.by_kind("BASELINE_TRANSFER"):
        d = doc_for(e)
        if d:
            d.baseline_origin = "RESEMBLES_AI_MESSAGE_IN_EPISODE"
            d.citations.append(ep.cite(e))
    for e in ep.by_kind("DOWNLOAD_OPENED_IN_WORD"):
        d = doc_for(e)
        if d:
            d.baseline_origin = "DOWNLOADED_FILE_OPENED_IN_WORD"
            d.citations.append(ep.cite(e))

    # Attribute correlated transfers to their source provider.
    link_by_target: dict[str, str] = {}
    for link in ep.by_kind("TRANSFER_EXACT", "TRANSFER_FUZZY", "TRANSFER_EVIDENCE"):
        provider = _transfer_provider(ep, link)
        for key in ("target_event_id", "destination_event_id", "document_event_id"):
            if link.get(key):
                link_by_target[str(link[key])] = provider
        link_by_target.setdefault(f"seq:{link.get('global_sequence', 0) - 1}", provider)

    for e in ep.by_kind("DOC_INSERT"):
        d = doc_for(e)
        if not d:
            continue
        chars = int(e.get("chars") or 0)
        cls = str(e.get("classification") or "")
        if cls == "TRANSFER_CORRELATED":
            d.transferred_chars += chars
            provider = (link_by_target.get(str(e.get("event_id")))
                        or link_by_target.get(f"seq:{e.get('global_sequence')}")
                        or "UNKNOWN_SOURCE")
            d.transfer_sources[provider] = d.transfer_sources.get(provider, 0) + chars
            text = str(e.get("text") or e.get("inserted_text") or "")
            d.transferred_excerpts.append({
                "provider": provider, "chars": chars,
                "text": text[:300] + ("…" if len(text) > 300 else ""),
                "citation": ep.cite(e),
            })
        elif cls == "BELOW_THRESHOLD":
            d.below_threshold_chars += chars
        else:
            d.no_correlated_transfer_chars += chars
        d.citations.append(ep.cite(e))

    for e in ep.by_kind("DOC_DELETE"):
        d = doc_for(e)
        if d:
            d.deleted_chars += int(e.get("chars") or 0)
    for e in ep.by_kind("DOC_REWRITE"):
        d = doc_for(e)
        if d:
            d.rewrites += 1
    for e in ep.by_kind("DOCUMENT_FINAL_TEXT"):
        d = doc_for(e)
        if d:
            d.final_chars = int(e.get("chars") or 0)
            d.citations.append(ep.cite(e))

    # ---------------------------------------------------------------- attention
    revisits: dict[str, int] = {}
    for e in ep.by_kind("SOURCE_REVISIT"):
        mid = str(e.get("message_id") or "")
        revisits[mid] = max(revisits.get(mid, 0), int(e.get("revisit_ordinal") or 1))

    attention: list[Attention] = []
    for e in ep.by_kind("EXPOSURE_SUMMARY"):
        if str(e.get("role") or "") != "assistant":
            continue
        words = int(e.get("response_words") or 0)
        ms = int(e.get("active_visible_ms") or 0)
        wps = e.get("response_words_per_active_visible_second")
        wps = float(wps) if wps is not None else (words / (ms / 1000) if ms else None)
        frac = e.get("segment_exposure_fraction")
        mid = str(e.get("message_id") or "")
        attention.append(Attention(
            provider=str(e.get("provider") or "?"), message_id=mid, words=words,
            active_visible_ms=ms, words_per_second=round(wps, 2) if wps else None,
            exposure_fraction=float(frac) if frac is not None else None,
            revisits=revisits.get(mid, 0),
            band=_band(wps, float(frac) if frac is not None else None),
            citation=ep.cite(e),
        ))

    # ---------------------------------------------------------------- turns
    # KD-2.3-D3: a provider may commit progress text ("Ran 3 searches", "Working
    # on it…") before the real answer, then amend it. The recorder's own defect
    # notes say to prefer the amendment as the later, stronger content state. The
    # first cold run of the held-out episode reported "Working on it — searching
    # for sources." as the AI's answer, which is exactly the failure that note
    # warns about.
    all_responses = ep.by_kind("AI_RESPONSE", "AI_RESPONSE_INCOMPLETE",
                               "AI_RESPONSE_AMENDED")
    superseded: set[str] = set()
    amended_by_msg: dict[tuple[str, str], dict[str, Any]] = {}
    for r in all_responses:
        if r.get("kind") != "AI_RESPONSE_AMENDED":
            continue
        key = (str((r.get("conversation_ref") or {}).get("local_conversation_id") or ""),
               str(r.get("message_id") or ""))
        prior = amended_by_msg.get(key)
        if prior is None or int(r.get("global_sequence", 0)) > int(prior.get("global_sequence", 0)):
            amended_by_msg[key] = r
    for r in all_responses:
        if r.get("kind") == "AI_RESPONSE_AMENDED":
            continue
        key = (str((r.get("conversation_ref") or {}).get("local_conversation_id") or ""),
               str(r.get("message_id") or ""))
        if key in amended_by_msg and str(r.get("message_id") or ""):
            superseded.add(str(r.get("event_id")))
    responses = [r for r in all_responses
                 if str(r.get("event_id")) not in superseded]
    turns: list[Turn] = []
    for p in ep.by_kind("AI_PROMPT"):
        conv = (p.get("conversation_ref") or {}).get("local_conversation_id")
        after = [r for r in responses
                 if (r.get("conversation_ref") or {}).get("local_conversation_id") == conv
                 and int(r.get("global_sequence", 0)) > int(p.get("global_sequence", 0))]
        r = after[0] if after else None
        turns.append(Turn(
            seq=int(p.get("global_sequence", 0)),
            at=str(p.get("observed_at") or ""),
            provider=str(p.get("provider") or (p.get("conversation_ref") or {}).get("provider") or "?"),
            prompt=str(p.get("text") or ""),
            prompt_chars=len(str(p.get("text") or "")),
            attachments=list(p.get("attachments") or []),
            response_seq=int(r.get("global_sequence", 0)) if r else None,
            response=str(r.get("text") or "") if r else "",
            actor_basis=str(p.get("actor_basis") or "UNKNOWN"),
        ))

    # ---------------------------------------------------------------- gaps
    gaps: list[Gap] = []
    excluded_ms = 0
    for e in ep.by_kind("WEB_EXCLUDED_ACTIVITY"):
        ms = int(e.get("duration_ms") or 0)
        excluded_ms += ms
        gaps.append(Gap(
            kind="EXCLUDED_HOST",
            detail=(f"{ms / 1000:.0f}s of browser activity on a privacy-excluded host. "
                    "No URL, title or content was captured, by policy."),
            grade="OBSERVED", citation=ep.cite(e),
        ))
    for e in ep.by_kind("FILE_DOWNLOADED"):
        hint = e.get("active_tab_hint") or {}
        gaps.append(Gap(
            kind="DOWNLOAD_ORIGIN_INFERRED",
            detail=(f"Downloaded {e.get('filename') or e.get('name')}. Its conversation context is the "
                    f"active tab at completion ({hint.get('provider') or 'unknown'}), "
                    "which is a hint, not an observed association."),
            grade=weakest("OBSERVED", str(hint.get("conversation_link_grade") or "INFERRED")),
            citation=ep.cite(e),
        ))
    for e in ep.by_kind("CONNECTOR_GAP_START", "CAPTURE_LIMITATION"):
        gaps.append(Gap(kind="CAPTURE_LIMITATION",
                        detail=str(e.get("summary") or e.get("limitation") or ""),
                        grade="OBSERVED", citation=ep.cite(e)))
    for d in docs.values():
        if d.baseline_chars > 0 and d.baseline_origin == "UNKNOWN_AT_DISCOVERY":
            gaps.append(Gap(
                kind="BASELINE_ORIGIN_UNKNOWN",
                detail=(f"{d.document} already contained {d.baseline_chars} characters "
                        "when the episode started. The chain does not evidence where "
                        "that text came from."),
                grade="OBSERVED", citation=d.citations[0] if d.citations else "-"))
    for att in [a for t in turns for a in t.attachments]:
        if str(att.get("attachment_basis") or "") == "ADDED_BEFORE_SUBMIT":
            gaps.append(Gap(
                kind="ATTACHMENT_BASIS_DERIVED",
                detail=(f"Attachment {att.get('name')} was observed added to the "
                        "composer before submit, not named in the sent message. It "
                        "could have been removed before sending."),
                grade="DERIVED", citation="-"))

    # ---------------------------------------------------------------- session shape
    times = [e.get("observed_at") for e in ep.events if e.get("observed_at")]
    duration = 0.0
    if len(times) >= 2:
        from .ingest import GRADE_ORDER  # noqa: F401  (keeps import surface explicit)
        from datetime import datetime

        def p(v: str) -> datetime:
            v = v[:-1] + "+00:00" if v.endswith("Z") else v
            return datetime.fromisoformat(v)

        try:
            duration = (p(times[-1]) - p(times[0])).total_seconds() / 60.0
        except Exception:
            duration = 0.0

    providers = sorted({t.provider for t in turns if t.provider != "?"})
    # Search terms are captured by the recorder and named in the product summary,
    # so they belong in the teacher's report. The first cold run dropped them.
    visits = [{"host": e.get("host"), "title": e.get("page_title"),
               "url": e.get("url"),
               "search_query": e.get("search_query") if e.get("query_present") else None,
               "citation": ep.cite(e)}
              for e in ep.by_kind("WEB_NAVIGATION")]

    # A follow-up is a prompt in a conversation that already had a prior turn:
    # it evidences the learner reacting to an answer rather than issuing one order.
    seen_conv: set[str] = set()
    follow_ups = 0
    for p_ in ep.by_kind("AI_PROMPT"):
        conv = str((p_.get("conversation_ref") or {}).get("local_conversation_id") or "")
        if conv in seen_conv:
            follow_ups += 1
        seen_conv.add(conv)

    linked_sources = {str(l.get("source_event_id")) for l in
                      ep.by_kind("TRANSFER_EXACT", "TRANSFER_FUZZY",
                                 "TRANSFER_EVIDENCE")}
    uncorrelated: list[UncorrelatedCopy] = []
    for c in ep.by_kind("COPY", "CUT"):
        if str(c.get("event_id")) in linked_sources:
            continue
        ctx = c.get("source_context") or {}
        text = str(c.get("text") or "")
        uncorrelated.append(UncorrelatedCopy(
            provider=str(ctx.get("provider") or ctx.get("host")
                         or ctx.get("source_type") or "UNKNOWN_SOURCE"),
            chars=int(c.get("chars") or len(text)),
            text=text[:300] + ("…" if len(text) > 300 else ""),
            at=str(c.get("observed_at") or ""), citation=ep.cite(c),
        ))

    # Which untraced inserts fall in the shadow of an uncorrelated copy.
    def _ts(v: Any) -> Any:
        from datetime import datetime
        t = str(v or "")
        if not t:
            return None
        try:
            return datetime.fromisoformat(t[:-1] + "+00:00" if t.endswith("Z") else t)
        except Exception:
            return None

    shadowed: list[ShadowedInsert] = []
    shadow_seqs: set[int] = set()
    for e in ep.by_kind("DOC_INSERT"):
        if str(e.get("classification") or "") != "NO_CORRELATED_TRANSFER":
            continue
        it = _ts(e.get("observed_at"))
        if it is None:
            continue
        best = None
        for c in uncorrelated:
            ct = _ts(c.at)
            if ct is None or ct > it:
                continue
            delta = (it - ct).total_seconds()
            if delta <= COPY_SHADOW_SECONDS and (best is None or delta < best[0]):
                best = (delta, c)
        if best is None:
            continue
        delta, c = best
        d = doc_for(e)
        text = str(e.get("text") or e.get("inserted_text") or "")
        shadow_seqs.add(int(e.get("global_sequence") or 0))
        shadowed.append(ShadowedInsert(
            document=d.document if d else "(unknown)",
            chars=int(e.get("chars") or 0),
            text=text[:300] + ("…" if len(text) > 300 else ""),
            seq=int(e.get("global_sequence") or 0),
            copy_seq=int(c.citation.lstrip("#") or 0),
            copy_provider=c.provider, seconds_after_copy=round(delta, 1),
        ))

    expression = Expression(
        untraced_chars=sum(d.no_correlated_transfer_chars for d in docs.values()),
        prompt_count=len(turns),
        prompt_chars=sum(t.prompt_chars for t in turns),
        follow_up_prompts=follow_ups,
        critique_submissions=sum(1 for t in turns if t.attachments),
        ai_answer_revisits=sum(a.revisits for a in attention),
    )

    return Ledger(documents=list(docs.values()), attention=attention, turns=turns,
                  gaps=gaps, excluded_ms=excluded_ms, duration_minutes=round(duration, 1),
                  providers=providers, web_visits=visits, expression=expression,
                  uncorrelated_copies=uncorrelated, shadowed_inserts=shadowed)

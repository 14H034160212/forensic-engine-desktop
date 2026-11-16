"""
Input adapter: deterministic mapping from the Ingester's compact student-actions output
(records keyed by `action` / `origin` / `origin_basis` / ...) into the DRE's recorder-event vocabulary
(`kind` / `evidence_grade` / attribution), WITHOUT fabricating a hash chain or original timestamps.

Why this exists: the Ingester (deterministic, no-LLM) reduces a full Tarski Telemetry stream to a compact
student-actions record. Feeding that straight to the DRE used to require hand-reshaping it to masquerade as
recorder events. This adapter does that mapping automatically and HONESTLY: the adapted events are marked
`evidence_grade: DERIVED` with capture_flags, so the DRE's independent hash-chain check records
"no chain present" (dre_core.load_all handles this) and the teacher/student report is generated on evidence
clearly labelled as a derived research view — never as authoritative recorder telemetry.

Engagement: dre_core.load_all calls `adapt()` only when `looks_like_ingester()` is true (records have an
`action` field and no recorder `kind`). A real TT episode always carries `kind`, so this never fires on
authoritative telemetry. Set env DRE_INGEST_ADAPTER=off to disable entirely.

Nothing here interprets or judges — it only renames/relabels fields and preserves every original field, so
the DRE's reasoning and verification safeguards are unchanged.
"""
import os

# Ingester `action` -> DRE recorder `kind`. Most already coincide; listed explicitly so the map is auditable.
_ACTION_TO_KIND = {
    "DOC_INSERT": "DOC_INSERT", "DOC_EDIT": "DOC_EDIT", "DOC_DELETE": "DOC_DELETE",
    "DOC_REWRITE": "DOC_REWRITE", "DOC_WHITESPACE_CHANGE": "DOC_WHITESPACE_CHANGE",
    "COPY": "COPY", "PASTE": "PASTE", "TRANSFER": "TRANSFER",
    "AI_PROMPT": "AI_PROMPT", "AI_RESPONSE": "AI_RESPONSE",
}

# Ingester `origin` -> coarse actor label. Preserves uncertainty; never upgrades an unknown to a claim.
_ORIGIN_TO_ACTOR = {
    "STUDENT": "student", "AI": "ai", "UNKNOWN": "unknown", "MIXED_OR_UNVERIFIED": "unverified",
}

_DERIVED_FLAGS = ["DERIVED_VIEW_NO_TT_CHAIN", "NO_ORIGINAL_TIMESTAMPS", "INGESTER_DERIVED_ACTIONS"]
_RECORDER = "DERIVED_INGESTER_VIEW_NOT_RECORDER"


def looks_like_ingester(records):
    """True only for the unambiguous Ingester signature: records carry `action` and no recorder `kind`."""
    if not records:
        return False
    sample = [r for r in records[:25] if isinstance(r, dict)]
    if not sample:
        return False
    return all("action" in r for r in sample) and not any("kind" in r for r in sample)


def adapt(records, author_label=None):
    """Return DRE-shaped events: one synthetic SESSION_START + each Ingester record relabelled.
    Pure, deterministic, order-preserving; every original field is preserved."""
    author_label = author_label or os.environ.get("DRE_INGEST_AUTHOR", "the learner")
    episode_id = next((r.get("episode_id") for r in records if isinstance(r, dict) and r.get("episode_id")),
                      "derived_ingester_episode")
    events = [{
        "kind": "SESSION_START",
        "episode_id": episode_id,
        "episode_name": os.environ.get("DRE_INGEST_EPISODE_NAME", "Derived student-actions session"),
        "author_label": author_label,
        "recorder_version": _RECORDER,
        "evidence_grade": "DERIVED",
        "capture_flags": list(_DERIVED_FLAGS),
        "synthetic": True,
    }]
    for r in records:
        if not isinstance(r, dict):
            continue
        ev = dict(r)  # preserve EVERYTHING: origin_basis, change_classification, entry_method, delta_group_id...
        ev["kind"] = _ACTION_TO_KIND.get(r.get("action"), r.get("action"))  # unknown actions pass through
        ev["evidence_grade"] = "DERIVED"               # a derived view is never graded higher than DERIVED
        ev["actor"] = _ORIGIN_TO_ACTOR.get(r.get("origin"), "unknown")
        ev["recorder_version"] = _RECORDER
        ev.setdefault("capture_flags", list(_DERIVED_FLAGS))
        if ev.get("chars") is None and isinstance(r.get("text"), str):
            ev["chars"] = len(r["text"])               # dre_core uses chars or len(text) for doc inserts
        events.append(ev)
    return events

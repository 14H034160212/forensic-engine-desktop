"""Episode ingest, independent integrity verification, and coverage declaration.

Design rule for the whole DRE: nothing downstream may assert anything the chain
does not carry, and every assertion inherits the weakest evidence grade on its
path.  This module establishes the three things the rest of the engine needs
before it is allowed to say a single word about a learner:

1. Is this chain intact, and *how strongly* is it intact?
2. What could this recorder version physically observe (capability declaration)?
3. What is known to be unobservable or defective for this version?

The hash chain is recomputed here from first principles rather than by calling
the recorder's own verifier.  A verifier that trusts the code that produced the
artefact is not a verifier.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Version-keyed limitations, transcribed from the recorder's KNOWN_DEFECTS.md.
# The recorder ships this file explicitly for downstream analysis; the DRE is the
# downstream consumer it was written for.
KNOWN_LIMITATIONS: dict[str, list[dict[str, str]]] = {
    "2.5.0c-poc": [
        {"id": "KD-2.5-L1", "effect": "Files uploaded to an AI are invisible.",
         "dre_rule": "Never infer that a short prompt carried no material."},
        {"id": "KD-2.5-L2", "effect": "Provider Copy-button copies lack message position.",
         "dre_rule": "Attribute such copies to the visible conversation at reduced confidence."},
        {"id": "KD-2.5-L3", "effect": "Exact pastes under 40 normalised chars read as BELOW_THRESHOLD.",
         "dre_rule": "Treat a BELOW_THRESHOLD insert matching a recent copy as a transfer."},
        {"id": "KD-2.5-L4", "effect": "Downloads and pre-session AI documents are invisible.",
         "dre_rule": "A document baseline's origin is unknown, not learner-authored."},
    ],
    "2.6.0c-poc": [
        {"id": "KD-2.6-A1", "effect": "ADDED_BEFORE_SUBMIT attachments may have been removed before sending.",
         "dre_rule": "Report such attachments as DERIVED, not as observed uploads."},
        {"id": "KD-2.6-A2", "effect": "A download's conversation context is an active-tab hint only.",
         "dre_rule": "Never state which conversation produced a downloaded file."},
        {"id": "KD-2.6-A3", "effect": "Attachment content above policy caps, or from STANDARD hosts, is hash-only.",
         "dre_rule": "Absence of attachment content is not absence of material."},
    ],
}

# Limitations that hold for every version, because they are properties of what a
# desktop recorder can see at all rather than bugs.  These are the ones an
# examiner will attack, so the report states them itself.
STRUCTURAL_LIMITATIONS = [
    "The chain evidences activity inside the recorded envelope only. Work done on "
    "another device, on paper, or before the episode started is outside it.",
    "NO_CORRELATED_TRANSFER means no source transfer was correlated. It is not "
    "evidence that the learner typed the text from their own knowledge.",
    "Time visible on screen is an upper bound on attention, not a measure of "
    "comprehension.",
]

GRADE_ORDER = {"OBSERVED": 3, "DERIVED": 2, "INFERRED": 1, "EVALUATED": 0}


def weakest(*grades: str) -> str:
    """The grade an assertion inherits: the weakest link on its evidence path."""
    present = [g for g in grades if g in GRADE_ORDER]
    if not present:
        return "INFERRED"
    return min(present, key=lambda g: GRADE_ORDER[g])


def canonical_bytes(event: dict[str, Any]) -> bytes:
    """Reimplementation of the recorder's canonical serialisation.

    Independent by design: if the recorder ever changes its canonicalisation, this
    verifier must disagree loudly rather than silently agree.
    """
    payload = {k: v for k, v in event.items() if k != "event_hash"}
    rendered = json.dumps(payload, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"))
    try:
        return rendered.encode("utf-8")
    except UnicodeEncodeError:
        return json.dumps(payload, ensure_ascii=True, sort_keys=True,
                          separators=(",", ":")).encode("ascii")


@dataclass
class Integrity:
    chain_ok: bool
    events_verified: int
    detail: str
    manifest_hash_matches: bool
    tamper_resistance: str
    caveat: str


@dataclass
class Episode:
    path: Path
    events: list[dict[str, Any]]
    manifest: dict[str, Any]
    integrity: Integrity
    recorder_version: str
    capabilities: list[str] = field(default_factory=list)
    limitations: list[dict[str, str]] = field(default_factory=list)
    aborted: bool = False

    def by_kind(self, *kinds: str) -> list[dict[str, Any]]:
        want = set(kinds)
        return [e for e in self.events if e.get("kind") in want]

    def by_seq(self, seq: int) -> dict[str, Any] | None:
        for e in self.events:
            if e.get("global_sequence") == seq:
                return e
        return None

    def cite(self, event: dict[str, Any]) -> str:
        return f"#{event.get('global_sequence')}"


def _verify_chain(events: list[dict[str, Any]]) -> tuple[bool, int, str]:
    previous = ""
    for i, ev in enumerate(events):
        stored = ev.get("event_hash")
        if not stored:
            return False, i, f"event {i} has no event_hash"
        if ev.get("previous_hash", "") != previous:
            return False, i, (
                f"event {i} (seq {ev.get('global_sequence')}) previous_hash does not "
                f"match the hash of event {i - 1}"
            )
        recomputed = hashlib.sha256(canonical_bytes(ev)).hexdigest()
        if recomputed != stored:
            return False, i, (
                f"event {i} (seq {ev.get('global_sequence')}) payload does not match "
                f"its own event_hash"
            )
        expected_seq = i + 1
        if ev.get("global_sequence") != expected_seq:
            return False, i, (
                f"sequence gap: event {i} declares global_sequence "
                f"{ev.get('global_sequence')}, expected {expected_seq}"
            )
        previous = stored
    return True, len(events), f"{len(events)} events verified"


def load(episode_dir: str | Path) -> Episode:
    path = Path(episode_dir)
    jsonl = sorted(path.glob("*.jsonl"))
    if not jsonl:
        raise FileNotFoundError(f"no .jsonl provenance log in {path}")
    events = [json.loads(line) for line in jsonl[0].read_text(encoding="utf-8").splitlines() if line.strip()]

    manifest: dict[str, Any] = {}
    mf = list(path.glob("*manifest*.json"))
    if mf:
        manifest = json.loads(mf[0].read_text(encoding="utf-8"))

    chain_ok, verified, detail = _verify_chain(events)
    final = events[-1].get("event_hash") if events else None
    manifest_final = manifest.get("final_chain_hash")
    # The manifest is written before SESSION_STOP is hashed in some paths, so a
    # mismatch is only meaningful if the manifest hash appears nowhere in the chain.
    hashes = {e.get("event_hash") for e in events}
    manifest_ok = bool(manifest_final) and (manifest_final == final or manifest_final in hashes)

    integrity = Integrity(
        chain_ok=chain_ok,
        events_verified=verified,
        detail=detail,
        manifest_hash_matches=manifest_ok,
        # Stated precisely, because this is the claim diligence will test.
        tamper_resistance="LOCAL_HASH_CHAIN_ONLY",
        caveat=(
            "Integrity is a local SHA-256 hash chain. It detects modification of a "
            "committed event and any break in the link order. It does not prove the "
            "chain was not regenerated wholesale on the recording machine, because no "
            "key withheld from that machine signs it and no digest is anchored "
            "off-machine. Treat this as VERIFIED-INTACT, not as tamper-proof."
        ),
    )

    start = next((e for e in events if e.get("kind") == "SESSION_START"), {})
    cfg = (start.get("capture_configuration") or {}) if isinstance(start, dict) else {}
    version = str(start.get("recorder_version_declared")
                  or manifest.get("recorder_version")
                  or (events[0].get("recorder_version") if events else "")
                  or "unknown")

    limitations = list(KNOWN_LIMITATIONS.get(version, []))
    aborted = any(e.get("kind") == "SESSION_ABORTED" for e in events)

    return Episode(
        path=path,
        events=events,
        manifest=manifest,
        integrity=integrity,
        recorder_version=version,
        capabilities=list(cfg.get("capabilities") or []),
        limitations=limitations,
        aborted=aborted,
    )

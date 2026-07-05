#!/usr/bin/env python3
"""
Reasoning Excavation — merges a 3-step method into the local engine.

  Step 0  Reader inference + author intent   (what a reasonable reader believes,
          and what the author wants them to believe — captured before analysis)
  Step 1+2 Reasoning Atom Register           (the document decomposed into small,
          categorised, stable-ID reasoning atoms across 16 atom types)
  Step 3  Bond mapping                       (the RELATIONSHIPS between atoms —
          dependencies, contradictions, load-bearing chains)

Runs fully local against Ollama (via prosecution_engine's chat helpers). Blind:
works only from the document text. IDs are assigned deterministically in Python so
the passes compose cleanly, exactly as the Step 1 -> 2 -> 3 chain requires.
"""
import os, sys, json, time
import prosecution_engine as E   # reuse chat / chat_json / LLM against local Ollama

# 16 atom categories (name, stable-ID prefix) — mirrors the Step 2 register
CATEGORIES = [
    ("Explicit Claim", "EC"), ("Implied Claim", "IM"), ("Assumption", "AS"),
    ("Presupposition", "PS"), ("Implication / Consequence", "IC"),
    ("Definition / Threshold", "DT"), ("Qualifier / Modality", "QM"),
    ("Causal", "CA"), ("Dependency", "DP"), ("Evidence-Burden", "EB"),
    ("Contradiction / Tension", "CT"), ("Ambiguity / Interpretive-Risk", "AM"),
    ("Reasoning-Risk Trigger", "RR"), ("Conclusion", "CO"),
    ("Recommendation / Action", "RA"), ("Candidate Load-Bearing", "LB"),
]
PREFIX = {name: pre for name, pre in CATEGORIES}

# ---------------------------------------------------------------- Step 0
def step0_reader_and_intent(text):
    sysp = ("You capture the PERSUASIVE SURFACE of a document before any analysis: what "
            "a reasonable, attentive reader is likely to believe/conclude/feel after a "
            "superficial read, and what the author appears to WANT the reader to conclude/"
            "believe/feel/do. This is not a summary, fact-check, or critique — only "
            "reader-level takeaways and inferred author intent. Work only from the text.")
    usr = ("<document>\n" + text + "\n</document>\n\n"
        'Return JSON {"reader_takeaways":[ "..." ], "author_intent":[ "..." ]}. '
        "Be thorough — 8-16 items each. Capture inferences the reader makes beyond the "
        "literal words (from logos, credentials, regulatory language, narrative momentum).")
    return E.chat_json(sysp, usr)

# ---------------------------------------------------------------- Step 1+2
def _atom_batch(text, cats):
    names = ", ".join(f'"{n}"' for n, _ in cats)
    defs = "\n".join(f"- {n}" for n, _ in cats)
    sysp = ("You decompose a document into REASONING ATOMS — the smallest discrete "
            "reasoning commitments in it. Trace each atom to where it comes from. Work "
            "ONLY from the text; do not fact-check or judge truth. Do not merge distinct "
            "atoms. Maximise recall.")
    usr = ("<document>\n" + text + "\n</document>\n\n"
        "Extract reasoning atoms ONLY for these categories:\n" + defs + "\n\n"
        'Return JSON {"atoms":[ {"category":"<one of: ' + names + '>", '
        '"text":"the atom, one sentence", "source":"slide/section it comes from"} ]}. '
        "Be EXHAUSTIVE — aim for 8-20 atoms per category wherever the document supports "
        "them; every slide/section yields several. Do not stop early or collapse atoms.")
    try:
        return E.chat_json(sysp, usr).get("atoms", [])
    except Exception:
        return []

def atom_register(text, batch=1, on_stage=None):
    """batch=1 => one focused pass per category (highest recall, ~16 calls).
    batch=4 => four grouped passes (faster, lower recall)."""
    atoms, counters = [], {}
    batches = [CATEGORIES[i:i+batch] for i in range(0, len(CATEGORIES), batch)]
    for bi, cats in enumerate(batches, 1):
        got = _atom_batch(text, cats)
        for a in got:
            cat = a.get("category", "").strip()
            pre = PREFIX.get(cat)
            if not pre:  # tolerate loose category names -> match by prefix of name
                pre = next((p for n, p in CATEGORIES if n.lower().startswith(cat.lower()[:6])), None)
                cat = next((n for n, p in CATEGORIES if p == pre), cat) if pre else cat
            if not pre:
                continue
            counters[pre] = counters.get(pre, 0) + 1
            atoms.append({"id": f"{pre}-{counters[pre]:03d}", "category": cat,
                          "text": a.get("text", "").strip(), "source": a.get("source", "")})
        if on_stage:
            on_stage("atoms", f"batch {bi}/{len(batches)} — {len(atoms)} atoms so far")
    return atoms

# ---------------------------------------------------------------- Step 3
def bond_map(atoms, on_stage=None):
    """Relationships between atoms. Focus on the reasoning-bearing categories to keep it
    tractable (bonds scale ~quadratically), but reference the full ID space."""
    key = [a for a in atoms if a["id"][:2] in ("EC", "IM", "AS", "PS", "CA", "DP",
                                               "CT", "EB", "RR", "CO", "LB")]
    # dedup near-identical atom texts so restatements aren't mistaken for contradictions
    seen, deduped = set(), []
    for a in key:
        norm = "".join(ch for ch in a["text"].lower() if ch.isalnum())[:60]
        if norm in seen:
            continue
        seen.add(norm); deduped.append(a)
    listing = "\n".join(f'{a["id"]}: {a["text"]}' for a in deduped[:200])
    sysp = ("You map the RELATIONSHIPS (bonds) between reasoning atoms from one document. "
            "A bond links two atoms by ID. Types: 'depends-on' (A needs B to hold), "
            "'supports' (A is evidence/reason for B), 'contradicts' (A and B cannot both "
            "hold), 'undercuts' (A weakens B), 'implies' (A entails B). Use ONLY the atoms "
            "given.\n\nA 'contradicts' bond requires two atoms making DIFFERENT commitments "
            "that cannot both hold at once — for example: a claim requiring human clinical "
            "supervision vs a claim of dramatic cost reduction at high scale; a present-tense "
            "'regulated/medically-cleared' claim vs a future clearance date; a 'first/only' "
            "claim vs prior art existing. Do NOT mark restatements, near-duplicates, or "
            "atoms that AGREE with each other as contradictions — those are not tensions. "
            "Actively hunt for the genuine cannot-both-be-true tensions.")
    usr = ("ATOMS:\n" + listing + "\n\n"
        'Return JSON {"bonds":[ {"from":"ID","to":"ID","type":"depends-on/supports/'
        'contradicts/undercuts/implies","note":"one line why"} ]}. Return the significant '
        "bonds (aim for 20-50), and include EVERY genuine contradiction/tension you can find "
        "(these are the most valuable). Then the dependency chains that make atoms load-bearing.")
    try:
        bonds = E.chat_json(sysp, usr).get("bonds", [])
    except Exception:
        bonds = []
    ids = {a["id"] for a in atoms}
    bonds = [b for b in bonds if b.get("from") in ids and b.get("to") in ids]
    return bonds

# ---------------------------------------------------------------- orchestrate
def excavate(text, label="Document", batch=1, on_stage=None):
    def stage(s, m):
        if on_stage: on_stage(s, m)
    t0 = time.time()
    stage("s0", "Step 0 — reader inference + author intent…")
    s0 = step0_reader_and_intent(text)
    stage("s0done", f"reader takeaways {len(s0.get('reader_takeaways',[]))}, "
                    f"author-intent {len(s0.get('author_intent',[]))}")

    stage("atoms", "Steps 1+2 — building the reasoning atom register…")
    atoms = atom_register(text, batch=batch, on_stage=on_stage)
    by_cat = {}
    for a in atoms:
        by_cat[a["category"]] = by_cat.get(a["category"], 0) + 1
    stage("atomsdone", f"{len(atoms)} atoms across {len(by_cat)} categories")

    stage("bonds", "Step 3 — mapping bonds between atoms…")
    bonds = bond_map(atoms, on_stage=on_stage)
    contradictions = [b for b in bonds if b.get("type") == "contradicts"]
    # load-bearing by in-degree of dependency/support
    indeg = {}
    for b in bonds:
        if b.get("type") in ("depends-on", "supports", "implies"):
            indeg[b["to"]] = indeg.get(b["to"], 0) + 1
    load_bearing = sorted(indeg.items(), key=lambda x: -x[1])[:8]
    stage("bondsdone", f"{len(bonds)} bonds ({len(contradictions)} contradictions)")

    return {"label": label, "model": E.LLM, "blind": True,
            "step0": s0, "atoms": atoms, "atoms_by_category": by_cat,
            "bonds": bonds, "contradictions": contradictions,
            "load_bearing_atoms": load_bearing,
            "stats": {"reader_takeaways": len(s0.get("reader_takeaways", [])),
                      "author_intent": len(s0.get("author_intent", [])),
                      "atoms": len(atoms), "categories": len(by_cat),
                      "bonds": len(bonds), "contradictions": len(contradictions),
                      "seconds": round(time.time() - t0)}}

if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "decks/quickbite.txt"
    label = sys.argv[2] if len(sys.argv) > 2 else os.path.basename(path).split(".")[0]
    text = open(path).read().strip()
    batch = int(os.environ.get("EXCAV_BATCH", "1"))
    res = excavate(text, label, batch=batch, on_stage=lambda s, m: print("  " + m, flush=True))
    os.makedirs("prosecution_out", exist_ok=True)
    json.dump(res, open(f"prosecution_out/{label}_excavation.json", "w"), indent=2, ensure_ascii=False)
    print("\nSTATS:", json.dumps(res["stats"], indent=2))

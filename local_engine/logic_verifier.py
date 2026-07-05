#!/usr/bin/env python3
"""
Logic verifier for the reasoning-excavation bond graph.

The excavation's Step-3 "contradiction" bonds are proposed by an LLM and are noisy
(we saw near-duplicate atoms mislabelled as contradictions). This module re-checks
each proposed pair with a trained entailment/NLI classifier — a rigorous, non-LLM
verification layer — and reclassifies it as:

  * equivalent / duplicate  (A entails B and B entails A)  -> should be DEDUPED, not a contradiction
  * contradiction           (A entails not-B, i.e. NLI=contradiction either direction)
  * neutral / unrelated     (no entailment either way)      -> not a real bond

Pluggable classifier: today it uses a general-domain NLI model (roberta-large-mnli),
which handles free prose.

AMR-LDA equivalence layer (Bao et al., ACL Findings 2024) — NOW INTEGRATED, optional.
Enable with USE_AMR=1 (heavy: parse+generate models ~2.5GB, offline stage only). It rewrites
each atom into its logical-equivalents (contrapositive / De Morgan / double-negation) via a
real AMR parse, keeps only rewrites that pass a bidirectional-equivalence check, and uses them
ONLY to reveal hidden equivalence between claims — de-duping near-duplicate pairs the LLM
mislabels as contradictions. It never infers a contradiction from a rewrite. Validated on real
decks (AMR_LDA_EXPERIMENT.md Part 3): 0 false positives, correctly upgrades paraphrase pairs to
'equivalent'. Off by default → the verifier stays CPU-light (roberta-large only).
"""
import os, sys, json
os.environ.setdefault("CUDA_VISIBLE_DEVICES", os.environ.get("VERIFIER_GPU", "7"))
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

NLI_MODEL = os.environ.get("NLI_MODEL", "roberta-large-mnli")
_LABELS = {0: "contradiction", 1: "neutral", 2: "entailment"}
_tok = _model = None

def _load():
    global _tok, _model
    if _model is None:
        _tok = AutoTokenizer.from_pretrained(NLI_MODEL)
        _model = AutoModelForSequenceClassification.from_pretrained(NLI_MODEL).eval()
        _model.to("cuda" if torch.cuda.is_available() else "cpu")
    return _tok, _model

def nli(premise, hypothesis):
    tok, model = _load()
    dev = next(model.parameters()).device
    t = tok(premise, hypothesis, return_tensors="pt", truncation=True, max_length=256).to(dev)
    with torch.no_grad():
        return _LABELS[model(**t).logits.argmax(-1).item()]

def nli_scored(premise, hypothesis):
    tok, model = _load()
    dev = next(model.parameters()).device
    t = tok(premise, hypothesis, return_tensors="pt", truncation=True, max_length=256).to(dev)
    with torch.no_grad():
        probs = torch.softmax(model(**t).logits, -1)[0]
    idx = int(probs.argmax())
    return _LABELS[idx], float(probs[idx])

def strict_contradiction(a, b, thr=0.9):
    """High-confidence contradiction in at least one direction, and no entailment either way."""
    la, pa = nli_scored(a, b)
    lb, pb = nli_scored(b, a)
    if "entailment" in (la, lb):
        return False
    return (la == "contradiction" and pa >= thr) or (lb == "contradiction" and pb >= thr)

def relation(a, b):
    """Symmetric relation between two atoms via bidirectional NLI."""
    ab, ba = nli(a, b), nli(b, a)
    if ab == "contradiction" or ba == "contradiction":
        return "contradiction"
    if ab == "entailment" and ba == "entailment":
        return "equivalent"        # mutual entailment -> duplicate / restatement
    if ab == "entailment" or ba == "entailment":
        return "entails"
    return "neutral"

# --------------------------------------------------------------------------- AMR-LDA layer
# Optional, DISCIPLINED AMR-LDA equivalence normalisation (Bao et al., ACL Findings 2024).
# Validated on real decks (AMR_LDA_EXPERIMENT.md Part 3): used ONLY to reveal hidden logical
# EQUIVALENCE between claims (paraphrases / contrapositives), never to infer a contradiction.
# It de-dupes near-duplicate pairs the LLM mislabels as contradictions. Heavy (parse+generate
# models ~2.5GB) so it is OFF by default; enable with USE_AMR=1 in the offline labelling stage.
USE_AMR = os.environ.get("USE_AMR", "").strip() in ("1", "true", "yes")
_amr_variants = None          # amr_transforms.equivalent_variants, loaded lazily
_amr_ok = None                # None=untried, True/False=availability
_amr_cache = {}

def _amr():
    """Return the AMR variant generator, or None if unavailable."""
    global _amr_variants, _amr_ok
    if _amr_ok is None:
        try:
            from amr_transforms import equivalent_variants
            _amr_variants = equivalent_variants
            _amr_ok = True
        except Exception as e:
            sys.stderr.write(f"[logic_verifier] AMR-LDA unavailable ({e}); using plain NLI.\n")
            _amr_ok = False
    return _amr_variants if _amr_ok else None

def _validated_variants(s):
    """AMR-generated rewrites of s that PASS a bidirectional-equivalence check (drops the
    polarity-flipped bad rewrites that caused the naive blow-up)."""
    if s in _amr_cache:
        return _amr_cache[s]
    gen = _amr()
    good = [s]
    if gen is not None:
        try:
            for v in gen(s)[1:]:
                if relation(s, v) == "equivalent" and relation(v, s) == "equivalent":
                    good.append(v)
        except Exception:
            pass
    _amr_cache[s] = good
    return good

def relation_amr(a, b):
    """relation() with disciplined AMR-LDA equivalence normalisation layered on top.
    Equivalence-only: a VALIDATED logical-equivalent of A (or B) that aligns with the other
    side reveals the pair is really equivalent/duplicate. Never infers contradiction from a
    rewrite. Falls back to plain relation() when AMR is off/unavailable."""
    raw = relation(a, b)
    if not USE_AMR or _amr() is None or raw in ("equivalent", "contradiction"):
        return raw
    for va in _validated_variants(a)[1:]:
        if relation(va, b) == "equivalent":
            return "equivalent"
    for vb in _validated_variants(b)[1:]:
        if relation(a, vb) == "equivalent":
            return "equivalent"
    return raw

def verify_contradictions(excavation):
    """Re-check every LLM-proposed contradiction bond. Returns per-bond verdicts + summary."""
    amap = {a["id"]: a.get("text", "") for a in excavation.get("atoms", [])}
    rel_fn = relation_amr if (USE_AMR and _amr() is not None) else relation
    out = []
    for b in excavation.get("contradictions", []):
        ta, tb = amap.get(b.get("from"), ""), amap.get(b.get("to"), "")
        if not ta or not tb:
            continue
        rel = rel_fn(ta, tb)
        out.append({"from": b.get("from"), "to": b.get("to"),
                    "a": ta, "b": tb, "llm": "contradiction", "verifier": rel,
                    "confirmed": rel == "contradiction"})
    n = len(out)
    conf = sum(1 for x in out if x["confirmed"])
    dup = sum(1 for x in out if x["verifier"] == "equivalent")
    return {"pairs": out, "llm_contradictions": n, "verifier_confirmed": conf,
            "false_positives": n - conf, "of_which_duplicates": dup,
            "amr_lda": bool(USE_AMR and _amr() is not None)}

if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "prosecution_out/quickbite_excavation.json"
    d = json.load(open(path))
    r = verify_contradictions(d)
    print(f"Verifier: {NLI_MODEL}  |  AMR-LDA layer: {'ON' if r.get('amr_lda') else 'off'}  |  "
          f"document: {d.get('label')}  |  atoms: {len(d.get('atoms',[]))}")
    print(f"\nLLM proposed {r['llm_contradictions']} contradiction bonds. "
          f"Verifier confirmed {r['verifier_confirmed']}, "
          f"rejected {r['false_positives']} "
          f"({r['of_which_duplicates']} were actually equivalent/duplicates).\n")
    for x in r["pairs"]:
        mark = "✅ real" if x["confirmed"] else ("♻ duplicate" if x["verifier"] == "equivalent" else "✗ " + x["verifier"])
        print(f"[{mark}]  {x['from']} ✕ {x['to']}")
        print(f"    A: {x['a'][:80]}")
        print(f"    B: {x['b'][:80]}")

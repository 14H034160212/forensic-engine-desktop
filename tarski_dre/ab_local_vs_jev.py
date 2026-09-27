"""
A/B: free-form local LLM vs constrained typed decoding (local "System One"), on the SAME episode.
Optional third arm: cloud/self-hosted Jev, if TYPESAFE_API_KEY (or JEV_ENDPOINT) is set.

Runs the DRE coverage traversal with each backend over identical evidence and reports: wall-clock,
how many constructs got a VALID coverage state (the failure mode of small models is unparseable JSON →
constructs dropped), coverage distribution, per-construct agreement, and disagreements. This is the
measurable claim behind "constrained typed decoding gives a valid, disciplined decision every time,
where free-form JSON silently drops constructs."

Usage:
  DRE_MODEL=mistral-small:latest OLLAMA_HOST=http://127.0.0.1:11455 python3 ab_local_vs_jev.py
"""
import os, sys, json, time
sys.path.insert(0, os.path.dirname(__file__))
import dre_core, dre_reason, typed_local

RES = os.path.join(os.path.dirname(__file__), "resources")

def run_backend(name, tax, brief, by_dom, classify):
    t0 = time.time()
    cov = {}
    for did in sorted(tax["domains"]):
        dom = tax["domains"][did]
        cons = by_dom.get(did, [])
        for i in range(0, len(cons), 12):
            part = classify(dom, cons[i:i+12], brief)
            for c in part.get("constructs", []):
                if c.get("id") and c.get("coverage"):
                    cov[c["id"]] = c["coverage"]
    return {"backend": name, "elapsed_s": round(time.time()-t0, 1), "coverage": cov}

def dist(cov):
    from collections import Counter
    return dict(Counter(cov.values()))

def main():
    tax, ep, obs = dre_core.load_all(os.path.join(RES, "sample_episode.jsonl"),
                                     os.path.join(RES, "demo_taxonomy.md"))
    brief = dre_reason.evidence_brief(ep, obs)
    by_dom = {}
    for c in tax["constructs"].values():
        by_dom.setdefault(c["domain"], []).append(c)
    N = len(tax["constructs"])
    print(f"episode={ep['episode_name']} · {N} constructs · model={dre_reason.MODEL}")

    freeform = run_backend("freeform-local", tax, brief, by_dom, dre_reason.reason_domain)
    print(f"  freeform-local : {freeform['elapsed_s']:6}s  valid {len(freeform['coverage'])}/{N}  dist={dist(freeform['coverage'])}")
    typed = run_backend("typed-local", tax, brief, by_dom, typed_local.classify_domain)
    print(f"  typed-local    : {typed['elapsed_s']:6}s  valid {len(typed['coverage'])}/{N}  dist={dist(typed['coverage'])}")

    arms = {"freeform": freeform, "typed": typed}
    try:
        import jev_backend
        if jev_backend.available():
            jev = run_backend("jev", tax, brief, by_dom, jev_backend.classify_domain)
            print(f"  jev            : {jev['elapsed_s']:6}s  valid {len(jev['coverage'])}/{N}  dist={dist(jev['coverage'])}")
            arms["jev"] = jev
    except Exception:
        pass

    ids = sorted(set(freeform["coverage"]) | set(typed["coverage"]))
    agree = sum(1 for i in ids if freeform["coverage"].get(i) == typed["coverage"].get(i))
    disagreements = [{"id": i, "freeform": freeform["coverage"].get(i), "typed": typed["coverage"].get(i)}
                     for i in ids if freeform["coverage"].get(i) != typed["coverage"].get(i)]
    print(f"\n  freeform vs typed agreement: {agree}/{len(ids)} ({agree*100//max(1,len(ids))}%)")
    print(f"  coverage completeness: freeform {len(freeform['coverage'])}/{N}, typed {len(typed['coverage'])}/{N}"
          "   (typed guarantees a valid state for every construct)")
    for d in disagreements[:30]:
        print(f"    {d['id']:30} freeform={d['freeform']}  typed={d['typed']}")

    out = {"episode": ep["episode_name"], "n_constructs": N, "arms": arms,
           "freeform_vs_typed_agreement": agree, "of": len(ids)}
    json.dump(out, open(os.path.join(os.path.dirname(__file__), "ab_result.json"), "w"), indent=2)
    print("\n  → ab_result.json")

if __name__ == "__main__":
    main()

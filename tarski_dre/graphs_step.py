"""
Knowledge-graph step for the Learning DRE — vendored from the TLI Part-2 engine (tli_graphs/).

Produces the two knowledge graphs the TLI design describes, over the SAME Recorder Episode:
  * Understanding graph — concepts (ENCOUNTERED / ORIGINATED / RESTATED / CORRECTED / APPLIED /
    VOICED_IN_PROMPT) and the relations between them;
  * Reasoning graph — five axes (THINK_CRITICALLY, REASON_LOGICALLY, BE_CREATIVE, SUPERVISE_AI,
    EXERCISE_EPISTEMIC_JUDGEMENT), each EVIDENCED or NOT_EVIDENCED;
plus a short teacher-facing narrative.

The value is the citation gate: every claim must cite event sequence numbers and survive a
deterministic role check, or it is DROPPED — a hallucinating model produces a missing finding,
never a fabricated one. We surface how many claims the gate discarded, because that is the honesty
guarantee a teacher is trusting.

Best-effort: any failure returns {"available": False, ...} and never breaks the main DRE report.
"""
import os, sys, json, tempfile, shutil, dataclasses

_HERE = os.path.dirname(__file__)
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)


def _episode_dir(episode_path):
    """tli_graphs.ingest.load wants a folder holding the *.jsonl provenance log. If we were given a
    single .jsonl file, stage it into a temp folder. Returns (dir, cleanup_or_None)."""
    if os.path.isdir(episode_path):
        return episode_path, None
    tmp = tempfile.mkdtemp(prefix="dre_graphs_")
    shutil.copyfile(episode_path, os.path.join(tmp, "episode.provenance.jsonl"))
    return tmp, tmp


def build_graphs(episode_path, host=None, model=None, no_llm=False):
    try:
        from tli_graphs import ingest, ledger, graphs as gmod
    except Exception as e:
        return {"available": False, "error": f"graphs package unavailable: {e}"}

    if host:
        gmod.ENGINE_HOST = host.rstrip("/")
    if model:
        gmod.LLM_MODEL = model

    epdir, cleanup = _episode_dir(episode_path)
    try:
        ep = ingest.load(epdir)
        led = ledger.build(ep)
        if no_llm:
            return {"available": True, "llm_available": False, "understanding_nodes": [],
                    "understanding_edges": [], "reasoning": [], "narrative": "",
                    "dropped": 0, "corrections": 0, "model": "(disabled)"}
        g = gmod.analyse(ep, led)
        return {
            "available": True,
            "llm_available": g.llm_available,
            "model": getattr(gmod, "LLM_MODEL", g.model),
            "narrative": g.narrative,
            "understanding_nodes": [dataclasses.asdict(n) for n in g.understanding_nodes],
            "understanding_edges": [dataclasses.asdict(e) for e in g.understanding_edges],
            "reasoning": [dataclasses.asdict(r) for r in g.reasoning],
            "dropped": len(g.dropped),
            "corrections": len(g.corrections),
            "dropped_detail": g.dropped[:20],
        }
    except Exception as e:
        import traceback
        return {"available": False, "error": str(e), "trace": traceback.format_exc()[-800:]}
    finally:
        if cleanup:
            shutil.rmtree(cleanup, ignore_errors=True)

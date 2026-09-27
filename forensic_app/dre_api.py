#!/usr/bin/env python3
"""
Tarski Deep Reasoning Engine (DRE) — web/desktop API surface.

Wraps the deterministic DRE pipeline (tarski_dre/dre_core.py + dre_reason.py) so the SAME native
app that runs the Forensic Engine can also run the Learning DRE: upload one learning Episode (the
Tarski Telemetry event stream) + the Canonical Taxonomy, and it reasons over the evidence and
returns selective Teacher + Student reports plus the full internal consideration for drill-down.

Shares the app's local Ollama (127.0.0.1:11434, auto-provisioned by entry.py) — no extra runtime.
A DRE run is long (many LLM calls), so it runs in a background thread and the UI polls for progress.

register_dre(app, HERE, DATA) is called from server.py to mount the routes.
"""
import os, sys, json, time, uuid, threading, datetime, shutil

# --- locate the bundled DRE package + sample resources (frozen-aware, like server.py) -------------
def _dre_dir(HERE):
    # HERE is .../forensic_app (source) or <_MEIPASS>/forensic_app (frozen); tarski_dre is a sibling.
    return os.path.join(os.path.dirname(HERE), "tarski_dre")

_JOBS = {}                      # job_id -> job dict
_JOBS_LOCK = threading.Lock()
_RUN_LOCK = threading.Lock()   # only one heavy DRE run at a time on a laptop


def register_dre(app, HERE, DATA):
    from fastapi import UploadFile, File, Form, Request
    from fastapi.responses import JSONResponse, FileResponse

    DRE_DIR = _dre_dir(HERE)
    RES_DIR = os.path.join(DRE_DIR, "resources")
    RUNS_DIR = os.path.join(DATA, "dre_runs")
    os.makedirs(RUNS_DIR, exist_ok=True)
    if DRE_DIR not in sys.path:
        sys.path.insert(0, DRE_DIR)

    SAMPLE_EPISODE = os.path.join(RES_DIR, "sample_episode.jsonl")
    DEFAULT_TAXONOMY = os.path.join(RES_DIR, "demo_taxonomy.md")

    def _ollama_host():
        return os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")

    def _installed_models():
        import urllib.request
        try:
            with urllib.request.urlopen(_ollama_host() + "/api/tags", timeout=4) as r:
                return [m.get("name", "") for m in json.load(r).get("models", [])]
        except Exception:
            return []

    # Models we consider well-suited to the DRE's structured-JSON reasoning, best first. The UI
    # offers whatever is actually installed; mistral-small is the recommended quality default.
    PREFERRED = ["mistral-small:latest", "gemma4:26b", "gpt-oss:20b", "qwen2.5:32b",
                 "qwen2.5-coder:32b", "qwen2.5-coder:7b", "llama3.2:3b"]

    @app.get("/api/dre/models")
    def dre_models():
        have = _installed_models()
        pref = [m for m in PREFERRED if m in have]
        rest = [m for m in have if m not in pref]
        ordered = pref + rest
        return {"models": ordered,
                "recommended": next((m for m in PREFERRED if m in have), None),
                "have_any": bool(have)}

    @app.get("/api/dre/sample")
    def dre_sample():
        return {"available": os.path.exists(SAMPLE_EPISODE),
                "episode": "Sample learning session — How photosynthesis works",
                "note": "A small synthetic sample episode (fictional learner) bundled so the "
                        "pipeline runs out of the box; upload a real Tarski Telemetry Episode to analyse it."}

    def _job_public(j):
        return {k: j[k] for k in ("id", "state", "progress", "model", "error",
                                  "started_at", "finished_at", "episode_name") if k in j}

    def _run_job(job_id, episode_path, taxonomy_path, model, outdir, decision_backend="local"):
        import dre_core, dre_reason
        j = _JOBS[job_id]
        with _RUN_LOCK:
            try:
                j["state"] = "running"
                # point the reasoning layer at the app's local Ollama + the chosen model
                dre_reason.OLLAMA = _ollama_host()
                dre_reason.MODEL = model
                os.environ["DRE_MODEL"] = model
                # coverage decision backend for THIS run (runs are serialised by _RUN_LOCK, so setting
                # the process env here is safe): 'local' free-form, or 'local_typed' constrained decoding.
                os.environ["OLLAMA_HOST"] = _ollama_host()
                os.environ["DRE_DECISION_BACKEND"] = decision_backend
                j["progress"] = {"stage": "loading", "done": 0, "total": 1, "pct": 2,
                                 "note": "Loading taxonomy + telemetry evidence"}
                tax, ep, obs = dre_core.load_all(episode_path, taxonomy_path)
                j["episode_name"] = ep.get("episode_name") or "episode"
                j["n_constructs"] = len(tax["constructs"])
                j["n_domains"] = len(tax["domains"])

                def progress(stage, done, total, note=""):
                    total = total or 1
                    # reserve ~10% for the two synthesis passes at the end
                    if stage == "domain":
                        pct = int(done * 88 / total) + 2
                    elif stage == "synthesise":
                        pct = 92
                    elif stage == "student":
                        pct = 96
                    else:
                        pct = 100
                    j["progress"] = {"stage": stage, "done": done, "total": total,
                                     "pct": pct, "note": note}

                internal, report = dre_reason.run(tax, ep, obs, outdir, progress=progress)
                # collect outputs for the result endpoint
                def _read(name):
                    p = os.path.join(outdir, name)
                    return open(p, encoding="utf-8").read() if os.path.exists(p) else ""
                j["result"] = {
                    "report": report,
                    "student": json.loads(_read("student.json") or "{}"),
                    "coverage_summary": internal.get("coverage_summary", {}),
                    "constructs_in_play": len(internal.get("constructs_in_play", [])),
                    "n_constructs": j.get("n_constructs"),
                    "n_domains": j.get("n_domains"),
                    "taxonomy_version": internal.get("taxonomy", {}).get("version"),
                    "taxonomy_sha256": internal.get("taxonomy", {}).get("sha256"),
                    "teacher_md": _read("teacher_report.md"),
                    "student_md": _read("student_report.md"),
                }
                j["state"] = "done"
                j["progress"] = {"stage": "done", "done": 1, "total": 1, "pct": 100, "note": "Reports ready"}
            except Exception as e:
                import traceback
                j["state"] = "error"
                j["error"] = str(e)
                j["trace"] = traceback.format_exc()[-1500:]
            finally:
                j["finished_at"] = datetime.datetime.now().isoformat(timespec="seconds")

    @app.post("/api/dre/run")
    async def dre_run(request: Request):
        form = await request.form()
        model = (form.get("model") or "").strip()
        use_sample = str(form.get("use_sample", "")).strip().lower() in ("1", "true", "yes", "on")
        decision_backend = (form.get("decision_backend") or "local").strip().lower()
        if decision_backend not in ("local", "local_typed", "jev"):
            decision_backend = "local"

        have = _installed_models()
        if not model:
            model = next((m for m in PREFERRED if m in have), (have[0] if have else ""))
        if not have:
            return JSONResponse({"error": "No local model is installed yet. Open the app's setup / "
                                          "pull a model first (e.g. mistral-small)."}, status_code=400)

        if _RUN_LOCK.locked():
            return JSONResponse({"error": "A DRE run is already in progress. Please wait for it to finish."},
                                status_code=429)

        job_id = uuid.uuid4().hex[:12]
        outdir = os.path.join(RUNS_DIR, job_id)
        os.makedirs(outdir, exist_ok=True)

        # resolve inputs: uploaded files win; otherwise fall back to the bundled sample / default taxonomy
        episode_path = os.path.join(outdir, "episode.json")
        taxonomy_path = os.path.join(outdir, "taxonomy.md")
        ep_file = form.get("episode")
        tax_file = form.get("taxonomy")
        try:
            if use_sample or ep_file is None:
                if not os.path.exists(SAMPLE_EPISODE):
                    return JSONResponse({"error": "No episode uploaded and no bundled sample available."},
                                        status_code=400)
                shutil.copyfile(SAMPLE_EPISODE, episode_path)
            else:
                with open(episode_path, "wb") as f:
                    f.write(await ep_file.read())
            if tax_file is not None and not use_sample:
                with open(taxonomy_path, "wb") as f:
                    f.write(await tax_file.read())
            else:
                shutil.copyfile(DEFAULT_TAXONOMY, taxonomy_path)
        except Exception as e:
            return JSONResponse({"error": f"Could not stage inputs: {e}"}, status_code=400)

        job = {"id": job_id, "state": "queued", "model": model, "error": "",
               "started_at": datetime.datetime.now().isoformat(timespec="seconds"),
               "finished_at": None, "episode_name": "(loading)",
               "progress": {"stage": "queued", "done": 0, "total": 1, "pct": 0, "note": "Queued"},
               "outdir": outdir}
        with _JOBS_LOCK:
            _JOBS[job_id] = job
        threading.Thread(target=_run_job,
                         args=(job_id, episode_path, taxonomy_path, model, outdir, decision_backend),
                         daemon=True).start()
        return {"job": job_id, "model": model, "decision_backend": decision_backend}

    @app.get("/api/dre/status/{job_id}")
    def dre_status(job_id: str):
        j = _JOBS.get(job_id)
        if not j:
            return JSONResponse({"error": "unknown job"}, status_code=404)
        return _job_public(j)

    @app.get("/api/dre/result/{job_id}")
    def dre_result(job_id: str):
        j = _JOBS.get(job_id)
        if not j:
            return JSONResponse({"error": "unknown job"}, status_code=404)
        if j["state"] != "done":
            return JSONResponse({"state": j["state"], "error": j.get("error", "")}, status_code=409)
        return j.get("result", {})

    @app.get("/api/dre/download/{job_id}/{which}")
    def dre_download(job_id: str, which: str):
        j = _JOBS.get(job_id)
        if not j:
            return JSONResponse({"error": "unknown job"}, status_code=404)
        allowed = {"internal": "internal_consideration.json",
                   "teacher": "teacher_report.md",
                   "student": "student_report.md",
                   "report": "report.json"}
        fn = allowed.get(which)
        if not fn:
            return JSONResponse({"error": "unknown artifact"}, status_code=400)
        p = os.path.join(j["outdir"], fn)
        if not os.path.exists(p):
            return JSONResponse({"error": "not ready"}, status_code=404)
        media = "application/json" if fn.endswith(".json") else "text/markdown"
        return FileResponse(p, media_type=media, filename=f"dre_{which}_{job_id}{os.path.splitext(fn)[1]}")

    return app

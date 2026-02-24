"""
Runner route — starts opt-out runs and streams live log via Server-Sent Events.
Single-user app so we use module-level state for simplicity.
"""
import queue
import threading
import json
from flask import Blueprint, render_template, request, Response, stream_with_context, jsonify
from brokers import load_registry
from core.engine import run_brokers

runner_bp = Blueprint("runner", __name__)

# Module-level state (safe for single-user local app)
_run_queue: queue.Queue = None
_run_in_progress: bool = False


@runner_bp.route("/run")
def run_page():
    registry = load_registry()
    return render_template("runner.html", brokers=registry, in_progress=_run_in_progress)


@runner_bp.route("/run/start", methods=["POST"])
def run_start():
    global _run_queue, _run_in_progress

    if _run_in_progress:
        return jsonify({"error": "A run is already in progress."}), 409

    broker_ids = request.form.getlist("broker_ids") or None
    _run_queue = queue.Queue()
    _run_in_progress = True

    def do_run():
        global _run_in_progress
        try:
            def log_callback(msg):
                _run_queue.put({"msg": msg})

            result = run_brokers(broker_ids=broker_ids, log_callback=log_callback)
            _run_queue.put({"msg": "─" * 60, "done": True, "result": result})
        except Exception as exc:
            _run_queue.put({"msg": f"FATAL ERROR: {exc}", "done": True})
        finally:
            _run_in_progress = False
            _run_queue.put(None)  # sentinel

    threading.Thread(target=do_run, daemon=True).start()
    return jsonify({"ok": True})


@runner_bp.route("/run/stream")
def run_stream():
    def generate():
        if _run_queue is None:
            yield f"data: {json.dumps({'msg': 'No run in progress.'})}\n\n"
            return

        while True:
            try:
                item = _run_queue.get(timeout=120)
            except queue.Empty:
                yield f"data: {json.dumps({'msg': 'Timed out waiting for runner.'})}\n\n"
                break

            if item is None:
                break

            yield f"data: {json.dumps(item)}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@runner_bp.route("/run/status")
def run_status():
    return jsonify({"in_progress": _run_in_progress})

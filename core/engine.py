"""
engine.py — orchestrates opt-out runs.
Dynamically loads broker handlers and logs progress via a callback.
"""
import uuid
import importlib
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.tracker import add_request, get_profile, save_run
from brokers import load_registry


def _load_handler(broker: dict):
    """Dynamically import a broker's Handler class, or None if not found."""
    handler_name = broker.get("handler")
    if not handler_name:
        return None
    try:
        module = importlib.import_module(f"brokers.handlers.{handler_name}")
        return getattr(module, "Handler", None)
    except (ImportError, AttributeError):
        return None


def run_brokers(broker_ids: list = None, log_callback=None) -> dict:
    """
    Run opt-out submissions for the given broker IDs (or all if None).
    log_callback(msg: str) is called for each log line — used for live streaming.
    Returns a summary dict.
    """
    profile = get_profile()
    registry = load_registry()
    run_id = str(uuid.uuid4())[:8]
    log_lines = []
    succeeded = 0
    failed = 0

    if not profile:
        msg = "ERROR: No profile found. Please fill in your profile first."
        if log_callback:
            log_callback(msg)
        return {"run_id": run_id, "log": [msg], "succeeded": 0, "failed": 0}

    brokers = (
        registry
        if not broker_ids
        else [b for b in registry if b["id"] in broker_ids]
    )

    def log(msg: str):
        log_lines.append(msg)
        if log_callback:
            log_callback(msg)

    log(f"Run ID: {run_id} — processing {len(brokers)} broker(s)")
    log("─" * 60)

    for broker in brokers:
        name = broker["name"]
        method = broker.get("method", "manual")

        HandlerClass = _load_handler(broker)

        if HandlerClass:
            try:
                handler = HandlerClass(profile, broker)
                result = handler.submit()
                status = result.get("status", "submitted")
                notes = result.get("notes", "")
                log(f"[{name}] {status.upper()} — {notes}")
            except Exception as exc:
                status = "error"
                notes = str(exc)
                log(f"[{name}] ERROR — {exc}")
        elif method == "manual":
            status = "manual_required"
            url = broker.get("opt_out_url", "")
            notes = f"Manual opt-out required. URL: {url}"
            log(f"[{name}] MANUAL REQUIRED — {url}")
        else:
            status = "manual_required"
            notes = f"No handler available. Visit: {broker.get('opt_out_url', 'N/A')}"
            log(f"[{name}] NO HANDLER — marked for manual action")

        add_request(broker["id"], name, method, status, notes, run_id)

        if status in ("submitted", "confirmed"):
            succeeded += 1
        else:
            failed += 1

    log("─" * 60)
    log(f"Done. Submitted: {succeeded} | Manual/Error: {failed}")

    save_run(run_id, len(brokers), succeeded, failed, log_lines)
    return {
        "run_id": run_id,
        "log": log_lines,
        "succeeded": succeeded,
        "failed": failed,
        "total": len(brokers),
    }

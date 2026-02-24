from flask import Blueprint, render_template
from brokers import load_registry
from core.tracker import get_latest_per_broker

brokers_bp = Blueprint("brokers", __name__)


@brokers_bp.route("/brokers")
def brokers():
    registry = load_registry()
    latest = {r["broker_id"]: r for r in get_latest_per_broker()}

    enriched = []
    for broker in registry:
        rec = latest.get(broker["id"])
        enriched.append({
            **broker,
            "last_status": rec["status"] if rec else None,
            "last_submitted": rec["submitted_at"] if rec else None,
            "last_notes": rec["notes"] if rec else None,
        })

    return render_template("brokers.html", brokers=enriched)

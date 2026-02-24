from flask import Blueprint, render_template
from core.tracker import get_stats, get_profile
from brokers import load_registry

dashboard_bp = Blueprint("dashboard", __name__)

STATUS_ORDER = ["confirmed", "submitted", "manual_required", "error", "pending"]


@dashboard_bp.route("/")
def index():
    stats = get_stats()
    profile = get_profile()
    registry = load_registry()

    total_in_registry = len(registry)
    brokers_contacted = stats["brokers_contacted"]
    brokers_remaining = total_in_registry - brokers_contacted
    statuses = stats["statuses"]
    recent_runs = stats["recent_runs"]

    return render_template(
        "dashboard.html",
        profile=profile,
        total_in_registry=total_in_registry,
        brokers_contacted=brokers_contacted,
        brokers_remaining=brokers_remaining,
        statuses=statuses,
        recent_runs=recent_runs,
    )

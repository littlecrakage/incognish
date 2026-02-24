from flask import Blueprint, render_template, request, redirect, url_for, flash
from core.tracker import get_requests, update_request

requests_bp = Blueprint("requests", __name__)

VALID_STATUSES = ["pending", "submitted", "confirmed", "denied", "manual_required", "error", "expired"]


@requests_bp.route("/requests")
def requests_list():
    status_filter = request.args.get("status")
    broker_filter = request.args.get("broker_id")
    since_filter = request.args.get("since")

    reqs = get_requests(
        broker_id=broker_filter or None,
        status=status_filter or None,
        since=since_filter or None,
    )
    return render_template(
        "requests.html",
        requests=reqs,
        status_filter=status_filter,
        broker_filter=broker_filter,
        since_filter=since_filter,
        valid_statuses=VALID_STATUSES,
    )


@requests_bp.route("/requests/<int:req_id>/update", methods=["POST"])
def update_status(req_id):
    new_status = request.form.get("status")
    new_notes = request.form.get("notes", "").strip()
    if new_status in VALID_STATUSES:
        update_request(req_id, new_status, new_notes or None)
        flash(f"Request #{req_id} updated to '{new_status}'.", "success")
    else:
        flash("Invalid status.", "danger")
    return redirect(url_for("requests.requests_list"))

from flask import Blueprint, render_template, request, redirect, url_for, flash
from core.tracker import take_snapshot, get_snapshots, get_snapshot

report_bp = Blueprint("report", __name__)


@report_bp.route("/report")
def report_list():
    snapshots = get_snapshots()
    return render_template("report.html", snapshots=snapshots, snapshot=None)


@report_bp.route("/report/take", methods=["POST"])
def take():
    label = request.form.get("label", "").strip() or "Manual snapshot"
    snapshot_id = take_snapshot(label)
    flash(f"Snapshot '{label}' saved.", "success")
    return redirect(url_for("report.view_snapshot", snapshot_id=snapshot_id))


@report_bp.route("/report/<int:snapshot_id>")
def view_snapshot(snapshot_id):
    snapshots = get_snapshots()
    snapshot = get_snapshot(snapshot_id)
    if not snapshot:
        flash("Snapshot not found.", "danger")
        return redirect(url_for("report.report_list"))
    return render_template("report.html", snapshots=snapshots, snapshot=snapshot)

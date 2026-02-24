from flask import Blueprint, render_template, request, redirect, url_for, flash
from core.tracker import get_profile, save_profile

profile_bp = Blueprint("profile", __name__)

PROFILE_FIELDS = [
    ("first_name",    "First Name",    "text",  True),
    ("last_name",     "Last Name",     "text",  True),
    ("email",         "Email Address", "email", True),
    ("phone",         "Phone Number",  "tel",   False),
    ("address",       "Street Address","text",  False),
    ("city",          "City",          "text",  False),
    ("state",         "State",         "text",  False),
    ("zip_code",      "ZIP Code",      "text",  False),
    ("date_of_birth", "Date of Birth", "date",  False),
]


@profile_bp.route("/profile", methods=["GET", "POST"])
def profile():
    if request.method == "POST":
        data = {field: request.form.get(field, "").strip() for field, *_ in PROFILE_FIELDS}
        save_profile(data)
        flash("Profile saved successfully.", "success")
        return redirect(url_for("profile.profile"))

    current = get_profile()
    return render_template("profile.html", profile=current, fields=PROFILE_FIELDS)

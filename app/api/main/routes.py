from flask import Blueprint, render_template, request, session, redirect, url_for
from app.core.permissions import login_required, role_required

main_bp = Blueprint(
    "main",
    __name__,
    url_prefix="/",
)

@main_bp.route("/", methods=["GET"])
def index():

    return render_template("main/index.html")

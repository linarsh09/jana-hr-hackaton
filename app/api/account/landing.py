from flask import Blueprint, redirect, url_for


landing_bp = Blueprint("landing", __name__)


@landing_bp.get("/")
def home():
    return redirect(url_for("users.login"))

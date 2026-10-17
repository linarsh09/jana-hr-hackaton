import os

from flask import Flask, redirect, url_for
from dotenv import load_dotenv

from app.extensions import db, migrate

load_dotenv()


def create_app():
    app = Flask(__name__)

    app.config["SECRET_KEY"] = os.getenv(
        "SECRET_KEY", "dev-secret"
    )

    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL"
    )

    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    migrate.init_app(app, db)

    from app import models

    from app.core.permissions import load_current_user
    app.before_request(load_current_user)

    from app.api.account.routes import account_bp
    app.register_blueprint(account_bp)

    @app.route("/")
    def index():
        return redirect(url_for("users.login"))

    return app
import os

from dotenv import load_dotenv
from flask import Flask, app

from app.extensions import db, migrate

load_dotenv()


def create_app():
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
        static_url_path="/static",
    )
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    if not app.config["SQLALCHEMY_DATABASE_URI"]:
        raise RuntimeError("DATABASE_URL is not set")

    db.init_app(app)
    migrate.init_app(app, db)

    # Load model metadata before Alembic inspects it.
    from app import models  # noqa: F401
    from app.core.permissions import load_current_user
    from app.api.account.routes import account_bp
    from app.api.account.landing import landing_bp
    from app.api.admin.routes import admin_bp
    from app.api.employee.routes import employees_bp
    from app.api.assistant.routes import assistant_bp
    from app.api.notifications.routes import notifications_bp
    from app.api.academy.routes import academy_bp
    from app.api.academy.pages import academy_pages 

    
    app.before_request(load_current_user)
    app.register_blueprint(account_bp)
    app.register_blueprint(landing_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(employees_bp)
    app.register_blueprint(academy_bp)
    app.register_blueprint(academy_pages)
    app.register_blueprint(assistant_bp)
    app.register_blueprint(notifications_bp)

    return app

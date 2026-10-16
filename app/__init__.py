import os
from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS
from app.extensions import db, migrate
from app.core.permissions import load_current_user

load_dotenv()

def create_app():
    app = Flask(
        __name__, 
        template_folder="templates",
        static_folder="static",
        static_url_path="/static",
    )

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not set")

    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")

    db.init_app(app)
    migrate.init_app(app, db)

    CORS(
        app,
        resources={
            r"/api/*": {
                "origins": "http://localhost:5173"
            }
        }
    )

    # ВАЖНО: импортируем модели,
    # чтобы Alembic их увидел
    from app import models

    from app.api.employees.routes import employees_bp
    from app.api.vacations.routes import vacations_bp
    from app.api.account.routes import account_bp
    from app.api.admin.routes import admin_bp

    app.before_request(load_current_user)

    app.register_blueprint(employees_bp)
    app.register_blueprint(vacations_bp)
    app.register_blueprint(account_bp)
    app.register_blueprint(admin_bp)

    return app

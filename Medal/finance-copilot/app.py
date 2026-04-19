from pathlib import Path

from flask import Flask

from config import BASE_DIR, SECRET_KEY
from models.db import init_db
from routes.auth import auth_bp
from routes.copilot import copilot_bp
from routes.dashboard import dashboard_bp, register_pages
from routes.upload import upload_bp


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder=str(BASE_DIR / "templates"),
        static_folder=str(BASE_DIR / "static"),
    )
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
    app.secret_key = SECRET_KEY

    Path(BASE_DIR / "data").mkdir(parents=True, exist_ok=True)
    init_db()

    app.register_blueprint(auth_bp)
    app.register_blueprint(upload_bp, url_prefix="/api")
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(copilot_bp)
    register_pages(app)
    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

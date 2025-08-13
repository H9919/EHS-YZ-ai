# app.py — Smart EHS (chat-first homepage)
import os
import sys
from datetime import datetime
from pathlib import Path

from flask import Flask, render_template, jsonify
from werkzeug.middleware.proxy_fix import ProxyFix

# --- Blueprints (present in your repo) ---
from routes.chatbot import chatbot_bp           # /chat, /chatbot, five-whys
from routes.incidents import incidents          # incidents pages/APIs
from routes.safety_concerns import safety_concerns
from routes.risk import risk
from routes.sds import sds
from routes.capa import capa
from routes.audits import audits
from routes.contractors import contractors


# ---------- Helpers ----------
def ensure_dirs() -> None:
    """Create directories the app expects at runtime."""
    for d in [
        "data", "data/tmp", "data/pdf", "data/sds",
        "static", "static/uploads", "static/qr"
    ]:
        Path(d).mkdir(parents=True, exist_ok=True)


def create_app() -> Flask:
    ensure_dirs()

    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB uploads safeguard
    app.secret_key = os.environ.get("SECRET_KEY", "ehs-dev-secret")

    # Make Flask respect X-Forwarded-* headers on Render/Gunicorn
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)

    # ---------- Register blueprints ----------
    app.register_blueprint(chatbot_bp)
    app.register_blueprint(incidents)
    app.register_blueprint(safety_concerns)
    app.register_blueprint(risk)
    app.register_blueprint(sds)
    app.register_blueprint(capa)
    app.register_blueprint(audits)
    app.register_blueprint(contractors)

    # ---------- Home: chat-first dashboard ----------
    @app.get("/")
    def home():
        # If you prefer the full-screen chat page instead, swap to: return render_template("chatbot.html")
        return render_template("enhanced_dashboard.html")

    # ---------- Simple health & readiness probes ----------
    @app.get("/health")
    @app.get("/live")
    def health():
        return jsonify({
            "status": "ok",
            "time": datetime.utcnow().isoformat() + "Z",
            "storage": {
                "data": Path("data").exists(),
                "uploads": Path("static/uploads").exists(),
                "sds": Path("data/sds").exists(),
            }
        })

    @app.get("/ready")
    def ready():
        # You could expand this with DB pings, etc.
        return jsonify({"ready": True})

    # ---------- Error handlers (nice pages, no stack traces to users) ----------
    @app.errorhandler(404)
    def _404(_e):
        try:
            return render_template("error_404.html"), 404
        except Exception:
            return "Not Found", 404

    @app.errorhandler(500)
    def _500(_e):
        try:
            return render_template("error_500.html"), 500
        except Exception:
            return "Server Error", 500

    return app


# Gunicorn entrypoint expects `app`
app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    debug = os.environ.get("FLASK_ENV") == "development"

    print("=" * 60)
    print("🚀 Starting Smart EHS")
    print("=" * 60)
    print(f"Port: {port}")
    print(f"Debug mode: {debug}")
    print(f"Python: {sys.version.split()[0]}")
    print("Homepage: enhanced_dashboard.html (chat-first)")
    print("=" * 60)

    app.run(host="0.0.0.0", port=port, debug=debug)

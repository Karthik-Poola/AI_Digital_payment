import os
from flask import Flask, jsonify, send_from_directory
from flask_jwt_extended.exceptions import NoAuthorizationError

from config import Config
from app.extensions import db, migrate, jwt, cors
from app.routes import register_blueprints
from app.utils.fraud_check import get_model_status


def create_app(config_class=Config):
    app = Flask(__name__, static_folder=None)
    app.config.from_object(config_class)

    # ---- Extensions ----
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": "*"}})

    # ---- Blueprints ----
    register_blueprints(app)

    # ---- Error handlers ----
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Resource not found"}), 404

    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({"error": "Bad request"}), 400

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({"error": "Internal server error"}), 500

    @app.errorhandler(NoAuthorizationError)
    def no_auth(e):
        return jsonify({"error": "Missing or invalid authorization token"}), 401

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({"error": "Token has expired"}), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(reason):
        return jsonify({"error": "Invalid token", "details": str(reason)}), 401

    @jwt.unauthorized_loader
    def missing_token_callback(reason):
        return jsonify({"error": "Authorization token is missing"}), 401

    # ---- Health check ----
    @app.route("/api/health")
    def health():
        return jsonify(
            {
                "status": "ok",
                "service": "apexpay-backend",
                "fraudModel": get_model_status(),
            }
        ), 200

    # ---- Optional: serve the frontend statically ----
    # If a `frontend/` directory exists alongside run.py (containing
    # index.html, css/, js/, etc.), serve it directly so the whole
    # app can run from a single Flask process during development.
    frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
    if os.path.isdir(frontend_dir):
        @app.route("/")
        def serve_index():
            return send_from_directory(frontend_dir, "index.html")

        @app.route("/<path:path>")
        def serve_frontend(path):
            full_path = os.path.join(frontend_dir, path)
            if os.path.isfile(full_path):
                return send_from_directory(frontend_dir, path)
            # Fallback to index.html for client-side routes (not used here,
            # but harmless for plain multi-page apps -- 404s naturally if
            # the path doesn't match anything real).
            return jsonify({"error": "Resource not found"}), 404

    return app

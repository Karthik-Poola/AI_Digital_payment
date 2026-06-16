from app.routes.auth import auth_bp
from app.routes.dashboard import dashboard_bp
from app.routes.transactions import transactions_bp
from app.routes.transfer import transfer_bp
from app.routes.insights import insights_bp
from app.routes.profile import profile_bp


def register_blueprints(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(transactions_bp)
    app.register_blueprint(transfer_bp)
    app.register_blueprint(insights_bp)
    app.register_blueprint(profile_bp)

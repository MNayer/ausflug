import os
from flask import Flask
from .extensions import db
from .models import Trip, Response # Import models so they are registered

def create_app():
    app = Flask(__name__)
    app.secret_key = os.environ.get("SECRET_KEY", "change-me")
    
    # Database config
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "app.db")
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    # Register Blueprints / Routes
    from .routes import main_bp
    from .multiday_routes import multiday_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(multiday_bp)

    # Create tables if they don't exist
    with app.app_context():
        db.create_all()

    return app

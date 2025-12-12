"""
Application de Gestion Scolaire - Package Principal
Version 2.0 - Architecture modulaire avec Blueprints
"""
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
import os

__version__ = "2.0.0"
__author__ = "Lycée Michel ALLAIRE"
__email__ = "clyelise@gmail.com"

# Extensions Flask
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()


def create_app(config_name='development'):
    """Factory pattern pour créer l'application Flask"""
    app = Flask(__name__)
    
    # Charger la configuration
    from config import config
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    
    # Initialiser les extensions
    db.init_app(app)
    migrate.init_app(app, db)
    
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Veuillez vous connecter pour accéder à cette page.'
    login_manager.login_message_category = 'info'
    
    # Créer le dossier de base de données s'il n'existe pas
    db_folder = os.path.join(os.path.dirname(__file__), 'database')
    if not os.path.exists(db_folder):
        os.makedirs(db_folder)
    
    # Importer et enregistrer les Blueprints
    from gestion_scolaire.routes.auth import auth_bp
    from gestion_scolaire.routes.main import main_bp
    from gestion_scolaire.routes.admin import admin_bp
    from gestion_scolaire.routes.teacher import teacher_bp
    from gestion_scolaire.routes.student import student_bp
    from gestion_scolaire.routes.parent import parent_bp
    from gestion_scolaire.routes.api import api_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(teacher_bp, url_prefix='/teacher')
    app.register_blueprint(student_bp, url_prefix='/student')
    app.register_blueprint(parent_bp, url_prefix='/parent')
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Charger le user loader
    from gestion_scolaire.models import User
    
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))
    
    # Context processors globaux
    @app.context_processor
    def utility_processor():
        """Fonctions utilitaires disponibles dans tous les templates"""
        from gestion_scolaire.models import AcademicYear, Announcement
        from datetime import datetime
        
        def get_current_year():
            year = AcademicYear.query.filter_by(is_current=True).first()
            return year.name if year else "2024-2025"
        
        def get_recent_announcements(limit=5):
            return Announcement.query.filter_by(is_active=True)\
                .order_by(Announcement.created_at.desc())\
                .limit(limit).all()
        
        def now():
            return datetime.now()
        
        return dict(
            get_current_year=get_current_year,
            get_recent_announcements=get_recent_announcements,
            now=now
        )
    
    # Filtres Jinja2 personnalisés
    @app.template_filter('datetime_format')
    def datetime_format(value, format='%d/%m/%Y %H:%M'):
        if value is None:
            return ""
        return value.strftime(format)
    
    @app.template_filter('date_format')
    def date_format(value, format='%d/%m/%Y'):
        if value is None:
            return ""
        return value.strftime(format)
    
    return app
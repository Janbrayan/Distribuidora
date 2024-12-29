from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_migrate import Migrate  # Importa Flask-Migrate

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
migrate = Migrate()  # Inicializa Migrate

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = '3ca949489ca01f012b2f867dc1216844e6f15ec06f564901802866a7f34a49cc'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///gestion.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Inicializar extensiones
    db.init_app(app)
    migrate.init_app(app, db)  # Conecta Flask-Migrate con Flask y SQLAlchemy
    login_manager.init_app(app)
    csrf.init_app(app)

    # Configuración de Flask-Login
    login_manager.login_view = 'auth.login'  # Redirige al login si no está autenticado
    login_manager.login_message = 'Por favor inicia sesión para acceder a esta página.'
    login_manager.login_message_category = 'info'

    # Función para cargar usuarios
    from app.models import Usuario

    @login_manager.user_loader
    def load_user(user_id):
        """Carga un usuario desde la base de datos usando su ID."""
        return Usuario.query.get(int(user_id))

    # Registro de Blueprints
    from app.auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/auth')

    from app.dashboard import dashboard as dashboard_blueprint
    app.register_blueprint(dashboard_blueprint, url_prefix='/dashboard')

    return app

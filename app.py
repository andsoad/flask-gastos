import os
from flask import Flask
from flask_login import LoginManager
from dotenv import load_dotenv
from extensions import mysql, login_manager
from routes.auth import auth_bp
from routes.gastos import gastos_bp
from routes.pagos_extra import pagos_extra_bp
from routes.reportes import reportes_bp
from routes.admin import admin_bp
from routes.descargas import descargas_bp

load_dotenv()

def create_app():
    app = Flask(__name__)
    app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')

    # MySQL config
    app.config['MYSQL_HOST']     = os.environ.get('MYSQL_HOST', 'localhost')
    app.config['MYSQL_PORT']     = int(os.environ.get('MYSQL_PORT', 3306))
    app.config['MYSQL_USER']     = os.environ.get('MYSQL_USER')
    app.config['MYSQL_PASSWORD'] = os.environ.get('MYSQL_PASSWORD')
    app.config['MYSQL_DB']       = os.environ.get('MYSQL_DB', 'gastos_pareja')
    app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

    mysql.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Inicia sesión para continuar.'
    login_manager.login_message_category = 'warning'

    app.register_blueprint(auth_bp)
    app.register_blueprint(gastos_bp)
    app.register_blueprint(pagos_extra_bp)
    app.register_blueprint(reportes_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(descargas_bp)

    # ── Manejador global de errores ────────────────────────────────────────────
    from logger import log_error
    from flask import render_template

    @app.errorhandler(500)
    def internal_error(e):
        log_error("Error 500 interno", e)
        return render_template('errors/500.html'), 500

    @app.errorhandler(404)
    def not_found(e):
        return render_template('errors/404.html'), 404

    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=False)

from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from models import Usuario
from logger import log_activity, log_error

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('reportes.dashboard'))
    return redirect(url_for('auth.login'))


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('reportes.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip().lower()
        password = request.form.get('password', '')

        row = Usuario.get_by_username(username)
        if row and row['activo'] and check_password_hash(row['password_hash'], password):
            user = Usuario(
                id       = row['id'],
                nombre   = row['nombre'],
                username = row['username'],
                rol      = row['rol'],
                persona  = row['persona'],
                activo   = row['activo']
            )
            login_user(user)
            log_activity(user.id, user.username, 'login', f"ip={request.remote_addr}")
            next_page = request.args.get('next')
            return redirect(next_page or url_for('reportes.dashboard'))
        else:
            log_error(f"Login fallido para username={username!r} ip={request.remote_addr}")
            flash('Correo o contraseña incorrectos.', 'danger')

    return render_template('login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    log_activity(current_user.id, current_user.username, 'logout')
    logout_user()
    flash('Sesión cerrada.', 'info')
    return redirect(url_for('auth.login'))

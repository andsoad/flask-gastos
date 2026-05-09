from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from extensions import mysql
from functools import wraps
from logger import log_activity, log_error

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash('Necesitas permisos de administrador.', 'danger')
            return redirect(url_for('reportes.dashboard'))
        return f(*args, **kwargs)
    return decorated


@admin_bp.route('/usuarios')
@login_required
@admin_required
def usuarios():
    cur = mysql.connection.cursor()
    cur.execute("SELECT id, nombre, username, rol, persona, activo, fecha_creacion FROM usuarios ORDER BY fecha_creacion")
    lista = cur.fetchall()
    cur.close()
    cfg = _get_config()
    return render_template('admin/usuarios.html', usuarios=lista, cfg=cfg)


@admin_bp.route('/usuarios/nuevo', methods=['GET', 'POST'])
@login_required
@admin_required
def nuevo_usuario():
    cfg = _get_config()
    if request.method == 'POST':
        nombre   = request.form.get('nombre', '').strip()
        username = request.form.get('username', '').strip().lower()
        password = request.form.get('password', '')
        rol      = request.form.get('rol', 'usuario')
        persona  = request.form.get('persona') or None

        if not all([nombre, username, password]):
            flash('Nombre, usuario y contraseña son obligatorios.', 'danger')
            return render_template('admin/form_usuario.html', cfg=cfg, usuario=request.form)

        pw_hash = generate_password_hash(password)
        try:
            cur = mysql.connection.cursor()
            cur.execute("""
                INSERT INTO usuarios (nombre, username, password_hash, rol, persona)
                VALUES (%s, %s, %s, %s, %s)
            """, (nombre, username, pw_hash, rol, persona))
            mysql.connection.commit()
            cur.close()
            log_activity(current_user.id, current_user.username, 'usuario_creado',
                         f"nuevo_usuario={username!r} rol={rol}")
            flash(f'Usuario {nombre} creado.', 'success')
            return redirect(url_for('admin.usuarios'))
        except Exception as e:
            log_error(f"Error creando usuario username={username!r}", e)
            flash('El nombre de usuario ya está en uso.', 'danger')

    return render_template('admin/form_usuario.html', cfg=cfg, usuario=None)


@admin_bp.route('/usuarios/editar/<int:uid>', methods=['GET', 'POST'])
@login_required
@admin_required
def editar_usuario(uid):
    cfg = _get_config()
    cur = mysql.connection.cursor()
    cur.execute("SELECT id, nombre, username, rol, persona, activo FROM usuarios WHERE id = %s", (uid,))
    usuario = cur.fetchone()
    cur.close()

    if not usuario:
        flash('Usuario no encontrado.', 'danger')
        return redirect(url_for('admin.usuarios'))

    if request.method == 'POST':
        nombre   = request.form.get('nombre', '').strip()
        username = request.form.get('username', '').strip().lower()
        rol      = request.form.get('rol', 'usuario')
        persona  = request.form.get('persona') or None
        activo   = 1 if request.form.get('activo') else 0
        password = request.form.get('password', '').strip()

        cur = mysql.connection.cursor()
        if password:
            pw_hash = generate_password_hash(password)
            cur.execute("""
                UPDATE usuarios SET nombre=%s, username=%s, rol=%s, persona=%s, activo=%s, password_hash=%s
                WHERE id=%s
            """, (nombre, username, rol, persona, activo, pw_hash, uid))
        else:
            cur.execute("""
                UPDATE usuarios SET nombre=%s, username=%s, rol=%s, persona=%s, activo=%s
                WHERE id=%s
            """, (nombre, username, rol, persona, activo, uid))
        mysql.connection.commit()
        cur.close()
        log_activity(current_user.id, current_user.username, 'usuario_editado',
                     f"uid={uid} username={username!r} rol={rol} activo={activo}")
        flash('Usuario actualizado.', 'success')
        return redirect(url_for('admin.usuarios'))

    return render_template('admin/form_usuario.html', cfg=cfg, usuario=usuario, editando=True)


@admin_bp.route('/usuarios/eliminar/<int:uid>', methods=['POST'])
@login_required
@admin_required
def eliminar_usuario(uid):
    if uid == current_user.id:
        flash('No puedes eliminar tu propia cuenta.', 'danger')
        return redirect(url_for('admin.usuarios'))
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM usuarios WHERE id = %s", (uid,))
    mysql.connection.commit()
    cur.close()
    log_activity(current_user.id, current_user.username, 'usuario_eliminado', f"uid={uid}")
    flash('Usuario eliminado.', 'info')
    return redirect(url_for('admin.usuarios'))


@admin_bp.route('/configuracion', methods=['GET', 'POST'])
@login_required
@admin_required
def configuracion():
    cfg = _get_config()
    if request.method == 'POST':
        n1 = request.form.get('nombre_persona1', '').strip()
        n2 = request.form.get('nombre_persona2', '').strip()
        if n1 and n2:
            cur = mysql.connection.cursor()
            cur.execute("UPDATE configuracion SET nombre_persona1=%s, nombre_persona2=%s WHERE id=1", (n1, n2))
            mysql.connection.commit()
            cur.close()
            flash('Nombres actualizados.', 'success')
            return redirect(url_for('admin.configuracion'))
    return render_template('admin/configuracion.html', cfg=cfg)


def _get_config():
    cur = mysql.connection.cursor()
    cur.execute("SELECT nombre_persona1, nombre_persona2 FROM configuracion WHERE id = 1")
    cfg = cur.fetchone()
    cur.close()
    return cfg

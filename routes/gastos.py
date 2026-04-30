from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from extensions import mysql
from datetime import date

gastos_bp = Blueprint('gastos', __name__, url_prefix='/gastos')

CATEGORIAS = [
    ('super',          '🛒 Súper/Comida'),
    ('restaurantes',   '🍽️ Restaurantes'),
    ('transporte',     '🚗 Transporte'),
    ('servicios',      '💡 Servicios'),
    ('entretenimiento','🎉 Entretenimiento'),
    ('salud',          '🏥 Salud'),
    ('viajes',         '✈️ Viajes'),
    ('ropa',           '👗 Ropa'),
    ('otros',          '📦 Otros'),
]


def get_config():
    cur = mysql.connection.cursor()
    cur.execute("SELECT nombre_persona1, nombre_persona2 FROM configuracion WHERE id = 1")
    cfg = cur.fetchone()
    cur.close()
    return cfg


@gastos_bp.route('/')
@login_required
def lista():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT g.*, u.nombre AS registrado_por_nombre,
               c.nombre_persona1, c.nombre_persona2
        FROM gastos g
        JOIN usuarios u ON g.creado_por = u.id
        JOIN configuracion c ON c.id = 1
        ORDER BY g.mes_inicio DESC, g.fecha_registro DESC
    """)
    gastos = cur.fetchall()
    cur.close()
    cfg = get_config()
    return render_template('gastos/lista.html', gastos=gastos, categorias=CATEGORIAS, cfg=cfg)


@gastos_bp.route('/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo():
    cfg = get_config()
    if request.method == 'POST':
        descripcion     = request.form.get('descripcion', '').strip()
        monto_total     = float(request.form.get('monto_total', 0))
        categoria       = request.form.get('categoria')
        pagado_por      = request.form.get('pagado_por')
        mes_inicio_str  = request.form.get('mes_inicio')
        meses_diferidos = int(request.form.get('meses_diferidos', 1))
        notas           = request.form.get('notas', '').strip()

        if not all([descripcion, monto_total > 0, categoria, pagado_por, mes_inicio_str]):
            flash('Por favor completa todos los campos requeridos.', 'danger')
            return render_template('gastos/form.html', categorias=CATEGORIAS, cfg=cfg, gasto=request.form)

        mes_inicio = mes_inicio_str + '-01'

        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO gastos (descripcion, monto_total, categoria, pagado_por,
                                mes_inicio, meses_diferidos, notas, creado_por)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (descripcion, monto_total, categoria, pagado_por,
              mes_inicio, meses_diferidos, notas, current_user.id))
        mysql.connection.commit()
        cur.close()
        flash('Gasto agregado correctamente.', 'success')
        return redirect(url_for('gastos.lista'))

    return render_template('gastos/form.html', categorias=CATEGORIAS, cfg=cfg, gasto=None)


@gastos_bp.route('/editar/<int:gasto_id>', methods=['GET', 'POST'])
@login_required
def editar(gasto_id):
    cfg = get_config()
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM gastos WHERE id = %s", (gasto_id,))
    gasto = cur.fetchone()
    cur.close()

    if not gasto:
        flash('Gasto no encontrado.', 'danger')
        return redirect(url_for('gastos.lista'))

    if request.method == 'POST':
        descripcion     = request.form.get('descripcion', '').strip()
        monto_total     = float(request.form.get('monto_total', 0))
        categoria       = request.form.get('categoria')
        pagado_por      = request.form.get('pagado_por')
        mes_inicio_str  = request.form.get('mes_inicio')
        meses_diferidos = int(request.form.get('meses_diferidos', 1))
        notas           = request.form.get('notas', '').strip()
        mes_inicio      = mes_inicio_str + '-01'

        cur = mysql.connection.cursor()
        cur.execute("""
            UPDATE gastos SET descripcion=%s, monto_total=%s, categoria=%s,
                pagado_por=%s, mes_inicio=%s, meses_diferidos=%s, notas=%s
            WHERE id=%s
        """, (descripcion, monto_total, categoria, pagado_por,
              mes_inicio, meses_diferidos, notas, gasto_id))
        mysql.connection.commit()
        cur.close()
        flash('Gasto actualizado.', 'success')
        return redirect(url_for('gastos.lista'))

    gasto['mes_inicio_str'] = gasto['mes_inicio'].strftime('%Y-%m')
    return render_template('gastos/form.html', categorias=CATEGORIAS, cfg=cfg, gasto=gasto, editando=True)


@gastos_bp.route('/eliminar/<int:gasto_id>', methods=['POST'])
@login_required
def eliminar(gasto_id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM gastos WHERE id = %s", (gasto_id,))
    mysql.connection.commit()
    cur.close()
    flash('Gasto eliminado.', 'info')
    return redirect(url_for('gastos.lista'))

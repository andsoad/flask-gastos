from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from extensions import mysql
from logger import log_activity, log_error

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
    ('mascotas',       '🐾 Mascotas'),
    ('casa',           '🏠 Casa'),
    ('bebe',           '👶 Bebé'),
    ('otros',          '📦 Otros'),
]


def get_config():
    cur = mysql.connection.cursor()
    cur.execute("SELECT nombre_persona1, nombre_persona2 FROM configuracion WHERE id = 1")
    cfg = cur.fetchone()
    cur.close()
    return cfg


def get_abonos(gasto_id):
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT id, persona, monto, notas, fecha_registro
        FROM abonos_gasto
        WHERE gasto_id = %s
        ORDER BY fecha_registro
    """, (gasto_id,))
    abonos = cur.fetchall()
    cur.close()
    return abonos


@gastos_bp.route('/')
@login_required
def lista():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT g.*, u.nombre AS registrado_por_nombre,
               c.nombre_persona1, c.nombre_persona2,
               COALESCE(SUM(a.monto), 0) AS total_abonado
        FROM gastos g
        JOIN usuarios u ON g.creado_por = u.id
        JOIN configuracion c ON c.id = 1
        LEFT JOIN abonos_gasto a ON a.gasto_id = g.id
        GROUP BY g.id
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
        pagado_por      = request.form.get('pagado_por') or None
        mes_inicio_str  = request.form.get('mes_inicio')
        meses_diferidos = int(request.form.get('meses_diferidos', 1))
        notas           = request.form.get('notas', '').strip()

        if not all([descripcion, monto_total > 0, categoria, mes_inicio_str]):
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
        gasto_id = cur.lastrowid
        cur.close()
        log_activity(current_user.id, current_user.username, 'gasto_creado',
                     f"id={gasto_id} descripcion={descripcion!r} monto={monto_total} categoria={categoria}")
        flash('Gasto agregado correctamente.', 'success')
        return redirect(url_for('gastos.detalle', gasto_id=gasto_id))

    return render_template('gastos/form.html', categorias=CATEGORIAS, cfg=cfg, gasto=None)


@gastos_bp.route('/<int:gasto_id>')
@login_required
def detalle(gasto_id):
    cfg = get_config()
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM gastos WHERE id = %s", (gasto_id,))
    gasto = cur.fetchone()
    cur.close()
    if not gasto:
        flash('Gasto no encontrado.', 'danger')
        return redirect(url_for('gastos.lista'))
    abonos  = get_abonos(gasto_id)
    abono_p1 = sum(float(a['monto']) for a in abonos if a['persona'] == 'persona1')
    abono_p2 = sum(float(a['monto']) for a in abonos if a['persona'] == 'persona2')
    gasto['mes_inicio_str'] = gasto['mes_inicio'].strftime('%B %Y')
    return render_template('gastos/detalle.html', gasto=gasto, abonos=abonos,
                           abono_p1=abono_p1, abono_p2=abono_p2, cfg=cfg, categorias=CATEGORIAS)


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
        pagado_por      = request.form.get('pagado_por') or None
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
        log_activity(current_user.id, current_user.username, 'gasto_editado',
                     f"id={gasto_id} descripcion={descripcion!r} monto={monto_total}")
        flash('Gasto actualizado.', 'success')
        return redirect(url_for('gastos.detalle', gasto_id=gasto_id))

    gasto['mes_inicio_str'] = gasto['mes_inicio'].strftime('%Y-%m')
    return render_template('gastos/form.html', categorias=CATEGORIAS, cfg=cfg, gasto=gasto, editando=True)


@gastos_bp.route('/eliminar/<int:gasto_id>', methods=['POST'])
@login_required
def eliminar(gasto_id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM gastos WHERE id = %s", (gasto_id,))
    mysql.connection.commit()
    cur.close()
    log_activity(current_user.id, current_user.username, 'gasto_eliminado', f"id={gasto_id}")
    flash('Gasto eliminado.', 'info')
    return redirect(url_for('gastos.lista'))


# ── Abonos ─────────────────────────────────────────────────────────────────────

@gastos_bp.route('/<int:gasto_id>/abonos/nuevo', methods=['POST'])
@login_required
def nuevo_abono(gasto_id):
    persona = request.form.get('persona')
    monto   = float(request.form.get('monto', 0))
    notas   = request.form.get('notas', '').strip()

    if not persona or monto <= 0:
        flash('Persona y monto son requeridos.', 'danger')
        return redirect(url_for('gastos.detalle', gasto_id=gasto_id))

    cur = mysql.connection.cursor()
    cur.execute("""
        INSERT INTO abonos_gasto (gasto_id, persona, monto, notas, creado_por)
        VALUES (%s, %s, %s, %s, %s)
    """, (gasto_id, persona, monto, notas, current_user.id))
    mysql.connection.commit()
    cur.close()
    log_activity(current_user.id, current_user.username, 'abono_creado',
                 f"gasto_id={gasto_id} persona={persona} monto={monto}")
    flash('Abono registrado.', 'success')
    return redirect(url_for('gastos.detalle', gasto_id=gasto_id))


@gastos_bp.route('/<int:gasto_id>/abonos/eliminar/<int:abono_id>', methods=['POST'])
@login_required
def eliminar_abono(gasto_id, abono_id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM abonos_gasto WHERE id = %s AND gasto_id = %s", (abono_id, gasto_id))
    mysql.connection.commit()
    cur.close()
    log_activity(current_user.id, current_user.username, 'abono_eliminado',
                 f"abono_id={abono_id} gasto_id={gasto_id}")
    flash('Abono eliminado.', 'info')
    return redirect(url_for('gastos.detalle', gasto_id=gasto_id))

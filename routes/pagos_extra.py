from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from extensions import mysql

pagos_extra_bp = Blueprint('pagos_extra', __name__, url_prefix='/pagos-extra')


def get_config():
    cur = mysql.connection.cursor()
    cur.execute("SELECT nombre_persona1, nombre_persona2 FROM configuracion WHERE id = 1")
    cfg = cur.fetchone()
    cur.close()
    return cfg


@pagos_extra_bp.route('/')
@login_required
def lista():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT p.*, u.nombre AS registrado_por_nombre,
               c.nombre_persona1, c.nombre_persona2
        FROM pagos_extra p
        JOIN usuarios u ON p.creado_por = u.id
        JOIN configuracion c ON c.id = 1
        ORDER BY p.mes DESC, p.fecha_registro DESC
    """)
    pagos = cur.fetchall()
    cur.close()
    cfg = get_config()
    return render_template('pagos_extra/lista.html', pagos=pagos, cfg=cfg)


@pagos_extra_bp.route('/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo():
    cfg = get_config()
    if request.method == 'POST':
        descripcion  = request.form.get('descripcion', '').strip()
        monto        = float(request.form.get('monto', 0))
        pagado_por   = request.form.get('pagado_por')
        recibido_por = request.form.get('recibido_por')
        mes_str      = request.form.get('mes')
        notas        = request.form.get('notas', '').strip()

        if pagado_por == recibido_por:
            flash('La persona que paga y la que recibe no pueden ser la misma.', 'danger')
            return render_template('pagos_extra/form.html', cfg=cfg, pago=request.form)

        if not all([descripcion, monto > 0, pagado_por, recibido_por, mes_str]):
            flash('Por favor completa todos los campos requeridos.', 'danger')
            return render_template('pagos_extra/form.html', cfg=cfg, pago=request.form)

        mes = mes_str + '-01'
        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO pagos_extra (descripcion, monto, pagado_por, recibido_por, mes, notas, creado_por)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (descripcion, monto, pagado_por, recibido_por, mes, notas, current_user.id))
        mysql.connection.commit()
        cur.close()
        flash('Pago extra registrado.', 'success')
        return redirect(url_for('pagos_extra.lista'))

    return render_template('pagos_extra/form.html', cfg=cfg, pago=None)


@pagos_extra_bp.route('/editar/<int:pago_id>', methods=['GET', 'POST'])
@login_required
def editar(pago_id):
    cfg = get_config()
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM pagos_extra WHERE id = %s", (pago_id,))
    pago = cur.fetchone()
    cur.close()

    if not pago:
        flash('Pago no encontrado.', 'danger')
        return redirect(url_for('pagos_extra.lista'))

    if request.method == 'POST':
        descripcion  = request.form.get('descripcion', '').strip()
        monto        = float(request.form.get('monto', 0))
        pagado_por   = request.form.get('pagado_por')
        recibido_por = request.form.get('recibido_por')
        mes_str      = request.form.get('mes')
        notas        = request.form.get('notas', '').strip()
        mes          = mes_str + '-01'

        cur = mysql.connection.cursor()
        cur.execute("""
            UPDATE pagos_extra SET descripcion=%s, monto=%s, pagado_por=%s,
                recibido_por=%s, mes=%s, notas=%s
            WHERE id=%s
        """, (descripcion, monto, pagado_por, recibido_por, mes, notas, pago_id))
        mysql.connection.commit()
        cur.close()
        flash('Pago actualizado.', 'success')
        return redirect(url_for('pagos_extra.lista'))

    pago['mes_str'] = pago['mes'].strftime('%Y-%m')
    return render_template('pagos_extra/form.html', cfg=cfg, pago=pago, editando=True)


@pagos_extra_bp.route('/eliminar/<int:pago_id>', methods=['POST'])
@login_required
def eliminar(pago_id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM pagos_extra WHERE id = %s", (pago_id,))
    mysql.connection.commit()
    cur.close()
    flash('Pago eliminado.', 'info')
    return redirect(url_for('pagos_extra.lista'))

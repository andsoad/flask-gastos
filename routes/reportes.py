from flask import Blueprint, render_template, request
from flask_login import login_required
from extensions import mysql
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
import calendar

reportes_bp = Blueprint('reportes', __name__)


def get_config():
    cur = mysql.connection.cursor()
    cur.execute("SELECT nombre_persona1, nombre_persona2 FROM configuracion WHERE id = 1")
    cfg = cur.fetchone()
    cur.close()
    return cfg


def primer_dia_mes(year, month):
    return date(year, month, 1)


def calcular_balance_mes(year, month):
    """
    Retorna el balance detallado de un mes específico.
    Incluye cuotas de gastos diferidos que caen en ese mes.
    """
    cfg = get_config()
    mes_actual = primer_dia_mes(year, month)
    cur = mysql.connection.cursor()

    # Traer todos los gastos cuyo rango de meses incluye este mes
    cur.execute("""
        SELECT id, descripcion, monto_total, categoria, pagado_por,
               mes_inicio, meses_diferidos
        FROM gastos
        WHERE mes_inicio <= %s
          AND DATE_ADD(mes_inicio, INTERVAL (meses_diferidos - 1) MONTH) >= %s
    """, (mes_actual, mes_actual))
    gastos_raw = cur.fetchall()

    gastos_mes = []
    total_p1 = 0.0
    total_p2 = 0.0

    for g in gastos_raw:
        cuota = round(float(g['monto_total']) / g['meses_diferidos'], 2)
        mitad = round(cuota / 2, 2)
        gastos_mes.append({
            'id':           g['id'],
            'descripcion':  g['descripcion'],
            'categoria':    g['categoria'],
            'pagado_por':   g['pagado_por'],
            'monto_total':  float(g['monto_total']),
            'meses_diferidos': g['meses_diferidos'],
            'cuota_mes':    cuota,
            'mitad':        mitad,
        })
        if g['pagado_por'] == 'persona1':
            total_p1 += cuota
        else:
            total_p2 += cuota

    # Pagos extra del mes
    cur.execute("""
        SELECT descripcion, monto, pagado_por, recibido_por, notas
        FROM pagos_extra
        WHERE mes = %s
    """, (mes_actual,))
    pagos_extra = cur.fetchall()
    cur.close()

    extra_p1 = 0.0  # pagos extra que persona1 hizo hacia persona2
    extra_p2 = 0.0

    for pe in pagos_extra:
        pe['monto'] = float(pe['monto'])
        if pe['pagado_por'] == 'persona1':
            extra_p1 += pe['monto']
        else:
            extra_p2 += pe['monto']

    total_gastado = total_p1 + total_p2
    mitad_total   = round(total_gastado / 2, 2)

    # Lo que cada quien debería pagar = mitad del total
    # Lo que cada quien ya pagó = sus propios gastos
    # Balance = pagado - debería pagar (+ si pagó de más, - si debe)
    balance_p1 = round(total_p1 - mitad_total + extra_p1 - extra_p2, 2)
    balance_p2 = round(total_p2 - mitad_total + extra_p2 - extra_p1, 2)

    # Quién le debe a quién
    deuda = None
    if balance_p1 < 0:
        deuda = {
            'deudor':    'persona1',
            'acreedor':  'persona2',
            'monto':     abs(balance_p1),
        }
    elif balance_p2 < 0:
        deuda = {
            'deudor':    'persona2',
            'acreedor':  'persona1',
            'monto':     abs(balance_p2),
        }

    return {
        'cfg':           cfg,
        'gastos':        gastos_mes,
        'pagos_extra':   pagos_extra,
        'total_p1':      round(total_p1, 2),
        'total_p2':      round(total_p2, 2),
        'total_gastado': round(total_gastado, 2),
        'mitad_total':   mitad_total,
        'balance_p1':    balance_p1,
        'balance_p2':    balance_p2,
        'deuda':         deuda,
        'extra_p1':      round(extra_p1, 2),
        'extra_p2':      round(extra_p2, 2),
    }


def calcular_balance_acumulado(hasta_year, hasta_month):
    """
    Suma los balances desde diciembre 2024 hasta el mes indicado.
    """
    inicio = date(2024, 12, 1)
    fin    = primer_dia_mes(hasta_year, hasta_month)

    acum_p1 = 0.0
    acum_p2 = 0.0
    acum_total = 0.0
    meses = []

    cur_date = inicio
    while cur_date <= fin:
        b = calcular_balance_mes(cur_date.year, cur_date.month)
        acum_p1    += b['total_p1']
        acum_p2    += b['total_p2']
        acum_total += b['total_gastado']
        meses.append({
            'year':    cur_date.year,
            'month':   cur_date.month,
            'label':   cur_date.strftime('%B %Y'),
            'total_p1': b['total_p1'],
            'total_p2': b['total_p2'],
            'total':    b['total_gastado'],
            'balance_p1': b['balance_p1'],
            'balance_p2': b['balance_p2'],
        })
        # Avanzar un mes
        if cur_date.month == 12:
            cur_date = date(cur_date.year + 1, 1, 1)
        else:
            cur_date = date(cur_date.year, cur_date.month + 1, 1)

    mitad_acum = round(acum_total / 2, 2)
    bal_acum_p1 = round(acum_p1 - mitad_acum, 2)
    bal_acum_p2 = round(acum_p2 - mitad_acum, 2)

    deuda_acum = None
    if bal_acum_p1 < 0:
        deuda_acum = {'deudor': 'persona1', 'acreedor': 'persona2', 'monto': abs(bal_acum_p1)}
    elif bal_acum_p2 < 0:
        deuda_acum = {'deudor': 'persona2', 'acreedor': 'persona1', 'monto': abs(bal_acum_p2)}

    return {
        'acum_p1':    round(acum_p1, 2),
        'acum_p2':    round(acum_p2, 2),
        'acum_total': round(acum_total, 2),
        'mitad_acum': mitad_acum,
        'bal_acum_p1': bal_acum_p1,
        'bal_acum_p2': bal_acum_p2,
        'deuda_acum':  deuda_acum,
        'meses':       meses,
    }


@reportes_bp.route('/dashboard')
@login_required
def dashboard():
    hoy = date.today()
    cfg = get_config()

    balance_mes = calcular_balance_mes(hoy.year, hoy.month)
    acumulado   = calcular_balance_acumulado(hoy.year, hoy.month)

    return render_template('dashboard.html',
        cfg=cfg,
        balance_mes=balance_mes,
        acumulado=acumulado,
        mes_actual=hoy.strftime('%B %Y'),
        year=hoy.year,
        month=hoy.month,
    )


@reportes_bp.route('/reporte')
@login_required
def reporte():
    hoy   = date.today()
    year  = int(request.args.get('year', hoy.year))
    month = int(request.args.get('month', hoy.month))

    cfg         = get_config()
    balance_mes = calcular_balance_mes(year, month)
    acumulado   = calcular_balance_acumulado(year, month)

    mes_label = primer_dia_mes(year, month).strftime('%B %Y')

    # Meses disponibles desde dic 2024
    meses_disponibles = []
    cur = date(2024, 12, 1)
    while cur <= hoy.replace(day=1):
        meses_disponibles.append({'year': cur.year, 'month': cur.month, 'label': cur.strftime('%B %Y')})
        if cur.month == 12:
            cur = date(cur.year + 1, 1, 1)
        else:
            cur = date(cur.year, cur.month + 1, 1)

    return render_template('reporte.html',
        cfg=cfg,
        balance_mes=balance_mes,
        acumulado=acumulado,
        mes_label=mes_label,
        year=year,
        month=month,
        meses_disponibles=meses_disponibles,
    )

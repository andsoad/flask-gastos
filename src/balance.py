"""
Lógica de cálculo de balance mensual y acumulado.
Solo usa stdlib de Python.
"""
from datetime import date
from src.db import db_fetch_all, get_config


def primer_dia_mes(year: int, month: int) -> str:
    return f"{year:04d}-{month:02d}-01"


def mes_label(year: int, month: int) -> str:
    MESES = ['Enero','Febrero','Marzo','Abril','Mayo','Junio',
             'Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre']
    return f"{MESES[month - 1]} {year}"


async def calcular_balance_mes(db, year: int, month: int) -> dict:
    mes_actual = primer_dia_mes(year, month)
    cfg = await get_config(db)

    gastos_raw = await db_fetch_all(db, """
        SELECT g.id, g.descripcion, g.monto_total, g.categoria, g.pagado_por,
               g.mes_inicio, g.meses_diferidos,
               COALESCE(SUM(CASE WHEN a.persona='persona1' THEN a.monto ELSE 0 END), 0) AS abono_p1,
               COALESCE(SUM(CASE WHEN a.persona='persona2' THEN a.monto ELSE 0 END), 0) AS abono_p2
        FROM gastos g
        LEFT JOIN abonos_gasto a ON a.gasto_id = g.id
        WHERE g.mes_inicio <= ?
          AND date(g.mes_inicio, '+' || (g.meses_diferidos - 1) || ' months') >= ?
        GROUP BY g.id
    """, [mes_actual, mes_actual])

    gastos_mes = []
    total_p1 = total_p2 = 0.0

    for g in gastos_raw:
        cuota    = round(float(g['monto_total']) / g['meses_diferidos'], 2)
        mitad    = round(cuota / 2, 2)
        abono_p1 = round(float(g['abono_p1']) / g['meses_diferidos'], 2)
        abono_p2 = round(float(g['abono_p2']) / g['meses_diferidos'], 2)

        if abono_p1 > 0 or abono_p2 > 0:
            pago_p1, pago_p2 = abono_p1, abono_p2
        elif g['pagado_por'] == 'persona1':
            pago_p1, pago_p2 = cuota, 0.0
        elif g['pagado_por'] == 'persona2':
            pago_p1, pago_p2 = 0.0, cuota
        else:
            pago_p1, pago_p2 = 0.0, 0.0

        gastos_mes.append({
            'id': g['id'], 'descripcion': g['descripcion'],
            'categoria': g['categoria'], 'pagado_por': g['pagado_por'],
            'monto_total': float(g['monto_total']), 'meses_diferidos': g['meses_diferidos'],
            'cuota_mes': cuota, 'mitad': mitad,
            'abono_p1': abono_p1, 'abono_p2': abono_p2,
            'pago_p1': pago_p1, 'pago_p2': pago_p2,
            'tiene_abonos': abono_p1 > 0 or abono_p2 > 0,
        })
        total_p1 += pago_p1
        total_p2 += pago_p2

    pagos_extra = await db_fetch_all(db,
        "SELECT descripcion, monto, pagado_por, recibido_por, notas FROM pagos_extra WHERE mes = ?",
        [mes_actual])

    extra_p1 = sum(float(p['monto']) for p in pagos_extra if p['pagado_por'] == 'persona1')
    extra_p2 = sum(float(p['monto']) for p in pagos_extra if p['pagado_por'] == 'persona2')
    for p in pagos_extra:
        p['monto'] = float(p['monto'])

    total_gastado = total_p1 + total_p2
    mitad_total   = round(total_gastado / 2, 2)
    balance_p1    = round(total_p1 - mitad_total + extra_p1 - extra_p2, 2)
    balance_p2    = round(total_p2 - mitad_total + extra_p2 - extra_p1, 2)

    deuda = None
    if balance_p1 < 0:
        deuda = {'deudor': 'persona1', 'acreedor': 'persona2', 'monto': abs(balance_p1)}
    elif balance_p2 < 0:
        deuda = {'deudor': 'persona2', 'acreedor': 'persona1', 'monto': abs(balance_p2)}

    return {
        'cfg': cfg, 'gastos': gastos_mes, 'pagos_extra': pagos_extra,
        'total_p1': round(total_p1, 2), 'total_p2': round(total_p2, 2),
        'total_gastado': round(total_gastado, 2), 'mitad_total': mitad_total,
        'balance_p1': balance_p1, 'balance_p2': balance_p2,
        'deuda': deuda, 'extra_p1': round(extra_p1, 2), 'extra_p2': round(extra_p2, 2),
    }


async def calcular_balance_acumulado(db, hasta_year: int, hasta_month: int) -> dict:
    acum_p1 = acum_p2 = acum_total = 0.0
    meses = []
    y, m  = 2024, 12

    while (y, m) <= (hasta_year, hasta_month):
        b = await calcular_balance_mes(db, y, m)
        acum_p1    += b['total_p1']
        acum_p2    += b['total_p2']
        acum_total += b['total_gastado']
        meses.append({
            'year': y, 'month': m, 'label': mes_label(y, m),
            'total_p1': b['total_p1'], 'total_p2': b['total_p2'],
            'total': b['total_gastado'],
            'balance_p1': b['balance_p1'], 'balance_p2': b['balance_p2'],
        })
        m += 1
        if m > 12:
            y, m = y + 1, 1

    mitad_acum  = round(acum_total / 2, 2)
    bal_acum_p1 = round(acum_p1 - mitad_acum, 2)
    bal_acum_p2 = round(acum_p2 - mitad_acum, 2)

    deuda_acum = None
    if bal_acum_p1 < 0:
        deuda_acum = {'deudor': 'persona1', 'acreedor': 'persona2', 'monto': abs(bal_acum_p1)}
    elif bal_acum_p2 < 0:
        deuda_acum = {'deudor': 'persona2', 'acreedor': 'persona1', 'monto': abs(bal_acum_p2)}

    return {
        'acum_p1': round(acum_p1, 2), 'acum_p2': round(acum_p2, 2),
        'acum_total': round(acum_total, 2), 'mitad_acum': mitad_acum,
        'bal_acum_p1': bal_acum_p1, 'bal_acum_p2': bal_acum_p2,
        'deuda_acum': deuda_acum, 'meses': meses,
    }

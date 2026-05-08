"""
Gastos Pareja — Cloudflare Workers + D1
Entry point para Pyodide runtime (Python puro, sin dependencias externas).
"""
from urllib.parse import urlparse, parse_qs, unquote_plus
from datetime import date as Date
import json

from js import Response as JSResponse, Headers

from src.router import Router, Response, redirect
from src.auth_utils import hash_password, verify_password, create_token, decode_token
from src.db import db_fetch_all, db_fetch_one, db_run, get_config
from src.balance import calcular_balance_mes, calcular_balance_acumulado, mes_label
from src.templating import render

router = Router()

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


# ── Helpers ────────────────────────────────────────────────────────────────────

def get_token_from_request(request) -> str | None:
    cookie_header = request.headers.get('Cookie') or ''
    for part in cookie_header.split(';'):
        part = part.strip()
        if part.startswith('token='):
            return part[6:]
    return None


async def get_current_user(request, env) -> dict | None:
    token = get_token_from_request(request)
    if not token:
        return None
    payload = decode_token(token, env.SECRET_KEY)
    if not payload:
        return None
    return await db_fetch_one(env.DB,
        "SELECT id, nombre, username, rol, persona, activo FROM usuarios WHERE id = ? AND activo = 1",
        [payload.get('sub')])


async def require_user(request, env):
    user = await get_current_user(request, env)
    if not user:
        return None, redirect('/login')
    return user, None


async def require_admin(request, env):
    user, err = await require_user(request, env)
    if err:
        return None, err
    if user['rol'] != 'admin':
        return None, Response('Forbidden', status=403)
    return user, None


async def parse_form(request) -> dict:
    body = await request.text()
    result = {}
    for part in body.split('&'):
        if '=' in part:
            k, v = part.split('=', 1)
            result[unquote_plus(k)] = unquote_plus(v)
    return result


def get_qs(request) -> dict:
    qs = urlparse(request.url).query
    params = parse_qs(qs)
    return {k: v[0] for k, v in params.items()}


def meses_disponibles():
    hoy  = Date.today()
    y, m = 2024, 12
    meses = []
    while (y, m) <= (hoy.year, hoy.month):
        meses.append({'year': y, 'month': m, 'label': mes_label(y, m)})
        m += 1
        if m > 12:
            y, m = y + 1, 1
    return meses


def html(content: str, status: int = 200) -> Response:
    return Response(content, status=status)


def set_token_cookie(response: Response, token: str) -> Response:
    response.extra_headers['Set-Cookie'] = f'token={token}; HttpOnly; SameSite=Lax; Path=/; Max-Age=604800'
    return response


def clear_token_cookie(response: Response) -> Response:
    response.extra_headers['Set-Cookie'] = 'token=; HttpOnly; SameSite=Lax; Path=/; Max-Age=0'
    return response


# ── Auth ───────────────────────────────────────────────────────────────────────

@router.get('/')
async def index(request, env):
    user = await get_current_user(request, env)
    if user:
        return redirect('/dashboard')
    return redirect('/login')


@router.get('/login')
async def login_get(request, env):
    return html(render('login.html', error=None))


@router.post('/login')
async def login_post(request, env):
    form = await parse_form(request)
    username = form.get('username', '').strip().lower()
    password = form.get('password', '')
    user = await db_fetch_one(env.DB,
        "SELECT * FROM usuarios WHERE username = ? AND activo = 1", [username])
    if not user or not verify_password(password, user['password_hash']):
        return html(render('login.html', error='Usuario o contraseña incorrectos'))
    token    = create_token({'sub': user['id']}, env.SECRET_KEY)
    response = redirect('/dashboard')
    return set_token_cookie(response, token)


@router.get('/logout')
async def logout(request, env):
    return clear_token_cookie(redirect('/login'))


# ── Dashboard ──────────────────────────────────────────────────────────────────

@router.get('/dashboard')
async def dashboard(request, env):
    user, err = await require_user(request, env)
    if err: return err
    hoy = Date.today()
    cfg = await get_config(env.DB)
    balance_mes = await calcular_balance_mes(env.DB, hoy.year, hoy.month)
    acumulado   = await calcular_balance_acumulado(env.DB, hoy.year, hoy.month)
    return html(render('dashboard.html',
        user=user, cfg=cfg, balance_mes=balance_mes, acumulado=acumulado,
        mes_actual=mes_label(hoy.year, hoy.month),
        year=hoy.year, month=hoy.month))


# ── Reporte ────────────────────────────────────────────────────────────────────

@router.get('/reporte')
async def reporte(request, env):
    user, err = await require_user(request, env)
    if err: return err
    hoy   = Date.today()
    qs    = get_qs(request)
    year  = int(qs.get('year',  hoy.year))
    month = int(qs.get('month', hoy.month))
    cfg         = await get_config(env.DB)
    balance_mes = await calcular_balance_mes(env.DB, year, month)
    acumulado   = await calcular_balance_acumulado(env.DB, year, month)
    return html(render('reporte.html',
        user=user, cfg=cfg, balance_mes=balance_mes, acumulado=acumulado,
        mes_label=mes_label(year, month), year=year, month=month,
        meses_disponibles=meses_disponibles()))


# ── Gastos ─────────────────────────────────────────────────────────────────────

@router.get('/gastos')
async def gastos_lista(request, env):
    user, err = await require_user(request, env)
    if err: return err
    cfg    = await get_config(env.DB)
    gastos = await db_fetch_all(env.DB, """
        SELECT g.*, u.nombre AS registrado_por_nombre,
               COALESCE(SUM(a.monto), 0) AS total_abonado
        FROM gastos g
        JOIN usuarios u ON g.creado_por = u.id
        LEFT JOIN abonos_gasto a ON a.gasto_id = g.id
        GROUP BY g.id ORDER BY g.mes_inicio DESC, g.fecha_registro DESC
    """)
    return html(render('gastos/lista.html', user=user, cfg=cfg,
                       gastos=gastos, categorias=CATEGORIAS))


@router.get('/gastos/nuevo')
async def gastos_nuevo_get(request, env):
    user, err = await require_user(request, env)
    if err: return err
    cfg = await get_config(env.DB)
    return html(render('gastos/form.html', user=user, cfg=cfg,
                       categorias=CATEGORIAS, gasto=None, editando=False))


@router.post('/gastos/nuevo')
async def gastos_nuevo_post(request, env):
    user, err = await require_user(request, env)
    if err: return err
    form            = await parse_form(request)
    descripcion     = form.get('descripcion', '').strip()
    monto_total     = float(form.get('monto_total', 0))
    categoria       = form.get('categoria', '')
    pagado_por      = form.get('pagado_por', '') or None
    mes_inicio      = form.get('mes_inicio', '') + '-01'
    meses_diferidos = int(form.get('meses_diferidos', 1))
    notas           = form.get('notas', '').strip()
    if pagado_por not in ('persona1', 'persona2'):
        pagado_por = None
    result = await db_run(env.DB, """
        INSERT INTO gastos (descripcion, monto_total, categoria, pagado_por,
                            mes_inicio, meses_diferidos, notas, creado_por)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, [descripcion, monto_total, categoria, pagado_por,
          mes_inicio, meses_diferidos, notas, user['id']])
    return redirect(f"/gastos/{result['last_row_id']}")


@router.get('/gastos/{gasto_id}')
async def gastos_detalle(request, env, gasto_id):
    user, err = await require_user(request, env)
    if err: return err
    cfg   = await get_config(env.DB)
    gasto = await db_fetch_one(env.DB, "SELECT * FROM gastos WHERE id = ?", [gasto_id])
    if not gasto: return redirect('/gastos')
    abonos   = await db_fetch_all(env.DB,
        "SELECT * FROM abonos_gasto WHERE gasto_id = ? ORDER BY fecha_registro", [gasto_id])
    abono_p1 = sum(float(a['monto']) for a in abonos if a['persona'] == 'persona1')
    abono_p2 = sum(float(a['monto']) for a in abonos if a['persona'] == 'persona2')
    return html(render('gastos/detalle.html', user=user, cfg=cfg, gasto=gasto,
                       abonos=abonos, abono_p1=abono_p1, abono_p2=abono_p2))


@router.get('/gastos/{gasto_id}/editar')
async def gastos_editar_get(request, env, gasto_id):
    user, err = await require_user(request, env)
    if err: return err
    cfg   = await get_config(env.DB)
    gasto = await db_fetch_one(env.DB, "SELECT * FROM gastos WHERE id = ?", [gasto_id])
    if not gasto: return redirect('/gastos')
    gasto['mes_inicio_str'] = gasto['mes_inicio'][:7]
    return html(render('gastos/form.html', user=user, cfg=cfg,
                       categorias=CATEGORIAS, gasto=gasto, editando=True))


@router.post('/gastos/{gasto_id}/editar')
async def gastos_editar_post(request, env, gasto_id):
    user, err = await require_user(request, env)
    if err: return err
    form            = await parse_form(request)
    pagado_por      = form.get('pagado_por', '') or None
    if pagado_por not in ('persona1', 'persona2'):
        pagado_por = None
    await db_run(env.DB, """
        UPDATE gastos SET descripcion=?, monto_total=?, categoria=?, pagado_por=?,
            mes_inicio=?, meses_diferidos=?, notas=? WHERE id=?
    """, [form.get('descripcion','').strip(), float(form.get('monto_total',0)),
          form.get('categoria',''), pagado_por,
          form.get('mes_inicio','') + '-01', int(form.get('meses_diferidos',1)),
          form.get('notas','').strip(), gasto_id])
    return redirect(f'/gastos/{gasto_id}')


@router.post('/gastos/{gasto_id}/eliminar')
async def gastos_eliminar(request, env, gasto_id):
    user, err = await require_user(request, env)
    if err: return err
    await db_run(env.DB, "DELETE FROM gastos WHERE id = ?", [gasto_id])
    return redirect('/gastos')


@router.post('/gastos/{gasto_id}/abonos/nuevo')
async def abono_nuevo(request, env, gasto_id):
    user, err = await require_user(request, env)
    if err: return err
    form = await parse_form(request)
    await db_run(env.DB, """
        INSERT INTO abonos_gasto (gasto_id, persona, monto, notas, creado_por)
        VALUES (?, ?, ?, ?, ?)
    """, [gasto_id, form.get('persona'), float(form.get('monto',0)),
          form.get('notas','').strip(), user['id']])
    return redirect(f'/gastos/{gasto_id}')


@router.post('/gastos/{gasto_id}/abonos/{abono_id}/eliminar')
async def abono_eliminar(request, env, gasto_id, abono_id):
    user, err = await require_user(request, env)
    if err: return err
    await db_run(env.DB, "DELETE FROM abonos_gasto WHERE id = ? AND gasto_id = ?",
                 [abono_id, gasto_id])
    return redirect(f'/gastos/{gasto_id}')


# ── Pagos Extra ────────────────────────────────────────────────────────────────

@router.get('/pagos-extra')
async def pagos_extra_lista(request, env):
    user, err = await require_user(request, env)
    if err: return err
    cfg   = await get_config(env.DB)
    pagos = await db_fetch_all(env.DB, """
        SELECT p.*, u.nombre AS registrado_por_nombre
        FROM pagos_extra p JOIN usuarios u ON p.creado_por = u.id
        ORDER BY p.mes DESC, p.fecha_registro DESC
    """)
    return html(render('pagos_extra/lista.html', user=user, cfg=cfg, pagos=pagos))


@router.get('/pagos-extra/nuevo')
async def pagos_extra_nuevo_get(request, env):
    user, err = await require_user(request, env)
    if err: return err
    cfg = await get_config(env.DB)
    return html(render('pagos_extra/form.html', user=user, cfg=cfg, pago=None, editando=False))


@router.post('/pagos-extra/nuevo')
async def pagos_extra_nuevo_post(request, env):
    user, err = await require_user(request, env)
    if err: return err
    form = await parse_form(request)
    await db_run(env.DB, """
        INSERT INTO pagos_extra (descripcion, monto, pagado_por, recibido_por, mes, notas, creado_por)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, [form.get('descripcion','').strip(), float(form.get('monto',0)),
          form.get('pagado_por'), form.get('recibido_por'),
          form.get('mes','') + '-01', form.get('notas','').strip(), user['id']])
    return redirect('/pagos-extra')


@router.get('/pagos-extra/{pago_id}/editar')
async def pagos_extra_editar_get(request, env, pago_id):
    user, err = await require_user(request, env)
    if err: return err
    cfg  = await get_config(env.DB)
    pago = await db_fetch_one(env.DB, "SELECT * FROM pagos_extra WHERE id = ?", [pago_id])
    if not pago: return redirect('/pagos-extra')
    pago['mes_str'] = pago['mes'][:7]
    return html(render('pagos_extra/form.html', user=user, cfg=cfg, pago=pago, editando=True))


@router.post('/pagos-extra/{pago_id}/editar')
async def pagos_extra_editar_post(request, env, pago_id):
    user, err = await require_user(request, env)
    if err: return err
    form = await parse_form(request)
    await db_run(env.DB, """
        UPDATE pagos_extra SET descripcion=?, monto=?, pagado_por=?,
            recibido_por=?, mes=?, notas=? WHERE id=?
    """, [form.get('descripcion','').strip(), float(form.get('monto',0)),
          form.get('pagado_por'), form.get('recibido_por'),
          form.get('mes','') + '-01', form.get('notas','').strip(), pago_id])
    return redirect('/pagos-extra')


@router.post('/pagos-extra/{pago_id}/eliminar')
async def pagos_extra_eliminar(request, env, pago_id):
    user, err = await require_user(request, env)
    if err: return err
    await db_run(env.DB, "DELETE FROM pagos_extra WHERE id = ?", [pago_id])
    return redirect('/pagos-extra')


# ── Descargas ──────────────────────────────────────────────────────────────────

@router.get('/descargas')
async def descargas_index(request, env):
    user, err = await require_user(request, env)
    if err: return err
    cfg = await get_config(env.DB)
    hoy = Date.today()
    return html(render('descargas/index.html', user=user, cfg=cfg,
                       meses=meses_disponibles(),
                       year_sel=hoy.year, month_sel=hoy.month))


# ── Admin ──────────────────────────────────────────────────────────────────────

@router.get('/admin/usuarios')
async def admin_usuarios(request, env):
    user, err = await require_admin(request, env)
    if err: return err
    cfg   = await get_config(env.DB)
    lista = await db_fetch_all(env.DB,
        "SELECT id, nombre, username, rol, persona, activo, fecha_creacion FROM usuarios ORDER BY fecha_creacion")
    return html(render('admin/usuarios.html', user=user, cfg=cfg, usuarios=lista))


@router.get('/admin/usuarios/nuevo')
async def admin_nuevo_get(request, env):
    user, err = await require_admin(request, env)
    if err: return err
    cfg = await get_config(env.DB)
    return html(render('admin/form_usuario.html', user=user, cfg=cfg, usuario=None, editando=False))


@router.post('/admin/usuarios/nuevo')
async def admin_nuevo_post(request, env):
    user, err = await require_admin(request, env)
    if err: return err
    form        = await parse_form(request)
    persona_val = form.get('persona','') if form.get('persona') in ('persona1','persona2') else None
    pw_hash     = hash_password(form.get('password',''))
    try:
        await db_run(env.DB, """
            INSERT INTO usuarios (nombre, username, password_hash, rol, persona)
            VALUES (?, ?, ?, ?, ?)
        """, [form.get('nombre','').strip(), form.get('username','').strip().lower(),
              pw_hash, form.get('rol','usuario'), persona_val])
    except Exception:
        cfg = await get_config(env.DB)
        return html(render('admin/form_usuario.html', user=user, cfg=cfg,
                           usuario=form, editando=False,
                           error='El nombre de usuario ya está en uso.'))
    return redirect('/admin/usuarios')


@router.get('/admin/usuarios/{uid}/editar')
async def admin_editar_get(request, env, uid):
    user, err = await require_admin(request, env)
    if err: return err
    cfg     = await get_config(env.DB)
    usuario = await db_fetch_one(env.DB,
        "SELECT id, nombre, username, rol, persona, activo FROM usuarios WHERE id = ?", [uid])
    if not usuario: return redirect('/admin/usuarios')
    return html(render('admin/form_usuario.html', user=user, cfg=cfg,
                       usuario=usuario, editando=True))


@router.post('/admin/usuarios/{uid}/editar')
async def admin_editar_post(request, env, uid):
    user, err = await require_admin(request, env)
    if err: return err
    form        = await parse_form(request)
    persona_val = form.get('persona','') if form.get('persona') in ('persona1','persona2') else None
    activo_val  = 1 if form.get('activo') else 0
    password    = form.get('password','').strip()
    if password:
        pw_hash = hash_password(password)
        await db_run(env.DB, """
            UPDATE usuarios SET nombre=?, username=?, rol=?, persona=?, activo=?, password_hash=?
            WHERE id=?
        """, [form.get('nombre','').strip(), form.get('username','').strip().lower(),
              form.get('rol','usuario'), persona_val, activo_val, pw_hash, uid])
    else:
        await db_run(env.DB, """
            UPDATE usuarios SET nombre=?, username=?, rol=?, persona=?, activo=? WHERE id=?
        """, [form.get('nombre','').strip(), form.get('username','').strip().lower(),
              form.get('rol','usuario'), persona_val, activo_val, uid])
    return redirect('/admin/usuarios')


@router.post('/admin/usuarios/{uid}/eliminar')
async def admin_eliminar(request, env, uid):
    user, err = await require_admin(request, env)
    if err: return err
    if str(uid) != str(user['id']):
        await db_run(env.DB, "DELETE FROM usuarios WHERE id = ?", [uid])
    return redirect('/admin/usuarios')


@router.get('/admin/configuracion')
async def admin_config_get(request, env):
    user, err = await require_admin(request, env)
    if err: return err
    cfg = await get_config(env.DB)
    return html(render('admin/configuracion.html', user=user, cfg=cfg))


@router.post('/admin/configuracion')
async def admin_config_post(request, env):
    user, err = await require_admin(request, env)
    if err: return err
    form = await parse_form(request)
    await db_run(env.DB,
        "UPDATE configuracion SET nombre_persona1=?, nombre_persona2=? WHERE id=1",
        [form.get('nombre_persona1','Ana'), form.get('nombre_persona2','Luis')])
    return redirect('/admin/configuracion')


# ── Setup primer admin ─────────────────────────────────────────────────────────

@router.get('/setup/crear-admin')
async def setup_get(request, env):
    count = await db_fetch_one(env.DB, "SELECT COUNT(*) as n FROM usuarios")
    if count and count['n'] > 0:
        return redirect('/login')
    return html(render('setup/crear_admin.html'))


@router.post('/setup/crear-admin')
async def setup_post(request, env):
    count = await db_fetch_one(env.DB, "SELECT COUNT(*) as n FROM usuarios")
    if count and count['n'] > 0:
        return redirect('/login')
    form    = await parse_form(request)
    pw_hash = hash_password(form.get('password',''))
    await db_run(env.DB, """
        INSERT INTO usuarios (nombre, username, password_hash, rol, activo)
        VALUES (?, ?, ?, 'admin', 1)
    """, [form.get('nombre','').strip(), form.get('username','').strip().lower(), pw_hash])
    return redirect('/login')


# ── Entry point de Cloudflare Workers ─────────────────────────────────────────

async def on_fetch(request, env):
    try:
        response = await router.dispatch(request, env)
        return response.to_js_response()
    except Exception as e:
        body = f"<h1>Error interno</h1><pre>{e}</pre>"
        return Response(body, status=500).to_js_response()

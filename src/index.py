"""
Gastos Pareja — Cloudflare Workers + FastAPI + D1
Todo inicializado dentro del fetch handler para minimizar startup CPU.
"""
from workers import WorkerEntrypoint, Response
import asgi

# Solo imports absolutamente necesarios al nivel de módulo
from typing import Optional
from datetime import date
import os

# ── App inicializada de forma lazy ─────────────────────────────────────────────

_app = None
_templates = None

def get_app():
    global _app, _templates
    if _app is not None:
        return _app, _templates

    from fastapi import FastAPI, Request, Depends, HTTPException, Form, Cookie
    from fastapi.responses import HTMLResponse, RedirectResponse
    from fastapi.templating import Jinja2Templates
    from auth_utils import verify_password, hash_password, create_token, decode_token
    from db import db_fetch_all, db_fetch_one, db_run, get_config
    from balance import calcular_balance_mes, calcular_balance_acumulado, mes_label

    _app = FastAPI()
    _templates = Jinja2Templates(
        directory=os.path.join(os.path.dirname(__file__), '..', 'templates')
    )

    CATEGORIAS = [
        ('super','🛒 Súper/Comida'), ('restaurantes','🍽️ Restaurantes'),
        ('transporte','🚗 Transporte'), ('servicios','💡 Servicios'),
        ('entretenimiento','🎉 Entretenimiento'), ('salud','🏥 Salud'),
        ('viajes','✈️ Viajes'), ('ropa','👗 Ropa'), ('mascotas','🐾 Mascotas'),
        ('casa','🏠 Casa'), ('bebe','👶 Bebé'), ('otros','📦 Otros'),
    ]

    def get_db(request: Request):
        return request.scope['env'].DB

    def get_secret(request: Request) -> str:
        return request.scope['env'].SECRET_KEY

    async def get_current_user(request: Request, token: Optional[str] = Cookie(None)):
        if not token: return None
        payload = decode_token(token, get_secret(request))
        if not payload: return None
        return await db_fetch_one(get_db(request),
            "SELECT id, nombre, username, rol, persona, activo FROM usuarios WHERE id = ? AND activo = 1",
            [payload.get('sub')])

    async def require_user(request: Request, token: Optional[str] = Cookie(None)):
        user = await get_current_user(request, token)
        if not user:
            raise HTTPException(status_code=302, headers={"Location": "/login"})
        return user

    async def require_admin(request: Request, token: Optional[str] = Cookie(None)):
        user = await require_user(request, token)
        if user['rol'] != 'admin':
            raise HTTPException(status_code=403, detail="Acceso denegado")
        return user

    def meses_disponibles():
        hoy = date.today()
        y, m = 2024, 12
        meses = []
        while (y, m) <= (hoy.year, hoy.month):
            meses.append({'year': y, 'month': m, 'label': mes_label(y, m)})
            m += 1
            if m > 12: y, m = y + 1, 1
        return meses

    def set_cookie_redirect(url: str, token: str) -> RedirectResponse:
        resp = RedirectResponse(url, status_code=302)
        resp.set_cookie('token', token, httponly=True, samesite='lax', max_age=604800)
        return resp

    app = _app
    t   = _templates

    # ── Auth ───────────────────────────────────────────────────────────────────

    @app.get('/', response_class=HTMLResponse)
    async def index(request: Request, token: Optional[str] = Cookie(None)):
        user = await get_current_user(request, token)
        return RedirectResponse('/dashboard' if user else '/login', status_code=302)

    @app.get('/login', response_class=HTMLResponse)
    async def login_get(request: Request):
        return t.TemplateResponse('login.html', {'request': request})

    @app.post('/login')
    async def login_post(request: Request, username: str = Form(...), password: str = Form(...)):
        user = await db_fetch_one(get_db(request),
            "SELECT * FROM usuarios WHERE username = ? AND activo = 1", [username.lower()])
        if not user or not verify_password(password, user['password_hash']):
            return t.TemplateResponse('login.html', {'request': request, 'error': 'Usuario o contraseña incorrectos'})
        token = create_token({'sub': user['id']}, get_secret(request))
        return set_cookie_redirect('/dashboard', token)

    @app.get('/logout')
    async def logout():
        resp = RedirectResponse('/login', status_code=302)
        resp.delete_cookie('token')
        return resp

    # ── Dashboard ──────────────────────────────────────────────────────────────

    @app.get('/dashboard', response_class=HTMLResponse)
    async def dashboard(request: Request, user=Depends(require_user)):
        hoy = date.today()
        cfg = await get_config(get_db(request))
        bal = await calcular_balance_mes(get_db(request), hoy.year, hoy.month)
        acm = await calcular_balance_acumulado(get_db(request), hoy.year, hoy.month)
        return t.TemplateResponse('dashboard.html', {
            'request': request, 'user': user, 'cfg': cfg,
            'balance_mes': bal, 'acumulado': acm,
            'mes_actual': mes_label(hoy.year, hoy.month),
            'year': hoy.year, 'month': hoy.month})

    # ── Reporte ────────────────────────────────────────────────────────────────

    @app.get('/reporte', response_class=HTMLResponse)
    async def reporte(request: Request, year: int = None, month: int = None, user=Depends(require_user)):
        hoy = date.today()
        year = year or hoy.year
        month = month or hoy.month
        cfg = await get_config(get_db(request))
        bal = await calcular_balance_mes(get_db(request), year, month)
        acm = await calcular_balance_acumulado(get_db(request), year, month)
        return t.TemplateResponse('reporte.html', {
            'request': request, 'user': user, 'cfg': cfg,
            'balance_mes': bal, 'acumulado': acm,
            'mes_label': mes_label(year, month), 'year': year, 'month': month,
            'meses_disponibles': meses_disponibles()})

    # ── Gastos ─────────────────────────────────────────────────────────────────

    @app.get('/gastos', response_class=HTMLResponse)
    async def gastos_lista(request: Request, user=Depends(require_user)):
        cfg = await get_config(get_db(request))
        gastos = await db_fetch_all(get_db(request), """
            SELECT g.*, COALESCE(SUM(a.monto), 0) AS total_abonado
            FROM gastos g LEFT JOIN abonos_gasto a ON a.gasto_id = g.id
            GROUP BY g.id ORDER BY g.mes_inicio DESC, g.fecha_registro DESC""")
        return t.TemplateResponse('gastos/lista.html', {
            'request': request, 'user': user, 'cfg': cfg,
            'gastos': gastos, 'categorias': CATEGORIAS})

    @app.get('/gastos/nuevo', response_class=HTMLResponse)
    async def gastos_nuevo_get(request: Request, user=Depends(require_user)):
        cfg = await get_config(get_db(request))
        return t.TemplateResponse('gastos/form.html', {
            'request': request, 'user': user, 'cfg': cfg,
            'categorias': CATEGORIAS, 'gasto': None, 'editando': False})

    @app.post('/gastos/nuevo')
    async def gastos_nuevo_post(request: Request, user=Depends(require_user),
        descripcion: str = Form(...), monto_total: float = Form(...),
        categoria: str = Form(...), pagado_por: str = Form(''),
        mes_inicio: str = Form(...), meses_diferidos: int = Form(1), notas: str = Form('')):
        pagador = pagado_por if pagado_por in ('persona1','persona2') else None
        result = await db_run(get_db(request), """
            INSERT INTO gastos (descripcion, monto_total, categoria, pagado_por,
                                mes_inicio, meses_diferidos, notas, creado_por)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            [descripcion, monto_total, categoria, pagador,
             mes_inicio + '-01', meses_diferidos, notas, user['id']])
        return RedirectResponse(f"/gastos/{result['last_row_id']}", status_code=302)

    @app.get('/gastos/{gasto_id}', response_class=HTMLResponse)
    async def gastos_detalle(request: Request, gasto_id: int, user=Depends(require_user)):
        cfg   = await get_config(get_db(request))
        gasto = await db_fetch_one(get_db(request), "SELECT * FROM gastos WHERE id = ?", [gasto_id])
        if not gasto: return RedirectResponse('/gastos', status_code=302)
        abonos   = await db_fetch_all(get_db(request),
            "SELECT * FROM abonos_gasto WHERE gasto_id = ? ORDER BY fecha_registro", [gasto_id])
        abono_p1 = sum(float(a['monto']) for a in abonos if a['persona'] == 'persona1')
        abono_p2 = sum(float(a['monto']) for a in abonos if a['persona'] == 'persona2')
        return t.TemplateResponse('gastos/detalle.html', {
            'request': request, 'user': user, 'cfg': cfg, 'gasto': gasto,
            'abonos': abonos, 'abono_p1': abono_p1, 'abono_p2': abono_p2})

    @app.get('/gastos/{gasto_id}/editar', response_class=HTMLResponse)
    async def gastos_editar_get(request: Request, gasto_id: int, user=Depends(require_user)):
        cfg   = await get_config(get_db(request))
        gasto = await db_fetch_one(get_db(request), "SELECT * FROM gastos WHERE id = ?", [gasto_id])
        if not gasto: return RedirectResponse('/gastos', status_code=302)
        gasto['mes_inicio_str'] = str(gasto['mes_inicio'])[:7]
        return t.TemplateResponse('gastos/form.html', {
            'request': request, 'user': user, 'cfg': cfg,
            'categorias': CATEGORIAS, 'gasto': gasto, 'editando': True})

    @app.post('/gastos/{gasto_id}/editar')
    async def gastos_editar_post(request: Request, gasto_id: int, user=Depends(require_user),
        descripcion: str = Form(...), monto_total: float = Form(...),
        categoria: str = Form(...), pagado_por: str = Form(''),
        mes_inicio: str = Form(...), meses_diferidos: int = Form(1), notas: str = Form('')):
        pagador = pagado_por if pagado_por in ('persona1','persona2') else None
        await db_run(get_db(request), """
            UPDATE gastos SET descripcion=?, monto_total=?, categoria=?, pagado_por=?,
                mes_inicio=?, meses_diferidos=?, notas=? WHERE id=?""",
            [descripcion, monto_total, categoria, pagador,
             mes_inicio + '-01', meses_diferidos, notas, gasto_id])
        return RedirectResponse(f'/gastos/{gasto_id}', status_code=302)

    @app.post('/gastos/{gasto_id}/eliminar')
    async def gastos_eliminar(request: Request, gasto_id: int, user=Depends(require_user)):
        await db_run(get_db(request), "DELETE FROM gastos WHERE id = ?", [gasto_id])
        return RedirectResponse('/gastos', status_code=302)

    @app.post('/gastos/{gasto_id}/abonos/nuevo')
    async def abono_nuevo(request: Request, gasto_id: int, user=Depends(require_user),
        persona: str = Form(...), monto: float = Form(...), notas: str = Form('')):
        await db_run(get_db(request),
            "INSERT INTO abonos_gasto (gasto_id, persona, monto, notas, creado_por) VALUES (?, ?, ?, ?, ?)",
            [gasto_id, persona, monto, notas, user['id']])
        return RedirectResponse(f'/gastos/{gasto_id}', status_code=302)

    @app.post('/gastos/{gasto_id}/abonos/{abono_id}/eliminar')
    async def abono_eliminar(request: Request, gasto_id: int, abono_id: int, user=Depends(require_user)):
        await db_run(get_db(request),
            "DELETE FROM abonos_gasto WHERE id = ? AND gasto_id = ?", [abono_id, gasto_id])
        return RedirectResponse(f'/gastos/{gasto_id}', status_code=302)

    # ── Pagos Extra ────────────────────────────────────────────────────────────

    @app.get('/pagos-extra', response_class=HTMLResponse)
    async def pe_lista(request: Request, user=Depends(require_user)):
        cfg = await get_config(get_db(request))
        pagos = await db_fetch_all(get_db(request),
            "SELECT * FROM pagos_extra ORDER BY mes DESC, fecha_registro DESC")
        return t.TemplateResponse('pagos_extra/lista.html', {
            'request': request, 'user': user, 'cfg': cfg, 'pagos': pagos})

    @app.get('/pagos-extra/nuevo', response_class=HTMLResponse)
    async def pe_nuevo_get(request: Request, user=Depends(require_user)):
        cfg = await get_config(get_db(request))
        return t.TemplateResponse('pagos_extra/form.html', {
            'request': request, 'user': user, 'cfg': cfg, 'pago': None, 'editando': False})

    @app.post('/pagos-extra/nuevo')
    async def pe_nuevo_post(request: Request, user=Depends(require_user),
        descripcion: str = Form(...), monto: float = Form(...),
        pagado_por: str = Form(...), recibido_por: str = Form(...),
        mes: str = Form(...), notas: str = Form('')):
        await db_run(get_db(request),
            "INSERT INTO pagos_extra (descripcion, monto, pagado_por, recibido_por, mes, notas, creado_por) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [descripcion, monto, pagado_por, recibido_por, mes + '-01', notas, user['id']])
        return RedirectResponse('/pagos-extra', status_code=302)

    @app.get('/pagos-extra/{pago_id}/editar', response_class=HTMLResponse)
    async def pe_editar_get(request: Request, pago_id: int, user=Depends(require_user)):
        cfg  = await get_config(get_db(request))
        pago = await db_fetch_one(get_db(request), "SELECT * FROM pagos_extra WHERE id = ?", [pago_id])
        if not pago: return RedirectResponse('/pagos-extra', status_code=302)
        pago['mes_str'] = str(pago['mes'])[:7]
        return t.TemplateResponse('pagos_extra/form.html', {
            'request': request, 'user': user, 'cfg': cfg, 'pago': pago, 'editando': True})

    @app.post('/pagos-extra/{pago_id}/editar')
    async def pe_editar_post(request: Request, pago_id: int, user=Depends(require_user),
        descripcion: str = Form(...), monto: float = Form(...),
        pagado_por: str = Form(...), recibido_por: str = Form(...),
        mes: str = Form(...), notas: str = Form('')):
        await db_run(get_db(request),
            "UPDATE pagos_extra SET descripcion=?, monto=?, pagado_por=?, recibido_por=?, mes=?, notas=? WHERE id=?",
            [descripcion, monto, pagado_por, recibido_por, mes + '-01', notas, pago_id])
        return RedirectResponse('/pagos-extra', status_code=302)

    @app.post('/pagos-extra/{pago_id}/eliminar')
    async def pe_eliminar(request: Request, pago_id: int, user=Depends(require_user)):
        await db_run(get_db(request), "DELETE FROM pagos_extra WHERE id = ?", [pago_id])
        return RedirectResponse('/pagos-extra', status_code=302)

    # ── Descargas ──────────────────────────────────────────────────────────────

    @app.get('/descargas', response_class=HTMLResponse)
    async def descargas(request: Request, user=Depends(require_user)):
        cfg = await get_config(get_db(request))
        hoy = date.today()
        return t.TemplateResponse('descargas/index.html', {
            'request': request, 'user': user, 'cfg': cfg,
            'meses': meses_disponibles(), 'year_sel': hoy.year, 'month_sel': hoy.month})

    # ── Admin ──────────────────────────────────────────────────────────────────

    @app.get('/admin/usuarios', response_class=HTMLResponse)
    async def admin_usuarios(request: Request, user=Depends(require_admin)):
        cfg   = await get_config(get_db(request))
        lista = await db_fetch_all(get_db(request),
            "SELECT id, nombre, username, rol, persona, activo, fecha_creacion FROM usuarios ORDER BY fecha_creacion")
        return t.TemplateResponse('admin/usuarios.html', {
            'request': request, 'user': user, 'cfg': cfg, 'usuarios': lista})

    @app.get('/admin/usuarios/nuevo', response_class=HTMLResponse)
    async def admin_nuevo_get(request: Request, user=Depends(require_admin)):
        cfg = await get_config(get_db(request))
        return t.TemplateResponse('admin/form_usuario.html', {
            'request': request, 'user': user, 'cfg': cfg, 'usuario': None, 'editando': False})

    @app.post('/admin/usuarios/nuevo')
    async def admin_nuevo_post(request: Request, user=Depends(require_admin),
        nombre: str = Form(...), username: str = Form(...), password: str = Form(...),
        rol: str = Form('usuario'), persona: str = Form('')):
        persona_val = persona if persona in ('persona1','persona2') else None
        try:
            await db_run(get_db(request),
                "INSERT INTO usuarios (nombre, username, password_hash, rol, persona) VALUES (?, ?, ?, ?, ?)",
                [nombre, username.lower(), hash_password(password), rol, persona_val])
        except Exception:
            cfg = await get_config(get_db(request))
            return t.TemplateResponse('admin/form_usuario.html', {
                'request': request, 'user': user, 'cfg': cfg,
                'usuario': None, 'editando': False, 'error': 'El usuario ya existe.'})
        return RedirectResponse('/admin/usuarios', status_code=302)

    @app.get('/admin/usuarios/{uid}/editar', response_class=HTMLResponse)
    async def admin_editar_get(request: Request, uid: int, user=Depends(require_admin)):
        cfg     = await get_config(get_db(request))
        usuario = await db_fetch_one(get_db(request),
            "SELECT id, nombre, username, rol, persona, activo FROM usuarios WHERE id = ?", [uid])
        if not usuario: return RedirectResponse('/admin/usuarios', status_code=302)
        return t.TemplateResponse('admin/form_usuario.html', {
            'request': request, 'user': user, 'cfg': cfg, 'usuario': usuario, 'editando': True})

    @app.post('/admin/usuarios/{uid}/editar')
    async def admin_editar_post(request: Request, uid: int, user=Depends(require_admin),
        nombre: str = Form(...), username: str = Form(...), password: str = Form(''),
        rol: str = Form('usuario'), persona: str = Form(''), activo: str = Form('')):
        persona_val = persona if persona in ('persona1','persona2') else None
        activo_val  = 1 if activo else 0
        if password:
            await db_run(get_db(request),
                "UPDATE usuarios SET nombre=?, username=?, rol=?, persona=?, activo=?, password_hash=? WHERE id=?",
                [nombre, username.lower(), rol, persona_val, activo_val, hash_password(password), uid])
        else:
            await db_run(get_db(request),
                "UPDATE usuarios SET nombre=?, username=?, rol=?, persona=?, activo=? WHERE id=?",
                [nombre, username.lower(), rol, persona_val, activo_val, uid])
        return RedirectResponse('/admin/usuarios', status_code=302)

    @app.post('/admin/usuarios/{uid}/eliminar')
    async def admin_eliminar(request: Request, uid: int, user=Depends(require_admin)):
        if uid != user['id']:
            await db_run(get_db(request), "DELETE FROM usuarios WHERE id = ?", [uid])
        return RedirectResponse('/admin/usuarios', status_code=302)

    @app.get('/admin/configuracion', response_class=HTMLResponse)
    async def admin_config_get(request: Request, user=Depends(require_admin)):
        cfg = await get_config(get_db(request))
        return t.TemplateResponse('admin/configuracion.html', {
            'request': request, 'user': user, 'cfg': cfg})

    @app.post('/admin/configuracion')
    async def admin_config_post(request: Request, user=Depends(require_admin),
        nombre_persona1: str = Form(...), nombre_persona2: str = Form(...)):
        await db_run(get_db(request),
            "UPDATE configuracion SET nombre_persona1=?, nombre_persona2=? WHERE id=1",
            [nombre_persona1, nombre_persona2])
        return RedirectResponse('/admin/configuracion', status_code=302)

    # ── Setup ──────────────────────────────────────────────────────────────────

    @app.get('/setup/crear-admin', response_class=HTMLResponse)
    async def setup_get(request: Request):
        count = await db_fetch_one(get_db(request), "SELECT COUNT(*) as n FROM usuarios")
        if count and count['n'] > 0:
            return RedirectResponse('/login', status_code=302)
        return t.TemplateResponse('setup/crear_admin.html', {'request': request})

    @app.post('/setup/crear-admin')
    async def setup_post(request: Request,
        nombre: str = Form(...), username: str = Form(...), password: str = Form(...)):
        count = await db_fetch_one(get_db(request), "SELECT COUNT(*) as n FROM usuarios")
        if count and count['n'] > 0:
            return RedirectResponse('/login', status_code=302)
        await db_run(get_db(request),
            "INSERT INTO usuarios (nombre, username, password_hash, rol, activo) VALUES (?, ?, ?, 'admin', 1)",
            [nombre, username.lower(), hash_password(password)])
        return RedirectResponse('/login', status_code=302)

    return _app, _templates


# ── Entry point de Cloudflare Workers ─────────────────────────────────────────

class Default(WorkerEntrypoint):
    async def fetch(self, request):
        app, _ = get_app()
        return await asgi.fetch(app, request, self.env)


async def on_fetch(request, env):
    app, _ = get_app()
    return await asgi.fetch(app, request, env)

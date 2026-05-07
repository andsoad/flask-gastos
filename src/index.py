"""
Gastos Pareja — FastAPI para Cloudflare Workers + D1
"""
from fastapi import FastAPI, Request, Depends, HTTPException, status, Form, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from datetime import date
import json

from src.auth_utils import verify_password, hash_password, create_access_token, decode_token
from src.db import db_fetch_all, db_fetch_one, db_run, get_config
from src.balance import calcular_balance_mes, calcular_balance_acumulado, primer_dia_mes

app = FastAPI()
templates = Jinja2Templates(directory="templates")

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


# ── Auth helpers ───────────────────────────────────────────────────────────────

def get_db(request: Request):
    return request.scope['env'].DB


def get_secret(request: Request) -> str:
    return request.scope['env'].SECRET_KEY


async def get_current_user(request: Request, token: Optional[str] = Cookie(None)):
    db     = get_db(request)
    secret = get_secret(request)
    if not token:
        return None
    payload = decode_token(token, secret)
    if not payload:
        return None
    user = await db_fetch_one(db,
        "SELECT id, nombre, username, rol, persona, activo FROM usuarios WHERE id = ?",
        [payload.get('sub')]
    )
    if not user or not user['activo']:
        return None
    return user


async def require_user(request: Request, token: Optional[str] = Cookie(None)):
    user = await get_current_user(request, token)
    if not user:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    return user


async def require_admin(request: Request, token: Optional[str] = Cookie(None)):
    user = await require_user(request, token)
    if user['rol'] != 'admin':
        raise HTTPException(status_code=403, detail="Se requieren permisos de administrador")
    return user


def meses_disponibles():
    inicio = date(2024, 12, 1)
    hoy    = date.today().replace(day=1)
    meses  = []
    y, m   = inicio.year, inicio.month
    while date(y, m, 1) <= hoy:
        meses.append({'year': y, 'month': m, 'label': date(y, m, 1).strftime('%B %Y')})
        if m == 12:
            y, m = y + 1, 1
        else:
            m += 1
    return meses


# ── Auth routes ────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, token: Optional[str] = Cookie(None)):
    user = await get_current_user(request, token)
    if user:
        return RedirectResponse("/dashboard", status_code=302)
    return RedirectResponse("/login", status_code=302)


@app.get("/login", response_class=HTMLResponse)
async def login_get(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login")
async def login_post(request: Request,
                     username: str = Form(...),
                     password: str = Form(...)):
    db     = get_db(request)
    secret = get_secret(request)
    user   = await db_fetch_one(db,
        "SELECT * FROM usuarios WHERE username = ? AND activo = 1", [username.lower()])
    if not user or not verify_password(password, user['password_hash']):
        return templates.TemplateResponse("login.html", {
            "request": request, "error": "Usuario o contraseña incorrectos"
        })
    token    = create_access_token({"sub": user['id']}, secret)
    response = RedirectResponse("/dashboard", status_code=302)
    response.set_cookie("token", token, httponly=True, samesite="lax")
    return response


@app.get("/logout")
async def logout():
    response = RedirectResponse("/login", status_code=302)
    response.delete_cookie("token")
    return response


# ── Dashboard ──────────────────────────────────────────────────────────────────

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, user=Depends(require_user)):
    db  = get_db(request)
    hoy = date.today()
    cfg = await get_config(db)
    balance_mes = await calcular_balance_mes(db, hoy.year, hoy.month)
    acumulado   = await calcular_balance_acumulado(db, hoy.year, hoy.month)
    return templates.TemplateResponse("dashboard.html", {
        "request": request, "user": user, "cfg": cfg,
        "balance_mes": balance_mes, "acumulado": acumulado,
        "mes_actual": hoy.strftime('%B %Y'),
        "year": hoy.year, "month": hoy.month,
    })


# ── Reporte ────────────────────────────────────────────────────────────────────

@app.get("/reporte", response_class=HTMLResponse)
async def reporte(request: Request, year: int = None, month: int = None,
                  user=Depends(require_user)):
    db  = get_db(request)
    hoy = date.today()
    year  = year  or hoy.year
    month = month or hoy.month
    cfg         = await get_config(db)
    balance_mes = await calcular_balance_mes(db, year, month)
    acumulado   = await calcular_balance_acumulado(db, year, month)
    mes_label   = date(year, month, 1).strftime('%B %Y')
    return templates.TemplateResponse("reporte.html", {
        "request": request, "user": user, "cfg": cfg,
        "balance_mes": balance_mes, "acumulado": acumulado,
        "mes_label": mes_label, "year": year, "month": month,
        "meses_disponibles": meses_disponibles(),
    })


# ── Gastos ─────────────────────────────────────────────────────────────────────

@app.get("/gastos", response_class=HTMLResponse)
async def gastos_lista(request: Request, user=Depends(require_user)):
    db  = get_db(request)
    cfg = await get_config(db)
    gastos = await db_fetch_all(db, """
        SELECT g.*, u.nombre AS registrado_por_nombre,
               COALESCE(SUM(a.monto), 0) AS total_abonado
        FROM gastos g
        JOIN usuarios u ON g.creado_por = u.id
        LEFT JOIN abonos_gasto a ON a.gasto_id = g.id
        GROUP BY g.id
        ORDER BY g.mes_inicio DESC, g.fecha_registro DESC
    """)
    return templates.TemplateResponse("gastos/lista.html", {
        "request": request, "user": user, "cfg": cfg,
        "gastos": gastos, "categorias": CATEGORIAS,
    })


@app.get("/gastos/nuevo", response_class=HTMLResponse)
async def gastos_nuevo_get(request: Request, user=Depends(require_user)):
    db  = get_db(request)
    cfg = await get_config(db)
    return templates.TemplateResponse("gastos/form.html", {
        "request": request, "user": user, "cfg": cfg,
        "categorias": CATEGORIAS, "gasto": None,
    })


@app.post("/gastos/nuevo")
async def gastos_nuevo_post(request: Request, user=Depends(require_user),
    descripcion: str = Form(...), monto_total: float = Form(...),
    categoria: str = Form(...), pagado_por: str = Form(""),
    mes_inicio: str = Form(...), meses_diferidos: int = Form(1),
    notas: str = Form("")):
    db = get_db(request)
    pagador = pagado_por if pagado_por in ('persona1','persona2') else None
    mes     = mes_inicio + "-01"
    result  = await db_run(db, """
        INSERT INTO gastos (descripcion, monto_total, categoria, pagado_por,
                            mes_inicio, meses_diferidos, notas, creado_por)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, [descripcion, monto_total, categoria, pagador, mes, meses_diferidos, notas, user['id']])
    return RedirectResponse(f"/gastos/{result['last_row_id']}", status_code=302)


@app.get("/gastos/{gasto_id}", response_class=HTMLResponse)
async def gastos_detalle(request: Request, gasto_id: int, user=Depends(require_user)):
    db    = get_db(request)
    cfg   = await get_config(db)
    gasto = await db_fetch_one(db, "SELECT * FROM gastos WHERE id = ?", [gasto_id])
    if not gasto:
        return RedirectResponse("/gastos", status_code=302)
    abonos   = await db_fetch_all(db,
        "SELECT * FROM abonos_gasto WHERE gasto_id = ? ORDER BY fecha_registro", [gasto_id])
    abono_p1 = sum(float(a['monto']) for a in abonos if a['persona'] == 'persona1')
    abono_p2 = sum(float(a['monto']) for a in abonos if a['persona'] == 'persona2')
    return templates.TemplateResponse("gastos/detalle.html", {
        "request": request, "user": user, "cfg": cfg,
        "gasto": gasto, "abonos": abonos,
        "abono_p1": abono_p1, "abono_p2": abono_p2,
    })


@app.get("/gastos/{gasto_id}/editar", response_class=HTMLResponse)
async def gastos_editar_get(request: Request, gasto_id: int, user=Depends(require_user)):
    db    = get_db(request)
    cfg   = await get_config(db)
    gasto = await db_fetch_one(db, "SELECT * FROM gastos WHERE id = ?", [gasto_id])
    if not gasto:
        return RedirectResponse("/gastos", status_code=302)
    gasto['mes_inicio_str'] = gasto['mes_inicio'][:7]
    return templates.TemplateResponse("gastos/form.html", {
        "request": request, "user": user, "cfg": cfg,
        "categorias": CATEGORIAS, "gasto": gasto, "editando": True,
    })


@app.post("/gastos/{gasto_id}/editar")
async def gastos_editar_post(request: Request, gasto_id: int, user=Depends(require_user),
    descripcion: str = Form(...), monto_total: float = Form(...),
    categoria: str = Form(...), pagado_por: str = Form(""),
    mes_inicio: str = Form(...), meses_diferidos: int = Form(1),
    notas: str = Form("")):
    db     = get_db(request)
    pagador = pagado_por if pagado_por in ('persona1','persona2') else None
    mes     = mes_inicio + "-01"
    await db_run(db, """
        UPDATE gastos SET descripcion=?, monto_total=?, categoria=?, pagado_por=?,
            mes_inicio=?, meses_diferidos=?, notas=? WHERE id=?
    """, [descripcion, monto_total, categoria, pagador, mes, meses_diferidos, notas, gasto_id])
    return RedirectResponse(f"/gastos/{gasto_id}", status_code=302)


@app.post("/gastos/{gasto_id}/eliminar")
async def gastos_eliminar(request: Request, gasto_id: int, user=Depends(require_user)):
    db = get_db(request)
    await db_run(db, "DELETE FROM gastos WHERE id = ?", [gasto_id])
    return RedirectResponse("/gastos", status_code=302)


@app.post("/gastos/{gasto_id}/abonos/nuevo")
async def abono_nuevo(request: Request, gasto_id: int, user=Depends(require_user),
    persona: str = Form(...), monto: float = Form(...), notas: str = Form("")):
    db = get_db(request)
    await db_run(db, """
        INSERT INTO abonos_gasto (gasto_id, persona, monto, notas, creado_por)
        VALUES (?, ?, ?, ?, ?)
    """, [gasto_id, persona, monto, notas, user['id']])
    return RedirectResponse(f"/gastos/{gasto_id}", status_code=302)


@app.post("/gastos/{gasto_id}/abonos/{abono_id}/eliminar")
async def abono_eliminar(request: Request, gasto_id: int, abono_id: int,
                         user=Depends(require_user)):
    db = get_db(request)
    await db_run(db, "DELETE FROM abonos_gasto WHERE id = ? AND gasto_id = ?", [abono_id, gasto_id])
    return RedirectResponse(f"/gastos/{gasto_id}", status_code=302)


# ── Pagos extra ────────────────────────────────────────────────────────────────

@app.get("/pagos-extra", response_class=HTMLResponse)
async def pagos_extra_lista(request: Request, user=Depends(require_user)):
    db  = get_db(request)
    cfg = await get_config(db)
    pagos = await db_fetch_all(db, """
        SELECT p.*, u.nombre AS registrado_por_nombre
        FROM pagos_extra p JOIN usuarios u ON p.creado_por = u.id
        ORDER BY p.mes DESC, p.fecha_registro DESC
    """)
    return templates.TemplateResponse("pagos_extra/lista.html", {
        "request": request, "user": user, "cfg": cfg, "pagos": pagos,
    })


@app.get("/pagos-extra/nuevo", response_class=HTMLResponse)
async def pagos_extra_nuevo_get(request: Request, user=Depends(require_user)):
    db  = get_db(request)
    cfg = await get_config(db)
    return templates.TemplateResponse("pagos_extra/form.html", {
        "request": request, "user": user, "cfg": cfg, "pago": None,
    })


@app.post("/pagos-extra/nuevo")
async def pagos_extra_nuevo_post(request: Request, user=Depends(require_user),
    descripcion: str = Form(...), monto: float = Form(...),
    pagado_por: str = Form(...), recibido_por: str = Form(...),
    mes: str = Form(...), notas: str = Form("")):
    db = get_db(request)
    await db_run(db, """
        INSERT INTO pagos_extra (descripcion, monto, pagado_por, recibido_por, mes, notas, creado_por)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, [descripcion, monto, pagado_por, recibido_por, mes + "-01", notas, user['id']])
    return RedirectResponse("/pagos-extra", status_code=302)


@app.get("/pagos-extra/{pago_id}/editar", response_class=HTMLResponse)
async def pagos_extra_editar_get(request: Request, pago_id: int, user=Depends(require_user)):
    db   = get_db(request)
    cfg  = await get_config(db)
    pago = await db_fetch_one(db, "SELECT * FROM pagos_extra WHERE id = ?", [pago_id])
    if not pago:
        return RedirectResponse("/pagos-extra", status_code=302)
    pago['mes_str'] = pago['mes'][:7]
    return templates.TemplateResponse("pagos_extra/form.html", {
        "request": request, "user": user, "cfg": cfg, "pago": pago, "editando": True,
    })


@app.post("/pagos-extra/{pago_id}/editar")
async def pagos_extra_editar_post(request: Request, pago_id: int, user=Depends(require_user),
    descripcion: str = Form(...), monto: float = Form(...),
    pagado_por: str = Form(...), recibido_por: str = Form(...),
    mes: str = Form(...), notas: str = Form("")):
    db = get_db(request)
    await db_run(db, """
        UPDATE pagos_extra SET descripcion=?, monto=?, pagado_por=?,
            recibido_por=?, mes=?, notas=? WHERE id=?
    """, [descripcion, monto, pagado_por, recibido_por, mes + "-01", notas, pago_id])
    return RedirectResponse("/pagos-extra", status_code=302)


@app.post("/pagos-extra/{pago_id}/eliminar")
async def pagos_extra_eliminar(request: Request, pago_id: int, user=Depends(require_user)):
    db = get_db(request)
    await db_run(db, "DELETE FROM pagos_extra WHERE id = ?", [pago_id])
    return RedirectResponse("/pagos-extra", status_code=302)


# ── Descargas ──────────────────────────────────────────────────────────────────

@app.get("/descargas", response_class=HTMLResponse)
async def descargas_index(request: Request, user=Depends(require_user)):
    db  = get_db(request)
    cfg = await get_config(db)
    hoy = date.today()
    return templates.TemplateResponse("descargas/index.html", {
        "request": request, "user": user, "cfg": cfg,
        "meses": meses_disponibles(),
        "year_sel": hoy.year, "month_sel": hoy.month,
    })


# ── Admin ──────────────────────────────────────────────────────────────────────

@app.get("/admin/usuarios", response_class=HTMLResponse)
async def admin_usuarios(request: Request, user=Depends(require_admin)):
    db  = get_db(request)
    cfg = await get_config(db)
    lista = await db_fetch_all(db,
        "SELECT id, nombre, username, rol, persona, activo, fecha_creacion FROM usuarios ORDER BY fecha_creacion")
    return templates.TemplateResponse("admin/usuarios.html", {
        "request": request, "user": user, "cfg": cfg, "usuarios": lista,
    })


@app.get("/admin/usuarios/nuevo", response_class=HTMLResponse)
async def admin_nuevo_usuario_get(request: Request, user=Depends(require_admin)):
    db  = get_db(request)
    cfg = await get_config(db)
    return templates.TemplateResponse("admin/form_usuario.html", {
        "request": request, "user": user, "cfg": cfg, "usuario": None,
    })


@app.post("/admin/usuarios/nuevo")
async def admin_nuevo_usuario_post(request: Request, user=Depends(require_admin),
    nombre: str = Form(...), username: str = Form(...), password: str = Form(...),
    rol: str = Form("usuario"), persona: str = Form("")):
    db      = get_db(request)
    pw_hash = hash_password(password)
    persona_val = persona if persona in ('persona1','persona2') else None
    try:
        await db_run(db, """
            INSERT INTO usuarios (nombre, username, password_hash, rol, persona)
            VALUES (?, ?, ?, ?, ?)
        """, [nombre, username.lower(), pw_hash, rol, persona_val])
    except Exception:
        cfg = await get_config(db)
        return templates.TemplateResponse("admin/form_usuario.html", {
            "request": request, "user": user, "cfg": cfg,
            "usuario": None, "error": "El nombre de usuario ya está en uso.",
        })
    return RedirectResponse("/admin/usuarios", status_code=302)


@app.get("/admin/usuarios/{uid}/editar", response_class=HTMLResponse)
async def admin_editar_usuario_get(request: Request, uid: int, user=Depends(require_admin)):
    db      = get_db(request)
    cfg     = await get_config(db)
    usuario = await db_fetch_one(db,
        "SELECT id, nombre, username, rol, persona, activo FROM usuarios WHERE id = ?", [uid])
    if not usuario:
        return RedirectResponse("/admin/usuarios", status_code=302)
    return templates.TemplateResponse("admin/form_usuario.html", {
        "request": request, "user": user, "cfg": cfg,
        "usuario": usuario, "editando": True,
    })


@app.post("/admin/usuarios/{uid}/editar")
async def admin_editar_usuario_post(request: Request, uid: int, user=Depends(require_admin),
    nombre: str = Form(...), username: str = Form(...), password: str = Form(""),
    rol: str = Form("usuario"), persona: str = Form(""), activo: str = Form("")):
    db          = get_db(request)
    persona_val = persona if persona in ('persona1','persona2') else None
    activo_val  = 1 if activo else 0
    if password:
        pw_hash = hash_password(password)
        await db_run(db, """
            UPDATE usuarios SET nombre=?, username=?, rol=?, persona=?, activo=?, password_hash=?
            WHERE id=?
        """, [nombre, username.lower(), rol, persona_val, activo_val, pw_hash, uid])
    else:
        await db_run(db, """
            UPDATE usuarios SET nombre=?, username=?, rol=?, persona=?, activo=? WHERE id=?
        """, [nombre, username.lower(), rol, persona_val, activo_val, uid])
    return RedirectResponse("/admin/usuarios", status_code=302)


@app.post("/admin/usuarios/{uid}/eliminar")
async def admin_eliminar_usuario(request: Request, uid: int, user=Depends(require_admin)):
    if uid == user['id']:
        return RedirectResponse("/admin/usuarios", status_code=302)
    db = get_db(request)
    await db_run(db, "DELETE FROM usuarios WHERE id = ?", [uid])
    return RedirectResponse("/admin/usuarios", status_code=302)


@app.get("/admin/configuracion", response_class=HTMLResponse)
async def admin_config_get(request: Request, user=Depends(require_admin)):
    db  = get_db(request)
    cfg = await get_config(db)
    return templates.TemplateResponse("admin/configuracion.html", {
        "request": request, "user": user, "cfg": cfg,
    })


@app.post("/admin/configuracion")
async def admin_config_post(request: Request, user=Depends(require_admin),
    nombre_persona1: str = Form(...), nombre_persona2: str = Form(...)):
    db = get_db(request)
    await db_run(db,
        "UPDATE configuracion SET nombre_persona1=?, nombre_persona2=? WHERE id=1",
        [nombre_persona1, nombre_persona2])
    return RedirectResponse("/admin/configuracion", status_code=302)


# ── Script crear admin (solo en desarrollo) ────────────────────────────────────

@app.get("/setup/crear-admin", response_class=HTMLResponse)
async def setup_crear_admin_get(request: Request):
    db    = get_db(request)
    count = await db_fetch_one(db, "SELECT COUNT(*) as n FROM usuarios")
    if count and count['n'] > 0:
        raise HTTPException(status_code=403, detail="Ya existen usuarios. Ruta deshabilitada.")
    return templates.TemplateResponse("setup/crear_admin.html", {"request": request})


@app.post("/setup/crear-admin")
async def setup_crear_admin_post(request: Request,
    nombre: str = Form(...), username: str = Form(...), password: str = Form(...)):
    db    = get_db(request)
    count = await db_fetch_one(db, "SELECT COUNT(*) as n FROM usuarios")
    if count and count['n'] > 0:
        raise HTTPException(status_code=403, detail="Ya existen usuarios.")
    pw_hash = hash_password(password)
    await db_run(db, """
        INSERT INTO usuarios (nombre, username, password_hash, rol, activo)
        VALUES (?, ?, ?, 'admin', 1)
    """, [nombre, username.lower(), pw_hash])
    return RedirectResponse("/login", status_code=302)

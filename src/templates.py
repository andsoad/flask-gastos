"""
Generación de HTML con Python puro (f-strings).
Sin Jinja2 ni ninguna dependencia externa.
"""

CATEGORIAS_DICT = {
    'super': '🛒 Súper/Comida', 'restaurantes': '🍽️ Restaurantes',
    'transporte': '🚗 Transporte', 'servicios': '💡 Servicios',
    'entretenimiento': '🎉 Entretenimiento', 'salud': '🏥 Salud',
    'viajes': '✈️ Viajes', 'ropa': '👗 Ropa', 'mascotas': '🐾 Mascotas',
    'casa': '🏠 Casa', 'bebe': '👶 Bebé', 'otros': '📦 Otros',
}

def esc(s):
    if s is None: return ''
    return str(s).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('"','&quot;')

def fmt(n):
    try: return f'${float(n):,.2f}'
    except: return '$0.00'

def persona_nombre(p, cfg):
    if p == 'persona1': return cfg['nombre_persona1']
    if p == 'persona2': return cfg['nombre_persona2']
    return '—'

# ── Layout base ────────────────────────────────────────────────────────────────

def base(title, content, user=None, cfg=None):
    nav = ''
    if user and cfg:
        admin_link = '<a href="/admin/usuarios">Admin</a>' if user.get('rol') == 'admin' else ''
        nav = f"""
        <nav class="navbar">
          <div class="nav-brand">💑 Gastos Pareja</div>
          <div class="nav-links">
            <a href="/dashboard">Inicio</a>
            <a href="/gastos">Gastos</a>
            <a href="/pagos-extra">Pagos Extra</a>
            <a href="/reporte">Reportes</a>
            <a href="/descargas">Descargas</a>
            {admin_link}
          </div>
          <div class="nav-user">
            <span>{esc(user.get('nombre',''))}</span>
            <a href="/logout" class="btn-logout">Salir</a>
          </div>
        </nav>"""
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{esc(title)} — Gastos Pareja</title>
  <link rel="stylesheet" href="/css/style.css">
</head>
<body>
{nav}
<main class="container">
{content}
</main>
<script src="/js/main.js"></script>
</body>
</html>"""

def alert(msg, cat='info'):
    return f'<div class="alert alert-{cat}">{esc(msg)}</div>' if msg else ''

def balance_cards(bal, cfg, mes_label=''):
    n1, n2 = cfg['nombre_persona1'], cfg['nombre_persona2']
    def sub(b, n):
        if b > 0: return f'<div class="stat-sub positive">Pagó {fmt(b)} de más</div>'
        if b < 0: return f'<div class="stat-sub negative">Debe {fmt(abs(b))}</div>'
        return '<div class="stat-sub">Balanceado ✓</div>'
    deuda_html = ''
    if bal.get('deuda'):
        d = bal['deuda']
        deuda_html = f'<div class="deuda-banner">💸 <strong>{esc(persona_nombre(d["deudor"],cfg))} le debe {fmt(d["monto"])} a {esc(persona_nombre(d["acreedor"],cfg))}</strong>{" este mes" if mes_label else ""}</div>'
    return f"""
    <div class="cards-grid">
      <div class="card card-stat"><div class="stat-label">Total gastado</div><div class="stat-value">{fmt(bal['total_gastado'])}</div></div>
      <div class="card card-stat"><div class="stat-label">Le toca a cada quien</div><div class="stat-value">{fmt(bal['mitad_total'])}</div></div>
      <div class="card card-stat"><div class="stat-label">{esc(n1)} pagó</div><div class="stat-value">{fmt(bal['total_p1'])}</div>{sub(bal['balance_p1'],n1)}</div>
      <div class="card card-stat"><div class="stat-label">{esc(n2)} pagó</div><div class="stat-value">{fmt(bal['total_p2'])}</div>{sub(bal['balance_p2'],n2)}</div>
    </div>
    {deuda_html}"""

# ── Login ──────────────────────────────────────────────────────────────────────

def login(error=None):
    err = f'<div class="alert alert-danger">{esc(error)}</div>' if error else ''
    return f"""<!DOCTYPE html>
<html lang="es"><head>
  <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Iniciar sesión — Gastos Pareja</title>
  <link rel="stylesheet" href="/css/style.css">
</head><body class="login-body">
  <div class="login-card">
    <div class="login-header"><div class="login-icon">💑</div><h1>Gastos Pareja</h1><p>Inicia sesión para continuar</p></div>
    {err}
    <form method="POST" action="/login">
      <div class="form-group"><label>Usuario</label><input type="text" name="username" required autofocus placeholder="tu_usuario"></div>
      <div class="form-group"><label>Contraseña</label><input type="password" name="password" required placeholder="••••••••"></div>
      <button type="submit" class="btn btn-primary btn-full">Entrar</button>
    </form>
  </div>
</body></html>"""

# ── Dashboard ──────────────────────────────────────────────────────────────────

def dashboard(user, cfg, balance_mes, acumulado, mes_actual, year, month):
    n1, n2 = cfg['nombre_persona1'], cfg['nombre_persona2']
    def acum_sub(b):
        if b > 0: return f'<div class="stat-sub positive">+{fmt(b)}</div>'
        if b < 0: return f'<div class="stat-sub negative">-{fmt(abs(b))}</div>'
        return '<div class="stat-sub">Balanceado ✓</div>'
    gastos_rows = ''
    for g in balance_mes.get('gastos', []):
        gastos_rows += f"""<tr>
          <td>{esc(g['descripcion'])}</td>
          <td><span class="badge badge-cat">{esc(CATEGORIAS_DICT.get(g['categoria'], g['categoria']))}</span></td>
          <td>{esc(persona_nombre(g['pagado_por'], cfg)) if not g['tiene_abonos'] else '<span class="badge badge-abono">Abonos</span>'}</td>
          <td>{fmt(g['monto_total'])}</td><td>{fmt(g['cuota_mes'])}</td><td>{g['meses_diferidos']}</td>
        </tr>"""
    gastos_table = f"""<h3 class="section-title" style="margin-top:2rem">Gastos en este mes</h3>
    <div class="table-wrap"><table class="table">
      <thead><tr><th>Descripción</th><th>Categoría</th><th>Pagó</th><th>Total</th><th>Cuota mes</th><th>Meses</th></tr></thead>
      <tbody>{gastos_rows}</tbody></table></div>""" if balance_mes.get('gastos') else ''

    content = f"""
    <div class="page-header"><h2>Resumen — {esc(mes_actual)}</h2><a href="/gastos/nuevo" class="btn btn-primary">+ Agregar gasto</a></div>
    <h3 class="section-title">Este mes</h3>
    {balance_cards(balance_mes, cfg, mes_label=True)}
    <h3 class="section-title" style="margin-top:2rem">Acumulado (desde dic 2024)</h3>
    <div class="cards-grid">
      <div class="card card-stat"><div class="stat-label">Total acumulado</div><div class="stat-value">{fmt(acumulado['acum_total'])}</div></div>
      <div class="card card-stat"><div class="stat-label">{esc(n1)}</div><div class="stat-value">{fmt(acumulado['acum_p1'])}</div>{acum_sub(acumulado['bal_acum_p1'])}</div>
      <div class="card card-stat"><div class="stat-label">{esc(n2)}</div><div class="stat-value">{fmt(acumulado['acum_p2'])}</div>{acum_sub(acumulado['bal_acum_p2'])}</div>
    </div>
    {gastos_table}
    <div class="quick-links">
      <a href="/reporte?year={year}&month={month}" class="btn btn-secondary">Ver reporte completo →</a>
      <a href="/pagos-extra/nuevo" class="btn btn-secondary">+ Pago extra</a>
    </div>"""
    return base(f'Inicio', content, user, cfg)

# ── Gastos lista ───────────────────────────────────────────────────────────────

def gastos_lista(user, cfg, gastos):
    rows = ''
    for g in gastos:
        pagador = persona_nombre(g.get('pagado_por'), cfg) if g.get('pagado_por') else '<span class="badge badge-abono">Abonos</span>'
        rows += f"""<tr>
          <td><a href="/gastos/{g['id']}" class="link-detalle">{esc(g['descripcion'])}</a></td>
          <td><span class="badge badge-cat">{esc(CATEGORIAS_DICT.get(g['categoria'], g['categoria']))}</span></td>
          <td>{pagador}</td>
          <td>{fmt(g['monto_total'])}</td>
          <td>{fmt(float(g['monto_total']) / g['meses_diferidos'])}</td>
          <td>{esc(str(g['mes_inicio'])[:7])}</td>
          <td>{g['meses_diferidos']}</td>
          <td class="text-muted">{esc(str(g['fecha_registro'])[:10])}</td>
          <td class="actions">
            <a href="/gastos/{g['id']}" class="btn-sm btn-edit">Ver</a>
            <a href="/gastos/{g['id']}/editar" class="btn-sm btn-edit">Editar</a>
            <form method="POST" action="/gastos/{g['id']}/eliminar" style="display:inline" onsubmit="return confirm('¿Eliminar?')">
              <button type="submit" class="btn-sm btn-delete">Eliminar</button>
            </form>
          </td></tr>"""
    empty = '<div class="empty-state"><p>No hay gastos.</p><a href="/gastos/nuevo" class="btn btn-primary">Agregar el primero</a></div>'
    table = f'<div class="table-wrap"><table class="table"><thead><tr><th>Descripción</th><th>Categoría</th><th>Pagó</th><th>Monto total</th><th>Cuota/mes</th><th>Mes inicio</th><th>Meses</th><th>Registrado</th><th>Acciones</th></tr></thead><tbody>{rows}</tbody></table></div>'
    content = f'<div class="page-header"><h2>Todos los gastos</h2><a href="/gastos/nuevo" class="btn btn-primary">+ Nuevo gasto</a></div>{table if gastos else empty}'
    return base('Gastos', content, user, cfg)

# ── Gastos form ────────────────────────────────────────────────────────────────

def gastos_form(user, cfg, categorias, gasto=None, editando=False, error=None):
    action = f'/gastos/{gasto["id"]}/editar' if editando else '/gastos/nuevo'
    title  = 'Editar gasto' if editando else 'Nuevo gasto'
    d = gasto or {}
    mes_val = str(d.get('mes_inicio',''))[:7] if editando else d.get('mes_inicio','')
    cat_opts = ''.join(f'<option value="{v}" {"selected" if d.get("categoria")==v else ""}>{esc(l)}</option>' for v,l in categorias)
    pag_opts = f'''<option value="">— Sin pagador (usar abonos) —</option>
      <option value="persona1" {"selected" if d.get("pagado_por")=="persona1" else ""}>{esc(cfg["nombre_persona1"])}</option>
      <option value="persona2" {"selected" if d.get("pagado_por")=="persona2" else ""}>{esc(cfg["nombre_persona2"])}</option>'''
    err_html = f'<div class="alert alert-danger">{esc(error)}</div>' if error else ''
    content = f"""
    <div class="page-header"><h2>{title}</h2><a href="/gastos" class="btn btn-secondary">← Volver</a></div>
    {err_html}
    <div class="form-card">
      <form method="POST" action="{action}">
        <div class="form-row">
          <div class="form-group"><label>Descripción *</label><input type="text" name="descripcion" required value="{esc(d.get('descripcion',''))}"></div>
          <div class="form-group"><label>Monto total *</label><input type="number" name="monto_total" step="0.01" min="0.01" required value="{esc(d.get('monto_total',''))}"></div>
        </div>
        <div class="form-row">
          <div class="form-group"><label>Categoría *</label><select name="categoria" required><option value="">— Selecciona —</option>{cat_opts}</select></div>
          <div class="form-group"><label>¿Quién pagó?</label><select name="pagado_por">{pag_opts}</select></div>
        </div>
        <div class="form-row">
          <div class="form-group"><label>Mes de inicio *</label><input type="month" name="mes_inicio" required value="{esc(mes_val)}" min="2024-12"></div>
          <div class="form-group"><label>Meses diferidos</label><input type="number" name="meses_diferidos" min="1" max="60" required value="{esc(d.get('meses_diferidos',1))}"></div>
        </div>
        <div class="form-group"><label>Notas</label><textarea name="notas" rows="2">{esc(d.get('notas',''))}</textarea></div>
        <div class="form-actions">
          <button type="submit" class="btn btn-primary">{'Guardar cambios' if editando else 'Agregar gasto'}</button>
          <a href="/gastos" class="btn btn-secondary">Cancelar</a>
        </div>
      </form>
    </div>"""
    return base(title, content, user, cfg)

# ── Gastos detalle ─────────────────────────────────────────────────────────────

def gastos_detalle(user, cfg, gasto, abonos, abono_p1, abono_p2):
    n1, n2 = cfg['nombre_persona1'], cfg['nombre_persona2']
    cuota = float(gasto['monto_total']) / gasto['meses_diferidos']
    mitad = cuota / 2
    def abono_sub(ab, n):
        if ab <= 0: return '<div class="stat-sub text-muted">Sin abonos</div>'
        diff = ab - mitad
        if diff > 0: return f'<div class="stat-sub positive">Pagó {fmt(diff)} de más</div>'
        if diff < 0: return f'<div class="stat-sub negative">Falta {fmt(abs(diff))}</div>'
        return '<div class="stat-sub positive">Exacto ✓</div>'
    pagador_html = persona_nombre(gasto.get('pagado_por'), cfg) if gasto.get('pagado_por') else '<span class="text-muted">Con abonos</span>'
    abono_rows = ''
    for a in abonos:
        abono_rows += f"""<tr>
          <td>{esc(persona_nombre(a['persona'], cfg))}</td>
          <td>{fmt(a['monto'])}</td>
          <td class="text-muted">{esc(a.get('notas') or '—')}</td>
          <td class="text-muted">{esc(str(a['fecha_registro'])[:10])}</td>
          <td><form method="POST" action="/gastos/{gasto['id']}/abonos/{a['id']}/eliminar" onsubmit="return confirm('¿Eliminar?')">
            <button type="submit" class="btn-sm btn-delete">Eliminar</button></form></td></tr>"""
    abono_table = f'<div class="table-wrap" style="margin-bottom:1.5rem"><table class="table"><thead><tr><th>Persona</th><th>Monto</th><th>Notas</th><th>Fecha</th><th></th></tr></thead><tbody>{abono_rows}</tbody></table></div>' if abonos else '<p class="text-muted" style="margin-bottom:1.5rem">No hay abonos.</p>'
    p1_opts = f'<option value="persona1">{esc(n1)}</option><option value="persona2">{esc(n2)}</option>'
    content = f"""
    <div class="page-header"><h2>{esc(gasto['descripcion'])}</h2>
      <div style="display:flex;gap:.5rem">
        <a href="/gastos/{gasto['id']}/editar" class="btn btn-secondary">✏️ Editar</a>
        <a href="/gastos" class="btn btn-secondary">← Volver</a>
      </div>
    </div>
    <div class="cards-grid" style="grid-template-columns:repeat(auto-fit,minmax(160px,1fr));margin-bottom:1.5rem">
      <div class="card card-stat"><div class="stat-label">Monto total</div><div class="stat-value">{fmt(gasto['monto_total'])}</div></div>
      <div class="card card-stat"><div class="stat-label">Cuota mensual</div><div class="stat-value">{fmt(cuota)}</div>{'<div class="stat-sub">' + str(gasto["meses_diferidos"]) + ' meses</div>' if gasto["meses_diferidos"]>1 else ''}</div>
      <div class="card card-stat"><div class="stat-label">Categoría</div><div class="stat-value" style="font-size:1rem">{esc(CATEGORIAS_DICT.get(gasto['categoria'], gasto['categoria']))}</div></div>
      <div class="card card-stat"><div class="stat-label">Mes inicio</div><div class="stat-value" style="font-size:1rem">{esc(str(gasto['mes_inicio'])[:7])}</div></div>
      <div class="card card-stat"><div class="stat-label">Pagador</div><div class="stat-value" style="font-size:1rem">{pagador_html}</div></div>
    </div>
    <h3 class="section-title">Abonos al gasto</h3>
    <div class="cards-grid" style="grid-template-columns:repeat(3,1fr);margin-bottom:1rem">
      <div class="card card-stat"><div class="stat-label">{esc(n1)} aportó</div><div class="stat-value">{fmt(abono_p1)}</div>{abono_sub(abono_p1, n1)}</div>
      <div class="card card-stat"><div class="stat-label">{esc(n2)} aportó</div><div class="stat-value">{fmt(abono_p2)}</div>{abono_sub(abono_p2, n2)}</div>
      <div class="card card-stat"><div class="stat-label">Total abonado</div><div class="stat-value">{fmt(abono_p1+abono_p2)}</div><div class="stat-sub">de {fmt(cuota)} (cuota del mes)</div></div>
    </div>
    {abono_table}
    <div class="form-card" style="max-width:560px">
      <h4 style="margin-bottom:1rem;font-size:.95rem;font-weight:700">+ Registrar abono</h4>
      <form method="POST" action="/gastos/{gasto['id']}/abonos/nuevo">
        <div class="form-row">
          <div class="form-group"><label>Persona *</label><select name="persona" required><option value="">— Selecciona —</option>{p1_opts}</select></div>
          <div class="form-group"><label>Monto *</label><input type="number" name="monto" step="0.01" min="0.01" required placeholder="0.00"></div>
        </div>
        <div class="form-group"><label>Notas</label><input type="text" name="notas" placeholder="Opcional"></div>
        <div class="form-actions"><button type="submit" class="btn btn-primary">Registrar abono</button></div>
      </form>
    </div>"""
    return base(esc(gasto['descripcion']), content, user, cfg)

# ── Pagos extra ────────────────────────────────────────────────────────────────

def pagos_extra_lista(user, cfg, pagos):
    rows = ''
    for p in pagos:
        rows += f"""<tr>
          <td>{esc(p['descripcion'])}</td>
          <td>{esc(persona_nombre(p['pagado_por'], cfg))}</td>
          <td>{esc(persona_nombre(p['recibido_por'], cfg))}</td>
          <td>{fmt(p['monto'])}</td>
          <td>{esc(str(p['mes'])[:7])}</td>
          <td class="text-muted">{esc(str(p['fecha_registro'])[:10])}</td>
          <td class="actions">
            <a href="/pagos-extra/{p['id']}/editar" class="btn-sm btn-edit">Editar</a>
            <form method="POST" action="/pagos-extra/{p['id']}/eliminar" style="display:inline" onsubmit="return confirm('¿Eliminar?')">
              <button type="submit" class="btn-sm btn-delete">Eliminar</button>
            </form>
          </td></tr>"""
    table = f'<div class="table-wrap"><table class="table"><thead><tr><th>Descripción</th><th>Pagó</th><th>Recibió</th><th>Monto</th><th>Mes</th><th>Registrado</th><th>Acciones</th></tr></thead><tbody>{rows}</tbody></table></div>' if pagos else '<div class="empty-state"><p>No hay pagos extra.</p></div>'
    content = f'<div class="page-header"><h2>Pagos extra</h2><a href="/pagos-extra/nuevo" class="btn btn-primary">+ Nuevo</a></div><p class="text-muted" style="margin-bottom:1rem">Transferencias directas entre {esc(cfg["nombre_persona1"])} y {esc(cfg["nombre_persona2"])}.</p>{table}'
    return base('Pagos Extra', content, user, cfg)

def pagos_extra_form(user, cfg, pago=None, editando=False, error=None):
    action = f'/pagos-extra/{pago["id"]}/editar' if editando else '/pagos-extra/nuevo'
    title  = 'Editar pago extra' if editando else 'Nuevo pago extra'
    d = pago or {}
    n1, n2 = cfg['nombre_persona1'], cfg['nombre_persona2']
    def sel(name, val):
        return f'<option value="persona1" {"selected" if val=="persona1" else ""}>{esc(n1)}</option><option value="persona2" {"selected" if val=="persona2" else ""}>{esc(n2)}</option>'
    mes_val = str(d.get('mes',''))[:7]
    err_html = f'<div class="alert alert-danger">{esc(error)}</div>' if error else ''
    content = f"""
    <div class="page-header"><h2>{title}</h2><a href="/pagos-extra" class="btn btn-secondary">← Volver</a></div>
    {err_html}
    <div class="form-card">
      <form method="POST" action="{action}">
        <div class="form-row">
          <div class="form-group"><label>Descripción *</label><input type="text" name="descripcion" required value="{esc(d.get('descripcion',''))}"></div>
          <div class="form-group"><label>Monto *</label><input type="number" name="monto" step="0.01" min="0.01" required value="{esc(d.get('monto',''))}"></div>
        </div>
        <div class="form-row">
          <div class="form-group"><label>¿Quién pagó? *</label><select name="pagado_por" required><option value="">— Selecciona —</option>{sel('pagado_por', d.get('pagado_por',''))}</select></div>
          <div class="form-group"><label>¿Quién recibió? *</label><select name="recibido_por" required><option value="">— Selecciona —</option>{sel('recibido_por', d.get('recibido_por',''))}</select></div>
        </div>
        <div class="form-row">
          <div class="form-group"><label>Mes *</label><input type="month" name="mes" required value="{esc(mes_val)}" min="2024-12"></div>
        </div>
        <div class="form-group"><label>Notas</label><textarea name="notas" rows="2">{esc(d.get('notas',''))}</textarea></div>
        <div class="form-actions">
          <button type="submit" class="btn btn-primary">{'Guardar cambios' if editando else 'Registrar pago'}</button>
          <a href="/pagos-extra" class="btn btn-secondary">Cancelar</a>
        </div>
      </form>
    </div>"""
    return base(title, content, user, cfg)

# ── Reporte ────────────────────────────────────────────────────────────────────

def reporte(user, cfg, balance_mes, acumulado, mes_lbl, year, month, meses_disponibles):
    n1, n2 = cfg['nombre_persona1'], cfg['nombre_persona2']
    mes_opts = ''.join(f'<option value="{m["year"]}-{m["month"]:02d}" {"selected" if m["year"]==year and m["month"]==month else ""}>{esc(m["label"])}</option>' for m in meses_disponibles)
    gastos_rows = ''
    for g in balance_mes.get('gastos', []):
        gastos_rows += f'<tr><td>{esc(g["descripcion"])}</td><td><span class="badge badge-cat">{esc(CATEGORIAS_DICT.get(g["categoria"],g["categoria"]))}</span></td><td>{esc(persona_nombre(g["pagado_por"],cfg)) if not g["tiene_abonos"] else "Abonos"}</td><td>{fmt(g["monto_total"])}</td><td>{fmt(g["cuota_mes"])}</td><td>{fmt(g["mitad"])}</td><td>{g["meses_diferidos"]}</td></tr>'
    pe_rows = ''
    for p in balance_mes.get('pagos_extra', []):
        pe_rows += f'<tr><td>{esc(p["descripcion"])}</td><td>{esc(persona_nombre(p["pagado_por"],cfg))}</td><td>{esc(persona_nombre(p["recibido_por"],cfg))}</td><td>{fmt(p["monto"])}</td></tr>'
    hist_rows = ''
    for m in acumulado.get('meses', []):
        hl = ' class="row-highlight"' if m['year']==year and m['month']==month else ''
        b1cls = 'positive' if m['balance_p1']>0 else ('negative' if m['balance_p1']<0 else '')
        b2cls = 'positive' if m['balance_p2']>0 else ('negative' if m['balance_p2']<0 else '')
        hist_rows += f'<tr{hl}><td>{esc(m["label"])}</td><td>{fmt(m["total_p1"])}</td><td>{fmt(m["total_p2"])}</td><td>{fmt(m["total"])}</td><td class="{b1cls}">{fmt(m["balance_p1"])}</td><td class="{b2cls}">{fmt(m["balance_p2"])}</td></tr>'
    deuda_acum = ''
    if acumulado.get('deuda_acum'):
        d = acumulado['deuda_acum']
        deuda_acum = f'<div class="deuda-banner deuda-acum">📊 Acumulado: <strong>{esc(persona_nombre(d["deudor"],cfg))} debe {fmt(d["monto"])} a {esc(persona_nombre(d["acreedor"],cfg))}</strong></div>'
    content = f"""
    <div class="page-header">
      <h2>Reporte: {esc(mes_lbl)}</h2>
      <select onchange="irAMes(this.value)">{mes_opts}</select>
    </div>
    <h3 class="section-title">Balance del mes</h3>
    {balance_cards(balance_mes, cfg, mes_label=True)}
    {'<h3 class="section-title" style="margin-top:2rem">Gastos del mes</h3><div class="table-wrap"><table class="table"><thead><tr><th>Descripción</th><th>Categoría</th><th>Pagó</th><th>Total</th><th>Cuota</th><th>Por persona</th><th>Meses</th></tr></thead><tbody>' + gastos_rows + '</tbody></table></div>' if balance_mes.get('gastos') else ''}
    {'<h3 class="section-title" style="margin-top:2rem">Pagos extra</h3><div class="table-wrap"><table class="table"><thead><tr><th>Descripción</th><th>Pagó</th><th>Recibió</th><th>Monto</th></tr></thead><tbody>' + pe_rows + '</tbody></table></div>' if balance_mes.get('pagos_extra') else ''}
    <h3 class="section-title" style="margin-top:2.5rem">Acumulado (desde dic 2024)</h3>
    <div class="cards-grid">
      <div class="card card-stat"><div class="stat-label">Total</div><div class="stat-value">{fmt(acumulado['acum_total'])}</div></div>
      <div class="card card-stat"><div class="stat-label">{esc(n1)}</div><div class="stat-value">{fmt(acumulado['acum_p1'])}</div></div>
      <div class="card card-stat"><div class="stat-label">{esc(n2)}</div><div class="stat-value">{fmt(acumulado['acum_p2'])}</div></div>
    </div>
    {deuda_acum}
    <h3 class="section-title" style="margin-top:2rem">Histórico mensual</h3>
    <div class="table-wrap"><table class="table">
      <thead><tr><th>Mes</th><th>{esc(n1)}</th><th>{esc(n2)}</th><th>Total</th><th>Balance {esc(n1)}</th><th>Balance {esc(n2)}</th></tr></thead>
      <tbody>{hist_rows}</tbody></table></div>
    <script>function irAMes(v){{const[y,m]=v.split('-');window.location='/reporte?year='+y+'&month='+parseInt(m);}}</script>"""
    return base(f'Reporte {mes_lbl}', content, user, cfg)

# ── Descargas ──────────────────────────────────────────────────────────────────

def descargas_index(user, cfg, meses, year_sel, month_sel):
    opts = ''.join(f'<option value="{m["year"]}-{m["month"]:02d}" {"selected" if m["year"]==year_sel and m["month"]==month_sel else ""}>{esc(m["label"])}</option>' for m in meses)
    content = f"""
    <div class="page-header"><h2>Descargar información</h2></div>
    <p class="text-muted" style="margin-bottom:1.5rem">Selecciona un mes para descargar un Excel con el resumen, gastos y pagos extra.</p>
    <div class="form-card" style="max-width:480px">
      <form method="GET" action="/descargas/excel">
        <div class="form-group"><label>Mes</label>
          <select name="" id="mes-sel" onchange="actualizarParams(this)">{opts}</select>
          <input type="hidden" name="year" id="inp-year" value="{year_sel}">
          <input type="hidden" name="month" id="inp-month" value="{month_sel}">
        </div>
        <div class="download-preview">
          <div class="download-icon">📊</div>
          <div><div class="download-title">Excel (.xlsx)</div><div class="download-desc">3 hojas: Resumen, Gastos y Pagos Extra</div></div>
        </div>
        <div class="form-actions" style="margin-top:1.25rem">
          <button type="submit" class="btn btn-primary">⬇️ Descargar Excel</button>
        </div>
      </form>
    </div>
    <style>.download-preview{{display:flex;align-items:center;gap:1rem;background:#f0faf4;border:1px solid #b7e4c7;border-radius:8px;padding:1rem 1.25rem;margin-top:.5rem}}.download-icon{{font-size:2rem}}.download-title{{font-weight:700;font-size:.95rem}}.download-desc{{font-size:.82rem;color:#6b6860;margin-top:2px}}</style>
    <script>function actualizarParams(s){{const[y,m]=s.value.split('-');document.getElementById('inp-year').value=y;document.getElementById('inp-month').value=parseInt(m);}}</script>"""
    return base('Descargas', content, user, cfg)

# ── Admin usuarios ─────────────────────────────────────────────────────────────

def admin_usuarios(user, cfg, usuarios):
    rows = ''
    for u in usuarios:
        persona_str = persona_nombre(u.get('persona'), cfg) if u.get('persona') else '—'
        rows += f"""<tr>
          <td>{esc(u['nombre'])}</td><td><code>{esc(u['username'])}</code></td>
          <td><span class="badge {'badge-admin' if u['rol']=='admin' else 'badge-user'}">{esc(u['rol'])}</span></td>
          <td>{esc(persona_str)}</td>
          <td><span class="badge {'badge-active' if u['activo'] else 'badge-inactive'}">{'Activo' if u['activo'] else 'Inactivo'}</span></td>
          <td class="text-muted">{esc(str(u['fecha_creacion'])[:10])}</td>
          <td class="actions">
            <a href="/admin/usuarios/{u['id']}/editar" class="btn-sm btn-edit">Editar</a>
            {f'<form method="POST" action="/admin/usuarios/{u["id"]}/eliminar" style="display:inline" onsubmit="return confirm(\'¿Eliminar?\')"><button type="submit" class="btn-sm btn-delete">Eliminar</button></form>' if u['id'] != user['id'] else ''}
          </td></tr>"""
    content = f"""
    <div class="page-header"><h2>Usuarios</h2>
      <div style="display:flex;gap:.5rem">
        <a href="/admin/configuracion" class="btn btn-secondary">⚙️ Config</a>
        <a href="/admin/usuarios/nuevo" class="btn btn-primary">+ Nuevo</a>
      </div>
    </div>
    <div class="table-wrap"><table class="table">
      <thead><tr><th>Nombre</th><th>Usuario</th><th>Rol</th><th>Persona</th><th>Estado</th><th>Creado</th><th>Acciones</th></tr></thead>
      <tbody>{rows}</tbody></table></div>"""
    return base('Usuarios', content, user, cfg)

def admin_form_usuario(user, cfg, usuario=None, editando=False, error=None):
    action = f'/admin/usuarios/{usuario["id"]}/editar' if editando else '/admin/usuarios/nuevo'
    title  = 'Editar usuario' if editando else 'Nuevo usuario'
    d = usuario or {}
    n1, n2 = cfg['nombre_persona1'], cfg['nombre_persona2']
    rol_opts = f'<option value="usuario" {"selected" if d.get("rol")!="admin" else ""}>Usuario</option><option value="admin" {"selected" if d.get("rol")=="admin" else ""}>Admin</option>'
    per_opts = f'<option value="">— Ninguna —</option><option value="persona1" {"selected" if d.get("persona")=="persona1" else ""}>{esc(n1)}</option><option value="persona2" {"selected" if d.get("persona")=="persona2" else ""}>{esc(n2)}</option>'
    activo_check = 'checked' if not editando or d.get('activo') else ''
    err_html = f'<div class="alert alert-danger">{esc(error)}</div>' if error else ''
    content = f"""
    <div class="page-header"><h2>{title}</h2><a href="/admin/usuarios" class="btn btn-secondary">← Volver</a></div>
    {err_html}
    <div class="form-card">
      <form method="POST" action="{action}">
        <div class="form-row">
          <div class="form-group"><label>Nombre completo *</label><input type="text" name="nombre" required value="{esc(d.get('nombre',''))}"></div>
          <div class="form-group"><label>Usuario *</label><input type="text" name="username" required value="{esc(d.get('username',''))}" placeholder="sin espacios"></div>
        </div>
        <div class="form-row">
          <div class="form-group"><label>Contraseña {'(dejar vacío para no cambiar)' if editando else '*'}</label><input type="password" name="password" {'required' if not editando else ''} placeholder="••••••••"></div>
          <div class="form-group"><label>Rol</label><select name="rol">{rol_opts}</select></div>
        </div>
        <div class="form-row">
          <div class="form-group"><label>Persona</label><select name="persona">{per_opts}</select></div>
          {'<div class="form-group"><label>Estado</label><div class="checkbox-group"><input type="checkbox" id="activo" name="activo" ' + activo_check + '><label for="activo">Usuario activo</label></div></div>' if editando else ''}
        </div>
        <div class="form-actions">
          <button type="submit" class="btn btn-primary">{'Guardar cambios' if editando else 'Crear usuario'}</button>
          <a href="/admin/usuarios" class="btn btn-secondary">Cancelar</a>
        </div>
      </form>
    </div>"""
    return base(title, content, user, cfg)

def admin_configuracion(user, cfg):
    content = f"""
    <div class="page-header"><h2>Configuración</h2><a href="/admin/usuarios" class="btn btn-secondary">← Usuarios</a></div>
    <div class="form-card">
      <form method="POST" action="/admin/configuracion">
        <p class="text-muted" style="margin-bottom:1.5rem">Nombres de las dos personas de la pareja.</p>
        <div class="form-row">
          <div class="form-group"><label>Nombre Persona 1</label><input type="text" name="nombre_persona1" required value="{esc(cfg['nombre_persona1'])}"></div>
          <div class="form-group"><label>Nombre Persona 2</label><input type="text" name="nombre_persona2" required value="{esc(cfg['nombre_persona2'])}"></div>
        </div>
        <div class="form-actions"><button type="submit" class="btn btn-primary">Guardar</button></div>
      </form>
    </div>"""
    return base('Configuración', content, user, cfg)

# ── Setup ──────────────────────────────────────────────────────────────────────

def setup_crear_admin():
    return f"""<!DOCTYPE html>
<html lang="es"><head>
  <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Setup — Gastos Pareja</title>
  <link rel="stylesheet" href="/css/style.css">
</head><body class="login-body">
  <div class="login-card">
    <div class="login-header"><div class="login-icon">⚙️</div><h1>Configuración inicial</h1><p>Crea el primer administrador</p></div>
    <form method="POST" action="/setup/crear-admin">
      <div class="form-group"><label>Nombre completo</label><input type="text" name="nombre" required placeholder="Tu nombre"></div>
      <div class="form-group"><label>Usuario</label><input type="text" name="username" required placeholder="sin espacios"></div>
      <div class="form-group"><label>Contraseña</label><input type="password" name="password" required placeholder="••••••••"></div>
      <button type="submit" class="btn btn-primary btn-full">Crear administrador</button>
    </form>
    <p style="margin-top:1rem;font-size:.8rem;color:#6b6860;text-align:center">Esta página se deshabilita después de crear el primer usuario.</p>
  </div>
</body></html>"""

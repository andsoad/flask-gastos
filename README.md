# Gastos Pareja 💑 — Cloudflare Workers + D1

FastAPI + Cloudflare D1 (SQLite) + pywrangler.

## Diferencias vs rama `main`

| | `main` (InMotion) | `cloudflare` (esta rama) |
|---|---|---|
| Framework | Flask | FastAPI |
| Base de datos | MySQL | Cloudflare D1 (SQLite) |
| Auth | Flask-Login (sesiones) | JWT (cookie httponly) |
| Deploy | passenger_wsgi.py | `uv run pywrangler deploy` |
| Primer admin | `python crear_admin.py` | `/setup/crear-admin` en el navegador |

---

## Requisitos

- [uv](https://docs.astral.sh/uv/getting-started/installation/) instalado
- Node.js 18+ (para wrangler)
- Cuenta en Cloudflare (gratis)

---

## Instalación

### 1. Instalar pywrangler

```bash
uv tool install workers-py
```

### 2. Crear la base de datos D1

```bash
uv run pywrangler d1 create gastos_pareja
```

Copia el `database_id` en `wrangler.toml`:

```toml
[[d1_databases]]
binding = "DB"
database_name = "gastos_pareja"
database_id = "TU_DATABASE_ID_AQUI"   # ← aquí
```

### 3. Crear las tablas

```bash
uv run pywrangler d1 execute gastos_pareja --file=schema_d1.sql
```

### 4. Configurar SECRET_KEY en wrangler.toml

```toml
[vars]
SECRET_KEY = "una_clave_larga_y_aleatoria"
```

### 5. Probar en local

```bash
uv run pywrangler dev
```

### 6. Crear el primer admin

Abre `http://localhost:8787/setup/crear-admin` y llena el formulario.

### 7. Deploy a producción

```bash
uv run pywrangler deploy
```

Tu app quedará en: `https://gastos-pareja.TU_USUARIO.workers.dev`

---

## Estructura

```
gastos_pareja/
├── wrangler.toml
├── pyproject.toml       # dependencias (pywrangler las empaqueta)
├── schema_d1.sql        # schema SQLite para D1
├── src/
│   ├── index.py         # FastAPI + WorkerEntrypoint (entry point)
│   ├── auth_utils.py    # JWT + passwords
│   ├── db.py            # Helper D1
│   └── balance.py       # Lógica de balances
├── templates/           # Jinja2 (igual que rama main)
└── static/              # CSS y JS (igual que rama main)
```

## Plan gratuito de Cloudflare Workers
- 100,000 requests/día
- 5 GB en D1
- HTTPS automático
- Dominio `.workers.dev` incluido

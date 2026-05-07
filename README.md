# Gastos Pareja 💑 — Cloudflare Workers + D1

Esta rama usa **FastAPI + Cloudflare D1 (SQLite)** en lugar de Flask + MySQL.
Los templates HTML y la lógica de negocio son idénticos a la rama `main`.

## Diferencias vs rama `main`

| | `main` (InMotion) | `cloudflare` (esta rama) |
|---|---|---|
| Framework | Flask | FastAPI |
| Base de datos | MySQL | Cloudflare D1 (SQLite) |
| Auth | Flask-Login (sesiones) | JWT (cookie httponly) |
| Deploy | passenger_wsgi.py | wrangler deploy |
| Primer admin | `python crear_admin.py` | `/setup/crear-admin` en el navegador |

---

## Requisitos

- Node.js 18+ (para Wrangler CLI)
- Cuenta en Cloudflare (gratis)

```bash
npm install -g wrangler
wrangler login
```

---

## Instalación

### 1. Crear la base de datos D1

```bash
wrangler d1 create gastos_pareja
```

Copia el `database_id` que te devuelve y pégalo en `wrangler.toml`:

```toml
[[d1_databases]]
binding = "DB"
database_name = "gastos_pareja"
database_id = "TU_DATABASE_ID_AQUI"
```

### 2. Crear las tablas

```bash
wrangler d1 execute gastos_pareja --file=schema_d1.sql
```

### 3. Configurar variables de entorno

En `wrangler.toml` actualiza:

```toml
[vars]
SECRET_KEY = "una_clave_secreta_larga_y_aleatoria"
```

### 4. Instalar dependencias Python

```bash
pip install -r requirements.txt
```

### 5. Probar en local

```bash
wrangler dev
```

### 6. Crear el primer admin

Abre en tu navegador: `http://localhost:8787/setup/crear-admin`

Esta ruta se deshabilita automáticamente después de crear el primer usuario.

### 7. Deploy a producción

```bash
wrangler deploy
```

Tu app quedará en: `https://gastos-pareja.TU_USUARIO.workers.dev`

---

## Estructura

```
gastos_pareja/
├── wrangler.toml
├── schema_d1.sql
├── requirements.txt
├── src/
│   ├── index.py        # FastAPI (todas las rutas)
│   ├── auth_utils.py   # JWT + passwords
│   ├── db.py           # Helper D1
│   └── balance.py      # Lógica de balances
├── templates/          # Jinja2 (igual que rama main)
└── static/             # CSS y JS (igual que rama main)
```

## Plan gratuito de Cloudflare
- 100,000 requests/día en Workers
- 5 GB en D1
- HTTPS automático
- Dominio `.workers.dev` incluido

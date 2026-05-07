"""
Helper para interactuar con Cloudflare D1.
En Workers, `env.DB` es el binding D1 accesible via JS interop.
"""


async def db_fetch_all(db, query: str, params: list = None) -> list[dict]:
    """Ejecuta un SELECT y retorna lista de dicts."""
    params = params or []
    stmt = db.prepare(query)
    if params:
        stmt = stmt.bind(*params)
    result = await stmt.all()
    return [dict(row) for row in (result.results or [])]


async def db_fetch_one(db, query: str, params: list = None) -> dict | None:
    """Ejecuta un SELECT y retorna el primer resultado."""
    rows = await db_fetch_all(db, query, params)
    return rows[0] if rows else None


async def db_run(db, query: str, params: list = None) -> dict:
    """Ejecuta INSERT/UPDATE/DELETE. Retorna meta (last_row_id, changes)."""
    params = params or []
    stmt = db.prepare(query)
    if params:
        stmt = stmt.bind(*params)
    result = await stmt.run()
    return {
        'last_row_id': result.meta.last_row_id if result.meta else None,
        'changes':     result.meta.changes     if result.meta else 0,
    }


async def get_config(db) -> dict:
    return await db_fetch_one(db,
        "SELECT nombre_persona1, nombre_persona2 FROM configuracion WHERE id = 1"
    )

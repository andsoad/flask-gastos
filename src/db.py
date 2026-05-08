"""
Helper para Cloudflare D1 usando el binding nativo de Workers.
No requiere librerías externas.
"""


async def db_fetch_all(db, query: str, params: list = None) -> list:
    params = params or []
    stmt   = db.prepare(query)
    if params:
        stmt = stmt.bind(*params)
    result = await stmt.all()
    rows   = result.results
    if not rows:
        return []
    return [dict(row) for row in rows]


async def db_fetch_one(db, query: str, params: list = None) -> dict | None:
    rows = await db_fetch_all(db, query, params)
    return rows[0] if rows else None


async def db_run(db, query: str, params: list = None) -> dict:
    params = params or []
    stmt   = db.prepare(query)
    if params:
        stmt = stmt.bind(*params)
    result = await stmt.run()
    return {
        'last_row_id': result.meta.last_row_id if result.meta else None,
        'changes':     result.meta.changes     if result.meta else 0,
    }


async def get_config(db) -> dict:
    return await db_fetch_one(
        db, "SELECT nombre_persona1, nombre_persona2 FROM configuracion WHERE id = 1"
    )

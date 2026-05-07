-- ============================================================
--  Gastos Pareja — Schema D1 (SQLite)
--  Cloudflare Workers + D1
-- ============================================================

CREATE TABLE IF NOT EXISTS configuracion (
    id               INTEGER PRIMARY KEY DEFAULT 1,
    nombre_persona1  TEXT NOT NULL DEFAULT 'Ana',
    nombre_persona2  TEXT NOT NULL DEFAULT 'Luis',
    CHECK (id = 1)
);

INSERT OR IGNORE INTO configuracion (id, nombre_persona1, nombre_persona2)
VALUES (1, 'Ana', 'Luis');

CREATE TABLE IF NOT EXISTS usuarios (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre         TEXT NOT NULL,
    username       TEXT NOT NULL UNIQUE,
    password_hash  TEXT NOT NULL,
    rol            TEXT NOT NULL DEFAULT 'usuario' CHECK (rol IN ('admin','usuario')),
    persona        TEXT DEFAULT NULL CHECK (persona IN ('persona1','persona2',NULL)),
    activo         INTEGER NOT NULL DEFAULT 1,
    fecha_creacion TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS gastos (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    descripcion     TEXT    NOT NULL,
    monto_total     REAL    NOT NULL,
    categoria       TEXT    NOT NULL,
    pagado_por      TEXT    DEFAULT NULL CHECK (pagado_por IN ('persona1','persona2',NULL)),
    mes_inicio      TEXT    NOT NULL, -- YYYY-MM-01
    meses_diferidos INTEGER NOT NULL DEFAULT 1,
    fecha_registro  TEXT    NOT NULL DEFAULT (datetime('now')),
    notas           TEXT,
    creado_por      INTEGER NOT NULL,
    FOREIGN KEY (creado_por) REFERENCES usuarios(id)
);

CREATE TABLE IF NOT EXISTS abonos_gasto (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    gasto_id       INTEGER NOT NULL,
    persona        TEXT    NOT NULL CHECK (persona IN ('persona1','persona2')),
    monto          REAL    NOT NULL,
    fecha_registro TEXT    NOT NULL DEFAULT (datetime('now')),
    notas          TEXT,
    creado_por     INTEGER NOT NULL,
    FOREIGN KEY (gasto_id)   REFERENCES gastos(id) ON DELETE CASCADE,
    FOREIGN KEY (creado_por) REFERENCES usuarios(id)
);

CREATE TABLE IF NOT EXISTS pagos_extra (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    descripcion    TEXT    NOT NULL,
    monto          REAL    NOT NULL,
    pagado_por     TEXT    NOT NULL CHECK (pagado_por IN ('persona1','persona2')),
    recibido_por   TEXT    NOT NULL CHECK (recibido_por IN ('persona1','persona2')),
    mes            TEXT    NOT NULL,
    fecha_registro TEXT    NOT NULL DEFAULT (datetime('now')),
    notas          TEXT,
    creado_por     INTEGER NOT NULL,
    FOREIGN KEY (creado_por) REFERENCES usuarios(id)
);

CREATE INDEX IF NOT EXISTS idx_gastos_mes      ON gastos(mes_inicio);
CREATE INDEX IF NOT EXISTS idx_gastos_cat      ON gastos(categoria);
CREATE INDEX IF NOT EXISTS idx_abonos_gasto    ON abonos_gasto(gasto_id);
CREATE INDEX IF NOT EXISTS idx_pagos_extra_mes ON pagos_extra(mes);

-- ============================================================
--  Gastos Pareja — Schema MySQL
--  Ejecutar una sola vez para crear todas las tablas
-- ============================================================

CREATE DATABASE IF NOT EXISTS gastos_pareja
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE gastos_pareja;

-- ------------------------------------------------------------
-- Usuarios
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS usuarios (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    nombre        VARCHAR(100)  NOT NULL,
    username      VARCHAR(60)   NOT NULL UNIQUE,
    password_hash VARCHAR(255)  NOT NULL,
    rol           ENUM('admin','usuario') NOT NULL DEFAULT 'usuario',
    persona       ENUM('persona1','persona2') DEFAULT NULL
                  COMMENT 'A qué persona de la pareja representa (opcional)',
    activo        TINYINT(1)    NOT NULL DEFAULT 1,
    fecha_creacion DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ------------------------------------------------------------
-- Configuración general (una sola fila)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS configuracion (
    id               INT PRIMARY KEY DEFAULT 1,
    nombre_persona1  VARCHAR(100) NOT NULL DEFAULT 'Ana',
    nombre_persona2  VARCHAR(100) NOT NULL DEFAULT 'Luis',
    CHECK (id = 1)
);

INSERT INTO configuracion (id, nombre_persona1, nombre_persona2)
VALUES (1, 'Ana', 'Luis')
ON DUPLICATE KEY UPDATE id = id;

-- ------------------------------------------------------------
-- Gastos
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS gastos (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    descripcion     VARCHAR(255)   NOT NULL,
    monto_total     DECIMAL(10,2)  NOT NULL,
    categoria       VARCHAR(50)    NOT NULL,
    pagado_por      ENUM('persona1','persona2') NOT NULL,
    mes_inicio      DATE           NOT NULL  COMMENT 'YYYY-MM-01: primer mes del gasto',
    meses_diferidos INT            NOT NULL DEFAULT 1,
    fecha_registro  DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    notas           TEXT,
    creado_por      INT            NOT NULL,
    FOREIGN KEY (creado_por) REFERENCES usuarios(id)
);

-- ------------------------------------------------------------
-- Pagos extra (transferencias directas entre personas)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pagos_extra (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    descripcion    VARCHAR(255)   NOT NULL,
    monto          DECIMAL(10,2)  NOT NULL,
    pagado_por     ENUM('persona1','persona2') NOT NULL,
    recibido_por   ENUM('persona1','persona2') NOT NULL,
    mes            DATE           NOT NULL  COMMENT 'YYYY-MM-01',
    fecha_registro DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    notas          TEXT,
    creado_por     INT            NOT NULL,
    FOREIGN KEY (creado_por) REFERENCES usuarios(id)
);

-- ------------------------------------------------------------
-- Índices
-- ------------------------------------------------------------
CREATE INDEX idx_gastos_mes      ON gastos(mes_inicio);
CREATE INDEX idx_gastos_cat      ON gastos(categoria);
CREATE INDEX idx_pagos_extra_mes ON pagos_extra(mes);

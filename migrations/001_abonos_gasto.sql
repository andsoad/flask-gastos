-- ============================================================
--  Migración: Agregar tabla abonos_gasto y hacer pagado_por opcional
--  Ejecutar si ya tienes la base de datos instalada
-- ============================================================

USE gastos_pareja;

-- Hacer pagado_por nullable
ALTER TABLE gastos
    MODIFY COLUMN pagado_por ENUM('persona1','persona2') DEFAULT NULL
    COMMENT 'NULL = gasto con abonos individuales';

-- Crear tabla de abonos
CREATE TABLE IF NOT EXISTS abonos_gasto (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    gasto_id       INT            NOT NULL,
    persona        ENUM('persona1','persona2') NOT NULL,
    monto          DECIMAL(10,2)  NOT NULL,
    fecha_registro DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    notas          TEXT,
    creado_por     INT            NOT NULL,
    FOREIGN KEY (gasto_id)   REFERENCES gastos(id) ON DELETE CASCADE,
    FOREIGN KEY (creado_por) REFERENCES usuarios(id)
);

CREATE INDEX IF NOT EXISTS idx_abonos_gasto ON abonos_gasto(gasto_id);

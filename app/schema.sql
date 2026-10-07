-- Esquema de la base de datos del Cuaderno de la Tienda (SQLite).
-- Las fechas se guardan como texto en hora local: 'YYYY-MM-DD HH:MM:SS'.
-- Las fechas de vencimiento son 'YYYY-MM-DD' o NULL si el producto no vence.

CREATE TABLE IF NOT EXISTS productos (
    id          INTEGER PRIMARY KEY,
    nombre      TEXT    NOT NULL,
    unidad      TEXT    NOT NULL DEFAULT 'unidad' CHECK (unidad IN ('unidad', 'lb')),
    precio      REAL    NOT NULL CHECK (precio >= 0),
    minimo      REAL    NOT NULL DEFAULT 5 CHECK (minimo >= 0),
    costo_ref   REAL    NOT NULL DEFAULT 0 CHECK (costo_ref >= 0),
    -- Cantidad vendida o descontada sin existencia registrada. La próxima entrada la cubre.
    faltante    REAL    NOT NULL DEFAULT 0 CHECK (faltante >= 0),
    archivado   INTEGER NOT NULL DEFAULT 0,
    creado      TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS clientes (
    id        INTEGER PRIMARY KEY,
    nombre    TEXT NOT NULL,
    telefono  TEXT NOT NULL DEFAULT '',
    creado    TEXT NOT NULL
);

-- Cada entrada de mercancía (o cambio con el proveedor) crea un lote con su costo y vencimiento.
-- Las ventas y pérdidas descuentan primero de los lotes que vencen antes.
CREATE TABLE IF NOT EXISTS lotes (
    id              INTEGER PRIMARY KEY,
    producto_id     INTEGER NOT NULL REFERENCES productos (id),
    origen          TEXT    NOT NULL CHECK (origen IN ('entrada', 'cambio')),
    cantidad        REAL    NOT NULL CHECK (cantidad > 0),
    restante        REAL    NOT NULL CHECK (restante >= 0),
    costo_unitario  REAL    NOT NULL CHECK (costo_unitario >= 0),
    vence           TEXT,
    fecha           TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_lotes_producto ON lotes (producto_id, restante);

CREATE TABLE IF NOT EXISTS ventas (
    id            INTEGER PRIMARY KEY,
    fecha         TEXT    NOT NULL,
    pago          TEXT    NOT NULL CHECK (pago IN ('contado', 'fiado')),
    cliente_id    INTEGER REFERENCES clientes (id),
    total         REAL    NOT NULL,
    costo         REAL    NOT NULL,
    anulada       INTEGER NOT NULL DEFAULT 0,
    anulada_fecha TEXT,
    CHECK (pago = 'contado' OR cliente_id IS NOT NULL)
);
CREATE INDEX IF NOT EXISTS ix_ventas_fecha ON ventas (fecha);
CREATE INDEX IF NOT EXISTS ix_ventas_cliente ON ventas (cliente_id);

CREATE TABLE IF NOT EXISTS venta_items (
    id           INTEGER PRIMARY KEY,
    venta_id     INTEGER NOT NULL REFERENCES ventas (id),
    producto_id  INTEGER NOT NULL REFERENCES productos (id),
    nombre       TEXT    NOT NULL,
    unidad       TEXT    NOT NULL,
    cantidad     REAL    NOT NULL CHECK (cantidad > 0),
    precio       REAL    NOT NULL,
    costo        REAL    NOT NULL,
    faltante     REAL    NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS ix_venta_items_venta ON venta_items (venta_id);

-- De qué lotes salió cada renglón de venta; permite devolver el inventario al anular.
CREATE TABLE IF NOT EXISTS venta_item_lotes (
    venta_item_id  INTEGER NOT NULL REFERENCES venta_items (id),
    lote_id        INTEGER NOT NULL REFERENCES lotes (id),
    cantidad       REAL    NOT NULL,
    PRIMARY KEY (venta_item_id, lote_id)
);

CREATE TABLE IF NOT EXISTS perdidas (
    id           INTEGER PRIMARY KEY,
    producto_id  INTEGER NOT NULL REFERENCES productos (id),
    cantidad     REAL    NOT NULL CHECK (cantidad > 0),
    costo        REAL    NOT NULL,
    motivo       TEXT    NOT NULL,
    fecha        TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_perdidas_fecha ON perdidas (fecha);

CREATE TABLE IF NOT EXISTS cambios (
    id            INTEGER PRIMARY KEY,
    producto_id   INTEGER NOT NULL REFERENCES productos (id),
    cantidad      REAL    NOT NULL CHECK (cantidad > 0),
    vence         TEXT    NOT NULL,
    lote_id       INTEGER NOT NULL REFERENCES lotes (id),
    fecha         TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS abonos (
    id          INTEGER PRIMARY KEY,
    cliente_id  INTEGER NOT NULL REFERENCES clientes (id),
    monto       REAL    NOT NULL CHECK (monto > 0),
    fecha       TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_abonos_cliente ON abonos (cliente_id);

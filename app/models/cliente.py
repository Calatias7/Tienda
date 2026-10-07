"""Clientes y su cuenta de fiado (saldo = lo fiado no anulado − abonos)."""
from ..db import transaction
from . import ErrorDeNegocio, NoEncontrado, ahora, numero, r2, r4, texto

_CONSULTA = """
SELECT c.*,
       COALESCE((SELECT SUM(total) FROM ventas v
                  WHERE v.cliente_id = c.id AND v.pago = 'fiado' AND v.anulada = 0), 0)
     - COALESCE((SELECT SUM(monto) FROM abonos a WHERE a.cliente_id = c.id), 0) AS saldo,
       NULLIF(MAX(COALESCE((SELECT MAX(fecha) FROM ventas v
                             WHERE v.cliente_id = c.id AND v.pago = 'fiado' AND v.anulada = 0), ''),
                  COALESCE((SELECT MAX(fecha) FROM abonos a WHERE a.cliente_id = c.id), '')), '') AS ultimo
  FROM clientes c
"""


def _fila(r):
    d = dict(r)
    d["saldo"] = r2(d["saldo"])
    return d


def listar(conn):
    filas = [_fila(r) for r in conn.execute(_CONSULTA).fetchall()]
    # Primero los que más deben; entre iguales, el de movimiento más reciente.
    filas.sort(key=lambda c: (c["saldo"], c["ultimo"] or ""), reverse=True)
    return filas


def obtener(conn, cliente_id):
    r = conn.execute(f"{_CONSULTA} WHERE c.id = ?", (cliente_id,)).fetchone()
    if r is None:
        raise NoEncontrado("Ese cliente no existe.")
    return _fila(r)


def detalle(conn, cliente_id):
    c = obtener(conn, cliente_id)
    ventas = conn.execute(
        "SELECT id, fecha, total FROM ventas WHERE cliente_id = ? AND pago = 'fiado' AND anulada = 0", (cliente_id,)
    ).fetchall()
    items = {}
    if ventas:
        ids = [v["id"] for v in ventas]
        for f in conn.execute(
            f"SELECT venta_id, nombre, unidad, cantidad FROM venta_items WHERE venta_id IN ({','.join('?' * len(ids))})",
            ids,
        ):
            items.setdefault(f["venta_id"], []).append(
                {"nombre": f["nombre"], "unidad": f["unidad"], "cantidad": r4(f["cantidad"])})
    historial = [{"tipo": "venta", "id": v["id"], "fecha": v["fecha"], "monto": v["total"], "items": items.get(v["id"], [])}
                 for v in ventas]
    historial += [{"tipo": "abono", "id": a["id"], "fecha": a["fecha"], "monto": a["monto"]}
                  for a in conn.execute("SELECT * FROM abonos WHERE cliente_id = ?", (cliente_id,))]
    historial.sort(key=lambda m: (m["fecha"], m["tipo"] == "abono", m["id"]), reverse=True)
    c["historial"] = historial
    return c


def crear(conn, nombre, telefono="", fecha=None):
    nombre = texto(nombre, "Escribe el nombre del cliente.")
    with transaction(conn):
        return conn.execute(
            "INSERT INTO clientes (nombre, telefono, creado) VALUES (?, ?, ?)",
            (nombre, str(telefono or "").strip()[:40], fecha or ahora()),
        ).lastrowid


def registrar_abono(conn, cliente_id, monto, fecha=None, permitir_excedente=False):
    monto = r2(numero(monto, "Escribe el monto que pagó.", positivo=True))
    c = obtener(conn, cliente_id)
    if not permitir_excedente and monto > c["saldo"] + 0.004:
        raise ErrorDeNegocio(f"{c['nombre']} solo debe Q{c['saldo']:.2f}.")
    with transaction(conn):
        return conn.execute(
            "INSERT INTO abonos (cliente_id, monto, fecha) VALUES (?, ?, ?)", (cliente_id, monto, fecha or ahora())
        ).lastrowid


def total_por_cobrar(conn):
    return r2(sum(max(0.0, c["saldo"]) for c in conn.execute(_CONSULTA).fetchall()))

"""Ventas al contado y al fiado, cotización y anulación."""
from ..db import transaction
from . import EPS, ErrorDeNegocio, NoEncontrado, ahora, numero, r2, r4
from . import cliente as clientes
from . import inventario
from . import producto as productos

PAGOS = ("contado", "fiado")


def _normalizar(items, con_precio=False):
    """Junta renglones repetidos del mismo producto y valida cantidades."""
    if not isinstance(items, list) or not items:
        raise ErrorDeNegocio("La venta no tiene productos.")
    juntos = {}
    for it in items:
        if not isinstance(it, dict):
            raise ErrorDeNegocio("Renglón de venta inválido.")
        try:
            pid = int(it.get("producto_id"))
        except (TypeError, ValueError):
            raise ErrorDeNegocio("Renglón de venta inválido.") from None
        cant = numero(it.get("cantidad"), "Cada producto necesita una cantidad mayor que cero.", positivo=True)
        if pid in juntos:
            juntos[pid]["cantidad"] += cant
        else:
            juntos[pid] = {"producto_id": pid, "cantidad": cant, "precio": it.get("precio") if con_precio else None}
    return list(juntos.values())


def cotizar(conn, items):
    """Total, costo y ganancia de un carrito sin registrar nada."""
    renglones, total, costo = [], 0.0, 0.0
    for it in _normalizar(items):
        p = productos.obtener(conn, it["producto_id"])
        sub = r2(it["cantidad"] * p["precio"])
        co = inventario.costo_de(conn, p["id"], it["cantidad"])
        renglones.append({"producto_id": p["id"], "cantidad": r4(it["cantidad"]), "subtotal": sub, "costo": co})
        total += sub
        costo += co
    return {"items": renglones, "total": r2(total), "costo": r2(costo), "ganancia": r2(total - costo)}


def registrar(conn, items, pago="contado", cliente_id=None, fecha=None, con_precio=False):
    """Registra la venta, descuenta el inventario y, si es fiado, la carga a la cuenta del cliente.

    Con `con_precio` se respeta el `precio` de cada renglón (solo para importar datos viejos);
    la venta normal siempre usa el precio actual del producto.
    """
    if pago not in PAGOS:
        raise ErrorDeNegocio("Forma de pago inválida.")
    if pago == "fiado":
        if not cliente_id:
            raise ErrorDeNegocio("Elige a quién le fías.")
        clientes.obtener(conn, cliente_id)
    else:
        cliente_id = None
    renglones = _normalizar(items, con_precio)
    fecha = fecha or ahora()
    with transaction(conn):
        venta_id = conn.execute(
            "INSERT INTO ventas (fecha, pago, cliente_id, total, costo) VALUES (?, ?, ?, 0, 0)",
            (fecha, pago, cliente_id),
        ).lastrowid
        total = costo = 0.0
        for it in renglones:
            p = productos.obtener(conn, it["producto_id"])
            precio = r2(it["precio"]) if it.get("precio") is not None else p["precio"]
            co, consumos, faltante = inventario.descontar(conn, p["id"], it["cantidad"])
            item_id = conn.execute(
                "INSERT INTO venta_items (venta_id, producto_id, nombre, unidad, cantidad, precio, costo, faltante)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (venta_id, p["id"], p["nombre"], p["unidad"], r4(it["cantidad"]), precio, co, faltante),
            ).lastrowid
            conn.executemany(
                "INSERT INTO venta_item_lotes (venta_item_id, lote_id, cantidad) VALUES (?, ?, ?)",
                [(item_id, lote_id, r4(q)) for lote_id, q in consumos],
            )
            total += r2(it["cantidad"] * precio)
            costo += co
        conn.execute("UPDATE ventas SET total = ?, costo = ? WHERE id = ?", (r2(total), r2(costo), venta_id))
    return venta_id


def obtener(conn, venta_id):
    v = conn.execute(
        "SELECT v.*, c.nombre AS cliente FROM ventas v LEFT JOIN clientes c ON c.id = v.cliente_id WHERE v.id = ?",
        (venta_id,),
    ).fetchone()
    if v is None:
        raise NoEncontrado("Esa venta no existe.")
    return _con_items(conn, [v])[0]


def _con_items(conn, ventas):
    if not ventas:
        return []
    ids = [v["id"] for v in ventas]
    filas = conn.execute(
        f"SELECT * FROM venta_items WHERE venta_id IN ({','.join('?' * len(ids))}) ORDER BY id", ids
    ).fetchall()
    por_venta = {}
    for f in filas:
        por_venta.setdefault(f["venta_id"], []).append(
            {"producto_id": f["producto_id"], "nombre": f["nombre"], "unidad": f["unidad"],
             "cantidad": r4(f["cantidad"]), "precio": f["precio"], "costo": f["costo"]}
        )
    out = []
    for v in ventas:
        d = dict(v)
        d["anulada"] = bool(d["anulada"])
        d["ganancia"] = r2(d["total"] - d["costo"])
        d["items"] = por_venta.get(v["id"], [])
        out.append(d)
    return out


def listar(conn, desde, hasta, limite=60):
    filas = conn.execute(
        "SELECT v.*, c.nombre AS cliente FROM ventas v LEFT JOIN clientes c ON c.id = v.cliente_id"
        " WHERE v.fecha >= ? AND v.fecha < ? ORDER BY v.fecha DESC, v.id DESC LIMIT ?",
        (desde, hasta, limite),
    ).fetchall()
    return _con_items(conn, filas)


def anular(conn, venta_id, fecha=None):
    """Anula la venta: devuelve el inventario a sus lotes y la quita de la cuenta del cliente."""
    v = obtener(conn, venta_id)
    if v["anulada"]:
        raise ErrorDeNegocio("Esa venta ya estaba anulada.")
    with transaction(conn):
        for it in conn.execute("SELECT * FROM venta_items WHERE venta_id = ?", (venta_id,)).fetchall():
            consumos = [(r["lote_id"], r["cantidad"]) for r in conn.execute(
                "SELECT lote_id, cantidad FROM venta_item_lotes WHERE venta_item_id = ?", (it["id"],))]
            inventario.devolver(conn, it["producto_id"], consumos, it["faltante"] if it["faltante"] > EPS else 0)
        conn.execute("UPDATE ventas SET anulada = 1, anulada_fecha = ? WHERE id = ?", (fecha or ahora(), venta_id))

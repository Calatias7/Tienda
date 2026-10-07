"""Existencias por lotes: entradas, pérdidas y cambios con el proveedor.

Regla principal: todo lo que sale (venta, pérdida, cambio) se descuenta primero del lote que
vence antes. El costo de lo que sale es el costo real de esos lotes. Si se saca más de lo que
hay registrado, la diferencia queda como "faltante" del producto, se costea al costo de
referencia y la próxima entrada la cubre.
"""
from datetime import date

from ..db import transaction
from . import EPS, ErrorDeNegocio, ahora, fecha_opcional, hoy, numero, r2, r4, texto
from . import producto as productos

AVISO_DIAS = 7
MOTIVOS_PERDIDA = ("Se venció", "Se dañó", "Se perdió", "Consumo de la casa")

_ORDEN_LOTES = "ORDER BY vence IS NULL, vence, fecha, id"


def lotes_disponibles(conn, producto_id):
    return conn.execute(
        f"SELECT * FROM lotes WHERE producto_id = ? AND restante > ? {_ORDEN_LOTES}",
        (producto_id, EPS),
    ).fetchall()


def _plan(lotes, cantidad, costo_respaldo):
    """Qué lotes se usan para sacar `cantidad`. No modifica nada."""
    falta, costo, consumos = cantidad, 0.0, []
    for l in lotes:
        if falta <= EPS:
            break
        q = min(l["restante"], falta)
        costo += q * l["costo_unitario"]
        falta -= q
        consumos.append((l["id"], q))
    falta = max(0.0, falta)
    return costo + falta * costo_respaldo, consumos, (r4(falta))


def costo_de(conn, producto_id, cantidad):
    """Lo que costaría sacar `cantidad` ahora mismo (para mostrar la ganancia antes de vender)."""
    p = productos.obtener(conn, producto_id)
    costo, _, _ = _plan(lotes_disponibles(conn, producto_id), cantidad, p["costo_ref"])
    return r2(costo)


def descontar(conn, producto_id, cantidad):
    """Saca `cantidad` del inventario. Devuelve (costo, consumos [(lote_id, cant)], faltante)."""
    p = productos.obtener(conn, producto_id)
    costo, consumos, faltante = _plan(lotes_disponibles(conn, producto_id), cantidad, p["costo_ref"])
    with transaction(conn):
        for lote_id, q in consumos:
            conn.execute(
                "UPDATE lotes SET restante = MAX(0, ROUND(restante - ?, 6)) WHERE id = ?", (q, lote_id)
            )
        if faltante > EPS:
            conn.execute(
                "UPDATE productos SET faltante = ROUND(faltante + ?, 6) WHERE id = ?", (faltante, producto_id)
            )
    return r2(costo), consumos, faltante


def devolver(conn, producto_id, consumos, faltante):
    """Revierte un `descontar` (al anular una venta)."""
    with transaction(conn):
        for lote_id, q in consumos:
            conn.execute("UPDATE lotes SET restante = ROUND(restante + ?, 6) WHERE id = ?", (q, lote_id))
        if faltante > EPS:
            p = productos.obtener(conn, producto_id)
            cubre = min(p["faltante"], faltante)
            conn.execute(
                "UPDATE productos SET faltante = MAX(0, ROUND(faltante - ?, 6)) WHERE id = ?", (cubre, producto_id)
            )
            # Lo que ya había cubierto una entrada posterior vuelve a ese último lote.
            resto = r4(faltante - cubre)
            if resto > EPS:
                ultimo = conn.execute(
                    "SELECT id FROM lotes WHERE producto_id = ? ORDER BY fecha DESC, id DESC LIMIT 1", (producto_id,)
                ).fetchone()
                if ultimo:
                    conn.execute("UPDATE lotes SET restante = ROUND(restante + ?, 6) WHERE id = ?", (resto, ultimo["id"]))


def registrar_entrada(conn, producto_id, cantidad, costo_unitario, vence=None, precio=None, fecha=None):
    cantidad = numero(cantidad, "Escribe la cantidad que llegó.", positivo=True)
    costo_unitario = numero(costo_unitario or 0, "El costo no es válido.")
    vence = fecha_opcional(vence, "La fecha de vencimiento no es válida.")
    p = productos.obtener(conn, producto_id)
    with transaction(conn):
        cubre = min(p["faltante"], cantidad)
        lote_id = conn.execute(
            "INSERT INTO lotes (producto_id, origen, cantidad, restante, costo_unitario, vence, fecha)"
            " VALUES (?, 'entrada', ?, ?, ?, ?, ?)",
            (producto_id, r4(cantidad), r4(cantidad - cubre), r4(costo_unitario), vence, fecha or ahora()),
        ).lastrowid
        cambios = {"costo_ref": r2(costo_unitario), "faltante": r4(p["faltante"] - cubre)}
        if precio not in (None, ""):
            cambios["precio"] = r2(numero(precio, "El precio de venta no es válido.", positivo=True))
        conn.execute(
            f"UPDATE productos SET {', '.join(k + ' = ?' for k in cambios)} WHERE id = ?",
            (*cambios.values(), producto_id),
        )
    return lote_id


def registrar_perdida(conn, producto_id, cantidad, motivo, fecha=None):
    cantidad = numero(cantidad, "Escribe la cantidad.", positivo=True)
    motivo = texto(motivo, "Elige el motivo de la pérdida.", 60)
    with transaction(conn):
        costo, _, _ = descontar(conn, producto_id, cantidad)
        return conn.execute(
            "INSERT INTO perdidas (producto_id, cantidad, costo, motivo, fecha) VALUES (?, ?, ?, ?, ?)",
            (producto_id, r4(cantidad), costo, motivo, fecha or ahora()),
        ).lastrowid


def registrar_cambio(conn, producto_id, cantidad, vence, fecha=None):
    """El proveedor se lleva `cantidad` (lo que vence antes) y deja lo mismo con fecha nueva."""
    cantidad = numero(cantidad, "Pon la cantidad y la nueva fecha.", positivo=True)
    vence = fecha_opcional(vence, "La fecha de vencimiento no es válida.")
    if not vence:
        raise ErrorDeNegocio("Pon la cantidad y la nueva fecha.")
    fecha = fecha or ahora()
    with transaction(conn):
        costo, _, _ = descontar(conn, producto_id, cantidad)
        lote_id = conn.execute(
            "INSERT INTO lotes (producto_id, origen, cantidad, restante, costo_unitario, vence, fecha)"
            " VALUES (?, 'cambio', ?, ?, ?, ?, ?)",
            (producto_id, r4(cantidad), r4(cantidad), r4(costo / cantidad), vence, fecha),
        ).lastrowid
        # Si había faltante, el lote nuevo lo cubre igual que una entrada.
        p = productos.obtener(conn, producto_id)
        cubre = min(p["faltante"], cantidad)
        if cubre > EPS:
            conn.execute("UPDATE lotes SET restante = ROUND(restante - ?, 6) WHERE id = ?", (cubre, lote_id))
            conn.execute("UPDATE productos SET faltante = ROUND(faltante - ?, 6) WHERE id = ?", (cubre, producto_id))
        conn.execute(
            "INSERT INTO cambios (producto_id, cantidad, vence, lote_id, fecha) VALUES (?, ?, ?, ?, ?)",
            (producto_id, r4(cantidad), vence, lote_id, fecha),
        )
    return lote_id


def dias_para(vence, referencia=None):
    return (date.fromisoformat(vence) - (referencia or hoy())).days


def alertas(conn, referencia=None):
    referencia = referencia or hoy()
    vencidos, por_vencer = [], []
    filas = conn.execute(
        "SELECT l.id, l.producto_id, l.restante, l.vence, p.nombre, p.unidad FROM lotes l"
        " JOIN productos p ON p.id = l.producto_id"
        " WHERE p.archivado = 0 AND l.restante > ? AND l.vence IS NOT NULL ORDER BY l.vence",
        (EPS,),
    ).fetchall()
    for f in filas:
        n = dias_para(f["vence"], referencia)
        item = {"producto_id": f["producto_id"], "nombre": f["nombre"], "unidad": f["unidad"],
                "cantidad": r4(f["restante"]), "vence": f["vence"], "dias": n}
        if n < 0:
            vencidos.append(item)
        elif n <= AVISO_DIAS:
            por_vencer.append(item)
    bajo = [
        {"producto_id": p["id"], "nombre": p["nombre"], "unidad": p["unidad"], "stock": p["stock"]}
        for p in productos.listar(conn) if p["stock"] <= p["minimo"]
    ]
    bajo.sort(key=lambda x: x["stock"])
    total = len({x["producto_id"] for x in vencidos + por_vencer + bajo})
    return {"vencidos": vencidos, "por_vencer": por_vencer, "bajo": bajo, "productos_con_alerta": total,
            "aviso_dias": AVISO_DIAS}

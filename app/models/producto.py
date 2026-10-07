"""Catálogo de productos y su existencia actual."""
from ..db import transaction
from . import UNIDADES, ErrorDeNegocio, NoEncontrado, ahora, numero, r2, r4, texto

_CONSULTA = """
SELECT p.*,
       ROUND(COALESCE(SUM(l.restante), 0) - p.faltante, 4) AS stock,
       MIN(CASE WHEN l.restante > 1e-9 THEN l.vence END)    AS proximo_vence
  FROM productos p
  LEFT JOIN lotes l ON l.producto_id = p.id
"""


def _fila(r):
    d = dict(r)
    d["archivado"] = bool(d["archivado"])
    d["stock"] = r4(d["stock"])
    d["ganancia_unitaria"] = r2(d["precio"] - d["costo_ref"])
    return d


def listar(conn, incluir_archivados=False):
    where = "" if incluir_archivados else "WHERE p.archivado = 0"
    filas = conn.execute(f"{_CONSULTA} {where} GROUP BY p.id ORDER BY p.nombre COLLATE NOCASE").fetchall()
    return [_fila(r) for r in filas]


def obtener(conn, producto_id):
    r = conn.execute(f"{_CONSULTA} WHERE p.id = ? GROUP BY p.id", (producto_id,)).fetchone()
    if r is None:
        raise NoEncontrado("Ese producto no existe.")
    return _fila(r)


def validar(datos, actual=None):
    actual = actual or {}
    unidad = datos.get("unidad", actual.get("unidad", "unidad"))
    if unidad not in UNIDADES:
        raise ErrorDeNegocio("La unidad debe ser 'unidad' o 'lb'.")
    return {
        "nombre": texto(datos.get("nombre", actual.get("nombre")), "Pon el nombre y el precio de venta."),
        "unidad": unidad,
        "precio": r2(numero(datos.get("precio", actual.get("precio")), "Pon el nombre y el precio de venta.", positivo=True)),
        "minimo": r4(numero(datos.get("minimo", actual.get("minimo", 5)) or 0, "El mínimo no es válido.")),
        "costo_ref": r2(numero(datos.get("costo_ref", actual.get("costo_ref", 0)) or 0, "El costo no es válido.")),
    }


def crear(conn, datos, fecha=None):
    """Crea el producto y, si viene `cantidad_inicial`, registra esa existencia como primera entrada."""
    from . import inventario

    v = validar(datos)
    fecha = fecha or ahora()
    with transaction(conn):
        pid = conn.execute(
            "INSERT INTO productos (nombre, unidad, precio, minimo, costo_ref, archivado, creado)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (v["nombre"], v["unidad"], v["precio"], v["minimo"], v["costo_ref"], int(bool(datos.get("archivado"))), fecha),
        ).lastrowid
        inicial = datos.get("cantidad_inicial")
        if inicial not in (None, "") and float(inicial) > 0:
            inventario.registrar_entrada(conn, pid, inicial, v["costo_ref"], datos.get("vence"), fecha=fecha)
    return pid


def actualizar(conn, producto_id, datos):
    actual = obtener(conn, producto_id)
    v = validar(datos, actual)
    with transaction(conn):
        conn.execute(
            "UPDATE productos SET nombre = ?, unidad = ?, precio = ?, minimo = ?, costo_ref = ? WHERE id = ?",
            (v["nombre"], v["unidad"], v["precio"], v["minimo"], v["costo_ref"], producto_id),
        )
    return obtener(conn, producto_id)


def archivar(conn, producto_id):
    """Quita el producto de la lista sin borrar su historial de ventas."""
    obtener(conn, producto_id)
    with transaction(conn):
        conn.execute("UPDATE productos SET archivado = 1 WHERE id = ?", (producto_id,))


def detalle(conn, producto_id):
    from . import inventario

    p = obtener(conn, producto_id)
    p["lotes"] = [
        {"id": l["id"], "origen": l["origen"], "restante": r4(l["restante"]),
         "costo_unitario": r2(l["costo_unitario"]), "vence": l["vence"]}
        for l in inventario.lotes_disponibles(conn, producto_id)
    ]
    return p

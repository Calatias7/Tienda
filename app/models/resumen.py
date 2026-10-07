"""Resumen de un periodo: ventas, costo, pérdidas, fiado y ganancia neta."""
from datetime import date, timedelta

from . import ErrorDeNegocio, r2, r4
from . import cliente as clientes
from . import producto as productos
from . import venta as ventas


def periodo(conn, desde, hasta):
    """`desde` incluido, `hasta` excluido, ambos 'YYYY-MM-DD'."""
    try:
        d0, d1 = date.fromisoformat(desde), date.fromisoformat(hasta)
    except (TypeError, ValueError):
        raise ErrorDeNegocio("El periodo no es válido.") from None
    if d1 <= d0 or (d1 - d0).days > 400:
        raise ErrorDeNegocio("El periodo no es válido.")
    rango = (d0.isoformat(), d1.isoformat())

    v = conn.execute(
        "SELECT COUNT(*) n, COALESCE(SUM(total), 0) total, COALESCE(SUM(costo), 0) costo,"
        " COALESCE(SUM(CASE WHEN pago = 'fiado' THEN total END), 0) fiado"
        " FROM ventas WHERE anulada = 0 AND fecha >= ? AND fecha < ?", rango).fetchone()
    p = conn.execute(
        "SELECT COUNT(*) n, COALESCE(SUM(costo), 0) costo FROM perdidas WHERE fecha >= ? AND fecha < ?", rango
    ).fetchone()
    abonos = conn.execute(
        "SELECT COALESCE(SUM(monto), 0) FROM abonos WHERE fecha >= ? AND fecha < ?", rango).fetchone()[0]

    por_dia = {(d0 + timedelta(days=i)).isoformat(): 0.0 for i in range((d1 - d0).days)}
    for f in conn.execute(
        "SELECT substr(fecha, 1, 10) dia, SUM(total - costo) g FROM ventas"
        " WHERE anulada = 0 AND fecha >= ? AND fecha < ? GROUP BY dia", rango):
        por_dia[f["dia"]] = r2(f["g"])

    top = [
        {"producto_id": f["producto_id"], "nombre": f["nombre"], "unidad": f["unidad"],
         "cantidad": r4(f["cant"]), "vendido": r2(f["vendido"]), "ganancia": r2(f["ganancia"])}
        for f in conn.execute(
            "SELECT i.producto_id, COALESCE(pr.nombre, MAX(i.nombre)) nombre, MAX(i.unidad) unidad,"
            " SUM(i.cantidad) cant, SUM(i.cantidad * i.precio) vendido, SUM(i.cantidad * i.precio - i.costo) ganancia"
            " FROM venta_items i JOIN ventas v ON v.id = i.venta_id LEFT JOIN productos pr ON pr.id = i.producto_id"
            " WHERE v.anulada = 0 AND v.fecha >= ? AND v.fecha < ?"
            " GROUP BY i.producto_id ORDER BY ganancia DESC", rango)
    ]
    vendidos = {t["producto_id"] for t in top}
    sin_venta = [x["nombre"] for x in productos.listar(conn) if x["id"] not in vendidos]

    return {
        "desde": rango[0], "hasta": rango[1],
        "ventas": {"cantidad": v["n"], "total": r2(v["total"]), "costo": r2(v["costo"]), "fiado": r2(v["fiado"])},
        "perdidas": {"cantidad": p["n"], "costo": r2(p["costo"])},
        "ganancia_bruta": r2(v["total"] - v["costo"]),
        "ganancia_neta": r2(v["total"] - v["costo"] - p["costo"]),
        "abonos": r2(abonos),
        "por_cobrar": clientes.total_por_cobrar(conn),
        "ganancia_por_dia": [{"dia": k, "ganancia": r2(g)} for k, g in sorted(por_dia.items())],
        "top_productos": top,
        "sin_venta": sin_venta,
        "historial": ventas.listar(conn, *rango, limite=60),
        "historial_total": conn.execute(
            "SELECT COUNT(*) FROM ventas WHERE fecha >= ? AND fecha < ?", rango).fetchone()[0],
    }

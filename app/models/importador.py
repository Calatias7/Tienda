"""Importa una copia de seguridad (.json) de la versión anterior, que guardaba en el navegador.

Aquella versión guardaba una lista de eventos (entrada, venta, pérdida, cambio, abono, anular).
Aquí se vuelven a registrar en orden, con sus fechas originales, usando las mismas reglas
del resto de la aplicación.
"""
from datetime import datetime

from ..db import transaction
from . import ErrorDeNegocio, ahora
from . import cliente as clientes
from . import inventario
from . import producto as productos
from . import venta as ventas


def _fecha(ts):
    try:
        return datetime.fromtimestamp(float(ts) / 1000).strftime("%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError, OverflowError, OSError):
        return ahora()


def base_vacia(conn):
    return not any(conn.execute(f"SELECT 1 FROM {t} LIMIT 1").fetchone()
                   for t in ("productos", "clientes", "ventas", "abonos"))


def importar(conn, copia):
    if not isinstance(copia, dict) or copia.get("app") != "cuaderno-tienda" or not isinstance(copia.get("data"), dict):
        raise ErrorDeNegocio("Ese archivo no es una copia de seguridad del Cuaderno.")
    if not base_vacia(conn):
        raise ErrorDeNegocio("La base de datos ya tiene información. Solo se puede importar en una base vacía.")
    data = copia["data"]
    res = {"productos": 0, "clientes": 0, "ventas": 0, "entradas": 0, "perdidas": 0, "cambios": 0,
           "abonos": 0, "anuladas": 0, "omitidos": 0}
    with transaction(conn):
        pmap, cmap, vmap = {}, {}, {}
        for viejo, p in (data.get("productos") or {}).items():
            pmap[viejo] = productos.crear(conn, {
                "nombre": p.get("nombre"), "unidad": p.get("unidad", "unidad"), "precio": p.get("precio"),
                "minimo": p.get("minimo", 5), "costo_ref": p.get("costoRef") or 0, "archivado": p.get("archivado"),
            }, fecha=_fecha(p.get("creado")))
            res["productos"] += 1
        for viejo, c in (data.get("clientes") or {}).items():
            cmap[viejo] = clientes.crear(conn, c.get("nombre"), c.get("tel", ""), fecha=_fecha(c.get("creado")))
            res["clientes"] += 1

        eventos = [e for m in (data.get("movs") or {}).values() for e in (m or {}).get("items", [])
                   if isinstance(e, dict) and e.get("t")]
        eventos.sort(key=lambda e: (e.get("ts") or 0, str(e.get("id"))))
        for e in eventos:
            t, f = e["t"], _fecha(e.get("ts"))
            try:
                if t == "entrada" and e.get("p") in pmap:
                    inventario.registrar_entrada(conn, pmap[e["p"]], e["c"], e.get("cu") or 0, e.get("v") or None, fecha=f)
                    res["entradas"] += 1
                elif t == "venta":
                    items = [{"producto_id": pmap[i["p"]], "cantidad": i["c"], "precio": i.get("pr")}
                             for i in e.get("items", []) if i.get("p") in pmap]
                    fiado = e.get("pago") == "fiado" and e.get("cli") in cmap
                    vmap[e.get("id")] = ventas.registrar(conn, items, "fiado" if fiado else "contado",
                                                         cmap.get(e.get("cli")) if fiado else None, fecha=f,
                                                         con_precio=True)
                    res["ventas"] += 1
                elif t == "perdida" and e.get("p") in pmap:
                    inventario.registrar_perdida(conn, pmap[e["p"]], e["c"], e.get("m") or "Se perdió", fecha=f)
                    res["perdidas"] += 1
                elif t == "cambio" and e.get("p") in pmap:
                    inventario.registrar_cambio(conn, pmap[e["p"]], e["c"], e.get("v"), fecha=f)
                    res["cambios"] += 1
                elif t == "abono" and e.get("cli") in cmap:
                    clientes.registrar_abono(conn, cmap[e["cli"]], e["monto"], fecha=f, permitir_excedente=True)
                    res["abonos"] += 1
                elif t == "anular" and e.get("ref") in vmap:
                    ventas.anular(conn, vmap[e["ref"]], fecha=f)
                    res["anuladas"] += 1
                else:
                    res["omitidos"] += 1
            except (ErrorDeNegocio, KeyError, TypeError):
                res["omitidos"] += 1
    return res

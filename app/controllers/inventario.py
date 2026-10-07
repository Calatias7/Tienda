from flask import Blueprint, jsonify

from ..db import get_db
from ..models import inventario, producto
from . import cuerpo

bp = Blueprint("inventario", __name__, url_prefix="/api")


@bp.get("/inventario")
def resumen_inventario():
    db = get_db()
    return jsonify(productos=producto.listar(db), alertas=inventario.alertas(db))


@bp.post("/productos")
def crear_producto():
    db = get_db()
    pid = producto.crear(db, cuerpo())
    return jsonify(producto.obtener(db, pid)), 201


@bp.get("/productos/<int:pid>")
def ver_producto(pid):
    return jsonify(producto.detalle(get_db(), pid))


@bp.put("/productos/<int:pid>")
def editar_producto(pid):
    return jsonify(producto.actualizar(get_db(), pid, cuerpo()))


@bp.delete("/productos/<int:pid>")
def archivar_producto(pid):
    producto.archivar(get_db(), pid)
    return "", 204


@bp.post("/productos/<int:pid>/entradas")
def entrada(pid):
    d = cuerpo()
    db = get_db()
    inventario.registrar_entrada(db, pid, d.get("cantidad"), d.get("costo_unitario"), d.get("vence"), d.get("precio"))
    return jsonify(producto.obtener(db, pid)), 201


@bp.post("/productos/<int:pid>/perdidas")
def perdida(pid):
    d = cuerpo()
    db = get_db()
    inventario.registrar_perdida(db, pid, d.get("cantidad"), d.get("motivo"))
    return jsonify(producto.obtener(db, pid)), 201


@bp.post("/productos/<int:pid>/cambios")
def cambio(pid):
    d = cuerpo()
    db = get_db()
    inventario.registrar_cambio(db, pid, d.get("cantidad"), d.get("vence"))
    return jsonify(producto.obtener(db, pid)), 201

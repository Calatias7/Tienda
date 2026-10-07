from flask import Blueprint, jsonify

from ..db import get_db
from ..models import venta
from . import cuerpo

bp = Blueprint("ventas", __name__, url_prefix="/api")


@bp.post("/cotizar")
def cotizar():
    return jsonify(venta.cotizar(get_db(), cuerpo().get("items")))


@bp.post("/ventas")
def registrar():
    d = cuerpo()
    db = get_db()
    vid = venta.registrar(db, d.get("items"), d.get("pago", "contado"), d.get("cliente_id"))
    return jsonify(venta.obtener(db, vid)), 201


@bp.get("/ventas/<int:vid>")
def ver(vid):
    return jsonify(venta.obtener(get_db(), vid))


@bp.post("/ventas/<int:vid>/anular")
def anular(vid):
    db = get_db()
    venta.anular(db, vid)
    return jsonify(venta.obtener(db, vid))

from flask import Blueprint, jsonify

from ..db import get_db
from ..models import cliente
from . import cuerpo

bp = Blueprint("clientes", __name__, url_prefix="/api/clientes")


@bp.get("")
def listar():
    db = get_db()
    return jsonify(clientes=cliente.listar(db), por_cobrar=cliente.total_por_cobrar(db))


@bp.post("")
def crear():
    d = cuerpo()
    db = get_db()
    cid = cliente.crear(db, d.get("nombre"), d.get("telefono", ""))
    return jsonify(cliente.obtener(db, cid)), 201


@bp.get("/<int:cid>")
def ver(cid):
    return jsonify(cliente.detalle(get_db(), cid))


@bp.post("/<int:cid>/abonos")
def abonar(cid):
    db = get_db()
    cliente.registrar_abono(db, cid, cuerpo().get("monto"))
    return jsonify(cliente.obtener(db, cid)), 201

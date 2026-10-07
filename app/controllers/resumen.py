from flask import Blueprint, jsonify, request

from ..db import get_db
from ..models import resumen

bp = Blueprint("resumen", __name__, url_prefix="/api")


@bp.get("/resumen")
def periodo():
    return jsonify(resumen.periodo(get_db(), request.args.get("desde"), request.args.get("hasta")))

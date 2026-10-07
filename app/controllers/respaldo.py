"""Copias de seguridad: descargar la base de datos e importar datos de la versión anterior."""
import io
import json
import sqlite3
import tempfile
from datetime import date
from pathlib import Path

from flask import Blueprint, jsonify, request, send_file

from ..db import get_db
from ..models import ErrorDeNegocio, importador

bp = Blueprint("respaldo", __name__, url_prefix="/api/respaldo")


@bp.get("")
def descargar():
    # La API de respaldo de SQLite copia la base de forma consistente aunque esté en uso.
    with tempfile.TemporaryDirectory() as tmp:
        destino = Path(tmp) / "copia.db"
        copia = sqlite3.connect(destino)
        try:
            get_db().backup(copia)
        finally:
            copia.close()
        datos = destino.read_bytes()
    return send_file(io.BytesIO(datos), mimetype="application/vnd.sqlite3", as_attachment=True,
                     download_name=f"cuaderno-tienda-{date.today().isoformat()}.db")


@bp.post("/importar")
def importar():
    archivo = request.files.get("archivo")
    if archivo is None:
        raise ErrorDeNegocio("Elige el archivo .json de la copia.")
    try:
        copia = json.load(archivo.stream)
    except (ValueError, UnicodeDecodeError):
        raise ErrorDeNegocio("Ese archivo no es una copia de seguridad del Cuaderno.") from None
    return jsonify(importador.importar(get_db(), copia))

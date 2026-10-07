"""Controladores: reciben la petición HTTP, llaman al modelo y devuelven la vista o JSON."""
from flask import jsonify, request

from ..models import ErrorDeNegocio, NoEncontrado


def cuerpo():
    datos = request.get_json(silent=True)
    if not isinstance(datos, dict):
        raise ErrorDeNegocio("La petición no tiene datos válidos.")
    return datos


def registrar_errores(app):
    @app.errorhandler(ErrorDeNegocio)
    def _negocio(e):
        return jsonify(error=str(e)), 400

    @app.errorhandler(NoEncontrado)
    def _no_encontrado(e):
        return jsonify(error=str(e)), 404


def registrar_blueprints(app):
    from . import clientes, inicio, inventario, respaldo, resumen, ventas

    for m in (inicio, inventario, ventas, clientes, resumen, respaldo):
        app.register_blueprint(m.bp)

"""Cuaderno de la Tienda: aplicación Flask con arquitectura MVC sobre SQLite.

- models/       reglas de negocio y acceso a la base de datos
- views/        plantillas HTML (Jinja) que ve el usuario
- static/       estilos y JavaScript de la interfaz
- controllers/  rutas HTTP que conectan las vistas con los modelos
"""
import json
from pathlib import Path

import click
from flask import Flask

from . import db
from .controllers import registrar_blueprints, registrar_errores

RAIZ = Path(__file__).resolve().parent.parent


def create_app(config=None):
    app = Flask(__name__, template_folder="views", static_folder="static")
    app.config.update(
        DATABASE=str(RAIZ / "datos" / "tienda.db"),
        MAX_CONTENT_LENGTH=20 * 1024 * 1024,
    )
    app.json.ensure_ascii = False
    app.json.sort_keys = False
    if config:
        app.config.update(config)

    db.init_db(app.config["DATABASE"])
    app.teardown_appcontext(db.close_db)
    registrar_errores(app)
    registrar_blueprints(app)

    @app.cli.command("importar")
    @click.argument("archivo", type=click.Path(exists=True, dir_okay=False))
    def importar_cmd(archivo):
        """Importa una copia .json de la versión anterior (solo en una base vacía)."""
        from .models import importador

        with open(archivo, encoding="utf-8") as f:
            res = importador.importar(db.get_db(), json.load(f))
        click.echo(", ".join(f"{k}: {v}" for k, v in res.items()))

    return app

from flask import Blueprint, render_template

bp = Blueprint("inicio", __name__)


@bp.get("/")
def index():
    return render_template("index.html")

"""Modelos: acceso a datos y reglas de negocio de la tienda.

Cada función recibe una conexión SQLite. Las que escriben abren su propia transacción
(o se suman a la que ya esté abierta), así que se pueden combinar sin dejar datos a medias.
"""
from datetime import date, datetime

EPS = 1e-9
UNIDADES = ("unidad", "lb")


class ErrorDeNegocio(ValueError):
    """Dato inválido o regla de la tienda que no se cumple. El mensaje se muestra al usuario."""


class NoEncontrado(LookupError):
    pass


def r2(n):
    return round(float(n or 0), 2) + 0.0


def r4(n):
    v = round(float(n or 0), 6)
    return 0.0 if abs(v) < EPS else v


def ahora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def hoy():
    return date.today()


def numero(valor, mensaje, minimo=0.0, positivo=False):
    try:
        n = float(valor)
    except (TypeError, ValueError):
        raise ErrorDeNegocio(mensaje) from None
    if n != n or n < minimo or (positivo and n <= 0):
        raise ErrorDeNegocio(mensaje)
    return n


def fecha_opcional(valor, mensaje="La fecha no es válida."):
    if valor in (None, ""):
        return None
    try:
        return date.fromisoformat(str(valor)).isoformat()
    except ValueError:
        raise ErrorDeNegocio(mensaje) from None


def texto(valor, mensaje, largo=120):
    t = str(valor or "").strip()
    if not t:
        raise ErrorDeNegocio(mensaje)
    return t[:largo]

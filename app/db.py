"""Conexión a SQLite: una conexión por petición y transacciones explícitas."""
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from flask import current_app, g

SCHEMA = Path(__file__).with_name("schema.sql")


def connect(path):
    conn = sqlite3.connect(path, isolation_level=None, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def get_db():
    if "db" not in g:
        g.db = connect(current_app.config["DATABASE"])
    return g.db


def close_db(_exc=None):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def init_db(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = connect(path)
    try:
        conn.executescript(SCHEMA.read_text(encoding="utf-8"))
    finally:
        conn.close()


@contextmanager
def transaction(conn):
    """Agrupa varias escrituras: o se guardan todas o ninguna.

    Dentro de otra transacción usa un SAVEPOINT, así un error deshace solo esta parte.
    """
    if conn.in_transaction:
        conn.execute("SAVEPOINT sp")
        try:
            yield conn
        except BaseException:
            conn.execute("ROLLBACK TO sp")
            conn.execute("RELEASE sp")
            raise
        else:
            conn.execute("RELEASE sp")
        return
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    else:
        conn.execute("COMMIT")

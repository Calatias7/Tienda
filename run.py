"""Arranca el Cuaderno de la Tienda en esta computadora.

    python run.py                 # http://localhost:5000
    python run.py --puerto 8080
    python run.py --db otra.db    # usar otro archivo de base de datos
    python run.py --red           # también accesible desde el celular en la misma WiFi
"""
import argparse
import socket
import webbrowser

from waitress import serve

from app import create_app


def ip_local():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))
            return s.getsockname()[0]
    except OSError:
        return None


def main():
    ap = argparse.ArgumentParser(description="Cuaderno de la Tienda")
    ap.add_argument("--puerto", type=int, default=5000)
    ap.add_argument("--red", action="store_true", help="aceptar conexiones de otros equipos de la red local")
    ap.add_argument("--db", help="archivo de base de datos a usar (por defecto datos/tienda.db)")
    ap.add_argument("--sin-navegador", action="store_true", help="no abrir el navegador al iniciar")
    args = ap.parse_args()

    app = create_app({"DATABASE": args.db} if args.db else None)
    host = "0.0.0.0" if args.red else "127.0.0.1"
    url = f"http://localhost:{args.puerto}"
    print(f"Cuaderno de la Tienda abierto en {url}")
    if args.red and (ip := ip_local()):
        print(f"Desde el celular (misma WiFi): http://{ip}:{args.puerto}")
    print(f"Base de datos: {app.config['DATABASE']}")
    print("Para cerrar, presiona Ctrl+C.")
    if not args.sin_navegador:
        webbrowser.open(url)
    serve(app, host=host, port=args.puerto, threads=8)


if __name__ == "__main__":
    main()

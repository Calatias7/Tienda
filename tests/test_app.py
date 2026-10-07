import io
import json
import os
import tempfile
import unittest
from datetime import date, timedelta

from app import create_app
from app.db import get_db
from app.models import ErrorDeNegocio, cliente, importador, inventario, producto, resumen, venta


def dia(n):
    return (date.today() + timedelta(days=n)).isoformat()


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = create_app({"DATABASE": os.path.join(self.tmp.name, "t.db"), "TESTING": True})
        self.ctx = self.app.app_context()
        self.ctx.push()
        self.db = get_db()

    def tearDown(self):
        self.ctx.pop()
        self.tmp.cleanup()

    def arroz(self, **extra):
        datos = {"nombre": "Arroz", "unidad": "lb", "precio": 5, "costo_ref": 3.5,
                 "cantidad_inicial": 10, "vence": dia(2)}
        datos.update(extra)
        return producto.crear(self.db, datos)


class TestInventario(Base):
    def test_venta_descuenta_primero_lo_que_vence_antes(self):
        a = self.arroz()
        inventario.registrar_entrada(self.db, a, 20, 4, dia(60))
        self.assertEqual(venta.cotizar(self.db, [{"producto_id": a, "cantidad": 12}])["costo"], 43.0)
        vid = venta.registrar(self.db, [{"producto_id": a, "cantidad": 12}])
        v = venta.obtener(self.db, vid)
        self.assertEqual((v["total"], v["costo"], v["ganancia"]), (60.0, 43.0, 17.0))
        lotes = producto.detalle(self.db, a)["lotes"]
        self.assertEqual([l["restante"] for l in lotes], [18.0])

    def test_faltante_lo_cubre_la_siguiente_entrada(self):
        a = self.arroz()
        venta.registrar(self.db, [{"producto_id": a, "cantidad": 15}])
        self.assertEqual(producto.obtener(self.db, a)["stock"], -5.0)
        inventario.registrar_entrada(self.db, a, 8, 4)
        p = producto.obtener(self.db, a)
        self.assertEqual((p["stock"], p["faltante"], p["costo_ref"]), (3.0, 0.0, 4.0))

    def test_anular_devuelve_inventario_y_saldo(self):
        a = self.arroz()
        c = cliente.crear(self.db, "Doña Marta")
        vid = venta.registrar(self.db, [{"producto_id": a, "cantidad": 4}], "fiado", c)
        self.assertEqual(cliente.obtener(self.db, c)["saldo"], 20.0)
        venta.anular(self.db, vid)
        self.assertEqual(producto.obtener(self.db, a)["stock"], 10.0)
        self.assertEqual(cliente.obtener(self.db, c)["saldo"], 0.0)
        with self.assertRaises(ErrorDeNegocio):
            venta.anular(self.db, vid)

    def test_anular_venta_con_faltante_ya_cubierto(self):
        a = self.arroz()
        vid = venta.registrar(self.db, [{"producto_id": a, "cantidad": 15}])
        inventario.registrar_entrada(self.db, a, 10, 4)
        venta.anular(self.db, vid)
        self.assertEqual(producto.obtener(self.db, a)["stock"], 20.0)

    def test_perdida_y_cambio(self):
        a = self.arroz()
        inventario.registrar_perdida(self.db, a, 2, "Se dañó")
        inventario.registrar_cambio(self.db, a, 8, dia(90))
        p = producto.detalle(self.db, a)
        self.assertEqual(p["stock"], 8.0)
        self.assertEqual(p["lotes"][0]["vence"], dia(90))
        self.assertEqual(p["lotes"][0]["costo_unitario"], 3.5)

    def test_alertas(self):
        self.arroz()
        producto.crear(self.db, {"nombre": "Leche", "precio": 9, "cantidad_inicial": 3, "vence": dia(-1)})
        al = inventario.alertas(self.db)
        self.assertEqual([x["nombre"] for x in al["vencidos"]], ["Leche"])
        self.assertEqual([x["nombre"] for x in al["por_vencer"]], ["Arroz"])
        self.assertEqual([x["nombre"] for x in al["bajo"]], ["Leche"])
        self.assertEqual(al["productos_con_alerta"], 2)

    def test_validaciones(self):
        with self.assertRaises(ErrorDeNegocio):
            producto.crear(self.db, {"nombre": "", "precio": 5})
        with self.assertRaises(ErrorDeNegocio):
            producto.crear(self.db, {"nombre": "X", "precio": 0})
        a = self.arroz()
        with self.assertRaises(ErrorDeNegocio):
            venta.registrar(self.db, [{"producto_id": a, "cantidad": 1}], "fiado")
        with self.assertRaises(ErrorDeNegocio):
            venta.registrar(self.db, [])
        c = cliente.crear(self.db, "Juan")
        with self.assertRaises(ErrorDeNegocio):
            cliente.registrar_abono(self.db, c, 5)  # no debe nada

    def test_venta_fallida_no_deja_datos_a_medias(self):
        a = self.arroz()
        with self.assertRaises(Exception):
            venta.registrar(self.db, [{"producto_id": a, "cantidad": 2}, {"producto_id": 999, "cantidad": 1}])
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM ventas").fetchone()[0], 0)
        self.assertEqual(producto.obtener(self.db, a)["stock"], 10.0)


class TestResumen(Base):
    def test_periodo(self):
        a = self.arroz()
        c = cliente.crear(self.db, "Ana")
        venta.registrar(self.db, [{"producto_id": a, "cantidad": 2}])
        venta.registrar(self.db, [{"producto_id": a, "cantidad": 4}], "fiado", c)
        cliente.registrar_abono(self.db, c, 5)
        inventario.registrar_perdida(self.db, a, 1, "Se dañó")
        r = resumen.periodo(self.db, dia(0), dia(1))
        self.assertEqual(r["ventas"], {"cantidad": 2, "total": 30.0, "costo": 21.0, "fiado": 20.0})
        self.assertEqual(r["ganancia_neta"], 5.5)
        self.assertEqual(r["abonos"], 5.0)
        self.assertEqual(r["por_cobrar"], 15.0)
        self.assertEqual(r["top_productos"][0]["ganancia"], 9.0)
        self.assertEqual(r["ganancia_por_dia"], [{"dia": dia(0), "ganancia": 9.0}])


class TestApi(Base):
    def test_flujo_completo(self):
        cl = self.app.test_client()
        self.assertEqual(cl.get("/").status_code, 200)
        r = cl.post("/api/productos", json={"nombre": "Gaseosa", "precio": 6, "costo_ref": 4, "cantidad_inicial": 24})
        self.assertEqual(r.status_code, 201)
        pid = r.get_json()["id"]
        self.assertEqual(cl.post("/api/productos", json={"nombre": ""}).status_code, 400)
        r = cl.post("/api/ventas", json={"items": [{"producto_id": pid, "cantidad": 3, "precio": 0.01}]})
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.get_json()["total"], 18.0)  # el precio lo pone el servidor
        inv = cl.get("/api/inventario").get_json()
        self.assertEqual(inv["productos"][0]["stock"], 21.0)
        r = cl.post(f"/api/ventas/{r.get_json()['id']}/anular")
        self.assertTrue(r.get_json()["anulada"])
        self.assertEqual(cl.get("/api/productos/999").status_code, 404)
        r = cl.get(f"/api/resumen?desde={dia(0)}&hasta={dia(1)}")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(cl.get("/api/resumen?desde=x&hasta=y").status_code, 400)
        r = cl.get("/api/respaldo")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.data.startswith(b"SQLite format 3"))


COPIA_VIEJA = {
    "app": "cuaderno-tienda", "v": 1,
    "data": {
        "productos": {"p1": {"nombre": "Azúcar", "unidad": "lb", "precio": 4.5, "minimo": 5, "costoRef": 3},
                      "p2": {"nombre": "Pan", "unidad": "unidad", "precio": 1, "minimo": 10, "costoRef": 0.6}},
        "clientes": {"c1": {"nombre": "Doña Marta", "tel": ""}},
        "movs": {
            "b1": {"items": [
                {"id": "e1", "t": "entrada", "p": "p1", "c": 50, "cu": 3, "v": "", "ts": 1759700000000},
                {"id": "e2", "t": "entrada", "p": "p2", "c": 40, "cu": 0.6, "v": "", "ts": 1759700001000},
                {"id": "v1", "t": "venta", "pago": "fiado", "cli": "c1", "total": 9, "costo": 6,
                 "items": [{"p": "p1", "n": "Azúcar", "u": "lb", "c": 2, "pr": 4.5, "co": 6}], "ts": 1759700100000},
            ]},
            "b2": {"items": [
                {"id": "v2", "t": "venta", "pago": "contado", "cli": "", "total": 5, "costo": 3,
                 "items": [{"p": "p2", "n": "Pan", "u": "unidad", "c": 5, "pr": 1, "co": 3}], "ts": 1759700200000},
                {"id": "a1", "t": "abono", "cli": "c1", "monto": 4, "ts": 1759700300000},
                {"id": "x1", "t": "anular", "ref": "v2", "ts": 1759700400000},
                {"id": "l1", "t": "perdida", "p": "p1", "c": 1, "co": 3, "m": "Se dañó", "ts": 1759700500000},
            ]},
        },
    },
}


class TestImportador(Base):
    def test_importa_copia_vieja(self):
        res = importador.importar(self.db, json.loads(json.dumps(COPIA_VIEJA)))
        self.assertEqual(res["omitidos"], 0)
        self.assertEqual((res["productos"], res["ventas"], res["anuladas"]), (2, 2, 1))
        stock = {p["nombre"]: p["stock"] for p in producto.listar(self.db)}
        self.assertEqual(stock, {"Azúcar": 47.0, "Pan": 40.0})
        marta = cliente.listar(self.db)[0]
        self.assertEqual(marta["saldo"], 5.0)
        with self.assertRaises(ErrorDeNegocio):
            importador.importar(self.db, COPIA_VIEJA)  # la base ya no está vacía

    def test_importa_por_api(self):
        cl = self.app.test_client()
        r = cl.post("/api/respaldo/importar", data={"archivo": (io.BytesIO(json.dumps(COPIA_VIEJA).encode()), "c.json")},
                    content_type="multipart/form-data")
        self.assertEqual(r.status_code, 200, r.get_json())
        r = cl.post("/api/respaldo/importar", data={"archivo": (io.BytesIO(b"no es json"), "c.json")},
                    content_type="multipart/form-data")
        self.assertEqual(r.status_code, 400)


if __name__ == "__main__":
    unittest.main()

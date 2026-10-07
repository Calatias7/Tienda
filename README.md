# Cuaderno de la Tienda

Aplicación web para llevar el inventario de una tienda de abarrotes: ventas, existencias, fechas de vencimiento, fiado y ganancia real, en quetzales (Q).

Funciona en tu computadora con un pequeño servidor en Python y guarda todo en una base de datos SQLite (`datos/tienda.db`).

## Qué hace

- **Vender:** toca los productos, cobra (calcula el vuelto) o fía a un cliente. Lo que se vende por libra acepta cantidades como 2.5 lb o un monto, por ejemplo "Q10 de arroz".
- **Inventario:**
  - Registra entradas de mercancía con costo y fecha de vencimiento.
  - Registra pérdidas (vencido, dañado) y cambios con el proveedor.
  - Avisa lo que vence en 7 días o menos y lo que está bajo el mínimo.
- **Fiado:** saldo por cliente, historial y abonos.
- **Resumen:** ventas, costo, pérdidas y ganancia neta por semana o por mes, ganancia por día y los productos que más ganancia dejan. Desde aquí se puede anular una venta; el inventario vuelve a su lugar.
- **Respaldo:** descarga una copia de la base de datos o importa los datos de la versión anterior.

La ganancia usa el costo real de cada entrada. Las ventas descuentan primero lo que vence antes.

## Cómo usarla

Necesitas [Python 3.10 o más reciente](https://www.python.org/downloads/) (al instalarlo en Windows, marca "Add Python to PATH").

**En Windows:** haz doble clic en `iniciar.bat`. La primera vez instala lo necesario; después abre el navegador en `http://localhost:5000`. Para cerrar, cierra esa ventana negra.

**A mano (cualquier sistema):**

```bash
python -m venv .venv
.venv\Scripts\activate          # en Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

Opciones de `run.py`:

| Opción | Para qué |
|---|---|
| `--puerto 8080` | Usar otro puerto (por defecto 5000). |
| `--red` | Abrirla también desde el celular u otra compu conectada a la misma WiFi. Al iniciar muestra la dirección, por ejemplo `http://192.168.1.20:5000`. |
| `--db ruta.db` | Usar otro archivo de base de datos. |
| `--sin-navegador` | No abrir el navegador al iniciar. |

Con `--red` varias personas pueden vender a la vez y comparten los mismos datos. La compu donde corre el programa tiene que estar encendida. Windows puede pedir permiso en el firewall la primera vez.

## Dónde se guardan los datos

Todo queda en `datos/tienda.db`. Esa carpeta no se sube al repositorio.

- **Haz respaldo cada semana:** botón **Respaldo → Descargar copia (.db)** y guarda el archivo en una USB o en la nube.
- **Para restaurar una copia:** cierra el programa, reemplaza `datos/tienda.db` por el archivo descargado (renómbralo a `tienda.db`) y vuelve a abrirlo.

### Pasar los datos de la versión anterior

La versión anterior era un solo `index.html` que guardaba en el navegador.

1. Abre la versión anterior y toca **Descargar copia** para obtener el `.json`.
2. En esta versión, toca **Respaldo → Importar copia anterior (.json)**.

Solo funciona con la base de datos vacía. También se puede hacer desde la terminal:

```bash
flask --app app importar cuaderno-tienda-2026-10-01.json
```

## Cómo está hecha (para programadores)

Flask + SQLite con arquitectura MVC. No usa ORM, solo `sqlite3` de Python y consultas parametrizadas.

```
app/
  __init__.py         fábrica de la aplicación (create_app) y comando `importar`
  db.py               conexión por petición y transacciones (BEGIN IMMEDIATE / SAVEPOINT)
  schema.sql          tablas: productos, clientes, lotes, ventas, venta_items,
                      venta_item_lotes, perdidas, cambios, abonos
  models/             MODELO: reglas de negocio y acceso a datos
    producto.py       catálogo y existencia (suma de lotes − faltante)
    inventario.py     lotes, salida por vencimiento (FIFO por fecha), entradas, pérdidas, cambios, alertas
    venta.py          cotizar, registrar y anular ventas
    cliente.py        clientes, saldo de fiado y abonos
    resumen.py        indicadores de un periodo
    importador.py     migra la copia .json de la versión anterior
  controllers/        CONTROLADOR: rutas HTTP (blueprints) que llaman a los modelos
  views/index.html    VISTA: plantilla Jinja de la página
  static/             VISTA: estilos y JavaScript de la interfaz (api.js habla con el servidor)
run.py                arranca el servidor (waitress)
tests/                pruebas automáticas
```

Reglas importantes del modelo:

- Cada entrada crea un **lote** con su cantidad, costo y vencimiento. Ventas, pérdidas y cambios descuentan primero el lote que vence antes, y el costo de la venta es el de esos lotes.
- Si se vende más de lo registrado, la diferencia queda como **faltante** del producto y la próxima entrada la cubre.
- `venta_item_lotes` guarda de qué lote salió cada venta, para que **anular** devuelva el inventario exacto.
- El precio de venta lo pone siempre el servidor; el navegador solo manda producto y cantidad.

### API

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/inventario` | Productos con existencia y alertas |
| POST | `/api/productos` | Crear producto (opcional `cantidad_inicial`, `vence`) |
| GET / PUT / DELETE | `/api/productos/<id>` | Ver con lotes / editar / quitar de la lista |
| POST | `/api/productos/<id>/entradas` | `cantidad`, `costo_unitario`, `vence`, `precio` |
| POST | `/api/productos/<id>/perdidas` | `cantidad`, `motivo` |
| POST | `/api/productos/<id>/cambios` | `cantidad`, `vence` |
| POST | `/api/cotizar` | Total, costo y ganancia de un carrito sin registrarlo |
| POST | `/api/ventas` | `items: [{producto_id, cantidad}]`, `pago: contado/fiado`, `cliente_id` |
| POST | `/api/ventas/<id>/anular` | Anula y devuelve el inventario |
| GET / POST | `/api/clientes` | Lista con saldos / crear |
| GET | `/api/clientes/<id>` | Detalle con historial |
| POST | `/api/clientes/<id>/abonos` | `monto` |
| GET | `/api/resumen?desde=AAAA-MM-DD&hasta=AAAA-MM-DD` | Indicadores del periodo (`hasta` no incluido) |
| GET | `/api/respaldo` | Descarga la base de datos |
| POST | `/api/respaldo/importar` | Importa la copia `.json` de la versión anterior |

Los errores de validación responden `400 {"error": "mensaje"}`.

### Pruebas

```bash
python -m unittest discover -s tests -t . -v
```

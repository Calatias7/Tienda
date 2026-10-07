# Cuaderno de la Tienda

Aplicación web para llevar el inventario de una tienda de abarrotes: ventas, existencias, fechas de vencimiento, fiado y ganancia real, en quetzales (Q).

Es un solo archivo, `index.html`. No necesita instalar nada ni servidor.

## Qué hace

- **Vender:** toca los productos, cobra (calcula el vuelto) o fía a un cliente. Lo que se vende por libra acepta cantidades como 2.5 lb o un monto, por ejemplo "Q10 de arroz".
- **Inventario:**
  - Registra entradas de mercancía con costo y fecha de vencimiento.
  - Registra pérdidas (vencido, dañado) y cambios con el proveedor.
  - Avisa lo que vence en 7 días o menos y lo que está bajo el mínimo.
- **Fiado:** saldo por cliente, historial y abonos.
- **Resumen:** ventas, costo, pérdidas y ganancia neta por semana o por mes, ganancia por día y los productos que más ganancia dejan.

La ganancia usa el costo real de cada entrada. Las ventas descuentan primero lo que vence antes.

## Cómo usarla

**En tu computadora:** abre `index.html` con Chrome, Edge o Firefox.

**En internet con GitHub Pages:**

1. Sube esta carpeta a un repositorio de GitHub.
2. En el repositorio, ve a **Settings → Pages**.
3. En "Branch", elige `main` y la carpeta `/ (root)`, y guarda.
4. En un par de minutos queda en `https://<tu-usuario>.github.io/<nombre-del-repo>/`.

## Dónde se guardan los datos

Abierta desde un archivo o desde GitHub Pages, la app funciona en **modo local**: los datos quedan guardados en el navegador de ese equipo.

- El celular y la computadora **no comparten** datos entre sí.
- Si borras los datos del navegador, se pierden. Usa **Descargar copia** (arriba en la app) cada semana y guarda el archivo `.json`. Con **Restaurar copia** lo recuperas, también en otro equipo.
- El repositorio solo guarda el programa, nunca tus ventas ni tus clientes.

Para que varias personas compartan los mismos datos en vivo, usa la versión publicada en claude.ai, que guarda en la nube.

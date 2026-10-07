/* Cliente de la API del servidor. Toda la lógica de negocio vive en el servidor (modelos). */
window.Api = (() => {
  "use strict";
  async function pedir(method, url, body) {
    const opt = {method, headers: {}};
    if (body instanceof FormData) opt.body = body;
    else if (body !== undefined) { opt.headers["Content-Type"] = "application/json"; opt.body = JSON.stringify(body); }
    let res;
    try { res = await fetch(url, opt); }
    catch { throw new Error("No hay conexión con el servidor. ¿Está abierto el programa?"); }
    if (res.status === 204) return null;
    const data = await res.json().catch(() => null);
    if (!res.ok) throw new Error(data?.error || "No se pudo completar la operación.");
    return data;
  }
  const qs = o => new URLSearchParams(o).toString();
  return {
    inventario: () => pedir("GET", "/api/inventario"),
    producto: id => pedir("GET", `/api/productos/${id}`),
    crearProducto: d => pedir("POST", "/api/productos", d),
    editarProducto: (id, d) => pedir("PUT", `/api/productos/${id}`, d),
    archivarProducto: id => pedir("DELETE", `/api/productos/${id}`),
    entrada: (id, d) => pedir("POST", `/api/productos/${id}/entradas`, d),
    perdida: (id, d) => pedir("POST", `/api/productos/${id}/perdidas`, d),
    cambio: (id, d) => pedir("POST", `/api/productos/${id}/cambios`, d),
    cotizar: items => pedir("POST", "/api/cotizar", {items}),
    vender: d => pedir("POST", "/api/ventas", d),
    anular: id => pedir("POST", `/api/ventas/${id}/anular`),
    clientes: () => pedir("GET", "/api/clientes"),
    cliente: id => pedir("GET", `/api/clientes/${id}`),
    crearCliente: d => pedir("POST", "/api/clientes", d),
    abonar: (id, monto) => pedir("POST", `/api/clientes/${id}/abonos`, {monto}),
    resumen: (desde, hasta) => pedir("GET", "/api/resumen?" + qs({desde, hasta})),
    importar: archivo => { const f = new FormData(); f.append("archivo", archivo); return pedir("POST", "/api/respaldo/importar", f); },
  };
})();

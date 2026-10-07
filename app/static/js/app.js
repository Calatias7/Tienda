/* Interfaz del Cuaderno de la Tienda. Muestra los datos del servidor y envía las acciones a la API. */
(() => {
"use strict";
/* ---------- utilidades ---------- */
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const r2 = n => Math.round((+n || 0) * 100) / 100;
const fmtN = n => r2(n).toLocaleString("es-GT", {maximumFractionDigits: 2});
const Q = n => (r2(n) < 0 ? "−" : "") + "Q" + Math.abs(r2(n)).toLocaleString("es-GT", {minimumFractionDigits: 2, maximumFractionDigits: 2});
const cantTxt = (n, u) => u === "lb" ? fmtN(n) + " lb" : fmtN(n);
const pad = n => String(n).padStart(2, "0");
const ymd = d => d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate());
const hoy = () => ymd(new Date());
const dias = v => v ? Math.round((new Date(v + "T12:00:00") - new Date(hoy() + "T12:00:00")) / 864e5) : null;
const MES = ["ene","feb","mar","abr","may","jun","jul","ago","sep","oct","nov","dic"];
const MESL = ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"];
const fFecha = v => { if (!v) return "sin fecha"; const [y, m, d] = v.split("-"); return +d + " " + MES[+m - 1] + (y != new Date().getFullYear() ? " " + y : ""); };
const fTs = s => s ? fFecha(s.slice(0, 10)) + ", " + s.slice(11, 16) : "";
const venceTxt = v => { const n = dias(v); if (n === null) return ""; if (n < 0) return "vencido hace " + (-n) + (n === -1 ? " día" : " días"); if (n === 0) return "vence hoy"; if (n === 1) return "vence mañana"; return "vence en " + n + " días"; };
const itemsTxt = items => items.map(i => cantTxt(i.cantidad, i.unidad) + " " + i.nombre).join(", ");
let AVISO_DIAS = 7;

/* ---------- estado ---------- */
const S = {
  prods: [], pmap: {}, alertas: null, clis: [], porCobrar: 0, loaded: false,
  view: "vender", cart: [], cartOpen: false, cotiz: null, periodo: "semana", offset: 0
};
const prod = id => S.pmap[id];

async function cargar() {
  try {
    const [inv, cl] = await Promise.all([Api.inventario(), Api.clientes()]);
    S.prods = inv.productos; S.pmap = Object.fromEntries(inv.productos.map(p => [p.id, p]));
    S.alertas = inv.alertas; AVISO_DIAS = inv.alertas.aviso_dias;
    S.clis = cl.clientes; S.porCobrar = cl.por_cobrar;
    S.loaded = true; setSync("ok");
  } catch (e) { setSync("off"); toast(e.message); }
  render();
}
function setSync(s) {
  const el = $("#sync"); el.dataset.s = s;
  $("span", el).textContent = {loading: "Conectando…", ok: "Guardado en la base de datos", off: "Sin conexión con el servidor"}[s];
}
/* Ejecuta una acción del servidor, evita doble envío y recarga los datos al terminar. */
async function accion(btn, fn, msg) {
  if (btn) btn.disabled = true;
  try {
    const r = await fn();
    await cargar();
    if (msg) toast(typeof msg === "function" ? msg(r) : msg);
    return r ?? true;
  } catch (e) { toast(e.message); return false; }
  finally { if (btn) btn.disabled = false; }
}

/* ---------- render ---------- */
function render() {
  for (const v of ["vender", "inv", "fiado", "resumen"]) $("#v-" + v).hidden = S.view !== v;
  $$("#nav button").forEach(b => b.toggleAttribute("aria-current", false) || (b.dataset.v === S.view && b.setAttribute("aria-current", "page")));
  document.body.classList.toggle("selling", S.view === "vender");
  const nAl = S.alertas?.productos_con_alerta || 0;
  $("#dotInv").hidden = !nAl; $("#dotInv").textContent = nAl;
  if (S.view === "vender") { renderGrid(); renderCart(); }
  else if (S.view === "inv") renderInv();
  else if (S.view === "fiado") renderFiado();
  else renderResumen();
}
const waiting = () => S.loaded ? "" : `<div class="notice"><b>Cargando tus productos…</b>Un momento.</div>`;
function armButton(btn, armedText, fn) {
  const orig = btn.textContent; let t;
  btn.addEventListener("click", () => {
    if (!btn.classList.contains("armed")) { btn.classList.add("armed"); btn.textContent = armedText; clearTimeout(t); t = setTimeout(() => { btn.classList.remove("armed"); btn.textContent = orig; }, 4000); return; }
    clearTimeout(t); fn();
  });
}

/* ----- Vender ----- */
function renderGrid() {
  const w = waiting(); const g = $("#prodGrid");
  if (w) { g.innerHTML = w; return; }
  const q = $("#buscar").value.trim().toLowerCase();
  const list = S.prods.filter(p => !q || p.nombre.toLowerCase().includes(q));
  if (!S.prods.length) { g.innerHTML = `<div class="notice" style="grid-column:1/-1"><b>Aún no hay productos</b>Ve a Inventario y toca “+ Nuevo producto” para agregar el primero.</div>`; return; }
  if (!list.length) { g.innerHTML = `<div class="notice" style="grid-column:1/-1"><b>No encontré “${esc(q)}”</b>Revisa cómo está escrito o agrégalo en Inventario.</div>`; return; }
  const inCart = new Set(S.cart.map(i => i.p));
  g.innerHTML = list.map(p => {
    const low = p.stock <= p.minimo, n = dias(p.proximo_vence);
    const vch = n !== null && n <= AVISO_DIAS ? `<span class="chip ${n < 0 ? "bad" : "warn"}">${n < 0 ? "vencido" : n === 0 ? "hoy" : n + " d"}</span>` : "";
    return `<button class="pbtn${inCart.has(p.id) ? " incart" : ""}" data-p="${p.id}"><span class="pn">${esc(p.nombre)}</span><span class="ps"><span class="${low ? "low" : ""}">Hay ${cantTxt(p.stock, p.unidad)}</span>${vch}</span><span class="pp num">${Q(p.precio)}${p.unidad === "lb" ? " <small>/lb</small>" : ""}</span></button>`;
  }).join("");
}
const cartItems = () => S.cart.map(i => ({producto_id: i.p, cantidad: i.c}));
const cartTotal = () => r2(S.cart.reduce((s, it) => s + r2(it.c * prod(it.p).precio), 0));
let cotizSeq = 0;
async function cotizarCarrito() {
  const seq = ++cotizSeq;
  if (!S.cart.length) { S.cotiz = null; return; }
  try { const r = await Api.cotizar(cartItems()); if (seq === cotizSeq) { S.cotiz = r; paintGanancia(); } } catch { /* solo informativo */ }
}
function paintGanancia() { const g = $("#cartGan"); if (g) g.textContent = S.cotiz ? "ganas " + Q(S.cotiz.ganancia) : ""; }
function renderCart() {
  S.cart = S.cart.filter(i => prod(i.p) && i.c > 0);
  const el = $("#cart"); const n = S.cart.length;
  el.classList.toggle("open", S.cartOpen);
  el.innerHTML = `
    <div class="cart-h"><h2>Venta actual${n ? ` <span class="muted" style="font-weight:600;font-size:14px">· ${n} ${n === 1 ? "producto" : "productos"}</span>` : ""}</h2>
      <div class="row" style="gap:4px">${n ? `<button class="btn ghost sm cart-toggle" id="cartTog">${S.cartOpen ? "Ocultar" : "Ver"}</button><button class="btn ghost sm" id="cartClear">Vaciar</button>` : ""}</div></div>
    <div class="cart-list">${n ? S.cart.map((it, i) => {
      const p = prod(it.p); const lb = p.unidad === "lb";
      return `<div class="ci"><div><div class="n">${esc(p.nombre)}</div><div class="u num">${Q(p.precio)}${lb ? " /lb" : " c/u"}</div></div>
        <div class="sub num">${Q(it.c * p.precio)}</div>
        <div></div>
        <div class="qty"><button data-dec="${i}" aria-label="Quitar">−</button><button class="qv num${lb ? " tap" : ""}" data-edit="${i}">${cantTxt(it.c, p.unidad)}</button><button data-inc="${i}" aria-label="Agregar">+</button></div></div>`;
    }).join("") : `<div class="cart-empty">Toca un producto para agregarlo a la venta.</div>`}</div>
    <div class="cart-f">
      <div class="tot"><span class="t num">${Q(cartTotal())}</span>${n ? `<span class="g num" id="cartGan"></span>` : ""}</div>
      <div class="cart-actions"><button class="btn pri big" id="btnCobrar" ${n ? "" : "disabled"}>Cobrar</button><button class="btn gold big" id="btnFiar" ${n ? "" : "disabled"}>Fiado</button></div>
    </div>`;
  paintGanancia();
}
function cartChanged() { S.cotiz = null; renderGrid(); renderCart(); cotizarCarrito(); }
function addToCart(p, c) {
  const it = S.cart.find(i => i.p === p);
  if (it) it.c = r2(it.c + c); else S.cart.push({p, c: r2(c)});
  cartChanged();
}
function sheetLb(pid, idx) {
  const p = prod(pid); const cur = idx != null ? S.cart[idx].c : null;
  openSheet(esc(p.nombre), `
    <form id="fLb">
      <div class="lbl">¿Cuántas libras?</div>
      <div class="quick">${[0.25, 0.5, 1, 2, 5].map(v => `<button type="button" class="btn" data-lb="${v}">${v === 0.25 ? "¼" : v === 0.5 ? "½" : v} lb</button>`).join("")}</div>
      <div class="grid2">
        <div class="field"><label for="lbCant">Libras</label><input id="lbCant" type="number" inputmode="decimal" step="0.01" min="0" value="${cur ?? ""}" placeholder="Ej. 3"></div>
        <div class="field"><label for="lbMonto">o por monto (Q)</label><input id="lbMonto" type="number" inputmode="decimal" step="0.01" min="0" placeholder="Ej. 10"></div>
      </div>
      <div class="calc num" id="lbCalc">${Q(p.precio)} por libra</div>
      <button class="btn pri big" type="submit">${idx != null ? "Cambiar cantidad" : "Agregar a la venta"}</button>
    </form>`);
  const cant = $("#lbCant"), monto = $("#lbMonto"), calc = $("#lbCalc");
  const upd = src => {
    if (src === "m" && monto.value) cant.value = r2(+monto.value / p.precio);
    const c = +cant.value || 0;
    calc.innerHTML = c ? `${fmtN(c)} lb × ${Q(p.precio)} = <b>${Q(c * p.precio)}</b>` : `${Q(p.precio)} por libra`;
  };
  cant.addEventListener("input", () => { monto.value = ""; upd("c"); });
  monto.addEventListener("input", () => upd("m"));
  $$("[data-lb]").forEach(b => b.addEventListener("click", () => { cant.value = b.dataset.lb; monto.value = ""; upd("c"); }));
  upd();
  setTimeout(() => cant.focus(), 50);
  $("#fLb").addEventListener("submit", e => {
    e.preventDefault(); const c = r2(+cant.value);
    if (!(c > 0)) { toast("Escribe cuántas libras."); return; }
    if (idx != null) { S.cart[idx].c = c; cartChanged(); } else addToCart(pid, c);
    closeSheet();
  });
}
async function vender(btn, pago, cliente_id) {
  const r = await accion(btn, () => Api.vender({items: cartItems(), pago, cliente_id}),
    v => (pago === "fiado" ? "Fiado a " + (v.cliente || "cliente") : "Venta registrada") + " · " + Q(v.total));
  if (r) { S.cart = []; S.cartOpen = false; S.cotiz = null; closeSheet(); render(); }
}
function sheetCobrar() {
  const total = cartTotal();
  openSheet("Cobrar", `
    <form id="fCob">
      <div class="tot"><span class="lbl">Total</span><span class="t num" style="font-family:var(--f-display);font-weight:800;font-size:34px">${Q(total)}</span></div>
      <div class="field"><label for="pagaCon">Paga con (opcional, para calcular el vuelto)</label><input id="pagaCon" type="number" inputmode="decimal" step="0.01" min="0" placeholder="Ej. 50"></div>
      <div class="quick">${[10, 20, 50, 100, 200].filter(v => v >= total).slice(0, 4).map(v => `<button type="button" class="btn" data-pc="${v}">Q${v}</button>`).join("")}</div>
      <div class="change" id="vuelto" hidden><span>Vuelto</span><span class="v num"></span></div>
      <button class="btn pri big" type="submit">Confirmar venta</button>
    </form>`);
  const pc = $("#pagaCon"), vu = $("#vuelto");
  const upd = () => { const v = +pc.value; vu.hidden = !(v > 0); if (v > 0) { $(".v", vu).textContent = v >= total ? Q(v - total) : "Faltan " + Q(total - v); } };
  pc.addEventListener("input", upd);
  $$("[data-pc]").forEach(b => b.addEventListener("click", () => { pc.value = b.dataset.pc; upd(); }));
  $("#fCob").addEventListener("submit", e => { e.preventDefault(); vender(e.submitter, "contado"); });
}
function sheetFiar() {
  openSheet("Fiado · " + Q(cartTotal()), `
    <div class="stack">
      <div class="field"><label for="cliQ">¿A quién le fías?</label><input id="cliQ" type="search" placeholder="Buscar cliente…" autocomplete="off"></div>
      <div class="card" style="padding:0"><div class="list" id="cliPick"></div></div>
      <form id="fNewCli" class="row" style="gap:8px;flex-wrap:nowrap"><input id="newCliName" type="text" placeholder="Nuevo cliente, ej. Doña Marta" aria-label="Nombre del nuevo cliente"><button class="btn gold" type="submit" style="white-space:nowrap">Fiar</button></form>
    </div>`);
  const clis = [...S.clis].sort((a, b) => a.nombre.localeCompare(b.nombre, "es"));
  const draw = () => {
    const q = $("#cliQ").value.trim().toLowerCase();
    const l = clis.filter(c => !q || c.nombre.toLowerCase().includes(q));
    $("#cliPick").innerHTML = l.length ? l.map(c => `<button class="li" data-cli="${c.id}"><span class="m"><b>${esc(c.nombre)}</b><small>Debe ${Q(c.saldo)}</small></span><span class="chip mute">Elegir</span></button>`).join("") : `<div class="li muted">${clis.length ? "Nadie con ese nombre. Créalo abajo." : "Todavía no hay clientes. Escribe el nombre abajo."}</div>`;
  };
  draw();
  $("#cliQ").addEventListener("input", () => { draw(); $("#newCliName").value = $("#cliQ").value; });
  $("#cliPick").addEventListener("click", e => { const b = e.target.closest("[data-cli]"); if (b) vender(b, "fiado", +b.dataset.cli); });
  $("#fNewCli").addEventListener("submit", async e => {
    e.preventDefault(); const nombre = $("#newCliName").value.trim();
    if (!nombre) { toast("Escribe el nombre del cliente."); return; }
    const btn = e.submitter; btn.disabled = true;
    try { const c = await Api.crearCliente({nombre}); await vender(btn, "fiado", c.id); }
    catch (err) { toast(err.message); btn.disabled = false; }
  });
}

/* ----- Inventario ----- */
function renderInv() {
  const w = waiting(); if (w) { $("#invTable").innerHTML = w; $("#alerts").innerHTML = ""; return; }
  const A = S.alertas;
  const block = (cls, title, rows) => `<div class="al ${cls}"><h3><span>${title}</span><span>${rows.length}</span></h3><ul>${rows.join("")}</ul></div>`;
  const li = (x, right) => `<li><button data-prod="${x.producto_id}"><span>${esc(x.nombre)}${x.cantidad != null ? " · " + cantTxt(x.cantidad, x.unidad) : ""}</span><span class="w">${right}</span></button></li>`;
  const al = [];
  if (A.vencidos.length) al.push(block("bad", "Vencidos", A.vencidos.map(x => li(x, venceTxt(x.vence)))));
  if (A.por_vencer.length) al.push(block("warn", `Vencen en ${AVISO_DIAS} días o menos`, A.por_vencer.map(x => li(x, venceTxt(x.vence)))));
  if (A.bajo.length) al.push(block("low", "Stock bajo · hay que pedir", A.bajo.map(x => li(x, "quedan " + cantTxt(x.stock, x.unidad)))));
  $("#alerts").innerHTML = al.length ? al.join("") : (S.prods.length ? `<div class="al okall">Nada por vencer en los próximos ${AVISO_DIAS} días y ningún producto bajo el mínimo.</div>` : "");
  const q = $("#buscarInv").value.trim().toLowerCase();
  const list = S.prods.filter(p => !q || p.nombre.toLowerCase().includes(q));
  if (!S.prods.length) { $("#invTable").innerHTML = `<div class="notice"><b>Tu inventario está vacío</b>Toca “+ Nuevo producto”. Puedes poner cuánto tienes ahora y su fecha de vencimiento.</div>`; return; }
  $("#invTable").innerHTML = `<div class="tbl-wrap"><table><thead><tr><th>Producto</th><th class="r">Hay</th><th>Próximo vencimiento</th><th class="r">Precio</th><th class="r hide-sm">Costo</th><th class="r hide-sm">Ganas</th></tr></thead><tbody>${
    list.map(p => {
      const low = p.stock <= p.minimo, v = p.proximo_vence, n = dias(v);
      const vc = !v ? `<span class="muted">—</span>` : `<span class="chip ${n < 0 ? "bad" : n <= AVISO_DIAS ? "warn" : "mute"}">${n < 0 ? "vencido" : fFecha(v)}</span>`;
      return `<tr class="click" data-prod="${p.id}" tabindex="0"><td class="pname">${esc(p.nombre)}<small>${p.unidad === "lb" ? "por libra" : "por unidad"} · mínimo ${fmtN(p.minimo)}</small></td><td class="r num ${low ? "stk-low" : ""}">${cantTxt(p.stock, p.unidad)}</td><td>${vc}</td><td class="r num">${Q(p.precio)}</td><td class="r num hide-sm">${Q(p.costo_ref)}</td><td class="r num hide-sm">${Q(p.ganancia_unitaria)}</td></tr>`;
    }).join("")}</tbody></table></div>`;
}
async function sheetProd(id) {
  let p;
  try { p = await Api.producto(id); } catch (e) { toast(e.message); return; }
  const s = p.stock;
  openSheet(esc(p.nombre), `
    <div class="stack">
      <div class="stats">
        <div class="stat"><div class="k">Hay</div><div class="v num ${s <= p.minimo ? "stk-low" : ""}">${cantTxt(s, p.unidad)}</div></div>
        <div class="stat"><div class="k">Precio</div><div class="v num">${Q(p.precio)}</div></div>
        <div class="stat"><div class="k">Costo</div><div class="v num">${Q(p.costo_ref)}</div></div>
        <div class="stat"><div class="k">Ganas</div><div class="v num" style="color:var(--ok)">${Q(p.ganancia_unitaria)}</div></div>
      </div>
      <div>
        <div class="lbl" style="margin-bottom:6px">En existencia por fecha de vencimiento</div>
        <div class="card" style="padding:0"><div class="list">${p.lotes.length ? p.lotes.map(l => { const n = dias(l.vence); return `<div class="li"><span class="m"><b class="num">${cantTxt(l.restante, p.unidad)}</b><small>${l.origen === "cambio" ? "cambio con proveedor · " : ""}costo ${Q(l.costo_unitario)} c/${p.unidad === "lb" ? "lb" : "u"}</small></span>${l.vence ? `<span class="chip ${n < 0 ? "bad" : n <= AVISO_DIAS ? "warn" : "mute"}">${n < 0 || n <= AVISO_DIAS ? venceTxt(l.vence) : "vence " + fFecha(l.vence)}</span>` : `<span class="chip mute">no vence</span>`}</div>`; }).join("") : `<div class="li muted">${s < 0 ? "Se vendió más de lo registrado. Registra una entrada para cuadrar." : "No hay existencia registrada."}</div>`}</div></div>
      </div>
      <div class="grid2">
        <button class="btn pri" data-act="entrada">Registrar entrada</button>
        <button class="btn" data-act="cambio">Cambio con proveedor</button>
        <button class="btn" data-act="perdida">Registrar pérdida</button>
        <button class="btn" data-act="editar">Editar producto</button>
      </div>
    </div>`);
  $$("[data-act]").forEach(b => b.addEventListener("click", () => ({entrada: sheetEntrada, cambio: sheetCambio, perdida: sheetPerdida, editar: sheetEditProd})[b.dataset.act](p)));
}
function sheetEditProd(p) {
  const nuevo = !p;
  p = p || {nombre: "", unidad: "unidad", precio: "", minimo: 5, costo_ref: ""};
  openSheet(nuevo ? "Nuevo producto" : "Editar producto", `
    <form id="fProd">
      <div class="field"><label for="pNom">Nombre</label><input id="pNom" type="text" required maxlength="120" value="${esc(p.nombre)}" placeholder="Ej. Arroz, Leche 1 L, Gaseosa 600 ml"></div>
      <div class="grid2">
        <div class="field"><label for="pUni">Se vende por</label><select id="pUni"><option value="unidad"${p.unidad !== "lb" ? " selected" : ""}>Unidad</option><option value="lb"${p.unidad === "lb" ? " selected" : ""}>Libra</option></select></div>
        <div class="field"><label for="pPre">Precio de venta (Q)</label><input id="pPre" type="number" inputmode="decimal" step="0.01" min="0" required value="${p.precio}"></div>
      </div>
      <div class="grid2">
        <div class="field"><label for="pMin">Avisar cuando queden</label><input id="pMin" type="number" inputmode="decimal" step="0.5" min="0" value="${p.minimo}"></div>
        <div class="field"><label for="pCos">Costo de referencia (Q)</label><input id="pCos" type="number" inputmode="decimal" step="0.01" min="0" value="${p.costo_ref}" placeholder="Lo que te cuesta"><span class="hint">Se actualiza solo con cada entrada.</span></div>
      </div>
      ${nuevo ? `<div class="card" style="background:var(--surface-2)"><div class="lbl" style="margin-bottom:8px">¿Cuánto tienes ahora? (opcional)</div><div class="grid2"><div class="field"><label for="pIni">Cantidad</label><input id="pIni" type="number" inputmode="decimal" step="0.01" min="0" placeholder="Ej. 20"></div><div class="field"><label for="pVen">Vence</label><input id="pVen" type="date"></div></div></div>` : ""}
      <button class="btn pri big" type="submit">${nuevo ? "Agregar producto" : "Guardar cambios"}</button>
      ${nuevo ? "" : `<button class="btn danger" type="button" id="btnArch">Quitar de la lista</button>`}
    </form>`);
  if (nuevo) setTimeout(() => $("#pNom").focus(), 50);
  $("#fProd").addEventListener("submit", async e => {
    e.preventDefault();
    const d = {nombre: $("#pNom").value.trim(), unidad: $("#pUni").value, precio: +$("#pPre").value, minimo: +$("#pMin").value || 0, costo_ref: +$("#pCos").value || 0};
    if (nuevo) { d.cantidad_inicial = +$("#pIni").value || 0; d.vence = $("#pVen").value || null; }
    const ok = await accion(e.submitter, () => nuevo ? Api.crearProducto(d) : Api.editarProducto(p.id, d), nuevo ? "Producto agregado" : "Producto actualizado");
    if (ok) closeSheet();
  });
  if (!nuevo) armButton($("#btnArch"), "Sí, quitarlo", async () => { if (await accion($("#btnArch"), () => Api.archivarProducto(p.id), "Producto quitado de la lista")) closeSheet(); });
}
function sheetEntrada(p) {
  const u = p.unidad === "lb" ? "lb" : "unidades";
  openSheet("Entrada · " + esc(p.nombre), `
    <form id="fEnt">
      <div class="grid2">
        <div class="field"><label for="eCant">Cantidad (${u})</label><input id="eCant" type="number" inputmode="decimal" step="0.01" min="0" required placeholder="${p.unidad === "lb" ? "Ej. 100 (un quintal)" : "Ej. 24"}"></div>
        <div class="field"><label for="eVen">Vence</label><input id="eVen" type="date"><span class="hint">Déjalo vacío si no vence.</span></div>
      </div>
      <div class="grid2">
        <div class="field"><label for="eTot">Pagaste en total (Q)</label><input id="eTot" type="number" inputmode="decimal" step="0.01" min="0" placeholder="Ej. 350"></div>
        <div class="field"><label for="eCu">o costo por ${p.unidad === "lb" ? "libra" : "unidad"} (Q)</label><input id="eCu" type="number" inputmode="decimal" step="0.01" min="0" value="${r2(p.costo_ref) || ""}"></div>
      </div>
      <div class="calc num" id="eCalc"></div>
      <div class="field"><label for="ePre">Precio de venta (Q)</label><input id="ePre" type="number" inputmode="decimal" step="0.01" min="0" value="${p.precio}"></div>
      <button class="btn pri big" type="submit">Registrar entrada</button>
    </form>`);
  const cant = $("#eCant"), tot = $("#eTot"), cu = $("#eCu"), calc = $("#eCalc"), pre = $("#ePre");
  const upd = src => {
    const c = +cant.value;
    if (src !== "cu" && tot.value && c > 0) cu.value = r2(+tot.value / c);
    if (src === "cu") tot.value = "";
    const k = +cu.value, pv = +pre.value;
    calc.innerHTML = k ? `Te cuesta <b>${Q(k)}</b> c/${p.unidad === "lb" ? "lb" : "u"} · lo vendes a ${Q(pv)} · ganas <b style="color:${pv - k >= 0 ? "var(--ok)" : "var(--bad)"}">${Q(pv - k)}</b> por ${p.unidad === "lb" ? "libra" : "unidad"}` : "Escribe lo que pagaste para calcular tu ganancia.";
  };
  cant.addEventListener("input", () => upd("c")); tot.addEventListener("input", () => upd("t")); cu.addEventListener("input", () => upd("cu")); pre.addEventListener("input", () => upd());
  upd(); setTimeout(() => cant.focus(), 50);
  $("#fEnt").addEventListener("submit", async e => {
    e.preventDefault(); const c = r2(+cant.value);
    if (!(c > 0)) { toast("Escribe la cantidad que llegó."); return; }
    const ok = await accion(e.submitter, () => Api.entrada(p.id, {cantidad: c, costo_unitario: r2(+cu.value), vence: $("#eVen").value || null, precio: +pre.value > 0 ? r2(+pre.value) : null}),
      "Entrada registrada · " + cantTxt(c, p.unidad) + " de " + p.nombre);
    if (ok) closeSheet();
  });
}
function sheetPerdida(p) {
  openSheet("Pérdida · " + esc(p.nombre), `
    <form id="fPer">
      <p class="muted" style="margin:0">Para lo que se venció, se dañó o se perdió y ya no se puede vender. Se descuenta del inventario y de tu ganancia.</p>
      <div class="grid2">
        <div class="field"><label for="lCant">Cantidad${p.unidad === "lb" ? " (lb)" : ""}</label><input id="lCant" type="number" inputmode="decimal" step="0.01" min="0" required></div>
        <div class="field"><label for="lMot">Motivo</label><select id="lMot"><option>Se venció</option><option>Se dañó</option><option>Se perdió</option><option>Consumo de la casa</option></select></div>
      </div>
      <div class="calc num" id="lCalc">Pierdes ${Q(0)}</div>
      <button class="btn danger big" type="submit">Registrar pérdida</button>
    </form>`);
  const cant = $("#lCant"); let seq = 0;
  cant.addEventListener("input", async () => {
    const c = +cant.value || 0, n = ++seq;
    if (!(c > 0)) { $("#lCalc").innerHTML = `Pierdes ${Q(0)}`; return; }
    try { const r = await Api.cotizar([{producto_id: p.id, cantidad: c}]); if (n === seq && $("#lCalc")) $("#lCalc").innerHTML = `Pierdes <b>${Q(r.costo)}</b> (lo que te costó)`; } catch {}
  });
  setTimeout(() => cant.focus(), 50);
  $("#fPer").addEventListener("submit", async e => {
    e.preventDefault(); const c = r2(+cant.value); if (!(c > 0)) { toast("Escribe la cantidad."); return; }
    if (await accion(e.submitter, () => Api.perdida(p.id, {cantidad: c, motivo: $("#lMot").value}), "Pérdida registrada")) closeSheet();
  });
}
function sheetCambio(p) {
  const first = p.lotes.find(l => l.vence);
  openSheet("Cambio con proveedor · " + esc(p.nombre), `
    <form id="fCam">
      <p class="muted" style="margin:0">El proveedor se lleva lo que está por vencer y te deja lo mismo con fecha nueva. No cuenta como pérdida.</p>
      <div class="grid2">
        <div class="field"><label for="cCant">Cantidad que cambió${p.unidad === "lb" ? " (lb)" : ""}</label><input id="cCant" type="number" inputmode="decimal" step="0.01" min="0" required value="${first ? r2(first.restante) : ""}"><span class="hint">${first ? "Se toma primero lo que vence " + fFecha(first.vence) + "." : ""}</span></div>
        <div class="field"><label for="cVen">Nueva fecha de vencimiento</label><input id="cVen" type="date" required></div>
      </div>
      <button class="btn pri big" type="submit">Registrar cambio</button>
    </form>`);
  $("#fCam").addEventListener("submit", async e => {
    e.preventDefault(); const c = r2(+$("#cCant").value), v = $("#cVen").value;
    if (!(c > 0) || !v) { toast("Pon la cantidad y la nueva fecha."); return; }
    if (await accion(e.submitter, () => Api.cambio(p.id, {cantidad: c, vence: v}), "Cambio registrado · ahora vence " + fFecha(v))) closeSheet();
  });
}

/* ----- Fiado ----- */
function renderFiado() {
  const el = $("#fiadoBody");
  if (!S.loaded) { el.innerHTML = `<div class="notice"><b>Cargando clientes…</b></div>`; return; }
  const clis = S.clis;
  el.innerHTML = `
    <div class="kpis"><div class="kpi hero"><div class="k">Te deben en total</div><div class="v num">${Q(S.porCobrar)}</div><div class="d">${clis.filter(x => x.saldo > 0.004).length} clientes con saldo</div></div></div>
    ${clis.length ? `<div class="card" style="padding:0"><div class="list">${clis.map(x => `<button class="li" data-cli="${x.id}"><span class="m"><b>${esc(x.nombre)}</b><small>${x.ultimo ? "Último movimiento " + fTs(x.ultimo) : "Sin movimientos"}</small></span><span class="amt num" style="color:${x.saldo > 0.004 ? "var(--bad)" : "var(--ok)"}">${x.saldo > 0.004 ? Q(x.saldo) : "Al día"}</span></button>`).join("")}</div></div>`
      : `<div class="notice"><b>Nadie te debe</b>Cuando vendas con el botón “Fiado”, el cliente aparecerá aquí con su saldo.</div>`}`;
}
async function sheetCli(id) {
  let c;
  try { c = await Api.cliente(id); } catch (e) { toast(e.message); return; }
  const s = c.saldo;
  openSheet(esc(c.nombre), `
    <div class="stack">
      <div class="stats"><div class="stat"><div class="k">Debe</div><div class="v num" style="color:${s > 0.004 ? "var(--bad)" : "var(--ok)"}">${Q(s)}</div></div>${c.telefono ? `<div class="stat"><div class="k">Teléfono</div><div class="v">${esc(c.telefono)}</div></div>` : ""}</div>
      ${s > 0.004 ? `<form id="fAbo" class="stack" style="gap:10px">
        <div class="row" style="flex-wrap:nowrap;gap:8px"><input id="aMonto" type="number" inputmode="decimal" step="0.01" min="0" max="${s}" placeholder="Monto que pagó (Q)" aria-label="Monto del abono"><button class="btn pri" type="submit" style="white-space:nowrap">Registrar abono</button></div>
        <button class="btn" type="button" id="aTodo">Pagó todo (${Q(s)})</button>
      </form>` : ""}
      <div>
        <div class="lbl" style="margin-bottom:6px">Historial</div>
        <div class="card" style="padding:0"><div class="list">${c.historial.length ? c.historial.map(m => m.tipo === "venta"
          ? `<div class="li"><span class="m"><b>Se llevó ${esc(itemsTxt(m.items))}</b><small>${fTs(m.fecha)}</small></span><span class="amt num" style="color:var(--bad)">+${Q(m.monto)}</span></div>`
          : `<div class="li"><span class="m"><b>Abono</b><small>${fTs(m.fecha)}</small></span><span class="amt num" style="color:var(--ok)">−${Q(m.monto)}</span></div>`).join("") : `<div class="li muted">Sin movimientos.</div>`}</div></div>
      </div>
    </div>`);
  const abonar = async (btn, m) => {
    if (!(m > 0)) { toast("Escribe el monto que pagó."); return; }
    if (await accion(btn, () => Api.abonar(id, r2(m)), r => "Abono de " + Q(m) + " registrado · " + c.nombre + " debe " + Q(r.saldo))) closeSheet();
  };
  $("#fAbo")?.addEventListener("submit", e => { e.preventDefault(); abonar(e.submitter, +$("#aMonto").value); });
  $("#aTodo")?.addEventListener("click", e => abonar(e.currentTarget, s));
}
function sheetNuevoCli() {
  openSheet("Nuevo cliente", `
    <form id="fCli">
      <div class="field"><label for="cNom">Nombre</label><input id="cNom" type="text" required maxlength="120" placeholder="Ej. Doña Marta"></div>
      <div class="field"><label for="cTel">Teléfono (opcional)</label><input id="cTel" type="text" inputmode="tel" maxlength="40" placeholder="Ej. 5555 1234"></div>
      <button class="btn pri big" type="submit">Agregar cliente</button>
    </form>`);
  setTimeout(() => $("#cNom").focus(), 50);
  $("#fCli").addEventListener("submit", async e => {
    e.preventDefault(); const nombre = $("#cNom").value.trim(); if (!nombre) return;
    if (await accion(e.submitter, () => Api.crearCliente({nombre, telefono: $("#cTel").value.trim()}), "Cliente agregado")) closeSheet();
  });
}

/* ----- Resumen ----- */
function rango() {
  const n = new Date(); n.setHours(0, 0, 0, 0);
  if (S.periodo === "semana") {
    const s = new Date(n); s.setDate(n.getDate() - ((n.getDay() + 6) % 7) + S.offset * 7);
    const e = new Date(s); e.setDate(s.getDate() + 7);
    const last = new Date(e); last.setDate(e.getDate() - 1);
    const lbl = s.getMonth() === last.getMonth() ? `${s.getDate()} al ${last.getDate()} ${MES[s.getMonth()]}` : `${s.getDate()} ${MES[s.getMonth()]} al ${last.getDate()} ${MES[last.getMonth()]}`;
    return {s, e, lbl: (S.offset === 0 ? "Esta semana · " : "") + lbl};
  }
  const s = new Date(n.getFullYear(), n.getMonth() + S.offset, 1), e = new Date(s.getFullYear(), s.getMonth() + 1, 1);
  return {s, e, lbl: MESL[s.getMonth()] + " " + s.getFullYear()};
}
let resSeq = 0;
async function renderResumen() {
  const {s, e, lbl} = rango(); $("#perLbl").textContent = lbl;
  $("#segSem").setAttribute("aria-pressed", S.periodo === "semana"); $("#segMes").setAttribute("aria-pressed", S.periodo === "mes");
  $("#perNext").disabled = S.offset >= 0;
  const el = $("#resBody"), seq = ++resSeq;
  if (!el.innerHTML) el.innerHTML = `<div class="notice"><b>Cargando ventas…</b></div>`;
  let R;
  try { R = await Api.resumen(ymd(s), ymd(e)); } catch (err) { el.innerHTML = `<div class="notice"><b>No se pudo cargar el resumen</b>${esc(err.message)}</div>`; return; }
  if (seq !== resSeq || S.view !== "resumen") return;
  const V = R.ventas, P = R.perdidas, top = R.top_productos, hist = R.historial;
  const maxG = Math.max(...top.map(r => r.ganancia), 0.01);
  el.innerHTML = `
    <div class="kpis">
      <div class="kpi hero"><div class="k">Ganancia neta</div><div class="v num">${Q(R.ganancia_neta)}</div><div class="d">ventas − costo − pérdidas</div></div>
      <div class="kpi"><div class="k">Vendiste</div><div class="v num">${Q(V.total)}</div><div class="d">${V.cantidad} ${V.cantidad === 1 ? "venta" : "ventas"}</div></div>
      <div class="kpi"><div class="k">Te costó</div><div class="v num">${Q(V.costo)}</div><div class="d">lo que pagaste por lo vendido</div></div>
      <div class="kpi"><div class="k">Pérdidas</div><div class="v num ${P.costo > 0 ? "bad" : ""}">${Q(P.costo)}</div><div class="d">${P.cantidad} registro${P.cantidad === 1 ? "" : "s"}</div></div>
      <div class="kpi"><div class="k">Fiado</div><div class="v num">${Q(V.fiado)}</div><div class="d">cobraste ${Q(R.abonos)} en abonos</div></div>
      <div class="kpi"><div class="k">Te deben hoy</div><div class="v num">${Q(R.por_cobrar)}</div><div class="d">todos los clientes</div></div>
    </div>
    <div class="rgrid">
      <div class="card chart"><h3>Ganancia por día</h3>${chart(R.ganancia_por_dia)}</div>
      <div class="card"><h3>Productos que más ganancia dejan</h3>${top.length ? `<div class="rank">${top.slice(0, 8).map((r, i) => `<div class="rk"><span class="i">${i + 1}</span><span class="n">${esc(r.nombre)}</span><span class="v num">${Q(r.ganancia)}</span><span class="barw"><span style="width:${Math.max(2, r.ganancia / maxG * 100)}%"></span></span><span class="s num">${cantTxt(r.cantidad, r.unidad)} vendidos · ${Q(r.vendido)}</span></div>`).join("")}</div>` : `<div class="empty-s">Sin ventas en este periodo.</div>`}
        ${R.sin_venta.length && top.length ? `<div style="margin-top:14px"><div class="lbl" style="margin-bottom:4px">No se vendieron en este periodo</div><div class="muted" style="font-size:14px">${R.sin_venta.slice(0, 10).map(esc).join(", ")}${R.sin_venta.length > 10 ? " y " + (R.sin_venta.length - 10) + " más" : ""}</div></div>` : ""}
      </div>
    </div>
    <div class="card hist" style="margin-top:16px"><h3>Ventas del periodo</h3>${hist.length ? `<div class="list">${hist.map(v => `<div class="li${v.anulada ? " voided" : ""}"><span class="m"><b>${esc(itemsTxt(v.items))}</b><small>${fTs(v.fecha)}${v.pago === "fiado" ? " · fiado a " + esc(v.cliente || "cliente") : ""}${v.anulada ? " · anulada" : ""}</small></span><span class="amt num">${Q(v.total)}</span>${v.anulada ? "" : `<button class="btn ghost sm" data-anular="${v.id}">Anular</button>`}</div>`).join("")}</div>${R.historial_total > hist.length ? `<div class="empty-s">Mostrando las ${hist.length} más recientes.</div>` : ""}` : `<div class="empty-s">No hay ventas registradas en este periodo.</div>`}</div>`;
  $$("[data-anular]", el).forEach(b => armButton(b, "¿Anular?", () => accion(b, () => Api.anular(+b.dataset.anular), "Venta anulada · el inventario se devolvió")));
}
function chart(serie) {
  const days = serie.map(x => x.dia), vals = serie.map(x => x.ganancia);
  const W = 560, H = 190, pl = 44, pr = 8, pt = 10, pb = 26;
  const max = Math.max(...vals, 1), min = Math.min(...vals, 0);
  const nice = v => { const m = Math.pow(10, Math.floor(Math.log10(v))); return Math.ceil(v / m) * m; };
  const top = nice(max), bot = min < 0 ? -nice(-min) : 0;
  const y = v => pt + (top - v) / (top - bot) * (H - pt - pb);
  const bw = (W - pl - pr) / days.length; const t = hoy();
  const ticks = [bot, (top + bot) / 2, top].filter((v, i, a) => a.indexOf(v) === i);
  const every = days.length > 10 ? 5 : 1;
  return `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Ganancia por día">
    ${ticks.map(v => `<line class="grid" x1="${pl}" x2="${W - pr}" y1="${y(v)}" y2="${y(v)}"/><text x="${pl - 6}" y="${y(v) + 3}" text-anchor="end">Q${fmtN(v)}</text>`).join("")}
    ${days.map((d, i) => { const v = vals[i], x = pl + i * bw + bw * .15, w = bw * .7, y0 = y(0), y1 = y(v); const dd = +d.slice(8);
      return `<rect class="bar${d === t ? " today" : ""}${v < 0 ? " neg" : ""}" x="${x}" y="${Math.min(y0, y1)}" width="${w}" height="${Math.max(v ? 1.5 : 0, Math.abs(y1 - y0))}" rx="2"><title>${fFecha(d)}: ${Q(v)}</title></rect>${(days.length <= 10 || dd === 1 || dd % every === 0) ? `<text x="${x + w / 2}" y="${H - 8}" text-anchor="middle">${days.length <= 7 ? ["lun","mar","mié","jue","vie","sáb","dom"][i] + " " + dd : dd}</text>` : ""}`; }).join("")}
  </svg>`;
}

/* ----- Respaldo ----- */
function sheetRespaldo() {
  openSheet("Respaldo", `
    <div class="stack">
      <div class="card"><p>Descarga una copia de toda la base de datos (productos, ventas, fiado). Guárdala en una memoria USB o en la nube cada semana.</p><a class="btn pri" href="/api/respaldo" download>Descargar copia (.db)</a></div>
      <div class="card"><p>¿Usabas la versión anterior que guardaba en el navegador? Sube aquí el archivo <b>.json</b> que descargaste con “Descargar copia”. Solo funciona con la base de datos vacía.</p>
        <label class="btn" for="impFile">Importar copia anterior (.json)</label><input id="impFile" type="file" accept=".json,application/json" hidden></div>
    </div>`);
  $("#impFile").addEventListener("change", async e => {
    const f = e.target.files[0]; if (!f) return;
    const r = await accion(null, () => Api.importar(f), r => `Importado: ${r.productos} productos, ${r.clientes} clientes, ${r.ventas} ventas`);
    if (r) closeSheet();
  });
}

/* ---------- hojas, avisos ---------- */
function openSheet(title, body) {
  $("#sheetRoot").innerHTML = `<div class="sheet-bg" id="sheetBg"><div class="sheet" role="dialog" aria-modal="true" aria-label="${title.replace(/<[^>]+>/g, "")}"><div class="sheet-h"><h2>${title}</h2><button class="x" id="sheetX" aria-label="Cerrar">×</button></div>${body}</div></div>`;
  $("#sheetX").addEventListener("click", closeSheet);
  $("#sheetBg").addEventListener("click", e => { if (e.target.id === "sheetBg") closeSheet(); });
}
function closeSheet() { $("#sheetRoot").innerHTML = ""; }
document.addEventListener("keydown", e => { if (e.key === "Escape" && $("#sheetBg")) closeSheet(); });
let toastT;
function toast(msg) { const t = $("#toast"); t.textContent = msg; t.hidden = false; clearTimeout(toastT); toastT = setTimeout(() => t.hidden = true, 3200); }

/* ---------- eventos de la interfaz ---------- */
$("#nav").addEventListener("click", e => { const b = e.target.closest("[data-v]"); if (!b) return; S.view = b.dataset.v; render(); window.scrollTo(0, 0); });
$("#btnRespaldo").addEventListener("click", sheetRespaldo);
$("#buscar").addEventListener("input", renderGrid);
$("#buscar").addEventListener("keydown", e => { if (e.key === "Enter") { const f = $(".pbtn", $("#prodGrid")); if (f) f.click(); } });
$("#prodGrid").addEventListener("click", e => {
  const b = e.target.closest("[data-p]"); if (!b) return; const id = +b.dataset.p;
  if (prod(id).unidad === "lb") sheetLb(id); else addToCart(id, 1);
});
$("#cart").addEventListener("click", e => {
  const t = e.target.closest("button"); if (!t) return;
  if (t.id === "cartTog") { S.cartOpen = !S.cartOpen; renderCart(); return; }
  if (t.id === "cartClear") { S.cart = []; cartChanged(); return; }
  if (t.id === "btnCobrar") return sheetCobrar();
  if (t.id === "btnFiar") return sheetFiar();
  const step = i => prod(S.cart[i].p).unidad === "lb" ? 0.5 : 1;
  if (t.dataset.inc != null) { const i = +t.dataset.inc; S.cart[i].c = r2(S.cart[i].c + step(i)); }
  else if (t.dataset.dec != null) { const i = +t.dataset.dec; S.cart[i].c = r2(S.cart[i].c - step(i)); }
  else if (t.dataset.edit != null) { const i = +t.dataset.edit; if (prod(S.cart[i].p).unidad === "lb") return sheetLb(S.cart[i].p, i); return; }
  else return;
  cartChanged();
});
$("#btnNuevoProd").addEventListener("click", () => sheetEditProd(null));
$("#buscarInv").addEventListener("input", renderInv);
$("#v-inv").addEventListener("click", e => { const r = e.target.closest("[data-prod]"); if (r) sheetProd(+r.dataset.prod); });
$("#v-inv").addEventListener("keydown", e => { if (e.key === "Enter") { const r = e.target.closest("[data-prod]"); if (r) sheetProd(+r.dataset.prod); } });
$("#btnNuevoCli").addEventListener("click", sheetNuevoCli);
$("#fiadoBody").addEventListener("click", e => { const r = e.target.closest("[data-cli]"); if (r) sheetCli(+r.dataset.cli); });
$("#segSem").addEventListener("click", () => { S.periodo = "semana"; S.offset = 0; renderResumen(); });
$("#segMes").addEventListener("click", () => { S.periodo = "mes"; S.offset = 0; renderResumen(); });
$("#perPrev").addEventListener("click", () => { S.offset--; renderResumen(); });
$("#perNext").addEventListener("click", () => { if (S.offset < 0) { S.offset++; renderResumen(); } });
// Si otra persona registró algo desde otro equipo, se ve al volver a esta pestaña.
document.addEventListener("visibilitychange", () => { if (!document.hidden && !$("#sheetBg")) cargar(); });

cargar();
})();

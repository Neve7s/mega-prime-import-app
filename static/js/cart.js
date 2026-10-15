/* Carrito público en localStorage. Sin cuentas, sin pasarela.
   Contrato: botones con data-add-sku, data-add-nombre, data-add-precio. */
(function () {
  const KEY = "mpi_cart_v1";
  const money = (n) => "USD " + Number(n).toFixed(2);

  function load() {
    try { return JSON.parse(localStorage.getItem(KEY) || "[]"); }
    catch { return []; }
  }
  function save(items) {
    localStorage.setItem(KEY, JSON.stringify(items));
    renderBadge();
    renderCart();
  }
  function totalQty(items) { return items.reduce((a, i) => a + i.cantidad, 0); }
  function totalMoney(items) { return items.reduce((a, i) => a + i.cantidad * Number(i.precio), 0); }

  window.MpiCart = {
    items: load,
    add(sku, nombre, precio) {
      const items = load();
      const found = items.find((i) => i.sku === sku);
      if (found) found.cantidad = Math.min(9999, found.cantidad + 1);
      else items.push({ sku, nombre, precio: Number(precio), cantidad: 1 });
      save(items);
      toast(nombre + " agregado ✓");
    },
    setQty(sku, qty) {
      let items = load();
      qty = parseInt(qty, 10) || 0;
      if (qty < 1) items = items.filter((i) => i.sku !== sku);
      else items = items.map((i) => (i.sku === sku ? { ...i, cantidad: Math.min(9999, qty) } : i));
      save(items);
    },
    remove(sku) { save(load().filter((i) => i.sku !== sku)); },
    clear() { save([]); },
    money,
  };

  function renderBadge() {
    const n = totalQty(load());
    document.querySelectorAll("#cart-badge").forEach((el) => {
      el.textContent = n;
    });
    document.querySelectorAll(".mobile-cart-count").forEach((el) => {
      el.textContent = n;
    });
  }

  function toast(msg) {
    let box = document.getElementById("mpi-toast");
    if (!box) {
      box = document.createElement("div");
      box.id = "mpi-toast";
      box.className = "fixed bottom-6 left-1/2 -translate-x-1/2 z-[60] bg-[#0A0A0B] text-white text-sm font-semibold px-5 py-3 rounded-lg shadow-xl transition-opacity";
      document.body.appendChild(box);
    }
    box.textContent = msg;
    box.style.opacity = "1";
    clearTimeout(box._t);
    box._t = setTimeout(() => { box.style.opacity = "0"; }, 2200);
  }

  function renderCart() {
    const box = document.getElementById("cart-items");
    if (!box) return;
    const items = load();
    if (!items.length) {
      box.innerHTML = '<p class="text-sm text-gray-500">Tu carrito está vacío.</p><a class="text-sm font-bold text-[#8C6D00] underline" href="/catalogo/">Explorar catálogo →</a>';
    } else {
      box.innerHTML = items.map((i) => `
        <div class="flex items-center justify-between gap-3 border rounded p-3 bg-white">
          <div><div class="font-bold text-sm">${i.nombre}</div>
          <div class="text-xs text-gray-500">${i.sku} · ${money(i.precio)}</div></div>
          <div class="flex items-center gap-2">
            <button class="border rounded px-2" data-dec="${i.sku}">−</button>
            <span class="text-sm font-bold">${i.cantidad}</span>
            <button class="border rounded px-2" data-inc="${i.sku}">+</button>
            <button class="text-red-600 text-sm" data-del="${i.sku}">Quitar</button>
          </div>
        </div>`).join("");
    }
    const t = document.getElementById("cart-total");
    if (t) t.textContent = money(totalMoney(items));
  }

  document.addEventListener("click", (e) => {
    const add = e.target.closest("[data-add-sku]");
    if (add) {
      window.MpiCart.add(add.dataset.addSku, add.dataset.addNombre, add.dataset.addPrecio);
      return;
    }
    const inc = e.target.closest("[data-inc]");
    if (inc) { const it = load().find((i) => i.sku === inc.dataset.inc); if (it) window.MpiCart.setQty(it.sku, it.cantidad + 1); return; }
    const dec = e.target.closest("[data-dec]");
    if (dec) { const it = load().find((i) => i.sku === dec.dataset.dec); if (it) window.MpiCart.setQty(it.sku, it.cantidad - 1); return; }
    const del = e.target.closest("[data-del]");
    if (del) window.MpiCart.remove(del.dataset.del);
  });

  document.addEventListener("DOMContentLoaded", () => { renderBadge(); renderCart(); });
  // Sincroniza entre pestañas: lo que cambia en una se refleja en las demás.
  window.addEventListener("storage", (e) => {
    if (e.key === KEY) { renderBadge(); renderCart(); }
  });
})();

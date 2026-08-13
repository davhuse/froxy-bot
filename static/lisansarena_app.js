"use strict";
(() => {
  const state = { csrf: "", products: [], selected: null };
  const byId = (id) => document.getElementById(id);
  const notice = byId("notice");
  const api = async (url, options = {}) => {
    const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
    if (state.csrf && options.method && options.method !== "GET") headers["X-CSRF-Token"] = state.csrf;
    const response = await fetch(url, { credentials: "same-origin", ...options, headers });
    const data = await response.json().catch(() => ({ error: "Sunucu yanıtı okunamadı" }));
    if (!response.ok) throw new Error(data.error || "İşlem başarısız");
    return data;
  };
  const setNotice = (text, error = false) => { notice.textContent = text; notice.classList.toggle("error", error); };
  const addText = (parent, tag, text, className = "") => { const node = document.createElement(tag); node.textContent = text; if (className) node.className = className; parent.appendChild(node); return node; };
  const renderProducts = () => {
    const root = byId("products"); root.replaceChildren();
    const query = byId("search").value.toLocaleLowerCase("tr"); const category = byId("category").value;
    state.products.filter((p) => (!category || p.category === category) && (!query || `${p.name} ${p.category}`.toLocaleLowerCase("tr").includes(query))).forEach((p) => {
      const card = document.createElement("article"); card.className = "product";
      addText(card, "span", p.category, "category"); addText(card, "h3", p.name);
      addText(card, "span", p.delivery_type === "automatic" ? `Anında teslim · Stok ${p.stock}` : "24 saat içinde manuel teslim", "stock");
      addText(card, "strong", p.price, "price"); const button = addText(card, "button", "İncele"); button.type = "button"; button.addEventListener("click", () => openProduct(p)); root.appendChild(card);
    });
  };
  const openProduct = (p) => { state.selected = p; byId("dialogTitle").textContent = p.name; byId("dialogDescription").textContent = p.description; byId("dialogMeta").textContent = `${p.price} · ${p.delivery_type === "automatic" ? "Otomatik teslim" : "24 saat içinde manuel teslim"}`; byId("dialogGuide").textContent = p.guide || "Satın alma sonrası sipariş durumunuz bu uygulamada gösterilir."; byId("productDialog").showModal(); };
  const loadWallet = async () => { const data = await api("/api/la/wallet"); byId("walletButton").textContent = `Bakiye: ${data.balance}`; };
  const loadCatalog = async () => { const data = await api("/api/la/catalog"); state.products = data.products; const values = [...new Set(data.products.map((p) => p.category))].sort(); values.forEach((value) => { const option = document.createElement("option"); option.value = value; option.textContent = value; byId("category").appendChild(option); }); renderProducts(); };
  const loadOrders = async () => { const data = await api("/api/la/orders"); const root = byId("orderList"); root.replaceChildren(); data.orders.forEach((o) => { const item = document.createElement("article"); addText(item, "strong", o.product_name); addText(item, "div", `${o.total} · ${o.status}`); if (o.deadline_at) addText(item, "small", `Son teslim: ${new Date(o.deadline_at).toLocaleString("tr-TR")}`); root.appendChild(item); }); };
  const authenticate = async () => { const tg = globalThis.Telegram && globalThis.Telegram.WebApp; if (!tg || !tg.initData) throw new Error("Mağazayı LisansArena Telegram botundaki Mağazayı Aç düğmesinden açın."); tg.ready(); tg.expand(); const data = await api("/api/la/auth/telegram", { method: "POST", body: JSON.stringify({ initData: tg.initData }) }); state.csrf = data.csrf; setNotice(`Hoş geldin ${data.user.first_name || ""}. Güvenli mağaza hazır.`); await Promise.all([loadCatalog(), loadWallet(), loadOrders()]); };
  document.querySelectorAll(".tabs button").forEach((button) => button.addEventListener("click", () => { document.querySelectorAll(".tabs button").forEach((item) => item.classList.toggle("active", item === button)); document.querySelectorAll(".view").forEach((view) => view.classList.toggle("active", view.id === button.dataset.tab)); if (button.dataset.tab === "orders") loadOrders().catch((e) => setNotice(e.message, true)); }));
  ["search", "category"].forEach((id) => byId(id).addEventListener("input", renderProducts)); byId("dialogClose").addEventListener("click", () => byId("productDialog").close());
  byId("buyButton").addEventListener("click", async () => { if (!state.selected) return; try { const result = await api("/api/la/purchases", { method: "POST", body: JSON.stringify({ product_id: state.selected.id, quantity: 1 }) }); byId("productDialog").close(); setNotice(result.status === "delivered" ? `Teslimat: ${result.delivery.join(" · ")}` : "Sipariş alındı. En geç 24 saat içinde teslim edilecek."); await Promise.all([loadWallet(), loadOrders(), loadCatalog()]); } catch (e) { setNotice(e.message, true); } });
  [1, 100, 200, 500, 1000, 2000, 5000].forEach((amount) => { const label = amount === 1 ? "1 TL · Test" : `${amount.toLocaleString("tr-TR")} TL`; const button = addText(byId("topupPackages"), "button", label); button.type = "button"; button.addEventListener("click", async () => { try { const result = await api("/api/la/topups", { method: "POST", body: JSON.stringify({ amount_cents: amount * 100 }) }); const root = byId("topupResult"); root.replaceChildren(); root.hidden = false; addText(root, "strong", `Sipariş kodunuz: ${result.code}`); addText(root, "p", `${result.amount} yüklemek için bu kodu Shopier sipariş notuna yazın. Kod 24 saat geçerlidir.`); if (result.shopier_url) { const link = addText(root, "a", "Shopier'de ödemeye geç"); link.href = result.shopier_url; link.rel = "noopener noreferrer"; } else addText(root, "p", "Bakiye ilanı henüz bağlanmadı; ödeme yapmayın."); } catch (e) { setNotice(e.message, true); } }); });
  authenticate().catch((error) => setNotice(error.message, true));
})();

"use strict";
(() => {
  const state = { csrf: "", products: [], selected: null };
  const byId = (id) => document.getElementById(id);
  const notice = byId("notice");
  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

  const api = async (url, options = {}) => {
    const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
    if (state.csrf && options.method && options.method !== "GET") headers["X-CSRF-Token"] = state.csrf;
    const response = await fetch(url, { credentials: "include", ...options, headers });
    const data = await response.json().catch(() => ({ error: "Sunucu yanıtı okunamadı" }));
    if (!response.ok) throw new Error(data.error || "İşlem başarısız");
    return data;
  };

  const setNotice = (message, error = false) => {
    notice.querySelector("span:last-child").textContent = message;
    notice.classList.toggle("error", error);
    notice.classList.remove("loading");
  };
  const addText = (parent, tag, value, className = "") => {
    const node = document.createElement(tag);
    node.textContent = value;
    if (className) node.className = className;
    parent.appendChild(node);
    return node;
  };

  const renderProducts = () => {
    const root = byId("products");
    root.replaceChildren();
    const query = byId("search").value.toLocaleLowerCase("tr");
    const category = byId("category").value;
    const products = state.products.filter((product) =>
      (!category || product.category === category) &&
      (!query || `${product.name} ${product.category}`.toLocaleLowerCase("tr").includes(query))
    );
    products.forEach((product) => {
      const card = document.createElement("article");
      card.className = "product";
      addText(card, "span", product.category, "category");
      addText(card, "h3", product.name);
      addText(card, "span", product.delivery_type === "automatic" ? `Anında teslim · Stok ${product.stock}` : "24 saat içinde manuel teslim", "stock");
      addText(card, "strong", product.price, "price");
      const button = addText(card, "button", "Ürünü İncele");
      button.type = "button";
      button.addEventListener("click", () => openProduct(product));
      root.appendChild(card);
    });
    if (!products.length) addText(root, "p", "Aramana uygun ürün bulunamadı.", "empty");
  };

  const openProduct = (product) => {
    state.selected = product;
    byId("dialogTitle").textContent = product.name;
    byId("dialogDescription").textContent = product.description;
    byId("dialogMeta").textContent = `${product.price} · ${product.delivery_type === "automatic" ? "Otomatik teslim" : "24 saat içinde manuel teslim"}`;
    byId("dialogGuide").textContent = product.guide || "Satın alma sonrası sipariş durumunuz bu uygulamada gösterilir.";
    byId("productDialog").showModal();
  };
  const loadWallet = async () => {
    const data = await api("/api/la/wallet");
    const wallet = byId("walletButton");
    wallet.querySelector("strong").textContent = data.balance;
  };
  const loadCatalog = async () => {
    const data = await api("/api/la/catalog");
    state.products = data.products;
    const category = byId("category");
    category.querySelectorAll("option:not(:first-child)").forEach((option) => option.remove());
    [...new Set(data.products.map((product) => product.category))].sort().forEach((value) => {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = value;
      category.appendChild(option);
    });
    renderProducts();
  };
  const loadOrders = async () => {
    const data = await api("/api/la/orders");
    const root = byId("orderList");
    root.replaceChildren();
    data.orders.forEach((order) => {
      const item = document.createElement("article");
      addText(item, "strong", order.product_name);
      addText(item, "div", `${order.total} · ${order.status}`);
      if (order.deadline_at) addText(item, "small", `Son teslim: ${new Date(order.deadline_at).toLocaleString("tr-TR")}`);
      root.appendChild(item);
    });
    if (!data.orders.length) addText(root, "p", "Henüz siparişin yok.", "empty");
  };

  const telegramInitData = async () => {
    const telegram = globalThis.Telegram && globalThis.Telegram.WebApp;
    if (!telegram) throw new Error("Telegram bağlantısı kurulamadı. Bot sohbetine dönüp Mağazayı Aç düğmesine yeniden dokun.");
    telegram.ready();
    telegram.expand();
    if (typeof telegram.disableVerticalSwipes === "function") telegram.disableVerticalSwipes();
    for (let attempt = 0; attempt < 10 && !telegram.initData; attempt += 1) await sleep(150);
    if (!telegram.initData) throw new Error("Telegram doğrulama bilgisi alınamadı. Sayfayı normal tarayıcıdan değil, LisansArena botunun menüsünden aç.");
    return telegram.initData;
  };
  const authenticate = async () => {
    const initData = await telegramInitData();
    const data = await api("/api/la/auth/telegram", { method: "POST", body: JSON.stringify({ initData }) });
    state.csrf = data.csrf;
    await Promise.all([loadCatalog(), loadWallet(), loadOrders()]);
    setNotice(`Hoş geldin ${data.user.first_name || ""}. Güvenli mağaza hazır.`);
  };

  document.querySelectorAll(".tabs button").forEach((button) => button.addEventListener("click", () => {
    document.querySelectorAll(".tabs button").forEach((item) => item.classList.toggle("active", item === button));
    document.querySelectorAll(".view").forEach((view) => view.classList.toggle("active", view.id === button.dataset.tab));
    if (button.dataset.tab === "orders") loadOrders().catch((error) => setNotice(error.message, true));
  }));
  ["search", "category"].forEach((id) => byId(id).addEventListener("input", renderProducts));
  byId("dialogClose").addEventListener("click", () => byId("productDialog").close());
  byId("buyButton").addEventListener("click", async () => {
    if (!state.selected) return;
    try {
      const result = await api("/api/la/purchases", { method: "POST", body: JSON.stringify({ product_id: state.selected.id, quantity: 1 }) });
      byId("productDialog").close();
      setNotice(result.status === "delivered" ? `Teslimat: ${result.delivery.join(" · ")}` : "Sipariş alındı. En geç 24 saat içinde teslim edilecek.");
      await Promise.all([loadWallet(), loadOrders(), loadCatalog()]);
    } catch (error) { setNotice(error.message, true); }
  });
  [1, 100, 200, 500, 1000, 2000, 5000].forEach((amount) => {
    const label = amount === 1 ? "1 TL · Test" : `${amount.toLocaleString("tr-TR")} TL`;
    const button = addText(byId("topupPackages"), "button", label);
    button.type = "button";
    button.addEventListener("click", async () => {
      try {
        const result = await api("/api/la/topups", { method: "POST", body: JSON.stringify({ amount_cents: amount * 100 }) });
        const root = byId("topupResult");
        root.replaceChildren();
        root.hidden = false;
        addText(root, "strong", `Sipariş kodunuz: ${result.code}`);
        addText(root, "p", `${result.amount} yüklemek için bu kodu Shopier sipariş notuna yazın. Kod 24 saat geçerlidir.`);
        if (result.shopier_url) {
          const link = addText(root, "a", "Shopier'de Ödemeye Geç");
          link.href = result.shopier_url;
          link.rel = "noopener noreferrer";
        } else addText(root, "p", "Bakiye ilanı henüz bağlanmadı; ödeme yapmayın.");
      } catch (error) { setNotice(error.message, true); }
    });
  });
  authenticate().catch((error) => setNotice(error.message, true));
})();

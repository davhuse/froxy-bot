"use strict";
(() => {
  const state = {
    csrf: "", products: [], user: null, category: "", quantities: {},
    cart: new Map(), selectedProduct: null, dialogQuantity: 1,
    selectedTopup: null, ticketType: "support", ticketContext: {},
  };
  const tg = globalThis.Telegram && globalThis.Telegram.WebApp;
  const byId = (id) => document.getElementById(id);
  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  const money = (cents) => `${(Number(cents || 0) / 100).toLocaleString("tr-TR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} TL`;
  const haptic = (kind = "selection") => {
    try {
      if (!tg || !tg.HapticFeedback) return;
      if (kind === "success" || kind === "error") tg.HapticFeedback.notificationOccurred(kind);
      else tg.HapticFeedback.selectionChanged();
    } catch (_) {}
  };
  const addText = (parent, tag, value, className = "") => {
    const node = document.createElement(tag);
    node.textContent = value;
    if (className) node.className = className;
    parent.appendChild(node);
    return node;
  };
  const api = async (url, options = {}) => {
    const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
    if (state.csrf && options.method && options.method !== "GET") headers["X-CSRF-Token"] = state.csrf;
    const response = await fetch(url, { credentials: "include", ...options, headers });
    const data = await response.json().catch(() => ({ error: "Sunucu yanıtı okunamadı" }));
    if (!response.ok) throw new Error(data.error || "İşlem başarısız");
    return data;
  };
  const setNotice = (message, error = false) => {
    const root = byId("notice");
    root.querySelector("span:last-child").textContent = message;
    root.classList.remove("loading");
    root.classList.toggle("error", error);
    haptic(error ? "error" : "success");
  };
  const openDialog = (id) => {
    const dialog = byId(id);
    if (!dialog.open) dialog.showModal();
  };
  const closeDialog = (id) => {
    const dialog = byId(id);
    if (dialog.open) dialog.close();
  };
  const switchTab = (name) => {
    document.querySelectorAll(".tabs button").forEach((button) => button.classList.toggle("active", button.dataset.tab === name));
    document.querySelectorAll(".view").forEach((view) => view.classList.toggle("active", view.id === name));
    haptic();
    if (name === "orders") loadOrders().catch((error) => setNotice(error.message, true));
    if (name === "profile") Promise.all([loadTickets(), loadDraws()]).catch((error) => setNotice(error.message, true));
    if (name === "balance") loadWallet().catch((error) => setNotice(error.message, true));
    globalThis.scrollTo({ top: 0, behavior: "smooth" });
  };

  const renderCategories = () => {
    const root = byId("categoryChips");
    root.replaceChildren();
    ["", ...new Set(state.products.map((product) => product.category))].forEach((category) => {
      const button = addText(root, "button", category || "Tümü");
      button.type = "button";
      button.classList.toggle("active", state.category === category);
      button.addEventListener("click", () => {
        state.category = category;
        renderCategories();
        renderProducts();
        haptic();
      });
    });
  };
  const productDelivery = (product) => {
    if (product.available && product.delivery_type === "automatic") return `Otomatik teslim · ${product.stock} stok`;
    if (product.available) return "24 saat içinde manuel teslim";
    return "Talep üzerine stok ve teslimat doğrulanır";
  };
  const adjustCardQuantity = (product, amount, label) => {
    const next = Math.max(1, Math.min(10, (state.quantities[product.id] || 1) + amount));
    state.quantities[product.id] = next;
    label.textContent = String(next);
    haptic();
  };
  const renderProducts = () => {
    const root = byId("products");
    root.replaceChildren();
    const query = byId("search").value.toLocaleLowerCase("tr").trim();
    const visible = state.products.filter((product) =>
      (!state.category || product.category === state.category) &&
      (!query || `${product.name} ${product.category} ${product.description || ""}`.toLocaleLowerCase("tr").includes(query))
    );
    visible.forEach((product, index) => {
      const card = document.createElement("article");
      card.className = `product${product.featured ? " featured" : ""}`;
      card.style.animationDelay = `${Math.min(index, 8) * 35}ms`;
      const image = document.createElement("img");
      image.className = "product-image";
      image.src = product.image_url || "/la/assets/logo";
      image.alt = `${product.name} ürün kapağı`;
      image.loading = "lazy";
      image.addEventListener("error", () => { image.src = "/la/assets/logo"; }, { once: true });
      card.appendChild(image);
      const copy = document.createElement("div");
      copy.className = "product-copy";
      const badges = document.createElement("div");
      badges.className = "badges";
      addText(badges, "span", product.category, "category");
      if (product.featured) addText(badges, "span", "Vitrin", "featured-badge");
      copy.appendChild(badges);
      addText(copy, "h3", product.name);
      addText(copy, "span", productDelivery(product), "stock");
      const footer = document.createElement("div");
      footer.className = "product-footer";
      addText(footer, "strong", product.price, "product-price");
      const actions = document.createElement("div");
      actions.className = "product-actions";
      if (product.available) {
        const qty = document.createElement("div");
        qty.className = "qty";
        const minus = addText(qty, "button", "−");
        const label = addText(qty, "strong", String(state.quantities[product.id] || 1));
        const plus = addText(qty, "button", "+");
        minus.type = plus.type = "button";
        minus.addEventListener("click", () => adjustCardQuantity(product, -1, label));
        plus.addEventListener("click", () => adjustCardQuantity(product, 1, label));
        actions.appendChild(qty);
      }
      const action = addText(actions, "button", product.available ? "Sepete ekle" : "Talep oluştur", `product-action${product.available ? "" : " request"}`);
      action.type = "button";
      action.addEventListener("click", () => product.available ? addToCart(product, state.quantities[product.id] || 1) : openTicket("request", { product_id: product.id, product_name: product.name }));
      footer.appendChild(actions);
      copy.appendChild(footer);
      card.appendChild(copy);
      image.addEventListener("click", () => openProduct(product));
      copy.querySelector("h3").addEventListener("click", () => openProduct(product));
      root.appendChild(card);
    });
    if (!visible.length) addText(root, "p", "Aramana uygun ürün bulunamadı. Ürün talebi oluşturabilirsin.", "empty");
  };
  const loadCatalog = async () => {
    const data = await api("/api/la/catalog");
    state.products = data.products || [];
    const active = state.products.filter((product) => product.available).length;
    byId("productCount").textContent = active ? `${active} ürün satışta · ${state.products.length} ürün katalogda` : `${state.products.length} ürün katalogda`;
    renderCategories();
    renderProducts();
  };

  const openProduct = (product) => {
    state.selectedProduct = product;
    state.dialogQuantity = state.quantities[product.id] || 1;
    byId("dialogImage").src = product.image_url || "/la/assets/logo";
    byId("dialogBadge").textContent = product.featured ? `${product.category} · Vitrin` : product.category;
    byId("dialogTitle").textContent = product.name;
    byId("dialogDescription").textContent = product.description;
    byId("dialogMeta").textContent = `${product.price} · ${productDelivery(product)}`;
    byId("dialogGuide").textContent = product.guide || "Sipariş ve teslimat durumu uygulamada gösterilir.";
    byId("dialogQuantity").textContent = String(state.dialogQuantity);
    byId("productAction").textContent = product.available ? "Sepete ekle" : "Talep oluştur";
    document.querySelector(".quantity-row").hidden = !product.available;
    openDialog("productDialog");
  };
  const addToCart = (product, quantity) => {
    const current = state.cart.get(product.id);
    const next = Math.min(10, (current ? current.quantity : 0) + Number(quantity || 1));
    state.cart.set(product.id, { product, quantity: next });
    updateCart();
    haptic("success");
    setNotice(`${product.name} sepete eklendi.`);
  };
  const updateCart = () => {
    let count = 0;
    let total = 0;
    state.cart.forEach(({ product, quantity }) => { count += quantity; total += Number(product.price_cents) * quantity; });
    byId("cartBar").hidden = count === 0;
    byId("cartCount").textContent = `${count} ürün`;
    byId("cartTotal").textContent = money(total);
    byId("cartDialogTotal").textContent = money(total);
    renderCartItems();
  };
  const renderCartItems = () => {
    const root = byId("cartItems");
    root.replaceChildren();
    state.cart.forEach(({ product, quantity }) => {
      const row = document.createElement("article");
      row.className = "cart-item";
      const image = document.createElement("img"); image.src = product.image_url || "/la/assets/logo"; image.alt = ""; row.appendChild(image);
      const copy = document.createElement("div"); addText(copy, "strong", product.name); addText(copy, "small", `${quantity} adet · ${money(product.price_cents * quantity)}`); row.appendChild(copy);
      const remove = addText(row, "button", "×"); remove.type = "button"; remove.addEventListener("click", () => { state.cart.delete(product.id); updateCart(); haptic(); });
      root.appendChild(row);
    });
    if (!state.cart.size) addText(root, "p", "Sepetin boş.", "empty");
  };
  const checkout = async () => {
    if (!state.cart.size) return;
    const button = byId("checkoutButton");
    button.disabled = true; button.textContent = "Sipariş oluşturuluyor…";
    try {
      const result = await api("/api/la/cart/checkout", { method: "POST", body: JSON.stringify({ items: [...state.cart.values()].map(({ product, quantity }) => ({ product_id: product.id, quantity })) }) });
      state.cart.clear(); updateCart(); closeDialog("cartDialog");
      const automatic = result.orders.filter((order) => order.status === "delivered");
      const message = automatic.length ? `Sipariş tamamlandı. Teslimat bilgisi Siparişler bölümünde.` : "Sipariş alındı. Manuel ürünler en geç 24 saat içinde teslim edilecek.";
      setNotice(message); switchTab("orders");
      await Promise.all([loadWallet(), loadOrders(), loadCatalog()]);
    } catch (error) { setNotice(error.message, true); }
    finally { button.disabled = false; button.textContent = "Bakiyemle satın al"; }
  };

  const loadWallet = async () => {
    const data = await api("/api/la/wallet");
    byId("walletButton").querySelector("strong").textContent = data.balance;
    const root = byId("walletEntries"); root.replaceChildren();
    (data.entries || []).slice(0, 20).forEach((entry) => {
      const row = document.createElement("article");
      addText(row, "strong", entry.entry_type.replaceAll("_", " "));
      const line = document.createElement("div"); addText(line, "span", entry.reference_id); addText(line, "span", entry.amount); row.appendChild(line); root.appendChild(row);
    });
    if (!data.entries.length) addText(root, "p", "Henüz bakiye hareketi yok.", "empty");
  };
  let topupTimer = null;
  const watchTopup = () => {
    if (topupTimer) clearInterval(topupTimer);
    let attempts = 0;
    topupTimer = setInterval(() => { attempts += 1; loadWallet().catch(() => {}); if (attempts >= 40) clearInterval(topupTimer); }, 15000);
  };
  const renderTopups = () => {
    const root = byId("topupPackages"); root.replaceChildren();
    [100, 200, 500, 1000, 2000, 5000].forEach((amount) => {
      const button = document.createElement("button"); button.type = "button"; button.className = "package"; button.setAttribute("role", "radio");
      addText(button, "strong", `${amount.toLocaleString("tr-TR")} TL`); addText(button, "span", "LisansArena bakiyesi");
      button.addEventListener("click", () => {
        state.selectedTopup = amount;
        document.querySelectorAll(".package").forEach((item) => { const chosen = item === button; item.classList.toggle("selected", chosen); item.setAttribute("aria-checked", String(chosen)); });
        byId("topupContinue").disabled = false; haptic();
      });
      root.appendChild(button);
    });
  };
  const createTopup = async () => {
    if (!state.selectedTopup) return;
    const button = byId("topupContinue"); button.disabled = true; button.textContent = "Bağlantı hazırlanıyor…";
    try {
      const result = await api("/api/la/topups", { method: "POST", body: JSON.stringify({ amount_cents: state.selectedTopup * 100 }) });
      const root = byId("topupResult"); root.replaceChildren(); root.hidden = false;
      addText(root, "span", "ÖDEME HAZIR", "payment-ready");
      addText(root, "strong", `Sipariş kodun: ${result.code}`, "payment-code");
      addText(root, "p", `${result.amount} bakiye yüklemesi için aşağıdaki kodu Shopier sipariş notuna aynen ekle.`);
      const actions = document.createElement("div"); actions.className = "payment-result-actions";
      const copy = addText(actions, "button", "Kodu kopyala", "copy-code"); copy.type = "button";
      copy.addEventListener("click", async () => {
        try { await navigator.clipboard.writeText(result.code); copy.textContent = "Kopyalandı ✓"; haptic("success"); }
        catch (_) { setNotice(`Kodu kopyalayamadık: ${result.code}`, true); }
      });
      const link = addText(actions, "a", "Shopier'de ödemeye geç", "shopier-payment");
      link.href = result.shopier_url; link.rel = "noopener noreferrer";
      link.addEventListener("click", (event) => {
        watchTopup();
        if (tg?.openLink) { event.preventDefault(); tg.openLink(result.shopier_url); }
      });
      root.appendChild(actions);
      addText(root, "p", "Kod 24 saat geçerlidir. Ödeme doğrulandıktan sonra bakiye en geç 10 dakika içinde otomatik güncellenir.", "payment-confirmation-note");
      haptic("success");
    } catch (error) { setNotice(error.message, true); }
    finally { button.disabled = false; button.textContent = "Ödeme adımına geç"; }
  };

  const loadOrders = async () => {
    const data = await api("/api/la/orders");
    const root = byId("orderList"); root.replaceChildren();
    (data.orders || []).forEach((order) => {
      const row = document.createElement("article");
      addText(row, "strong", order.product_name);
      const detail = document.createElement("div"); addText(detail, "span", `${order.quantity} adet · ${order.total}`); addText(detail, "span", order.status, "status-pill"); row.appendChild(detail);
      if (order.deadline_at) addText(row, "small", `Son teslim: ${new Date(order.deadline_at).toLocaleString("tr-TR")}`);
      const refund = addText(row, "button", "İade / sorun bildir", "product-action request"); refund.type = "button"; refund.addEventListener("click", () => openTicket("refund", { order_id: order.id, product_name: order.product_name }));
      root.appendChild(row);
    });
    if (!data.orders.length) addText(root, "p", "Henüz siparişin yok.", "empty");
  };
  const openTicket = (type, context = {}) => {
    state.ticketType = type; state.ticketContext = context;
    const labels = { support: "Destek talebi", request: "Ürün talebi", refund: "İade talebi" };
    byId("ticketTitle").textContent = labels[type] || "Talep oluştur";
    byId("ticketSubject").value = context.product_name ? `${labels[type]} · ${context.product_name}` : labels[type];
    byId("ticketMessage").value = "";
    openDialog("ticketDialog");
  };
  const submitTicket = async () => {
    const message = byId("ticketMessage").value.trim();
    const payload = { ticket_type: state.ticketType, subject: byId("ticketSubject").value.trim(), message, ...state.ticketContext };
    try {
      const result = await api("/api/la/tickets", { method: "POST", body: JSON.stringify(payload) });
      closeDialog("ticketDialog"); setNotice(`Talebin alındı (#${result.id}).`); await loadTickets();
    } catch (error) { setNotice(error.message, true); }
  };
  const loadTickets = async () => {
    const data = await api("/api/la/tickets"); const root = byId("ticketList"); root.replaceChildren();
    (data.tickets || []).forEach((ticket) => {
      const row = document.createElement("article"); addText(row, "strong", ticket.subject);
      const line = document.createElement("div"); addText(line, "span", `#${ticket.id} · ${ticket.ticket_type}`); addText(line, "span", ticket.status, "status-pill"); row.appendChild(line);
      if (ticket.admin_reply) addText(row, "small", `Yanıt: ${ticket.admin_reply}`); root.appendChild(row);
    });
    if (!data.tickets.length) addText(root, "p", "Henüz açık talebin yok.", "empty");
  };
  const loadDraws = async () => {
    const data = await api("/api/la/draws"); const root = byId("drawList"); root.replaceChildren();
    (data.draws || []).forEach((draw) => {
      const row = document.createElement("article"); addText(row, "strong", draw.title); addText(row, "small", draw.description || "LisansArena çekilişi");
      const button = addText(row, "button", draw.entered ? "Katılım alındı" : "Katıl", "product-action"); button.type = "button"; button.disabled = draw.entered;
      button.addEventListener("click", async () => { try { await api(`/api/la/draws/${draw.id}/enter`, { method: "POST", body: "{}" }); setNotice("Çekiliş katılımın alındı."); await loadDraws(); } catch (error) { setNotice(error.message, true); } }); root.appendChild(row);
    });
    if (!data.draws.length) addText(root, "p", "Şu anda aktif çekiliş yok.", "empty");
  };
  const renderProfile = (user) => {
    const fullName = [user.first_name, user.last_name].filter(Boolean).join(" ") || "Telegram kullanıcısı";
    byId("profileName").textContent = fullName; byId("profileUsername").textContent = user.username ? `@${user.username}` : "Telegram hesabı";
    byId("referralCode").textContent = user.referral_code || "Hazırlanıyor"; byId("telegramBadge").textContent = "Telegram bağlı";
    byId("profileInitial").textContent = fullName.slice(0, 2).toLocaleUpperCase("tr");
    byId("referralStatus").textContent = `${user.referral_count || 0} kayıtlı referans · Ödül sistemi kârlılık testi sonrasında açılacak.`;
    if (user.photo_url) { const photo = byId("profilePhoto"); photo.src = user.photo_url; photo.hidden = false; byId("profileInitial").hidden = true; photo.addEventListener("error", () => { photo.hidden = true; byId("profileInitial").hidden = false; }, { once: true }); }
  };
  const telegramInitData = async () => {
    if (tg) { tg.ready(); tg.expand(); if (typeof tg.disableVerticalSwipes === "function") tg.disableVerticalSwipes(); }
    const read = () => {
      if (tg && tg.initData) return tg.initData;
      const hash = new URLSearchParams(globalThis.location.hash.replace(/^#/, "")); const query = new URLSearchParams(globalThis.location.search);
      return hash.get("tgWebAppData") || query.get("tgWebAppData") || "";
    };
    for (let attempt = 0; attempt < 20 && !read(); attempt += 1) await sleep(150);
    if (!read()) throw new Error("Telegram doğrulaması gerekli. Mağazayı LisansArenaBot içindeki Mağazayı Aç düğmesinden başlat.");
    return read();
  };
  const authenticate = async () => {
    const initData = await telegramInitData();
    const startParam = (tg && tg.initDataUnsafe && tg.initDataUnsafe.start_param) || "";
    const data = await api("/api/la/auth/telegram", { method: "POST", body: JSON.stringify({ initData, startParam }) });
    state.csrf = data.csrf; state.user = data.user; renderProfile(data.user);
    await Promise.all([loadCatalog(), loadWallet(), loadOrders(), loadTickets(), loadDraws()]);
    setNotice(`Hoş geldin ${data.user.first_name || ""}. Mağaza hazır.`);
    setTimeout(() => byId("splash").classList.add("done"), 220);
  };

  document.querySelectorAll(".tabs button").forEach((button) => button.addEventListener("click", () => switchTab(button.dataset.tab)));
  document.querySelectorAll("[data-close]").forEach((button) => button.addEventListener("click", () => closeDialog(button.dataset.close)));
  document.querySelectorAll("[data-ticket]").forEach((button) => button.addEventListener("click", () => openTicket(button.dataset.ticket)));
  document.querySelectorAll("[data-open-tab]").forEach((button) => button.addEventListener("click", () => switchTab(button.dataset.openTab)));
  byId("search").addEventListener("input", renderProducts);
  byId("openCart").addEventListener("click", () => openDialog("cartDialog"));
  byId("checkoutButton").addEventListener("click", checkout);
  byId("topupContinue").addEventListener("click", createTopup);
  byId("ticketSubmit").addEventListener("click", submitTicket);
  byId("quantityMinus").addEventListener("click", () => { state.dialogQuantity = Math.max(1, state.dialogQuantity - 1); byId("dialogQuantity").textContent = state.dialogQuantity; haptic(); });
  byId("quantityPlus").addEventListener("click", () => { state.dialogQuantity = Math.min(10, state.dialogQuantity + 1); byId("dialogQuantity").textContent = state.dialogQuantity; haptic(); });
  byId("productAction").addEventListener("click", () => {
    const product = state.selectedProduct; if (!product) return;
    closeDialog("productDialog");
    if (product.available) addToCart(product, state.dialogQuantity);
    else openTicket("request", { product_id: product.id, product_name: product.name });
  });
  renderTopups();
  globalThis.addEventListener("focus", () => { if (state.user) loadWallet().catch(() => {}); });
  document.addEventListener("visibilitychange", () => { if (document.visibilityState === "visible" && state.user) loadWallet().catch(() => {}); });
  setTimeout(() => { if (!state.user) byId("splash").classList.add("done"); }, 4500);
  authenticate().catch((error) => { byId("splash").classList.add("done"); setNotice(error.message, true); });
})();

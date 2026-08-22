// ==========================================================================
// LISANSARENA APP — ULTRAVIOLET CYBERVAULT JAVASCRIPT ENGINE (v8.0)
// Features: Full Multi-item Cart, Real-Time Shopier Sync, Instant Cleanup, AI Artworks
// ==========================================================================

(function () {
  'use strict';

  // Telegram WebApp Setup
  const tg = window.Telegram?.WebApp;
  const API_BASE = window.location.pathname.startsWith('/la/app') ? '/la/app' : '';
  const api = path => `${API_BASE}${path}`;
  const telegramInitData = tg?.initData || '';
  function authHeaders() {
    const headers = { 'Content-Type': 'application/json' };
    if (telegramInitData) headers['X-Telegram-Init-Data'] = telegramInitData;
    return headers;
  }
  if (tg) {
    tg.ready();
    tg.expand();
    try {
      tg.headerColor = '#06050C';
      tg.backgroundColor = '#06050C';
    } catch (e) {}
  }

  // App State
  let allProducts = [];
  let currentCategory = 'all';
  let searchQuery = '';
  let activeTopupAmount = 50;
  let selectedModalProduct = null;
  let cart = []; // Array of { id, title, price_num, price, image, qty }

  // Load cart from localStorage
  try {
    const savedCart = localStorage.getItem('lisansarena_cart');
    if (savedCart) {
      cart = JSON.parse(savedCart);
    }
  } catch (e) {}

  const tgUser = tg?.initDataUnsafe?.user || {
    id: null,
    first_name: "LisansArena",
    last_name: "Müşterisi",
    username: "LisansArenaOnline"
  };

  let userProfile = {
    id: tgUser.id,
    full_name: `${tgUser.first_name || ''} ${tgUser.last_name || ''}`.trim() || 'LisansArena Müşterisi',
    balance: 0.0,
    referrals_count: 0,
    referral_earnings: 0.0,
    orders: []
  };

  // DOM Elements
  const headerBalance = document.getElementById('headerBalance');
  const walletTabBalance = document.getElementById('walletTabBalance');
  const profileFullName = document.getElementById('profileFullName');
  const profileUserId = document.getElementById('profileUserId');
  const refCount = document.getElementById('refCount');
  const refEarnings = document.getElementById('refEarnings');
  const refLinkInput = document.getElementById('refLinkInput');
  const productsGrid = document.getElementById('productsGrid');
  const productCountBadge = document.getElementById('productCountBadge');
  const currentCategoryTitle = document.getElementById('currentCategoryTitle');
  const customAmountInput = document.getElementById('customAmountInput');
  const btnProceedTopup = document.getElementById('btnProceedTopup');
  const headerCartCount = document.getElementById('headerCartCount');
  const dockCartBadge = document.getElementById('dockCartBadge');
  const cartItemsContainer = document.getElementById('cartItemsContainer');
  const cartSummaryBox = document.getElementById('cartSummaryBox');
  const cartEmptyState = document.getElementById('cartEmptyState');
  const cartTotalItems = document.getElementById('cartTotalItems');
  const cartTotalAmount = document.getElementById('cartTotalAmount');
  const laOrdersList = document.getElementById('laOrdersList');

  // Modals
  const productModal = document.getElementById('productModal');
  const modalImg = document.getElementById('modalImg');
  const modalTitle = document.getElementById('modalTitle');
  const modalPrice = document.getElementById('modalPrice');
  const modalDesc = document.getElementById('modalDesc');
  const modalBadge = document.getElementById('modalBadge');
  const modalShopierLink = document.getElementById('modalShopierLink');
  const modalWalletBuyBtn = document.getElementById('modalWalletBuyBtn');
  const topupRedirectModal = document.getElementById('topupRedirectModal');
  const topupRedirectBtn = document.getElementById('topupRedirectBtn');
  const vaultToast = document.getElementById('vaultToast');

  // Category Labels
  const CATEGORY_TITLES = {
    all: 'Tüm Lisanslar',
    vitrin: '⭐ Vitrin & Özel Seçimler',
    ai: '🤖 Yapay Zeka & LLM Lisansları',
    gaming: '🎮 Oyun & E-Pin Arenası',
    design: '🎨 Tasarım & Kreatif Araçlar',
    software: '💻 Yazılım & Lisans Keyleri',
    cinema: '🎬 Sinema, Dizi & Müzik',
    social: '💬 Hesap & Sosyal Medya',
    coupons: '🎟️ İndirim Kuponu & Yakıt'
  };

  // Toast Function
  window.showToast = function (msg) {
    if (!vaultToast) return;
    vaultToast.textContent = msg;
    vaultToast.classList.add('show');
    if (tg?.HapticFeedback) {
      tg.HapticFeedback.notificationOccurred('success');
    }
    setTimeout(() => {
      vaultToast.classList.remove('show');
    }, 2800);
  };

  // Init
  document.addEventListener('DOMContentLoaded', async () => {
    updateCartUI();
    await fetchProducts();
    await fetchUserProfile();
    await fetchReferralData();

    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('payment') === 'success' || urlParams.get('order') === 'success') {
      showPurchaseSuccessModal("Shopier Ödemesi Onaylandı", null);
      try { window.history.replaceState({}, document.title, window.location.pathname); } catch (e) {}
    }

    // Auto sync paid orders every 12 seconds
    setInterval(() => syncOrdersSilently(true), 12000);

    // Instant auto-refresh when switching back to Telegram from Shopier
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'visible') {
        syncOrdersSilently(true);
      }
    });
    window.addEventListener('focus', () => {
      syncOrdersSilently(true);
    });
  });

  // Fetch Products
  async function fetchProducts() {
    try {
      const res = await fetch(api('/api/products'));
      const data = await res.json();
      if (data.success && data.products) {
        allProducts = data.products;
        renderProducts();

        // Deep-link product modal auto-open
        try {
          const urlParams = new URLSearchParams(window.location.search);
          const targetParam = urlParams.get('product') || tg?.initDataUnsafe?.start_param;
          if (targetParam) {
            const cleanId = String(targetParam).replace(/^p_/, '').trim().toLowerCase();
            const matched = allProducts.find(p => String(p.id).toLowerCase() === cleanId);
            if (matched) {
              setTimeout(() => openProductModal(matched), 250);
            }
          }
        } catch (err) {}
      }
    } catch (e) {
      console.error('Products fetch error:', e);
    }
  }

  // Fetch User Profile
  async function fetchUserProfile() {
    try {
      const res = await fetch(api('/api/user/profile'), {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({
          init_data: telegramInitData,
          user_id: tgUser.id,
          username: tgUser.username || "",
          first_name: tgUser.first_name || "",
          last_name: tgUser.last_name || ""
        })
      });
      const data = await res.json();
      if (data.success && data.user) {
        userProfile.balance = Number(data.user.balance || 0);
        userProfile.full_name = data.user.full_name || userProfile.full_name;
        userProfile.orders = Array.isArray(data.user.orders) ? data.user.orders : [];
        updateUI();
      }
    } catch (e) {
      console.error('User profile fetch error:', e);
    }
  }

  // Fetch Referral Data
  async function fetchReferralData() {
    try {
      const res = await fetch(api(`/api/referrals/${tgUser.id}`), { headers: authHeaders() });
      const data = await res.json();
      if (data.success) {
        userProfile.referrals_count = data.referrals_count || 0;
        userProfile.referral_earnings = data.referral_earnings || 0.0;
        if (refLinkInput) {
          refLinkInput.value = data.ref_link || `https://t.me/LisansArenaOnline?start=ref_${tgUser.id}`;
        }
        updateUI();
      }
    } catch (e) {
      console.error('Referrals fetch error:', e);
    }
  }

  // Manual Refresh
  window.manualRefreshData = async function () {
    window.showToast("🔄 Bilgiler güncelleniyor...");
    await fetchProducts();
    await syncOrdersSilently(false);
    window.showToast("✅ Siparişler ve bakiye güncellendi!");
  };

  // Sync Orders Silently & Real-time Auto-Detection
  let isSyncing = false;
  async function syncOrdersSilently(triggerSuccessOnNewOrder = true) {
    if (isSyncing) return;
    isSyncing = true;
    try {
      const prevOrderCount = Array.isArray(userProfile.orders) ? userProfile.orders.length : 0;
      const prevLastOrderId = prevOrderCount > 0 ? (userProfile.orders[userProfile.orders.length - 1].order_id || '') : '';
      
      const res = await fetch(api('/api/balance/sync-orders'), { headers: authHeaders() });
      const data = await res.json();
      await fetchUserProfile();
      
      if (data.success && data.credited_orders && data.credited_orders.length > 0) {
        window.showToast("🎉 Bakiye yüklemeniz onaylandı ve cüzdanınıza yansıtıldı!");
      }

      if (triggerSuccessOnNewOrder) {
        const currentOrders = Array.isArray(userProfile.orders) ? userProfile.orders : [];
        if (currentOrders.length > prevOrderCount) {
          const latestOrder = currentOrders[currentOrders.length - 1];
          if (latestOrder && (latestOrder.order_id || '') !== prevLastOrderId) {
            showPurchaseSuccessModal(latestOrder.title || "Dijital Lisans", latestOrder.subtotal || latestOrder.price);
          }
        }
      }
    } catch (e) {
    } finally {
      isSyncing = false;
    }
  }

  // Active Polling when Shopier payment initiated
  let activePollingInterval = null;
  window.startRealtimePaymentWatcher = function () {
    if (activePollingInterval) clearInterval(activePollingInterval);
    let pollsLeft = 40; // 40 x 3s = 120 seconds active watcher
    activePollingInterval = setInterval(async () => {
      pollsLeft--;
      if (pollsLeft <= 0) {
        clearInterval(activePollingInterval);
        activePollingInterval = null;
        return;
      }
      await syncOrdersSilently(true);
    }, 3000);
  };

  // Update UI Elements
  function updateUI() {
    const formattedBal = `₺${Number(userProfile.balance).toFixed(2)}`;
    if (headerBalance) headerBalance.textContent = formattedBal;
    if (walletTabBalance) walletTabBalance.textContent = formattedBal;
    if (profileFullName) profileFullName.textContent = userProfile.full_name;
    if (profileUserId) profileUserId.textContent = `Telegram ID: ${tgUser.id}`;
    if (refCount) refCount.textContent = userProfile.referrals_count;
    if (refEarnings) refEarnings.textContent = `₺${Number(userProfile.referral_earnings).toFixed(2)}`;
    renderOrders();
  }

  function renderOrders() {
    const dedicatedList = document.getElementById('dedicatedOrdersList');
    const legacyList = document.getElementById('laOrdersList');
    const containers = [dedicatedList, legacyList].filter(Boolean);
    
    if (containers.length === 0) return;
    
    containers.forEach(c => c.replaceChildren());
    const orders = Array.isArray(userProfile.orders) ? [...userProfile.orders].reverse() : [];
    
    if (!orders.length) {
      containers.forEach(c => {
        const empty = document.createElement('div');
        empty.className = 'la-orders-empty';
        empty.style.cssText = 'padding: 30px 15px; text-align: center; color: var(--text-muted);';
        empty.innerHTML = `
          <div style="font-size: 2.2rem; margin-bottom: 8px;">📦</div>
          <p style="font-size: 0.88rem; font-weight: 600;">Henüz bir siparişiniz bulunmuyor.</p>
        `;
        c.append(empty);
      });
      return;
    }

    const labels = {
      delivered: '✅ Teslim Edildi',
      pending_delivery: '⏳ Hazırlanıyor',
      processing: '⏳ İşlemde',
      paid: '⚡ Ödeme Alındı',
      completed: '✅ Tamamlandı',
      cancelled: '❌ İptal Edildi'
    };

    orders.slice(0, 30).forEach((order, index) => {
      const card = document.createElement('div');
      card.className = 'order-card-cyber';

      const topRow = document.createElement('div');
      topRow.className = 'order-card-top';

      const title = document.createElement('h3');
      title.className = 'order-card-title';
      title.textContent = order.title || order.product_name || 'LisansArena Lisans Siparişi';

      const isDelivered = order.status === 'delivered' || order.status === 'completed' || Boolean(order.license_key);
      const statusBadge = document.createElement('span');
      statusBadge.className = `order-status-badge ${isDelivered ? 'delivered' : 'pending'}`;
      statusBadge.textContent = labels[order.status] || (isDelivered ? '✅ Teslim Edildi' : '⏳ Hazırlanıyor');

      topRow.append(title, statusBadge);

      const number = order.order_id || order.id || order.product_id || `LA-${String(index + 1).padStart(5, '0')}`;
      const amount = Number(order.subtotal ?? order.price ?? order.amount ?? 0).toFixed(2);
      const date = order.created_at ? new Date(Number(order.created_at) * 1000) : null;
      const dateStr = date && !Number.isNaN(date.getTime()) ? date.toLocaleString('tr-TR') : 'Şimdi';

      const metaGrid = document.createElement('div');
      metaGrid.className = 'order-meta-grid';
      metaGrid.innerHTML = `
        <div class="order-meta-item">
          <span class="order-meta-label">Sipariş No</span>
          <span class="order-meta-val">${number}</span>
        </div>
        <div class="order-meta-item">
          <span class="order-meta-label">Tutar</span>
          <span class="order-meta-val price-highlight">₺${amount}</span>
        </div>
        <div class="order-meta-item" style="grid-column: span 2;">
          <span class="order-meta-label">Tarih</span>
          <span class="order-meta-val">${dateStr}</span>
        </div>
      `;

      card.append(topRow, metaGrid);

      if (order.license_key) {
        const codeBox = document.createElement('div');
        codeBox.className = 'license-code-box';

        const codeText = document.createElement('span');
        codeText.className = 'license-code-text';
        codeText.textContent = `🔑 ${order.license_key}`;

        const copyBtn = document.createElement('button');
        copyBtn.className = 'btn-copy-code';
        copyBtn.type = 'button';
        copyBtn.textContent = 'KOPYALA';
        copyBtn.addEventListener('click', (e) => {
          e.stopPropagation();
          window.copyOrderLicenseCode(order.license_key);
        });

        codeBox.append(codeText, copyBtn);
        card.append(codeBox);

        const isYoutube = order.redeem_url || /youtube/i.test(order.title || order.product_name || '');
        if (isYoutube) {
          const ytGuide = document.createElement('div');
          ytGuide.style.cssText = 'background: rgba(255, 0, 80, 0.1); border: 1px solid rgba(255, 0, 80, 0.3); border-radius: var(--radius-sm); padding: 10px 12px; margin-top: 6px; font-size: 0.76rem; color: #fff; line-height: 1.4;';
          ytGuide.innerHTML = `
            <div style="display:flex; align-items:center; gap:6px; color:#FF0050; font-weight:800; margin-bottom:4px;">
              <span>🔗</span>
              <span>YouTube Etkinleştirme Rehberi</span>
            </div>
            <div style="margin-bottom:6px;">Kodunuzu <a href="https://youtube.com/redeem" target="_blank" style="color:var(--neon-pink); font-weight:800; text-decoration:underline;">youtube.com/redeem</a> linkinden kullanabilirsiniz.</div>
            <div style="color:var(--text-muted); font-size:0.72rem;">⚠️ <strong>Önemli:</strong> Yeni açılmış bir Google hesabı ve daha önce YouTube Premium kullanılmamış yeni bir kart ile aktif ettiğinizden emin olunuz.</div>
          `;
          card.append(ytGuide);
        }
      } else {
        const isEmail = order.needs_email || /duolingo|gemini|canva/i.test(order.title || order.product_name || '');
        const manualBox = document.createElement('div');
        manualBox.className = 'manual-delivery-box';
        manualBox.innerHTML = `
          <div class="mdb-header" style="color:${isEmail ? '#A855F7' : '#FBBF24'};">
            <span>${isEmail ? '📧' : '💬'}</span>
            <strong>${isEmail ? 'E-Posta Tanımlaması Bekleniyor' : 'Manuel Teslimat / Temsilci Bekleniyor'}</strong>
          </div>
          <p class="mdb-desc">
            ${isEmail 
              ? `Bu ürün üyelik e-posta tanımlaması ile teslim edilir. Lütfen aşağıdaki butona dokunarak destek ekibimize sipariş kodunuz (<strong>#${number}</strong>) ile birlikte <strong>E-posta (Mail)</strong> adresinizi iletiniz; üyeliğiniz anında tanımlanacaktır.`
              : `Bu ürün temsilci teslimatı kapsamındadır. Lütfen aşağıdaki butona dokunarak destek temsilcimize sipariş kodunuzu (<strong>#${number}</strong>) iletiniz; temsilcimiz hesabınızı/lisansınızı anında teslim edecektir.`
            }
          </p>
          <a href="https://t.me/LisansArenaOnline" target="_blank" class="btn-support-contact" style="${isEmail ? 'background: linear-gradient(135deg, #A855F7, #EC4899); color:#fff;' : ''}">
            <span>🚀 @LisansArenaOnline ile İletişime Geç</span>
          </a>
        `;
        card.append(manualBox);
      }

      if (dedicatedList) dedicatedList.append(card.cloneNode(true));
      if (legacyList) legacyList.append(card);
    });
  }

  // Success Modal Functions
  window.showPurchaseSuccessModal = function (title, amount) {
    const modal = document.getElementById('purchaseSuccessModal');
    if (!modal) return;
    const prodEl = document.getElementById('successModalProduct');
    if (prodEl) prodEl.textContent = title || 'Dijital Ürün / Lisans';
    const amtEl = document.getElementById('successModalAmount');
    if (amtEl) amtEl.textContent = amount ? `₺${Number(amount).toFixed(2)}` : 'Ödeme Onaylandı';
    modal.classList.add('active');
    if (tg?.HapticFeedback) {
      tg.HapticFeedback.notificationOccurred('success');
    }
  };

  window.closePurchaseSuccessModal = function () {
    const modal = document.getElementById('purchaseSuccessModal');
    if (modal) modal.classList.remove('active');
  };

  window.goToOrdersFromSuccess = function () {
    closePurchaseSuccessModal();
    switchVaultTab('orders');
  };

  window.copyOrderLicenseCode = function (code) {
    navigator.clipboard.writeText(code).then(() => {
      window.showToast('Lisans anahtarı panoya kopyalandı! 📋');
    });
  };

  // Tab Switching
  window.switchVaultTab = function (tabName) {
    document.querySelectorAll('.tab-pane').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.dock-btn').forEach(el => el.classList.remove('active'));

    const targetPane = document.getElementById(`tab-${tabName}`);
    if (targetPane) targetPane.classList.add('active');

    const targetBtn = document.querySelector(`.dock-btn[data-tab="${tabName}"]`);
    if (targetBtn) targetBtn.classList.add('active');

    if (tg?.HapticFeedback) {
      tg.HapticFeedback.impactOccurred('light');
    }

    if (tabName === 'cart') {
      renderCartItems();
    }

    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  // Category Filtering
  window.filterCategory = function (cat, btn) {
    currentCategory = cat;
    document.querySelectorAll('.cyber-tab').forEach(el => el.classList.remove('active'));
    if (btn) btn.classList.add('active');

    if (currentCategoryTitle) {
      currentCategoryTitle.textContent = CATEGORY_TITLES[cat] || 'Lisanslar';
    }

    if (tg?.HapticFeedback) {
      tg.HapticFeedback.impactOccurred('light');
    }

    renderProducts();
  };

  // Search Handling
  window.handleSearch = function (val) {
    searchQuery = val.trim().toLowerCase();
    const clearBtn = document.getElementById('clearSearchBtn');
    if (clearBtn) {
      clearBtn.style.display = searchQuery.length > 0 ? 'flex' : 'none';
    }
    renderProducts();
  };

  window.clearSearch = function () {
    const input = document.getElementById('searchInput');
    if (input) input.value = '';
    searchQuery = '';
    const clearBtn = document.getElementById('clearSearchBtn');
    if (clearBtn) clearBtn.style.display = 'none';
    renderProducts();
  };

  // Render Products Grid
  function renderProducts() {
    if (!productsGrid) return;
    productsGrid.innerHTML = '';

    let filtered = allProducts.filter(p => {
      if (currentCategory === 'vitrin') {
        return p.showcase === true || p.is_vitrin === true;
      }
      if (currentCategory !== 'all' && p.category !== currentCategory) {
        return false;
      }
      if (searchQuery) {
        const t = (p.title || '').toLowerCase();
        const d = (p.description || '').toLowerCase();
        return t.includes(searchQuery) || d.includes(searchQuery);
      }
      return true;
    });

    if (productCountBadge) {
      productCountBadge.textContent = `${filtered.length} Ürün`;
    }

    if (filtered.length === 0) {
      productsGrid.innerHTML = `
        <div class="empty-state" style="grid-column: 1 / -1; padding: 40px 10px; text-align: center;">
          <div style="font-size: 2.5rem; margin-bottom: 8px;">🔍</div>
          <h3 style="color: #fff; font-size: 1rem; margin-bottom: 4px;">Aradığınız kriterde lisans bulunamadı</h3>
          <p style="color: var(--text-muted); font-size: 0.78rem;">Lütfen başka bir arama veya kategori seçin.</p>
        </div>
      `;
      return;
    }

    filtered.forEach(p => {
      const card = document.createElement('div');
      card.className = 'cyber-product-card';
      const badgeText = (p.showcase || p.is_vitrin) ? "💎 VIP Lisans" : "⚡ Orijinal";

      card.innerHTML = `
        <div class="card-media" onclick='openProductModal(${JSON.stringify(p).replace(/'/g, "&apos;")})'>
          <img src="${p.image}?v=8.0" alt="${p.title}" loading="lazy" onerror="this.src='assets/products/art_48945493.jpg'">
          <span class="card-tag">${badgeText}</span>
        </div>
        <div class="card-info">
          <h3 class="card-info-title" onclick='openProductModal(${JSON.stringify(p).replace(/'/g, "&apos;")})'>${p.title}</h3>
          <div class="card-price-row">
            <span class="card-price-val">${p.price}</span>
          </div>
          <div class="card-btns-grid">
            <button class="btn-card-cart" onclick='addToCart(${JSON.stringify(p).replace(/'/g, "&apos;")})' title="Sepete Ekle">
              <span>🛒 + Sepete Ekle</span>
            </button>
            <button class="btn-card-buy" onclick='openProductModal(${JSON.stringify(p).replace(/'/g, "&apos;")})' title="Satın Al">
              ➔
            </button>
          </div>
        </div>
      `;
      productsGrid.appendChild(card);
    });
  }

  // ==================== CART (SEPET) ENGINE ====================
  function saveCart() {
    try {
      localStorage.setItem('lisansarena_cart', JSON.stringify(cart));
    } catch (e) {}
    updateCartUI();
  }

  function updateCartUI() {
    const totalCount = cart.reduce((sum, it) => sum + it.qty, 0);
    if (headerCartCount) headerCartCount.textContent = totalCount;
    if (dockCartBadge) dockCartBadge.textContent = totalCount;
  }

  window.openCartDrawer = function () {
    switchVaultTab('cart');
  };

  window.addToCart = function (product) {
    if (!product) return;
    const existing = cart.find(it => String(it.id) === String(product.id));
    if (existing) {
      existing.qty += 1;
    } else {
      cart.push({
        id: String(product.id),
        title: product.title,
        price: product.price,
        price_num: Number(product.price_num || 0),
        image: product.image,
        qty: 1
      });
    }
    saveCart();
    window.showToast(`🛒 "${product.title}" sepete eklendi!`);
  };

  window.addModalProductToCart = function () {
    if (selectedModalProduct) {
      window.addToCart(selectedModalProduct);
      closeProductModal();
    }
  };

  window.updateCartQty = function (productId, change) {
    const item = cart.find(it => String(it.id) === String(productId));
    if (item) {
      item.qty += change;
      if (item.qty <= 0) {
        cart = cart.filter(it => String(it.id) !== String(productId));
      }
    }
    saveCart();
    renderCartItems();
  };

  window.removeCartItem = function (productId) {
    cart = cart.filter(it => String(it.id) !== String(productId));
    saveCart();
    renderCartItems();
    window.showToast("Ürün sepetten çıkarıldı.");
  };

  window.clearFullCart = function () {
    cart = [];
    saveCart();
    renderCartItems();
    window.showToast("Sepetiniz temizlendi.");
  };

  function renderCartItems() {
    if (!cartItemsContainer) return;
    cartItemsContainer.innerHTML = '';

    if (cart.length === 0) {
      if (cartSummaryBox) cartSummaryBox.style.display = 'none';
      if (cartEmptyState) cartEmptyState.style.display = 'block';
      return;
    }

    if (cartSummaryBox) cartSummaryBox.style.display = 'block';
    if (cartEmptyState) cartEmptyState.style.display = 'none';

    let totalQty = 0;
    let totalPrice = 0.0;

    cart.forEach(it => {
      totalQty += it.qty;
      totalPrice += it.price_num * it.qty;

      const row = document.createElement('div');
      row.className = 'cart-item-row';
      row.innerHTML = `
        <img class="cart-item-img" src="${it.image}?v=8.0" alt="${it.title}" onerror="this.src='assets/products/art_48945493.jpg'">
        <div class="cart-item-info">
          <div class="cart-item-title">${it.title}</div>
          <div class="cart-item-price">₺${(it.price_num * it.qty).toFixed(2)}</div>
        </div>
        <div class="cart-qty-ctrl">
          <button class="btn-qty" onclick="updateCartQty('${it.id}', -1)">-</button>
          <span class="qty-val">${it.qty}</span>
          <button class="btn-qty" onclick="updateCartQty('${it.id}', 1)">+</button>
        </div>
        <button class="btn-cart-remove" onclick="removeCartItem('${it.id}')" title="Sil">✕</button>
      `;
      cartItemsContainer.appendChild(row);
    });

    if (cartTotalItems) cartTotalItems.textContent = `${totalQty} Adet Ürün`;
    if (cartTotalAmount) cartTotalAmount.textContent = `₺${totalPrice.toFixed(2)}`;
  }

  // Checkout with Wallet
  window.checkoutCartWithWallet = async function () {
    if (cart.length === 0) return;
    const totalCost = cart.reduce((sum, it) => sum + (it.price_num * it.qty), 0);

    if (userProfile.balance < totalCost) {
      window.showToast(`⚠️ Yetersiz Bakiye! Gerekli: ₺${totalCost.toFixed(2)}, Mevcut: ₺${userProfile.balance.toFixed(2)}`);
      setTimeout(() => {
        switchVaultTab('wallet');
      }, 1000);
      return;
    }

    try {
      const res = await fetch(api('/api/user/purchase-cart'), {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({
          init_data: telegramInitData,
          user_id: tgUser.id,
          items: cart
        })
      });
      const data = await res.json();
      if (data.success) {
        userProfile.balance = data.new_balance;
        updateUI();
        window.clearFullCart();
        showPurchaseSuccessModal("Sepet Alışverişi", totalCost);
      } else {
        window.showToast(`⚠️ Hata: ${data.error || 'İşlem gerçekleştirilemedi'}`);
      }
    } catch (e) {
      window.showToast("⚠️ Sipariş bağlantı hatası oluştu.");
    }
  };

  // Product Modal
  window.openProductModal = function (product) {
    selectedModalProduct = product;
    if (!productModal) return;

    if (modalImg) modalImg.src = `${product.image}?v=8.0`;
    if (modalTitle) modalTitle.textContent = product.title;
    if (modalPrice) modalPrice.textContent = product.price;
    if (modalDesc) modalDesc.textContent = product.description || `${product.title} - LisansArena güvencesiyle anında teslimat.`;
    if (modalBadge) modalBadge.textContent = (product.showcase || product.is_vitrin) ? "💎 VIP Lisans" : "⚡ Orijinal";
    if (modalShopierLink) modalShopierLink.href = product.url;

    if (modalWalletBuyBtn) {
      modalWalletBuyBtn.innerHTML = `<span>💰 Cüzdan Bakiyesiyle Al (₺${Number(product.price_num || 0).toFixed(2)})</span>`;
    }

    productModal.classList.add('active');
  };

  window.closeProductModal = function () {
    if (productModal) productModal.classList.remove('active');
  };

  // Buy Single with Wallet
  window.buyWithWalletBalance = async function () {
    if (!selectedModalProduct) return;
    const price = Number(selectedModalProduct.price_num || 0);

    if (userProfile.balance < price) {
      window.showToast("⚠️ Yetersiz bakiye! Lütfen önce Cüzdan sekmesinden bakiye yükleyin.");
      setTimeout(() => {
        closeProductModal();
        switchVaultTab('wallet');
      }, 1000);
      return;
    }

    try {
      const res = await fetch(api('/api/user/purchase'), {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({
          init_data: telegramInitData,
          user_id: tgUser.id,
          product_id: selectedModalProduct.id
        })
      });
      const data = await res.json();
      if (data.success) {
        userProfile.balance = data.new_balance;
        updateUI();
        closeProductModal();
        showPurchaseSuccessModal(selectedModalProduct.title, price);
      } else {
        window.showToast(`⚠️ Hata: ${data.error || 'İşlem gerçekleştirilemedi'}`);
      }
    } catch (e) {
      window.showToast("⚠️ Bağlantı hatası oluştu.");
    }
  };

  // Buy Single with Direct Dynamic Shopier Listing (Zero Ban Risk)
  window.buyWithDirectShopier = async function () {
    if (!selectedModalProduct) return;
    const price = Number(selectedModalProduct.price_num || 0);

    if (price < 5) {
      window.showToast("⚠️ Minimum işlem tutarı ₺5'dir.");
      return;
    }

    const modalShopierBtn = document.getElementById('modalShopierBuyBtn');
    if (modalShopierBtn) {
      modalShopierBtn.disabled = true;
      modalShopierBtn.innerHTML = `<span>⏳ İlan Hazırlanıyor...</span>`;
    }

    try {
      window.showToast("⚡ Güvenli 3D Shopier ödeme sayfası hazırlanıyor...");
      const res = await fetch(api('/api/balance/create-dynamic-topup'), {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({
          init_data: telegramInitData,
          user_id: tgUser.id,
          user_name: userProfile.full_name || `${tgUser.first_name} ${tgUser.last_name}`.trim(),
          username: tgUser.username || "",
          amount: price,
          idempotency_key: `la_buy_${selectedModalProduct.id}_${tgUser.id}_${Date.now()}`
        })
      });

      const data = await res.json();

      if (data.success && data.payment_url) {
        window.currentActiveTopupPid = data.product_id;
        window.startRealtimePaymentWatcher();

        const badgeEl = document.getElementById('redirectModalBadge');
        const titleEl = document.getElementById('redirectModalTitle');
        const descEl = document.getElementById('redirectModalDesc');
        if (badgeEl) badgeEl.textContent = '⚡ KARTLA DİREKT SATIN ALMA';
        if (titleEl) titleEl.textContent = `${selectedModalProduct.title} Ödemesi Bekleniyor...`;
        if (descEl) descEl.innerHTML = `<strong>${selectedModalProduct.title}</strong> için güvenli 3D ödeme sayfası açıldı. Ödeme tamamlandığında lisans kodunuz anında bu ekrana ve <strong>Siparişlerim</strong> sekmesine aktarılacaktır.`;

        if (tg?.openLink) {
          tg.openLink(data.payment_url);
        }

        if (topupRedirectBtn) {
          topupRedirectBtn.href = data.payment_url;
        }
        closeProductModal();
        if (topupRedirectModal) {
          topupRedirectModal.classList.add('active');
        }

        try {
          window.open(data.payment_url, '_blank');
        } catch (e) {}

      } else {
        window.showToast(`⚠️ Ödeme Başlatılamadı: ${data.error || 'Bilinmeyen hata'}`);
      }
    } catch (e) {
      window.showToast("⚠️ Ödeme servisine bağlanırken hata oluştu.");
    } finally {
      if (modalShopierBtn) {
        modalShopierBtn.disabled = false;
        modalShopierBtn.innerHTML = `
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><rect x="1" y="4" width="22" height="16" rx="2" ry="2"/><line x1="1" y1="10" x2="23" y2="10"/></svg>
          <span>💳 Kartla Direkt Satın Al</span>
        `;
      }
    }
  };

  // Topup Amount Selection
  window.setTopupAmount = function (amt, btn) {
    activeTopupAmount = amt;
    document.querySelectorAll('.preset-chip').forEach(el => el.classList.remove('active'));
    if (btn) btn.classList.add('active');
    if (customAmountInput) customAmountInput.value = amt;
  };

  window.handleCustomAmount = function (val) {
    const num = parseFloat(val);
    if (!isNaN(num) && num >= 5) {
      activeTopupAmount = num;
      document.querySelectorAll('.preset-chip').forEach(el => {
        el.classList.toggle('active', parseFloat(el.textContent.replace('₺', '')) === num);
      });
    }
  };

  // DYNAMIC SHOPIER TOPUP (INSTANT DELETE ON CANCEL OR LEAVE)
  window.startDynamicTopup = async function () {
    const amt = activeTopupAmount;
    if (!amt || amt < 5) {
      window.showToast("⚠️ Minimum yükleme tutarı ₺5'dir.");
      return;
    }

    if (btnProceedTopup) {
      btnProceedTopup.disabled = true;
      btnProceedTopup.innerHTML = `<span>⏳ İlan Hazırlanıyor...</span>`;
    }

    try {
      const res = await fetch(api('/api/balance/create-dynamic-topup'), {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({
          init_data: telegramInitData,
          user_id: tgUser.id,
          user_name: userProfile.full_name || `${tgUser.first_name} ${tgUser.last_name}`.trim(),
          username: tgUser.username || "",
          amount: amt,
          idempotency_key: `la_${tgUser.id}_${Date.now()}`
        })
      });

      const data = await res.json();

      if (data.success && data.payment_url) {
        window.currentActiveTopupPid = data.product_id;
        window.startRealtimePaymentWatcher();

        const badgeEl = document.getElementById('redirectModalBadge');
        const titleEl = document.getElementById('redirectModalTitle');
        const descEl = document.getElementById('redirectModalDesc');
        if (badgeEl) badgeEl.textContent = '💰 CÜZDAN BAKİYESİ YÜKLEME';
        if (titleEl) titleEl.textContent = `₺${amt}.00 Bakiye Yükleme Bekleniyor...`;
        if (descEl) descEl.innerHTML = `<strong>₺${amt}.00</strong> cüzdan bakiye yüklemesi için güvenli 3D ödeme sayfası açıldı. Ödeme tamamlandığında bakiyeniz anında cüzdanınıza yansıyacaktır.`;

        if (tg?.openLink) {
          tg.openLink(data.payment_url);
        }

        if (topupRedirectBtn) {
          topupRedirectBtn.href = data.payment_url;
        }
        if (topupRedirectModal) {
          topupRedirectModal.classList.add('active');
        }

        try {
          window.open(data.payment_url, '_blank');
        } catch (e) {}

      } else {
        window.showToast(`⚠️ Shopier İlan Hatası: ${data.error || 'Bilinmeyen hata'}`);
      }
    } catch (e) {
      window.showToast("⚠️ Ödeme servisine bağlanırken hata oluştu.");
    } finally {
      if (btnProceedTopup) {
        btnProceedTopup.disabled = false;
        btnProceedTopup.innerHTML = `
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
          <span>Shopier ile Güvenli Yükle</span>
        `;
      }
    }
  };

  window.manualCheckPayment = async function () {
    window.showToast("🔄 Ödeme durumu kontrol ediliyor...");
    await window.syncOrdersSilently(true);
    await window.syncProfileSilently();
  };

  window.closeTopupRedirectModal = function () {
    if (topupRedirectModal) topupRedirectModal.classList.remove('active');
    if (window.currentActiveTopupPid) {
      fetch(api('/api/balance/cancel-topup'), {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({
          init_data: telegramInitData,
          product_id: window.currentActiveTopupPid
        })
      }).catch(() => {});
      window.currentActiveTopupPid = null;
    }
  };

  window.addEventListener('pagehide', function () {
    if (window.currentActiveTopupPid) {
      const payload = JSON.stringify({
        init_data: telegramInitData,
        product_id: window.currentActiveTopupPid
      });
      if (navigator.sendBeacon) {
        navigator.sendBeacon(api('/api/balance/cancel-topup'), new Blob([payload], { type: 'application/json' }));
      } else {
        fetch(api('/api/balance/cancel-topup'), {
          method: 'POST',
          headers: authHeaders(),
          body: payload,
          keepalive: true
        }).catch(() => {});
      }
    }
  });

  // Referral Copy & Share
  window.copyRefLink = function () {
    if (!refLinkInput) return;
    refLinkInput.select();
    navigator.clipboard.writeText(refLinkInput.value).then(() => {
      window.showToast("📋 Davet bağlantınız panoya kopyalandı!");
    });
  };

  window.shareOnTelegram = function () {
    const link = refLinkInput?.value || `https://t.me/LisansArenaOnline?start=ref_${tgUser.id}`;
    const text = `🔥 LisansArena ile ChatGPT Plus, Canva, FC26 ve tüm yapay zeka lisanslarında dev indirimler!\n\nHemen mağazayı açmak için tıkla:`;
    const shareUrl = `https://t.me/share/url?url=${encodeURIComponent(link)}&text=${encodeURIComponent(text)}`;
    if (tg?.openTelegramLink) {
      tg.openTelegramLink(shareUrl);
    } else {
      window.open(shareUrl, '_blank');
    }
  };

})();

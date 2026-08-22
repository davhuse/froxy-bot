// KeyVadi Ultra-Premium Mini App Controller (v11.0 - Next-Gen Glassmorphism & Direct Shopier Engine)

const tg = window.Telegram?.WebApp || null;
const API_BASE = window.location.pathname.startsWith('/keyvadi') ? '/keyvadi' : '';
const api = path => `${API_BASE}${path}`;

// Initialize Telegram WebApp SDK
if (tg) {
  try {
    tg.ready();
    tg.expand();
    if (tg.setHeaderColor) tg.setHeaderColor('#07090E');
    if (tg.setBackgroundColor) tg.setBackgroundColor('#07090E');
    if (tg.enableClosingConfirmation) tg.enableClosingConfirmation();
  } catch (e) {
    console.log('TG SDK Init:', e);
  }
}

// Telegram User & Auth
const tgUser = tg?.initDataUnsafe?.user || null;
const telegramInitData = tg?.initData || '';

function authHeaders() {
  const h = { 'Content-Type': 'application/json' };
  if (telegramInitData) {
    h['X-Telegram-Init-Data'] = telegramInitData;
  }
  return h;
}

// Global App State
let state = {
  products: [],
  filteredProducts: [],
  selectedCategory: 'all',
  searchQuery: '',
  walletBalance: 0.00,
  selectedProduct: null,
  referralsCount: 0,
  referralEarnings: 0.00,
  selectedTopupAmount: 50,
  orders: [],
  cart: [] // Array of { id, title, price_num, price, image, qty }
};

// Load cart from localStorage
try {
  const savedCart = localStorage.getItem('keyvadi_cart');
  if (savedCart) {
    state.cart = JSON.parse(savedCart);
  }
} catch (e) {}

// Haptic feedback helper
function triggerHaptic(type = 'light') {
  if (tg?.HapticFeedback) {
    try {
      if (type === 'light') tg.HapticFeedback.impactOccurred('light');
      else if (type === 'medium') tg.HapticFeedback.impactOccurred('medium');
      else if (type === 'heavy') tg.HapticFeedback.impactOccurred('heavy');
      else if (type === 'success') tg.HapticFeedback.notificationOccurred('success');
      else if (type === 'warning') tg.HapticFeedback.notificationOccurred('warning');
    } catch (e) {}
  }
}

// Toast notification helper
function showToast(message, icon = '✅') {
  const toast = document.getElementById('toastNotification');
  if (!toast) return;
  toast.innerHTML = `<span>${icon}</span><span>${message}</span>`;
  toast.classList.add('show');
  triggerHaptic('light');
  setTimeout(() => {
    toast.classList.remove('show');
  }, 3200);
}

// Format currency
function formatTL(num) {
  return '₺' + (typeof num === 'number' ? num : parseFloat(num) || 0).toLocaleString('tr-TR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

// Initialize on DOM Ready
document.addEventListener('DOMContentLoaded', async () => {
  renderUserInfo();
  updateCartUI();
  setupEventListeners();
  if (tgUser && telegramInitData) await registerAndSyncUserProfile();
  await loadProducts();
  if (tgUser && telegramInitData) startBackgroundBalanceSync();

  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.get('payment') === 'success' || urlParams.get('order') === 'success') {
    showPurchaseSuccessModal("Shopier Ödemesi Onaylandı", null);
    try { window.history.replaceState({}, document.title, window.location.pathname); } catch (e) {}
  }
});

async function registerAndSyncUserProfile() {
  if (!tgUser || !telegramInitData) return false;
  try {
    const res = await fetch(api(`/api/user/${tgUser.id}`), {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({ init_data: telegramInitData })
    });
    if (res.ok) {
      const data = await res.json();
      if (data.success && data.user) {
        state.walletBalance = parseFloat(data.user.balance) || 0;
        state.referralsCount = data.user.referrals_count || state.referralsCount;
        state.referralEarnings = data.user.referral_earnings || state.referralEarnings;
        state.orders = Array.isArray(data.user.orders) ? data.user.orders : [];
        updateBalanceUI();
        renderUserInfo();
        renderOrders();
      }
    }
  } catch (e) {
    console.log('Profile sync error:', e);
  }
}

async function loadProducts() {
  try {
    const res = await fetch(api('/api/products'));
    const data = await res.json();
    if (data.success && data.products) {
      state.products = data.products;
      renderCategoryChips();
      filterAndRenderProducts();
    }
  } catch (e) {
    console.error('Products load error:', e);
  }
}

let isKvSyncing = false;
async function syncKvOrdersSilently(triggerSuccessOnNewOrder = true) {
  if (isKvSyncing) return;
  isKvSyncing = true;
  try {
    const prevOrderCount = Array.isArray(state.orders) ? state.orders.length : 0;
    const prevLastOrderId = prevOrderCount > 0 ? (state.orders[state.orders.length - 1].order_id || '') : '';

    const res = await fetch(api('/api/balance/sync-orders'), {
      headers: authHeaders()
    });
    const data = await res.json();
    await registerAndSyncUserProfile();

    if (data.success && data.credited_orders && data.credited_orders.length > 0) {
      showToast("🎉 Bakiye yüklemeniz onaylandı ve cüzdanınıza yansıtıldı!", "💰");
    }

    if (triggerSuccessOnNewOrder) {
      const currentOrders = Array.isArray(state.orders) ? state.orders : [];
      if (currentOrders.length > prevOrderCount) {
        const latestOrder = currentOrders[currentOrders.length - 1];
        if (latestOrder && (latestOrder.order_id || '') !== prevLastOrderId) {
          showPurchaseSuccessModal(latestOrder.title || "Dijital Lisans", latestOrder.subtotal || latestOrder.price);
        }
      }
    }
  } catch (e) {
  } finally {
    isKvSyncing = false;
  }
}

function startBackgroundBalanceSync() {
  setInterval(() => syncKvOrdersSilently(true), 12000);

  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') {
      syncKvOrdersSilently(true);
    }
  });
  window.addEventListener('focus', () => {
    syncKvOrdersSilently(true);
  });
}

// Active Realtime Polling when user clicks Shopier payment in KeyVadi
let kvActivePollingInterval = null;
window.startKvRealtimePaymentWatcher = function() {
  if (kvActivePollingInterval) clearInterval(kvActivePollingInterval);
  let pollsLeft = 40; // 40 x 3s = 120 seconds active watcher
  kvActivePollingInterval = setInterval(async () => {
    pollsLeft--;
    if (pollsLeft <= 0) {
      clearInterval(kvActivePollingInterval);
      kvActivePollingInterval = null;
      return;
    }
    await syncKvOrdersSilently(true);
  }, 3000);
};

window.manualRefreshKvData = async function() {
  showToast("Veriler güncelleniyor...", "🔄");
  await loadProducts();
  await syncKvOrdersSilently(false);
  showToast("Siparişler ve bakiye güncellendi!", "✅");
};

function renderUserInfo() {
  if (!tgUser) {
    const nameEl = document.getElementById('headerUserName');
    if (nameEl) nameEl.textContent = 'Misafir Kullanıcı';
    const wallUid = document.getElementById('walletUserId');
    if (wallUid) wallUid.textContent = 'Bakiye için Telegram doğrulaması gerekir';
    return;
  }
  const nameEl = document.getElementById('headerUserName');
  if (nameEl) {
    nameEl.textContent = `${tgUser.first_name || 'KeyVadi'} ${tgUser.last_name || ''}`.trim() || 'KeyVadi Üyesi';
  }
  const wallUid = document.getElementById('walletUserId');
  if (wallUid) {
    wallUid.textContent = `ID: ${tgUser.id}`;
  }
  const refInput = document.getElementById('refLinkInput');
  if (refInput) {
    refInput.value = `https://t.me/KeyVadiSatisBot?start=ref_${tgUser.id}`;
  }
  const refCountEl = document.getElementById('refTotalCount');
  if (refCountEl) refCountEl.textContent = state.referralsCount;
  const refEarnEl = document.getElementById('refTotalEarnings');
  if (refEarnEl) refEarnEl.textContent = formatTL(state.referralEarnings);
}

function updateBalanceUI() {
  const formatted = formatTL(state.walletBalance);
  document.querySelectorAll('.dynamic-balance').forEach(el => {
    el.textContent = formatted;
  });
}

function renderOrders() {
  const container = document.getElementById('ordersList');
  if (!container) return;
  container.replaceChildren();
  const orders = Array.isArray(state.orders) ? [...state.orders].reverse() : [];
  if (!orders.length) {
    const empty = document.createElement('div');
    empty.className = 'empty-state';
    empty.style.padding = '30px 15px';
    empty.style.textAlign = 'center';
    empty.innerHTML = `
      <div style="font-size: 2rem; margin-bottom: 8px;">📦</div>
      <p style="color: #8E9BAE; font-size: 0.85rem;">Henüz bir siparişiniz bulunmuyor.</p>
    `;
    container.append(empty);
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
    const item = document.createElement('div');
    item.className = 'order-history-item';
    
    const title = document.createElement('strong');
    title.textContent = order.title || order.product_name || 'Dijital Lisans Siparişi';
    
    const meta = document.createElement('span');
    meta.className = 'order-meta-text';
    const number = order.order_id || order.id || order.product_id || `KV-${String(index + 1).padStart(5, '0')}`;
    const amount = Number(order.subtotal ?? order.price ?? order.amount ?? 0);
    const date = order.created_at ? new Date(Number(order.created_at) * 1000) : null;
    meta.textContent = `No: ${number} • ${formatTL(amount)}${date && !Number.isNaN(date.getTime()) ? ` • ${date.toLocaleString('tr-TR')}` : ''}`;
    
    const status = document.createElement('span');
    status.className = `order-status ${order.status === 'delivered' || order.status === 'completed' ? 'delivered' : 'pending'}`;
    status.textContent = labels[order.status] || (order.license_key ? '✅ Teslim Edildi' : '⏳ Hazırlanıyor');
    
    item.append(title, meta, status);

    if (order.license_key) {
      const codeBox = document.createElement('div');
      codeBox.style.cssText = 'background: rgba(0, 240, 255, 0.1); border: 1px dashed var(--primary-cyan); border-radius: 6px; padding: 8px 10px; margin-top: 8px; display: flex; justify-content: space-between; align-items: center; gap: 8px;';
      
      const codeText = document.createElement('span');
      codeText.style.cssText = 'font-family: monospace; font-weight: 700; font-size: 0.82rem; color: #fff; word-break: break-all;';
      codeText.textContent = `🔑 ${order.license_key}`;

      const copyBtn = document.createElement('button');
      copyBtn.type = 'button';
      copyBtn.style.cssText = 'background: var(--primary-cyan); color: #000; border: none; border-radius: 4px; padding: 4px 8px; font-size: 0.72rem; font-weight: 800; cursor: pointer; white-space: nowrap;';
      copyBtn.textContent = 'KOPYALA';
      copyBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        navigator.clipboard.writeText(order.license_key).then(() => {
          showToast('Lisans anahtarı kopyalandı!', '📋');
          triggerHaptic('success');
        });
      });

      codeBox.append(codeText, copyBtn);
      item.append(codeBox);
    } else {
      const manualBox = document.createElement('div');
      manualBox.className = 'manual-delivery-box';
      manualBox.innerHTML = `
        <div class="mdb-header">
          <span>💬</span>
          <strong>Manuel Teslimat / Temsilci Bekleniyor</strong>
        </div>
        <p class="mdb-desc">Bu ürün temsilci teslimatı kapsamındadır. Lütfen aşağıdaki butona dokunarak destek ekibimize sipariş numaranızı (<strong>#${number}</strong>) iletiniz; temsilcimiz hesabınızı/lisansınızı anında teslim edecektir.</p>
        <a href="https://t.me/KeyVadiDestek" target="_blank" class="btn-support-contact">
          <span>🚀 @KeyVadiDestek ile İletişime Geç</span>
        </a>
      `;
      item.append(manualBox);
    }

    container.append(item);
  });
}

// Success Modal Functions
window.showPurchaseSuccessModal = function(title, amount) {
  const modal = document.getElementById('purchaseSuccessModal');
  if (!modal) return;
  const prodEl = document.getElementById('successModalProduct');
  if (prodEl) prodEl.textContent = title || 'Dijital Ürün / Lisans';
  const amtEl = document.getElementById('successModalAmount');
  if (amtEl) amtEl.textContent = amount ? formatTL(amount) : 'Ödeme Onaylandı';
  modal.classList.add('active');
  triggerHaptic('success');
};

window.closePurchaseSuccessModal = function() {
  const modal = document.getElementById('purchaseSuccessModal');
  if (modal) modal.classList.remove('active');
};

window.goToOrdersFromSuccess = function() {
  closePurchaseSuccessModal();
  switchTab('ordersTab');
};

// Category mappings
const CATEGORY_NAMES = {
  all: 'Tüm Ürünler',
  vitrin: 'Vitrin Seçimleri',
  ai: 'Yapay Zekâ',
  design: 'Tasarım & Edit',
  entertainment: 'Sinema & Müzik',
  gaming: 'Oyun & Pin',
  security: 'Yazılım & Güvenlik',
  deals: 'Günün Fırsatları'
};

const CATEGORY_ICONS = {
  all: '⌂',
  vitrin: '⭐',
  ai: '🤖',
  design: '🎨',
  entertainment: '🎬',
  gaming: '🎮',
  security: '🛡️',
  deals: '🔥'
};

function renderCategoryChips() {
  const root = document.getElementById('categoriesScroll');
  if (!root) return;
  const available = new Set(state.products.map(product => product.category));
  const categories = ['all', 'vitrin', 'ai', 'gaming', 'entertainment', 'design', 'security', 'deals']
    .filter(category => category === 'all' || category === 'vitrin' || available.has(category));
  
  root.replaceChildren(...categories.map(category => {
    const button = document.createElement('button');
    button.className = `category-chip${state.selectedCategory === category ? ' active' : ''}`;
    button.dataset.cat = category;
    button.type = 'button';
    const icon = document.createElement('span'); icon.className = 'cat-icon'; icon.textContent = CATEGORY_ICONS[category] || '✦';
    const label = document.createElement('span'); label.textContent = CATEGORY_NAMES[category] || category;
    button.append(icon, label);
    button.addEventListener('click', () => window.setCategory(category, button));
    return button;
  }));
}

function filterAndRenderProducts() {
  const { products, selectedCategory, searchQuery } = state;
  
  state.filteredProducts = products.filter(p => {
    let matchCategory = false;
    if (selectedCategory === 'all') {
      matchCategory = true;
    } else if (selectedCategory === 'vitrin') {
      matchCategory = p.showcase === true || p.is_vitrin === true;
    } else {
      matchCategory = p.category === selectedCategory;
    }

    const matchSearch = !searchQuery || 
      p.title.toLowerCase().includes(searchQuery.toLowerCase()) || 
      (p.description && p.description.toLowerCase().includes(searchQuery.toLowerCase()));
    return matchCategory && matchSearch;
  });

  const countBadge = document.getElementById('filteredCountBadge');
  if (countBadge) countBadge.textContent = `${state.filteredProducts.length} Ürün`;

  const headingEl = document.getElementById('currentCategoryHeading');
  if (headingEl) headingEl.textContent = CATEGORY_NAMES[selectedCategory] || 'Popüler Lisanslar';

  renderProductGrid();
}

function renderProductGrid() {
  const grid = document.getElementById('productsGrid');
  if (!grid) return;

  if (state.filteredProducts.length === 0) {
    grid.innerHTML = `
      <div class="empty-state" style="grid-column: 1 / -1; padding: 50px 20px; text-align: center;">
        <div style="font-size: 2.5rem; margin-bottom: 12px;">🔍</div>
        <h3 style="color: #fff; margin-bottom: 6px;">Aradığınız kriterde ürün bulunamadı</h3>
        <p style="font-size: 0.82rem; color: #8E9BAE;">Lütfen farklı bir kategori veya arama terimi deneyin.</p>
      </div>
    `;
    return;
  }

  grid.innerHTML = state.filteredProducts.map(p => `
    <div class="product-card" onclick="openProductModal('${p.id}')">
      <div class="card-img-wrapper">
        <img class="card-img" src="${p.image}?v=11.0" alt="${p.title}" loading="lazy" onerror="this.src='assets/keyvadi_banner_new_1781380687628.png'"/>
        <span class="card-badge-tag">${(p.showcase || p.is_vitrin) ? '⭐ VİTRİN' : (p.badge || '⚡ ANINDA')}</span>
      </div>
      <div class="card-content">
        <div class="card-meta-row">
          <span class="card-category">${p.category_label || CATEGORY_NAMES[p.category] || 'DİJİTAL LİSANS'}</span>
        </div>
        <div class="card-title">${p.title}</div>
        <div class="card-price-row">
          <span class="card-price">${p.price}</span>
        </div>
        <div class="card-delivery">${p.delivery_label || '⚡ 7/24 Anında Otomatik Teslimat'}</div>
        <div class="card-actions" onclick="event.stopPropagation()">
          <button class="btn-buy" onclick="addKvProductToCart('${p.id}')" title="Sepete Ekle">
            <span>🛒 + Sepet</span>
          </button>
          <button class="btn-detail" onclick="openProductModal('${p.id}')" title="İncele & Satın Al">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
          </button>
        </div>
      </div>
    </div>
  `).join('');
}

// ==================== KEYVADI CART (SEPET) SYSTEM ====================
function saveKvCart() {
  try {
    localStorage.setItem('keyvadi_cart', JSON.stringify(state.cart));
  } catch (e) {}
  updateCartUI();
}

function updateCartUI() {
  const totalCount = state.cart.reduce((sum, it) => sum + it.qty, 0);
  const hCart = document.getElementById('headerCartCount');
  if (hCart) hCart.textContent = totalCount;
  const dCart = document.getElementById('dockKvCartBadge');
  if (dCart) dCart.textContent = totalCount;
}

window.addKvProductToCart = function(productId) {
  const product = state.products.find(p => String(p.id) === String(productId));
  if (!product) return;

  const existing = state.cart.find(it => String(it.id) === String(product.id));
  const maxQty = Math.max(1, Number(product.max_qty || 1));
  if (existing) {
    existing.qty = Math.min(maxQty, existing.qty + 1);
  } else {
    state.cart.push({
      id: String(product.id),
      title: product.title,
      price: product.price,
      price_num: Number(product.price_num || 0),
      image: product.image,
      delivery_label: product.delivery_label,
      max_qty: maxQty,
      qty: 1
    });
  }
  saveKvCart();
  triggerHaptic('success');
  showToast(`"${product.title}" sepete eklendi!`, '🛒');
};

window.addModalProductToKvCart = function() {
  if (state.selectedProduct) {
    window.addKvProductToCart(state.selectedProduct.id);
    closeProductModal();
  }
};

window.updateKvCartQty = function(productId, change) {
  const item = state.cart.find(it => String(it.id) === String(productId));
  if (item) {
    item.qty = Math.min(Math.max(1, Number(item.max_qty || 1)), item.qty + change);
    if (item.qty <= 0) {
      state.cart = state.cart.filter(it => String(it.id) !== String(productId));
    }
  }
  saveKvCart();
  renderKvCartItems();
};

window.removeKvCartItem = function(productId) {
  state.cart = state.cart.filter(it => String(it.id) !== String(productId));
  saveKvCart();
  renderKvCartItems();
  showToast("Ürün sepetten çıkarıldı.", "🗑️");
};

window.clearKvFullCart = function() {
  state.cart = [];
  localStorage.removeItem('keyvadi_cart_idempotency');
  saveKvCart();
  renderKvCartItems();
  showToast("Sepetiniz temizlendi.", "🗑️");
};

function renderKvCartItems() {
  const container = document.getElementById('kvCartItemsContainer');
  const summaryBox = document.getElementById('kvCartSummaryBox');
  const emptyState = document.getElementById('kvCartEmptyState');
  const totalItemsEl = document.getElementById('kvCartTotalItems');
  const totalAmtEl = document.getElementById('kvCartTotalAmount');

  if (!container) return;
  container.innerHTML = '';

  if (state.cart.length === 0) {
    if (summaryBox) summaryBox.style.display = 'none';
    if (emptyState) emptyState.style.display = 'block';
    return;
  }

  if (summaryBox) summaryBox.style.display = 'block';
  if (emptyState) emptyState.style.display = 'none';

  let totalQty = 0;
  let totalPrice = 0.0;

  state.cart.forEach(it => {
    totalQty += it.qty;
    totalPrice += it.price_num * it.qty;

    const row = document.createElement('div');
    row.className = 'cart-item-row';
    row.innerHTML = `
      <img class="cart-item-img" src="${it.image}?v=11.0" alt="${it.title}" onerror="this.src='assets/keyvadi_banner_new_1781380687628.png'">
      <div class="cart-item-info">
        <div class="cart-item-title">${it.title}</div>
        <div class="cart-item-price">₺${(it.price_num * it.qty).toFixed(2)}</div>
        <div class="cart-item-delivery">${it.delivery_label || '⚡ 7/24 Anında Otomatik Teslimat'}</div>
      </div>
      <div class="cart-qty-ctrl">
        <button class="btn-qty" onclick="updateKvCartQty('${it.id}', -1)">-</button>
        <span class="qty-val">${it.qty}</span>
        <button class="btn-qty" onclick="updateKvCartQty('${it.id}', 1)">+</button>
      </div>
      <button class="btn-cart-remove" onclick="removeKvCartItem('${it.id}')" title="Sil">✕</button>
    `;
    container.appendChild(row);
  });

  if (totalItemsEl) totalItemsEl.textContent = `${totalQty} Adet Ürün`;
  if (totalAmtEl) totalAmtEl.textContent = `₺${totalPrice.toFixed(2)}`;
}

window.checkoutKvCartWithWallet = async function() {
  if (state.cart.length === 0) return;
  if (!tgUser || !telegramInitData) {
    showToast('Satın alma için mağazayı @KeyVadiSatisBot içinden açın.', '⚠️');
    return;
  }
  const totalCost = state.cart.reduce((sum, it) => sum + (it.price_num * it.qty), 0);

  if (state.walletBalance < totalCost) {
    showToast(`Yetersiz Bakiye! Gerekli: ₺${totalCost.toFixed(2)}, Mevcut: ₺${state.walletBalance.toFixed(2)}`, '⚠️');
    setTimeout(() => {
      const shortfall = Math.max(5, Math.ceil((totalCost - state.walletBalance) * 100) / 100);
      const input = document.getElementById('customTopupInput');
      if (input) input.value = shortfall.toFixed(2);
      state.selectedTopupAmount = shortfall;
      switchTab('walletTab');
    }, 1200);
    return;
  }

  try {
    const res = await fetch(api('/api/user/purchase-cart'), {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({
        user_id: tgUser.id,
        items: state.cart,
        idempotency_key: getCartIdempotencyKey()
      })
    });
    const data = await res.json();
    if (data.success) {
      state.walletBalance = data.new_balance;
      updateBalanceUI();
      window.clearKvFullCart();
      localStorage.removeItem('keyvadi_cart_idempotency');
      await registerAndSyncUserProfile();
      showPurchaseSuccessModal('Sepet Alışverişi', totalCost);
    } else {
      showToast(`Hata: ${data.error || 'İşlem başarısız'}`, '⚠️');
    }
  } catch (e) {
    showToast("Sipariş bağlantı hatası oluştu.", "⚠️");
  }
};

// ==================== PRODUCT MODAL & DIRECT SHOPIER ====================
window.openProductModal = function(productId) {
  const product = state.products.find(p => String(p.id) === String(productId));
  if (!product) return;

  state.selectedProduct = product;
  triggerHaptic('medium');

  document.getElementById('modalProductImg').src = `${product.image}?v=11.0`;
  document.getElementById('modalProductTitle').textContent = product.title;
  document.getElementById('modalProductPrice').textContent = product.price;
  document.getElementById('modalProductDesc').textContent = product.description || `${product.title}. Teslimat ve uygunluk bilgileri ödeme öncesi doğrulanır.`;
  document.getElementById('modalBadge').textContent = (product.showcase || product.is_vitrin) ? "VİTRİN" : (product.category_label || CATEGORY_NAMES[product.category] || 'ÜRÜN');
  document.getElementById('modalDeliveryInfo').textContent = product.delivery_label || '7/24 Anında Otomatik Teslimat';
  document.getElementById('modalEligibilityInfo').textContent = 'Orijinal Lisans & Garanti Güvencesi';

  const modal = document.getElementById('productDetailModal');
  if (modal) modal.classList.add('active');
};

window.closeProductModal = function() {
  const modal = document.getElementById('productDetailModal');
  if (modal) modal.classList.remove('active');
  triggerHaptic('light');
};

// DIRECT SHOPIER 1-CLICK CHECKOUT
window.buyViaShopier = async function(productId) {
  const product = state.selectedProduct || state.products.find(p => String(p.id) === String(productId));
  if (!product) return;

  triggerHaptic('medium');

  if (!tgUser || !telegramInitData) {
    const targetUrl = product.url || 'https://www.shopier.com/keyvadi';
    if (tg?.openLink) tg.openLink(targetUrl);
    else window.open(targetUrl, '_blank');
    return;
  }

  const amount = Number(product.price_num || 0);
  if (amount < 5) {
    showToast('Geçersiz ürün tutarı.', '⚠️');
    return;
  }

  const btn = document.getElementById('btnModalDirectShopier');
  const oldText = btn ? btn.innerHTML : '';
  if (btn) {
    btn.innerHTML = '<span>⏳ Ödeme Sayfası Açılıyor...</span>';
    btn.disabled = true;
  }

  showToast(`"${product.title}" için 3D Secure sayfası hazırlanıyor...`, '⚡');

  try {
    const res = await fetch(api('/api/balance/create-dynamic-topup'), {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({
        amount: amount,
        user_id: tgUser.id,
        user_name: `${tgUser.first_name || ''} ${tgUser.last_name || ''}`.trim() || 'KeyVadi Müşteri',
        username: tgUser.username || '',
        idempotency_key: `kv-buy-direct-${tgUser.id}-${product.id}-${Date.now()}`
      })
    });
    const data = await res.json();
    if (data.success && data.payment_url) {
      window.currentActiveTopupPid = data.product_id;
      startKvRealtimePaymentWatcher();

      const topupRedirectModal = document.getElementById('topupRedirectModal');
      const topupRedirectBtn = document.getElementById('topupRedirectBtn');
      const badgeEl = document.getElementById('redirectModalBadge');
      const titleEl = document.getElementById('redirectModalTitle');
      const descEl = document.getElementById('redirectModalDesc');

      if (badgeEl) badgeEl.textContent = '⚡ KARTLA DİREKT SATIN ALMA';
      if (titleEl) titleEl.textContent = `${product.title} Ödemesi Bekleniyor...`;
      if (descEl) descEl.innerHTML = `<strong>${product.title}</strong> için güvenli 3D ödeme sayfası açıldı. Ödeme tamamlandığında lisans kodunuz anında bu ekrana ve <strong>Siparişlerim</strong> sekmesine aktarılacaktır.`;
      if (topupRedirectBtn) topupRedirectBtn.href = data.payment_url;

      closeProductModal();
      if (topupRedirectModal) topupRedirectModal.classList.add('active');

      showToast('Shopier ödeme sayfası açılıyor...', '💳');
      if (tg?.openLink) {
        tg.openLink(data.payment_url);
      } else {
        window.open(data.payment_url, '_blank');
      }
    } else {
      const fallbackUrl = product.url || 'https://www.shopier.com/keyvadi';
      if (tg?.openLink) tg.openLink(fallbackUrl);
      else window.open(fallbackUrl, '_blank');
    }
  } catch (e) {
    const fallbackUrl = product.url || 'https://www.shopier.com/keyvadi';
    if (tg?.openLink) tg.openLink(fallbackUrl);
    else window.open(fallbackUrl, '_blank');
  } finally {
    if (btn) {
      btn.innerHTML = oldText;
      btn.disabled = false;
    }
  }
};

window.closeTopupRedirectModal = function() {
  const topupRedirectModal = document.getElementById('topupRedirectModal');
  if (topupRedirectModal) topupRedirectModal.classList.remove('active');
};

window.manualCheckPayment = async function() {
  showToast('🔄 Ödeme durumu kontrol ediliyor...', '⚡');
  await registerAndSyncUserProfile();
};

window.buyWithWallet = async function() {
  const product = state.selectedProduct;
  if (!product) return;
  if (!tgUser || !telegramInitData) {
    showToast('Satın alma için mağazayı @KeyVadiSatisBot içinden açın.', '⚠️');
    return;
  }

  triggerHaptic('medium');

  if (state.walletBalance < product.price_num) {
    triggerHaptic('warning');
    showToast('Yetersiz bakiye! Lütfen bakiye yükleyin.', '⚠️');
    setTimeout(() => {
      closeProductModal();
      switchTab('walletTab');
    }, 1200);
    return;
  }

  try {
    const res = await fetch(api('/api/user/purchase'), {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({
        product_id: product.id,
        user_id: tgUser.id,
        idempotency_key: globalThis.crypto?.randomUUID?.() || `kv-buy-${Date.now()}-${product.id}`
      })
    });
    const data = await res.json();
    if (data.success) {
      state.walletBalance = data.new_balance;
      updateBalanceUI();
      closeProductModal();
      await registerAndSyncUserProfile();
      showPurchaseSuccessModal(product.title, product.price_num);
    } else {
      showToast(data.error || 'İşlem başarısız', '⚠️');
    }
  } catch (e) {
    showToast('Sipariş oluşturulamadı. Bakiye değişmedi.', '⚠️');
  }
};

// Navigation Tab Switching
window.switchTab = function(tabId) {
  triggerHaptic('light');

  document.querySelectorAll('.tab-view').forEach(view => {
    view.classList.remove('active');
  });
  document.querySelectorAll('.dock-item').forEach(nav => {
    nav.classList.remove('active');
  });

  const activeView = document.getElementById(tabId);
  if (activeView) activeView.classList.add('active');

  const navButton = document.querySelector(`[data-tab="${tabId}"]`);
  if (navButton) navButton.classList.add('active');

  if (tabId === 'cartTab') {
    renderKvCartItems();
  } else if (tabId === 'ordersTab') {
    renderOrders();
  }

  window.scrollTo({ top: 0, behavior: 'smooth' });
};

window.setCategory = function(category, element) {
  triggerHaptic('light');
  state.selectedCategory = category;

  document.querySelectorAll('.category-chip').forEach(chip => {
    chip.classList.remove('active');
  });
  
  if (element && element.classList.contains('category-chip')) {
    element.classList.add('active');
  } else {
    const targetChip = document.querySelector(`.category-chip[data-cat="${category}"]`);
    if (targetChip) targetChip.classList.add('active');
  }

  filterAndRenderProducts();
};

function getCartIdempotencyKey() {
  let value = localStorage.getItem('keyvadi_cart_idempotency');
  if (!value) {
    value = globalThis.crypto?.randomUUID?.() || `kv-${Date.now()}-${Math.random().toString(16).slice(2)}`;
    localStorage.setItem('keyvadi_cart_idempotency', value);
  }
  return value;
}

window.selectTopupPreset = function(amount, element) {
  triggerHaptic('light');
  state.selectedTopupAmount = amount;
  
  document.querySelectorAll('.topup-btn').forEach(btn => btn.classList.remove('selected'));
  if (element) element.classList.add('selected');

  const input = document.getElementById('customTopupInput');
  if (input) input.value = amount;
};

window.handleCustomAmount = function(val) {
  const num = parseFloat(val);
  if (!isNaN(num) && num >= 5) {
    state.selectedTopupAmount = num;
    document.querySelectorAll('.topup-btn').forEach(el => {
      el.classList.toggle('selected', parseFloat(el.textContent.replace('₺', '')) === num);
    });
  }
};

// DYNAMIC SHOPIER TOPUP
window.proceedShopierTopup = async function() {
  if (!tgUser || !telegramInitData) {
    showToast('Bakiye yüklemek için mağazayı @KeyVadiSatisBot içinden açın.', '⚠️');
    return;
  }
  triggerHaptic('medium');
  const amountInput = document.getElementById('customTopupInput');
  const amount = parseFloat(amountInput?.value) || state.selectedTopupAmount;
  const topupKeyName = `keyvadi_topup_${tgUser.id}_${amount}`;
  let topupIdempotency = localStorage.getItem(topupKeyName);
  if (!topupIdempotency) {
    topupIdempotency = globalThis.crypto?.randomUUID?.() || `kv-topup-${tgUser.id}-${amount}-${Date.now()}`;
    localStorage.setItem(topupKeyName, topupIdempotency);
  }
  
  if (amount < 5) {
    showToast('Minimum yükleme tutarı 5 TL\'dir.', '⚠️');
    return;
  }

  const topupBtn = document.getElementById('btnProceedTopup');
  const originalText = topupBtn ? topupBtn.innerHTML : '';
  if (topupBtn) {
    topupBtn.innerHTML = `<span>⏳ İlan Hazırlanıyor...</span>`;
    topupBtn.disabled = true;
  }

  showToast(`${amount} TL için anlık Shopier ilanı açılıyor...`, '⚡');

  try {
    const res = await fetch(api('/api/balance/create-dynamic-topup'), {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({
        amount: amount,
        user_id: tgUser.id,
        user_name: `${tgUser.first_name || ''} ${tgUser.last_name || ''}`.trim() || 'KeyVadi Müşteri',
        username: tgUser.username || "",
        idempotency_key: topupIdempotency
      })
    });

    const data = await res.json();
    if (data.success && data.payment_url) {
      localStorage.removeItem(topupKeyName);
      window.currentActiveTopupPid = data.product_id;
      startKvRealtimePaymentWatcher();

      const topupRedirectModal = document.getElementById('topupRedirectModal');
      const topupRedirectBtn = document.getElementById('topupRedirectBtn');
      const badgeEl = document.getElementById('redirectModalBadge');
      const titleEl = document.getElementById('redirectModalTitle');
      const descEl = document.getElementById('redirectModalDesc');

      if (badgeEl) badgeEl.textContent = '💰 CÜZDAN BAKİYESİ YÜKLEME';
      if (titleEl) titleEl.textContent = `₺${amount}.00 Bakiye Yükleme Bekleniyor...`;
      if (descEl) descEl.innerHTML = `<strong>₺${amount}.00</strong> cüzdan bakiye yüklemesi için güvenli 3D ödeme sayfası açıldı. Ödeme onaylandığında bakiyeniz anında cüzdanınıza yansıyacaktır.`;
      if (topupRedirectBtn) topupRedirectBtn.href = data.payment_url;

      if (topupRedirectModal) topupRedirectModal.classList.add('active');
      showToast(`Ödeme sayfası açılıyor! (${amount} TL)`, '💳');
      
      if (tg?.openLink) {
        tg.openLink(data.payment_url);
      }
      try {
        window.open(data.payment_url, '_blank');
      } catch (e) {}
    } else {
      showToast('Shopier bağlantısı oluşturulamadı. Tekrar deneyin.', '⚠️');
    }
  } catch (err) {
    showToast('Shopier bağlantı hatası.', '⚠️');
  } finally {
    if (topupBtn) {
      topupBtn.innerHTML = originalText;
      topupBtn.disabled = false;
    }
  }
};

// Copy Referral Link
window.copyRefLink = function() {
  triggerHaptic('success');
  const input = document.getElementById('refLinkInput');
  if (!input) return;

  input.select();
  navigator.clipboard.writeText(input.value).then(() => {
    showToast('Davet linkiniz panoya kopyalandı!', '📋');
  });
};

// Share via Telegram
window.shareOnTelegram = function() {
  if (!tgUser) {
    showToast('Referans bağlantısı için mağazayı Telegram botundan açın.', '⚠️');
    return;
  }
  triggerHaptic('medium');
  const refLink = document.getElementById('refLinkInput')?.value || `https://t.me/KeyVadiSatisBot?start=ref_${tgUser.id}`;
  const shareText = `🔥 KeyVadi ile ChatGPT Plus, Netflix, Canva Pro, FC26 ve tüm lisanslar %70 indirimli!\n\nHemen mağazayı açmak için tıkla:`;
  const shareUrl = `https://t.me/share/url?url=${encodeURIComponent(refLink)}&text=${encodeURIComponent(shareText)}`;

  if (tg?.openTelegramLink) {
    tg.openTelegramLink(shareUrl);
  } else {
    window.open(shareUrl, '_blank');
  }
};

// Support Contact
window.notifySupport = function() {
  triggerHaptic('medium');
  const supportUrl = 'https://t.me/KeyVadiDestek';
  if (tg?.openTelegramLink) {
    tg.openTelegramLink(supportUrl);
  } else {
    window.open(supportUrl, '_blank');
  }
};

// Search handling
function setupEventListeners() {
  const searchInput = document.getElementById('searchInput');
  const searchClear = document.getElementById('searchClear');

  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      state.searchQuery = e.target.value;
      if (searchClear) {
        searchClear.style.display = e.target.value ? 'flex' : 'none';
      }
      filterAndRenderProducts();
    });
  }

  if (searchClear) {
    searchClear.addEventListener('click', () => {
      if (searchInput) searchInput.value = '';
      state.searchQuery = '';
      searchClear.style.display = 'none';
      filterAndRenderProducts();
    });
  }

  const modalOverlay = document.getElementById('productDetailModal');
  if (modalOverlay) {
    modalOverlay.addEventListener('click', (e) => {
      if (e.target === modalOverlay) {
        closeProductModal();
      }
    });
  }
}

// KeyVadi Ultra-Premium Mini App Controller (v9.0 - Perfect Architecture & Full Shopping Cart)

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

// User Profile extraction from Telegram
const tgUser = tg?.initDataUnsafe?.user || {
  id: 8797763469,
  first_name: "KeyVadi",
  last_name: "Müşterisi",
  username: "KeyVadiSatisBot"
};
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
  }, 3000);
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
  await registerAndSyncUserProfile();
  await loadProducts();
  startBackgroundBalanceSync();
});

async function registerAndSyncUserProfile() {
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
      filterAndRenderProducts();
    }
  } catch (e) {
    console.error('Products load error:', e);
  }
}

function startBackgroundBalanceSync() {
  setInterval(async () => {
    try {
      const res = await fetch(api('/api/balance/sync-orders'), {
        headers: authHeaders()
      });
      const data = await res.json();
      if (data.success && data.credited_orders && data.credited_orders.length > 0) {
        await registerAndSyncUserProfile();
        showToast("🎉 Bakiye yüklemeniz onaylandı ve cüzdanınıza yansıtıldı!", "💰");
      }
    } catch (e) {}
  }, 15000);
}

function renderUserInfo() {
  const nameEl = document.getElementById('headerUserName');
  if (nameEl) {
    nameEl.textContent = `${tgUser.first_name || 'Müşteri'} ${tgUser.last_name || ''}`.trim() || 'KeyVadi Üyesi';
  }
  const profNameEl = document.getElementById('profileName');
  if (profNameEl) {
    profNameEl.textContent = `${tgUser.first_name || 'KeyVadi'} ${tgUser.last_name || 'Müşterisi'}`.trim();
  }
  const profBadge = document.getElementById('profileBadgeId');
  if (profBadge) {
    profBadge.textContent = `ID: ${tgUser.id}`;
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
    const empty = document.createElement('p');
    empty.className = 'orders-empty';
    empty.textContent = 'Henüz bir siparişiniz bulunmuyor.';
    container.append(empty);
    return;
  }
  const labels = { pending_delivery: 'Teslimat hazırlanıyor', processing: 'İşlemde', paid: 'Ödeme alındı', completed: 'Tamamlandı', cancelled: 'İptal edildi' };
  orders.slice(0, 20).forEach((order, index) => {
    const item = document.createElement('div');
    item.className = 'order-history-item';
    const title = document.createElement('strong');
    title.textContent = order.title || order.product_name || 'Bakiye yükleme';
    const meta = document.createElement('span');
    const number = order.order_id || order.id || order.product_id || `KV-${String(index + 1).padStart(5, '0')}`;
    const amount = Number(order.subtotal ?? order.price ?? order.amount ?? 0);
    const date = order.created_at ? new Date(Number(order.created_at) * 1000) : null;
    meta.textContent = `Sipariş: ${number} • ${formatTL(amount)}${date && !Number.isNaN(date.getTime()) ? ` • ${date.toLocaleString('tr-TR')}` : ''}`;
    const status = document.createElement('span');
    status.className = 'order-status';
    status.textContent = labels[order.status] || 'İşlemde';
    item.append(title, meta, status);
    container.append(item);
  });
}

// Category filter names
const CATEGORY_NAMES = {
  all: 'Popüler Lisanslar',
  vitrin: '⭐ Vitrin & Özel Seçimler',
  ai: '🤖 Yapay Zeka & LLM',
  gaming: '🎮 Oyun & E-Pin',
  streaming: '🎬 Sinema & Müzik',
  design: '🎨 Tasarım & Araçlar',
  software: '💻 Yazılım & Key',
  social: '💬 Hesap & Sosyal',
  coupons: '🎟️ Kupon & İndirim'
};

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
        <img class="card-img" src="${p.image}?v=9.0" alt="${p.title}" loading="lazy" onerror="this.src='assets/keyvadi_banner_new_1781380687628.png'"/>
        <span class="card-badge">${(p.showcase || p.is_vitrin) ? "⭐ VİTRİN" : "⚡ ORİJİNAL"}</span>
      </div>
      <div class="card-content">
        <div class="card-title">${p.title}</div>
        <div class="card-price-row">
          <span class="card-price">${p.price}</span>
        </div>
        <div class="card-actions" onclick="event.stopPropagation()">
          <button class="btn-buy" onclick="addKvProductToCart('${p.id}')" title="Sepete Ekle">
            <span>🛒 + Sepet</span>
          </button>
          <button class="btn-detail" onclick="openProductModal('${p.id}')" title="İncele">
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
  if (existing) {
    existing.qty += 1;
  } else {
    state.cart.push({
      id: String(product.id),
      title: product.title,
      price: product.price,
      price_num: Number(product.price_num || 0),
      image: product.image,
      qty: 1
    });
  }
  saveKvCart();
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
    item.qty += change;
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
      <img class="cart-item-img" src="${it.image}?v=9.0" alt="${it.title}" onerror="this.src='assets/keyvadi_banner_new_1781380687628.png'">
      <div class="cart-item-info">
        <div class="cart-item-title">${it.title}</div>
        <div class="cart-item-price">₺${(it.price_num * it.qty).toFixed(2)}</div>
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
  const totalCost = state.cart.reduce((sum, it) => sum + (it.price_num * it.qty), 0);

  if (state.walletBalance < totalCost) {
    showToast(`Yetersiz Bakiye! Gerekli: ₺${totalCost.toFixed(2)}, Mevcut: ₺${state.walletBalance.toFixed(2)}`, '⚠️');
    setTimeout(() => {
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
        items: state.cart
      })
    });
    const data = await res.json();
    if (data.success) {
      state.walletBalance = data.new_balance;
      updateBalanceUI();
      window.clearKvFullCart();
      showToast(data.message || "🎉 Sepetiniz başarıyla satın alındı!", "💰");
    } else {
      showToast(`Hata: ${data.error || 'İşlem başarısız'}`, '⚠️');
    }
  } catch (e) {
    showToast("Sipariş bağlantı hatası oluştu.", "⚠️");
  }
};

// Product Modal Handling
window.openProductModal = function(productId) {
  const product = state.products.find(p => String(p.id) === String(productId));
  if (!product) return;

  state.selectedProduct = product;
  triggerHaptic('medium');

  document.getElementById('modalProductImg').src = `${product.image}?v=9.0`;
  document.getElementById('modalProductTitle').textContent = product.title;
  document.getElementById('modalProductPrice').textContent = product.price;
  document.getElementById('modalProductDesc').textContent = product.description || `${product.title} - KeyVadi güvencesiyle anında teslimat.`;
  document.getElementById('modalBadge').textContent = (product.showcase || product.is_vitrin) ? "⭐ VİTRİN" : "⚡ ORİJİNAL";

  const modal = document.getElementById('productDetailModal');
  if (modal) modal.classList.add('active');
};

window.closeProductModal = function() {
  const modal = document.getElementById('productDetailModal');
  if (modal) modal.classList.remove('active');
  triggerHaptic('light');
};

// Purchase Actions
window.buyViaShopier = function(url) {
  triggerHaptic('medium');
  const targetUrl = url || state.selectedProduct?.url;
  if (!targetUrl) {
    showToast('Bu ürün için güvenli satın alma bağlantısı hazır değil.', '⚠️');
    return;
  }
  
  if (tg?.openLink) {
    tg.openLink(targetUrl);
  } else {
    window.open(targetUrl, '_blank');
  }
};

window.buyWithWallet = async function() {
  const product = state.selectedProduct;
  if (!product) return;

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
        user_id: tgUser.id
      })
    });
    const data = await res.json();
    if (data.success) {
      state.walletBalance = data.new_balance;
      updateBalanceUI();
      triggerHaptic('success');
      showToast(data.message || 'Sipariş kaydınız oluşturuldu.', '🎉');
      closeProductModal();
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
  triggerHaptic('medium');
  const amountInput = document.getElementById('customTopupInput');
  const amount = parseFloat(amountInput?.value) || state.selectedTopupAmount;
  
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
        user_name: `${tgUser.first_name} ${tgUser.last_name}`.trim(),
        username: tgUser.username || ""
      })
    });

    const data = await res.json();
    if (data.success && data.payment_url) {
      window.currentActiveTopupPid = data.product_id;
      showToast(`Ödeme sayfası açılıyor! (${amount} TL)`, '💳');
      
      if (tg?.openLink) {
        tg.openLink(data.payment_url);
      }
      try {
        window.location.href = data.payment_url;
      } catch (e) {
        window.open(data.payment_url, '_blank');
      }
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

// Do not cancel here: opening Shopier or returning from its checkout can fire
// beforeunload. Abandoned listings are closed by the server-side TTL cleaner.

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

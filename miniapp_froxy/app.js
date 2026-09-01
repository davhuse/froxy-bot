// FROXY NEURAL AI STUDIO — ULTRA-PREMIUM SPA CONTROLLER (v12.0)

const tg = window.Telegram?.WebApp || null;
const isFroxyApp = window.location.pathname.startsWith('/froxy/app') || window.location.pathname.startsWith('/froxy');
const API_BASE = isFroxyApp ? (window.location.pathname.startsWith('/froxy/app') ? '/froxy/app' : '/froxy') : '';
const api = path => `${API_BASE}${path}`;

// Initialize Telegram WebApp SDK
if (tg) {
  try {
    tg.ready();
    tg.expand();
    if (tg.setHeaderColor) tg.setHeaderColor('#06080F');
    if (tg.setBackgroundColor) tg.setBackgroundColor('#06080F');
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
  selectedTopupAmount: 100,
  orders: [],
  cart: [],
  canSpin: true,
  spinCooldownRemaining: 0
};

// Load cart from localStorage
try {
  const savedCart = localStorage.getItem('froxy_cart');
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
function showToast(message, icon = '⚡') {
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
  const val = typeof num === 'number' ? num : parseFloat(num) || 0;
  return '₺' + val.toLocaleString('tr-TR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

// DOM Ready Init
document.addEventListener('DOMContentLoaded', async () => {
  renderUserInfo();
  updateCartBadge();
  drawWheel();
  if (tgUser && telegramInitData) await registerAndSyncUserProfile();
  await loadProducts();
  if (tgUser && telegramInitData) startBackgroundBalanceSync();

  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.get('payment') === 'success' || urlParams.get('order') === 'success') {
    showPurchaseSuccessModal("Shopier Ödemeniz Onaylandı", "Yapay zeka lisansınız veya bakiye yüklemeniz hesabınıza tanımlandı.");
    try { window.history.replaceState({}, document.title, window.location.pathname); } catch (e) {}
  }
});

function renderUserInfo() {
  const nameEl = document.getElementById('headerUserName');
  const walletIdEl = document.getElementById('walletUserId');
  const walletIdText = document.getElementById('walletUserIdText');

  if (tgUser) {
    const fullName = `${tgUser.first_name || ''} ${tgUser.last_name || ''}`.trim() || tgUser.username || 'Müşteri';
    if (nameEl) nameEl.textContent = `👋 Merhaba, ${fullName}`;
    if (walletIdEl) walletIdEl.textContent = `ID: ${tgUser.id}`;
    if (walletIdText) walletIdText.textContent = tgUser.id;
  } else {
    if (nameEl) nameEl.textContent = '🌐 Misafir Kullanıcı';
    if (walletIdEl) walletIdEl.textContent = 'ID: 8845484139';
    if (walletIdText) walletIdText.textContent = '8845484139';
  }
}

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
        state.orders = Array.isArray(data.user.orders) ? data.user.orders : [];
        state.canSpin = data.user.can_spin ?? true;
        state.spinCooldownRemaining = data.user.spin_cooldown_remaining || 0;
        updateBalanceUI();
        renderUserInfo();
        renderOrders();
        updateSpinUI();
      }
    }
  } catch (e) {
    console.log('Profile sync error:', e);
  }
}

function updateBalanceUI() {
  const balanceEls = document.querySelectorAll('.dynamic-balance');
  balanceEls.forEach(el => {
    el.textContent = formatTL(state.walletBalance);
  });
}

function startBackgroundBalanceSync() {
  setInterval(async () => {
    if (tgUser && telegramInitData) {
      try {
        const res = await fetch(api(`/api/user/${tgUser.id}`), {
          method: 'GET',
          headers: authHeaders()
        });
        if (res.ok) {
          const data = await res.json();
          if (data.success && data.user) {
            const newBal = parseFloat(data.user.balance) || 0;
            if (newBal !== state.walletBalance) {
              state.walletBalance = newBal;
              updateBalanceUI();
            }
            if (Array.isArray(data.user.orders)) {
              state.orders = data.user.orders;
              renderOrders();
            }
          }
        }
      } catch (e) {}
    }
  }, 12000);
}

// Load Products from API
async function loadProducts() {
  try {
    const res = await fetch(api('/api/products'));
    const data = await res.json();
    if (data.success && data.products) {
      state.products = data.products;
      filterAndRenderProducts();

      // Deep-link handling
      try {
        const urlParams = new URLSearchParams(window.location.search);
        const targetParam = urlParams.get('product') || tg?.initDataUnsafe?.start_param;
        if (targetParam) {
          if (targetParam === 'orders') switchTab('ordersTab');
          else if (targetParam === 'wallet') switchTab('walletTab');
          else {
            const cleanId = String(targetParam).replace(/^p_/, '').trim();
            const matched = state.products.find(p => String(p.id) === cleanId);
            if (matched) setTimeout(() => openProductModal(matched.id), 250);
          }
        }
      } catch (e) {}
    }
  } catch (e) {
    console.log('Error loading products:', e);
  }
}

// Category & Filter
function setCategory(cat, btn) {
  state.selectedCategory = cat;
  triggerHaptic('light');

  const chips = document.querySelectorAll('.cat-chip');
  chips.forEach(c => c.classList.remove('active'));
  if (btn) btn.classList.add('active');
  else {
    const activeChip = document.querySelector(`.cat-chip[data-cat="${cat}"]`);
    if (activeChip) activeChip.classList.add('active');
  }

  filterAndRenderProducts();
}

function handleSearch(val) {
  state.searchQuery = val.trim().toLowerCase();
  const clearBtn = document.getElementById('clearSearchBtn');
  if (clearBtn) clearBtn.style.display = state.searchQuery ? 'block' : 'none';
  filterAndRenderProducts();
}

function clearSearch() {
  const input = document.getElementById('searchInput');
  if (input) input.value = '';
  state.searchQuery = '';
  const clearBtn = document.getElementById('clearSearchBtn');
  if (clearBtn) clearBtn.style.display = 'none';
  setCategory('all', null);
}

function filterAndRenderProducts() {
  let list = state.products;

  if (state.selectedCategory !== 'all') {
    list = list.filter(p => p.category === state.selectedCategory);
  }

  if (state.searchQuery) {
    list = list.filter(p =>
      (p.title || '').toLowerCase().includes(state.searchQuery) ||
      (p.description || '').toLowerCase().includes(state.searchQuery) ||
      (p.model_tag || '').toLowerCase().includes(state.searchQuery) ||
      (p.category_label || '').toLowerCase().includes(state.searchQuery)
    );
  }

  state.filteredProducts = list;

  const grid = document.getElementById('productsGrid');
  const emptyState = document.getElementById('emptyState');
  const countBadge = document.getElementById('productCountBadge');

  if (countBadge) countBadge.textContent = `${list.length} Model`;

  if (!list.length) {
    if (grid) grid.innerHTML = '';
    if (emptyState) emptyState.style.display = 'block';
    return;
  }

  if (emptyState) emptyState.style.display = 'none';

  if (grid) {
    grid.innerHTML = list.map(p => `
      <div class="ai-product-card" data-id="${p.id}">
        <div class="card-top-tags">
          <span class="card-badge-pill">${p.badge || '🔥 POPÜLER'}</span>
          <span class="card-model-tag">${p.model_tag || 'AI MODEL'}</span>
        </div>

        <div class="card-media-wrap" onclick="openProductModal('${p.id}')">
          <img src="${p.image || 'assets/froxy_chat_logo_1783808162276.png'}" alt="${p.title}" class="card-img" onerror="this.src='assets/froxy_chat_logo_1783808162276.png'" />
        </div>

        <div class="card-body">
          <div class="card-title" onclick="openProductModal('${p.id}')">${p.title}</div>
          <div class="card-desc">${p.description || 'En son teknoloji yapay zeka lisansı.'}</div>

          <div class="card-price-row">
            <span class="price-label">FİYAT</span>
            <span class="card-price">${p.price || formatTL(p.price_num)}</span>
          </div>

          <div class="card-actions-grid">
            <button class="buy-direct-btn" onclick="directBuyProduct('${p.id}')">
              <span>⚡ 1-Tıkla Satın Al</span>
            </button>
            <button class="detail-btn" onclick="openProductModal('${p.id}')" title="İncele">
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.3"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
            </button>
          </div>
        </div>
      </div>
    `).join('');
  }
}

// Direct Buy / Shopier 3D Secure
function directBuyProduct(productId) {
  triggerHaptic('medium');
  const p = state.products.find(item => String(item.id) === String(productId));
  if (!p) return;

  if (p.url) {
    if (tg?.openLink) {
      tg.openLink(p.url);
    } else {
      window.open(p.url, '_blank');
    }
  } else {
    addToCart(productId);
    openCartDrawer();
  }
}

// Product Detail Modal
function openProductModal(productId) {
  triggerHaptic('light');
  const p = state.products.find(item => String(item.id) === String(productId));
  if (!p) return;

  state.selectedProduct = p;
  const modal = document.getElementById('productModal');
  const content = document.getElementById('productModalContent');

  if (content) {
    content.innerHTML = `
      <div style="text-align: center; margin-bottom: 16px;">
        <span class="card-badge-pill" style="display:inline-block; margin-bottom:8px;">${p.category_label || 'YAPAY ZEKA LİSANSI'}</span>
        <h3 style="font-family: var(--font-heading); font-size: 19px; font-weight: 800; color: #FFF; margin-bottom: 6px;">${p.title}</h3>
        <span class="card-model-tag" style="font-size:11px;">⚡ Model: ${p.model_tag || 'GPT-4o & Canvas'}</span>
      </div>

      <div style="background: var(--bg-surface); border: 1px solid var(--border-glass); border-radius: var(--radius-lg); padding: 14px; margin-bottom: 16px;">
        <div style="font-size: 13px; color: var(--text-secondary); line-height: 1.5; margin-bottom: 12px;">
          ${p.description}
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 11.5px;">
          <div style="background: rgba(0,240,255,0.08); border: 1px solid var(--border-cyan); border-radius: var(--radius-sm); padding: 8px; color:#FFF;">
            ⚡ <b>7/24 Anında Teslimat</b>
          </div>
          <div style="background: rgba(16,185,129,0.08); border: 1px solid var(--border-emerald); border-radius: var(--radius-sm); padding: 8px; color:#FFF;">
            🔒 <b>3D Secure Korumalı</b>
          </div>
        </div>
      </div>

      <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom: 16px; padding: 12px 16px; background: var(--bg-primary); border-radius: var(--radius-lg); border: 1px solid var(--border-cyan);">
        <span style="color: var(--text-secondary); font-weight: 700;">Toplam Fiyat:</span>
        <span style="font-family: var(--font-mono); font-size: 22px; font-weight: 900; color: var(--accent-cyan);">${p.price || formatTL(p.price_num)}</span>
      </div>

      <div style="display:flex; flex-direction:column; gap: 10px;">
        <button class="buy-direct-btn" style="padding:14px; font-size:14px;" onclick="directBuyProduct('${p.id}')">
          <span>⚡ Kredi / Banka Kartıyla Satın Al (Shopier 3D)</span>
        </button>
        <button style="padding:12px; border-radius:var(--radius-lg); background:var(--bg-surface-elevated); border:1px solid var(--border-glass); color:#FFF; font-weight:700; cursor:pointer;" onclick="buyWithWalletBalance('${p.id}')">
          <span>💳 Bakiyemle Satın Al (Mevcut: ${formatTL(state.walletBalance)})</span>
        </button>
      </div>
    `;
  }

  if (modal) modal.style.display = 'flex';
}

function closeProductModal() {
  const modal = document.getElementById('productModal');
  if (modal) modal.style.display = 'none';
}

// Buy with Wallet Balance
async function buyWithWalletBalance(productId) {
  const p = state.products.find(item => String(item.id) === String(productId));
  if (!p) return;

  const priceNum = p.price_num || parseFloat(p.price) || 0;
  if (state.walletBalance < priceNum) {
    triggerHaptic('warning');
    showToast(`Yetersiz bakiye! Gerekli: ${formatTL(priceNum)}, Bakiyeniz: ${formatTL(state.walletBalance)}`, '⚠️');
    setTimeout(() => {
      closeProductModal();
      switchTab('walletTab');
    }, 1200);
    return;
  }

  triggerHaptic('medium');
  try {
    const res = await fetch(api('/api/order/create-with-balance'), {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({
        product_id: p.id,
        user_id: tgUser?.id || 8845484139
      })
    });
    const data = await res.json();
    if (data.success) {
      state.walletBalance -= priceNum;
      updateBalanceUI();
      closeProductModal();
      showPurchaseSuccessModal("Siparişiniz Teslim Edildi!", `Tebrikler! ${p.title} lisansınız oluşturuldu.`);
      if (tgUser && telegramInitData) registerAndSyncUserProfile();
    } else {
      showToast(data.error || 'İşlem gerçekleştirilemedi', '❌');
    }
  } catch (e) {
    showToast('Bağlantı hatası oluştu', '❌');
  }
}

// Cart Drawer
function openCartDrawer() {
  triggerHaptic('light');
  renderCartDrawer();
  const modal = document.getElementById('cartDrawer');
  if (modal) modal.style.display = 'flex';
}

function closeCartDrawer() {
  const modal = document.getElementById('cartDrawer');
  if (modal) modal.style.display = 'none';
}

function addToCart(productId) {
  const p = state.products.find(item => String(item.id) === String(productId));
  if (!p) return;

  const existing = state.cart.find(item => String(item.id) === String(productId));
  if (existing) {
    existing.qty += 1;
  } else {
    state.cart.push({
      id: p.id,
      title: p.title,
      price: p.price,
      price_num: p.price_num || parseFloat(p.price) || 0,
      image: p.image,
      qty: 1
    });
  }
  saveCart();
  updateCartBadge();
  showToast(`${p.title} sepete eklendi!`, '🛒');
}

function updateCartQty(productId, delta) {
  const item = state.cart.find(i => String(i.id) === String(productId));
  if (!item) return;

  item.qty += delta;
  if (item.qty <= 0) {
    state.cart = state.cart.filter(i => String(i.id) !== String(productId));
  }
  saveCart();
  updateCartBadge();
  renderCartDrawer();
}

function clearCart() {
  state.cart = [];
  saveCart();
  updateCartBadge();
  renderCartDrawer();
}

function saveCart() {
  try {
    localStorage.setItem('froxy_cart', JSON.stringify(state.cart));
  } catch (e) {}
}

function updateCartBadge() {
  const count = state.cart.reduce((sum, i) => sum + i.qty, 0);
  const badge = document.getElementById('headerCartCount');
  const drawerCount = document.getElementById('cartItemCount');
  if (badge) badge.textContent = count;
  if (drawerCount) drawerCount.textContent = count;
}

function renderCartDrawer() {
  const listEl = document.getElementById('cartItemsList');
  const totalEl = document.getElementById('cartTotalAmount');

  let total = 0;
  if (!state.cart.length) {
    if (listEl) listEl.innerHTML = '<div style="text-align:center; padding:24px 0; color:var(--text-muted); font-size:13px;">Sepetiniz henüz boş.</div>';
    if (totalEl) totalEl.textContent = formatTL(0);
    return;
  }

  if (listEl) {
    listEl.innerHTML = state.cart.map(item => {
      const subtotal = item.price_num * item.qty;
      total += subtotal;
      return `
        <div class="cart-item-row">
          <div class="cart-item-info">
            <span class="cart-item-name">${item.title}</span>
            <span class="cart-item-price">${formatTL(item.price_num)} × ${item.qty} = ${formatTL(subtotal)}</span>
          </div>
          <div class="cart-item-controls">
            <button class="qty-btn" onclick="updateCartQty('${item.id}', -1)">−</button>
            <span class="qty-val">${item.qty}</span>
            <button class="qty-btn" onclick="updateCartQty('${item.id}', 1)">+</button>
          </div>
        </div>
      `;
    }).join('');
  }

  if (totalEl) totalEl.textContent = formatTL(total);
}

function checkoutCart() {
  if (!state.cart.length) return;
  triggerHaptic('medium');
  if (state.cart.length === 1 && state.cart[0].id) {
    const singleProduct = state.products.find(p => String(p.id) === String(state.cart[0].id));
    if (singleProduct?.url) {
      closeCartDrawer();
      if (tg?.openLink) tg.openLink(singleProduct.url);
      else window.open(singleProduct.url, '_blank');
      return;
    }
  }
  showToast('Shopier ödeme sayfasına yönlendiriliyorsunuz...', '⚡');
}

// Topup selection
function selectTopupAmount(amt, btn) {
  state.selectedTopupAmount = amt;
  triggerHaptic('light');

  const chips = document.querySelectorAll('.topup-chip');
  chips.forEach(c => c.classList.remove('active'));
  if (btn) btn.classList.add('active');

  const customInput = document.getElementById('customTopupInput');
  if (customInput) customInput.value = '';
}

function handleCustomAmountInput(val) {
  const num = parseFloat(val);
  if (!isNaN(num) && num > 0) {
    state.selectedTopupAmount = num;
    const chips = document.querySelectorAll('.topup-chip');
    chips.forEach(c => c.classList.remove('active'));
  }
}

async function initiateDynamicTopup() {
  const amt = state.selectedTopupAmount || 100;
  triggerHaptic('medium');

  if (amt < 5) {
    showToast("Minimum yükleme tutarı 5 TL'dir", '⚠️');
    return;
  }

  showToast('Ödeme linki oluşturuluyor...', '⚡');
  const btn = document.getElementById('dynamicPayBtn');
  if (btn) btn.disabled = true;

  try {
    const res = await fetch(api('/api/balance/create-dynamic-topup'), {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({
        amount: amt,
        user_id: tgUser?.id || 8845484139
      })
    });
    const data = await res.json();
    if (data.success && data.payment_url) {
      if (tg?.openLink) tg.openLink(data.payment_url);
      else window.open(data.payment_url, '_blank');
    } else {
      showToast(data.error || 'Ödeme linki oluşturulamadı', '❌');
    }
  } catch (e) {
    showToast('Bağlantı hatası', '❌');
  } finally {
    if (btn) btn.disabled = false;
  }
}

function copyIBAN() {
  const ibanText = document.getElementById('ibanText')?.textContent || 'TR48 0011 1000 0000 0127 7564 36';
  navigator.clipboard.writeText(ibanText.replace(/\s+/g, ''));
  showToast('IBAN panoya kopyalandı!', '📋');
}

// Orders Render
function renderOrders() {
  const listEl = document.getElementById('ordersList');
  const emptyEl = document.getElementById('ordersEmpty');

  if (!state.orders || !state.orders.length) {
    if (listEl) listEl.innerHTML = '';
    if (emptyEl) emptyEl.style.display = 'block';
    return;
  }

  if (emptyEl) emptyEl.style.display = 'none';

  if (listEl) {
    listEl.innerHTML = state.orders.map(o => `
      <div class="order-card">
        <div class="order-top">
          <span class="order-id">#${o.order_id || o.id || 'FX-1001'}</span>
          <span class="order-date">${o.created_at || 'Bugün'}</span>
        </div>
        <div class="order-title">${o.product_title || o.title || 'Froxy AI Lisansı'}</div>
        <div class="order-credential-box">
          <span>${o.license_key || o.credential || 'Hesap Bilgisi Hazırlanıyor...'}</span>
          <button class="order-copy-btn" onclick="copyText('${o.license_key || o.credential || ''}')">Kopyala</button>
        </div>
      </div>
    `).join('');
  }
}

function copyText(txt) {
  if (!txt) return;
  navigator.clipboard.writeText(txt);
  showToast('Bilgiler kopyalandı!', '📋');
}

// FAQ Toggle
function toggleFaq(el) {
  triggerHaptic('light');
  el.classList.toggle('active');
}

// Tab Switching
function switchTab(tabId) {
  triggerHaptic('light');

  const tabs = document.querySelectorAll('.tab-view');
  tabs.forEach(t => t.classList.remove('active'));

  const activeTab = document.getElementById(tabId);
  if (activeTab) activeTab.classList.add('active');

  const navItems = document.querySelectorAll('.nav-item');
  navItems.forEach(n => {
    if (n.getAttribute('data-tab') === tabId) n.classList.add('active');
    else n.classList.remove('active');
  });

  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// Success Modal
function showPurchaseSuccessModal(title, msg) {
  triggerHaptic('success');
  const titleEl = document.querySelector('.success-title');
  const descEl = document.getElementById('successModalMessage');
  if (titleEl && title) titleEl.textContent = title;
  if (descEl && msg) descEl.textContent = msg;

  const modal = document.getElementById('purchaseSuccessModal');
  if (modal) modal.style.display = 'flex';
}

function closeSuccessModal() {
  const modal = document.getElementById('purchaseSuccessModal');
  if (modal) modal.style.display = 'none';
}

function goToOrders() {
  closeSuccessModal();
  switchTab('ordersTab');
}

// AI Wheel of Fortune
const wheelPrizes = [
  { label: '₺5 Bakiye', value: 5, color: '#0A0E1A', textColor: '#00F0FF' },
  { label: '₺10 Bakiye', value: 10, color: '#10B981', textColor: '#000000' },
  { label: 'Tekrar Dene', value: 0, color: '#0A0E1A', textColor: '#94A3B8' },
  { label: '₺25 Bakiye', value: 25, color: '#8B5CF6', textColor: '#FFFFFF' },
  { label: '%20 İndirim', value: 'coupon', color: '#0A0E1A', textColor: '#F59E0B' },
  { label: '₺50 Bakiye', value: 50, color: '#00F0FF', textColor: '#000000' }
];

let wheelAngle = 0;
let isSpinning = false;

function drawWheel() {
  const canvas = document.getElementById('wheelCanvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const numSlices = wheelPrizes.length;
  const sliceAngle = (2 * Math.PI) / numSlices;
  const radius = canvas.width / 2;

  ctx.clearRect(0, 0, canvas.width, canvas.height);

  for (let i = 0; i < numSlices; i++) {
    const start = wheelAngle + i * sliceAngle;
    const end = start + sliceAngle;

    ctx.beginPath();
    ctx.moveTo(radius, radius);
    ctx.arc(radius, radius, radius - 4, start, end);
    ctx.closePath();

    ctx.fillStyle = wheelPrizes[i].color;
    ctx.fill();
    ctx.strokeStyle = 'rgba(0, 240, 255, 0.4)';
    ctx.lineWidth = 2;
    ctx.stroke();

    ctx.save();
    ctx.translate(radius, radius);
    ctx.rotate(start + sliceAngle / 2);
    ctx.textAlign = 'right';
    ctx.fillStyle = wheelPrizes[i].textColor;
    ctx.font = 'bold 12px Plus Jakarta Sans';
    ctx.fillText(wheelPrizes[i].label, radius - 24, 4);
    ctx.restore();
  }
}

function openSpinModal() {
  triggerHaptic('light');
  drawWheel();
  updateSpinUI();
  const modal = document.getElementById('spinModal');
  if (modal) modal.style.display = 'flex';
}

function closeSpinModal() {
  const modal = document.getElementById('spinModal');
  if (modal) modal.style.display = 'none';
}

function updateSpinUI() {
  const btn = document.getElementById('spinActionBtn');
  const msg = document.getElementById('spinCooldownMsg');
  if (!btn) return;

  if (state.canSpin) {
    btn.disabled = false;
    btn.style.opacity = '1';
    if (msg) msg.style.display = 'none';
  } else {
    btn.disabled = true;
    btn.style.opacity = '0.5';
    if (msg) {
      msg.style.display = 'block';
      msg.textContent = '⏳ Günlük çevirme hakkınızı kullandınız. 24 saat sonra tekrar deneyin!';
    }
  }
}

function spinWheel() {
  if (isSpinning || !state.canSpin) return;
  isSpinning = true;
  triggerHaptic('heavy');

  const winIndex = Math.floor(Math.random() * wheelPrizes.length);
  const prize = wheelPrizes[winIndex];

  const totalRounds = 5 + Math.floor(Math.random() * 3);
  const sliceAngle = (2 * Math.PI) / wheelPrizes.length;
  // target pointer at top (-PI/2)
  const targetAngle = totalRounds * 2 * Math.PI + (wheelPrizes.length - winIndex - 0.5) * sliceAngle - Math.PI / 2;

  const startTime = performance.now();
  const duration = 4000;

  function animate(now) {
    const elapsed = now - startTime;
    const progress = Math.min(elapsed / duration, 1);
    const easeOut = 1 - Math.pow(1 - progress, 3);

    wheelAngle = easeOut * targetAngle;
    drawWheel();

    if (progress < 1) {
      requestAnimationFrame(animate);
    } else {
      isSpinning = false;
      state.canSpin = false;
      updateSpinUI();

      if (prize.value > 0) {
        state.walletBalance += prize.value;
        updateBalanceUI();
        showPurchaseSuccessModal("Tebrikler! 🎉", `Şans çarkından ${prize.label} kazandınız! Bakiyenize eklendi.`);
      } else if (prize.value === 'coupon') {
        showPurchaseSuccessModal("İndirim Kodu Kazandınız! 🎟️", "Tebrikler! %20 indirim kuponunuz: FROXY20");
      } else {
        showToast("Şansını yarın tekrar dene!", '🤖');
      }
    }
  }

  requestAnimationFrame(animate);
}

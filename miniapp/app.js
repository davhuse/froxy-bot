// KeyVadi Ultra-Premium Mini App Controller (v6.0 - Vitrin Category & Instant Sync)

const tg = window.Telegram?.WebApp || null;

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
const tgUser = tg?.initDataUnsafe?.user || null;
const telegramInitData = tg?.initData || '';

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
  selectedTopupAmount: 100,
  purchaseRequestKey: null,
  topupRequestKey: null
};

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
  setupEventListeners();
  await registerAndSyncUserProfile();
  await loadProducts();
  startBackgroundBalanceSync();
});

async function registerAndSyncUserProfile() {
  if (!tgUser || !telegramInitData) {
    showToast('Bu mağaza Telegram içinden açılmalıdır.', '⚠️');
    return;
  }
  try {
    const res = await fetch(`/api/user/${tgUser.id}`, {
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
        updateBalanceUI();
        renderUserInfo();
      }
    }
  } catch (e) {
    console.log('Profile sync error:', e);
  }
}

function renderUserInfo() {
  const userNameEl = document.getElementById('headerUserName');
  const profileNameEl = document.getElementById('profileUserName');
  const profileIdEl = document.getElementById('profileUserId');
  const walletShortIdEl = document.getElementById('walletUserShortId');
  const refLinkInput = document.getElementById('refLinkInput');

  const fullName = tgUser ? `${tgUser.first_name || ''} ${tgUser.last_name || ''}`.trim() : 'Telegram kullanıcısı';
  const handle = tgUser ? (tgUser.username ? `@${tgUser.username}` : `ID: ${tgUser.id}`) : 'Doğrulama bekleniyor';

  if (userNameEl) userNameEl.textContent = fullName;
  if (profileNameEl) profileNameEl.textContent = `${fullName} (${handle})`;
  if (profileIdEl) profileIdEl.textContent = tgUser?.id || '—';
  if (walletShortIdEl) walletShortIdEl.textContent = tgUser?.id || '—';

  const botRefLink = tgUser ? `https://t.me/KeyVadiSatisBot?start=ref_${tgUser.id}` : '';
  if (refLinkInput) refLinkInput.value = botRefLink;

  const refCountEl = document.getElementById('refCountVal');
  const refEarnEl = document.getElementById('refEarningsVal');
  if (refCountEl) refCountEl.textContent = state.referralsCount;
  if (refEarnEl) refEarnEl.textContent = formatTL(state.referralEarnings);
}

function updateBalanceUI() {
  const balanceElements = document.querySelectorAll('.dynamic-balance');
  balanceElements.forEach(el => {
    el.textContent = formatTL(state.walletBalance);
  });
}

function authHeaders() {
  const headers = { 'Content-Type': 'application/json' };
  if (telegramInitData) headers['X-Telegram-Init-Data'] = telegramInitData;
  return headers;
}

// Background auto sync for Shopier balance updates
function startBackgroundBalanceSync() {
  if (!tgUser || !telegramInitData) return;
  setInterval(async () => {
    try {
      const res = await fetch(`/api/user/${tgUser.id}`, { headers: authHeaders() });
      if (res.ok) {
        const data = await res.json();
        if (data.success && data.user) {
          const newBal = parseFloat(data.user.balance) || 0;
          if (newBal > state.walletBalance) {
            const added = newBal - state.walletBalance;
            state.walletBalance = newBal;
            updateBalanceUI();
            triggerHaptic('success');
            showToast(`🎉 ₺${added.toFixed(2)} bakiye hesabınıza yüklendi!`, '💳');
          } else {
            state.walletBalance = newBal;
            updateBalanceUI();
          }
        }
      }
    } catch (e) {}
  }, 4000);
}

// Fetch & render products
async function loadProducts() {
  const grid = document.getElementById('productsGrid');
  try {
    const res = await fetch('products_db.json?v=' + Date.now());
    if (!res.ok) throw new Error('Ürünler yüklenemedi');
    state.products = await res.json();
    filterAndRenderProducts();
  } catch (err) {
    console.error('Ürün yükleme hatası:', err);
    if (grid) {
      grid.innerHTML = `
        <div class="empty-state" style="grid-column: 1 / -1; padding: 40px 20px; text-align: center;">
          <div style="font-size: 2rem; margin-bottom: 10px;">⚠️</div>
          <p>Ürünler yüklenirken bir sorun oluştu. Lütfen tekrar deneyin.</p>
        </div>
      `;
    }
  }
}

const CATEGORY_NAMES = {
  all: 'Tüm Ürünler',
  vitrin: '⭐ Vitrin İlanları (Öne Çıkanlar)',
  ai: '🤖 Yapay Zeka Araçları',
  cinema: '🎬 Sinema & Dizi Üyelikleri',
  gaming: '🎮 Oyun & E-Pin Ürünleri',
  design: '🎨 Tasarım & Kurgu Lisansları',
  software: '💻 Yazılım & İşletim Sistemi',
  social: '📱 Sosyal Medya & Hesaplar',
  coupons: '🎟️ İndirim Kuponu & Puanlar'
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
      p.description.toLowerCase().includes(searchQuery.toLowerCase());
    return matchCategory && matchSearch;
  });

  const countBadge = document.getElementById('filteredCountBadge');
  if (countBadge) countBadge.textContent = `${state.filteredProducts.length} Ürün`;

  const headingEl = document.getElementById('currentCategoryHeading');
  if (headingEl) headingEl.textContent = CATEGORY_NAMES[selectedCategory] || 'Ürünler';

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
        <img class="card-img" src="${p.image}?v=6.0" alt="${p.title}" loading="lazy" onerror="this.src='assets/keyvadi_banner.png'"/>
        <span class="card-badge">${p.badge}</span>
      </div>
      <div class="card-content">
        <div class="card-title">${p.title}</div>
        <div class="card-price-row">
          <span class="card-price">${p.price}</span>
        </div>
        <div class="card-actions" onclick="event.stopPropagation()">
          <button class="btn-buy" onclick="buyViaShopier('${p.url}')">
            <span>⚡ Satın Al</span>
          </button>
          <button class="btn-detail" onclick="openProductModal('${p.id}')" title="İncele">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
          </button>
        </div>
      </div>
    </div>
  `).join('');
}

// Product Modal Handling
window.openProductModal = function(productId) {
  const product = state.products.find(p => p.id === productId);
  if (!product) return;

  state.selectedProduct = product;
  triggerHaptic('medium');

  document.getElementById('modalProductImg').src = `${product.image}?v=6.0`;
  document.getElementById('modalProductTitle').textContent = product.title;
  document.getElementById('modalProductPrice').textContent = product.price;
  document.getElementById('modalProductDesc').textContent = product.description;
  document.getElementById('modalBadge').textContent = product.badge;

  const modal = document.getElementById('productDetailModal');
  modal.classList.add('active');
};

window.closeProductModal = function() {
  const modal = document.getElementById('productDetailModal');
  modal.classList.remove('active');
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
    const res = await fetch('/api/user/purchase', {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({
        product_id: product.id,
        idempotency_key: state.purchaseRequestKey || (state.purchaseRequestKey = (window.crypto?.randomUUID ? window.crypto.randomUUID() : `${Date.now()}-${product.id}`))
      })
    });
    const data = await res.json();
    if (data.success) {
      state.walletBalance = data.new_balance;
      updateBalanceUI();
      triggerHaptic('success');
      showToast(data.message || 'Sipariş kaydınız oluşturuldu.', '🎉');
      closeProductModal();
      state.purchaseRequestKey = null;
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

  window.scrollTo({ top: 0, behavior: 'smooth' });
};

// Category filter
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

// Wallet Top-Up Presets
window.selectTopupPreset = function(amount, element) {
  triggerHaptic('light');
  state.selectedTopupAmount = amount;
  
  document.querySelectorAll('.topup-btn').forEach(btn => btn.classList.remove('selected'));
  if (element) element.classList.add('selected');

  document.getElementById('customTopupInput').value = amount;
};

// ==================== BARLASMEDYA TARZI DİNAMİK SHOPIER YÜKLEME ====================
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
    topupBtn.innerHTML = `<span>⏳</span> <span>Shopier İlanı Açılıyor...</span>`;
    topupBtn.disabled = true;
  }

  if (!tgUser || !telegramInitData) {
    showToast('Telegram doğrulaması gerekli.', '⚠️');
    return;
  }
  const idempotencyKey = state.topupRequestKey || (state.topupRequestKey = (window.crypto?.randomUUID ? window.crypto.randomUUID() : `${Date.now()}-${amount}`));
  showToast(`${amount} TL için anlık Shopier ilanı açılıyor...`, '⚡');

  try {
    const res = await fetch('/api/balance/create-dynamic-topup', {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({
        amount: amount,
        idempotency_key: idempotencyKey
      })
    });

    const data = await res.json();
    if (data.success && data.payment_url) {
      showToast(`Ödeme sayfası açılıyor! (${amount} TL)`, '💳');
      
      setTimeout(() => {
        if (tg?.openLink) {
          tg.openLink(data.payment_url);
        } else {
          window.open(data.payment_url, '_blank');
        }
      }, 400);
      state.topupRequestKey = null;
    } else {
      showToast('Shopier bağlantısı oluşturulamadı. Tekrar deneyin.', '⚠️');
    }
  } catch (err) {
    console.error('Dinamik yükleme hatası:', err);
    showToast('Shopier bağlantısı oluşturulamadı. Bakiye değişmedi.', '⚠️');
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
  }).catch(() => {
    showToast('Link kopyalandı!', '📋');
  });
};

// Share via Telegram
window.shareOnTelegram = function() {
  triggerHaptic('medium');
  const refLink = document.getElementById('refLinkInput')?.value || (tgUser ? `https://t.me/KeyVadiSatisBot?start=ref_${tgUser.id}` : '');
  if (!refLink) {
    showToast('Önce Telegram doğrulaması tamamlanmalı.', '⚠️');
    return;
  }
  const shareText = `🔥 KeyVadi ile Netflix, ChatGPT Plus, Canva Pro, Gemini ve tüm lisanslar %70 indirimli ve 7/24 anında teslimatla!\n\nHemen mağazayı incelemek için tıkla:`;
  const shareUrl = `https://t.me/share/url?url=${encodeURIComponent(refLink)}&text=${encodeURIComponent(shareText)}`;

  if (tg?.openTelegramLink) {
    tg.openTelegramLink(shareUrl);
  } else {
    window.open(shareUrl, '_blank');
  }
};

// Copy IBAN
window.copyIBAN = function(ibanText) {
  triggerHaptic('success');
  navigator.clipboard.writeText(ibanText).then(() => {
    showToast('IBAN numarası kopyalandı!', '🏦');
  });
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

window.notifyPayment = function() {
  triggerHaptic('medium');
  const supportUrl = 'https://t.me/KeyVadiDestek';
  if (tg?.openTelegramLink) {
    tg.openTelegramLink(supportUrl);
  } else {
    window.open(supportUrl, '_blank');
  }
};

// Setup Event Listeners
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

  // Modal backdrop click to close
  const modalOverlay = document.getElementById('productDetailModal');
  if (modalOverlay) {
    modalOverlay.addEventListener('click', (e) => {
      if (e.target === modalOverlay) {
        closeProductModal();
      }
    });
  }
}

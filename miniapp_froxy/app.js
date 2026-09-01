// FROXY AI SUPERAPP & NEURAL WORKSPACE CONTROLLER (v13.0)

const tg = window.Telegram?.WebApp || null;
const isFroxyApp = window.location.pathname.startsWith('/froxy/app') || window.location.pathname.startsWith('/froxy');
const API_BASE = isFroxyApp ? (window.location.pathname.startsWith('/froxy/app') ? '/froxy/app' : '/froxy') : '';
const api = path => `${API_BASE}${path}`;

// Initialize Telegram WebApp SDK
if (tg) {
  try {
    tg.ready();
    tg.expand();
    if (tg.setHeaderColor) tg.setHeaderColor('#070A14');
    if (tg.setBackgroundColor) tg.setBackgroundColor('#05070E');
    if (tg.enableClosingConfirmation) tg.enableClosingConfirmation();
  } catch (e) {
    console.log('TG SDK Init:', e);
  }
}

// Telegram User & Auth
const localDevUserId = ['localhost', '127.0.0.1'].includes(window.location.hostname)
  ? new URLSearchParams(window.location.search).get('dev_user_id')
  : null;
const tgUser = tg?.initDataUnsafe?.user || (localDevUserId ? { id: Number(localDevUserId), first_name: 'Froxy Test' } : null);
const telegramInitData = tg?.initData || '';
const hasUserAuth = Boolean(telegramInitData || localDevUserId);

function authHeaders() {
  const h = { 'Content-Type': 'application/json' };
  if (telegramInitData) {
    h['X-Telegram-Init-Data'] = telegramInitData;
  } else if (localDevUserId) {
    h['X-Dev-User-Id'] = localDevUserId;
  }
  return h;
}

// Global App State
let state = {
  currentView: 'view-chat',
  selectedModel: { id: 'froxy-fast', name: 'Froxy Hızlı', icon: '⚡' },
  models: [],
  chatId: (window.crypto?.randomUUID?.() || `chat-${Date.now()}`),
  chatMessages: [],
  isGeneratingChat: false,
  webSearchEnabled: false,
  reasoningEnabled: true,
  
  // Image Studio State
  imagePrompt: '',
  selectedStyle: 'photoreal',
  selectedRatio: '1:1',
  isGeneratingImage: false,
  lastGeneratedImageUrl: 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&w=1000&q=80',

  // Store & Products State
  products: [],
  filteredProducts: [],
  selectedCategory: 'all',
  searchQuery: '',
  selectedProduct: null,

  // Wallet & Profile State
  walletBalance: 0.00,
  aiCredits: 0,
  freeTextRemaining: 3,
  freeImageRemaining: 1,
  orders: [],
  selectedTopupAmount: 100,
  canSpin: true
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
  drawWheel();
  if (tgUser && hasUserAuth) await registerAndSyncUserProfile();
  if (tgUser && hasUserAuth) await loadModels();
  await loadStoreProducts();
  if (tgUser && hasUserAuth) startBackgroundBalanceSync();

  // URL deep link routing
  const urlParams = new URLSearchParams(window.location.search);
  const routeParam = urlParams.get('tab') || urlParams.get('view') || tg?.initDataUnsafe?.start_param;
  if (routeParam) {
    if (routeParam === 'store' || routeParam === 'magaza') switchView('view-store');
    else if (routeParam === 'image' || routeParam === 'gorsel') switchView('view-image');
    else if (routeParam === 'wallet' || routeParam === 'cuzdan') switchView('view-wallet');
    else if (routeParam === 'agents' || routeParam === 'ajanlar') switchView('view-agents');
  }

  if (urlParams.get('payment') === 'success' || urlParams.get('order') === 'success') {
    showPurchaseSuccessModal("Shopier Ödemeniz Onaylandı", "Yapay zeka lisansınız veya bakiye yüklemeniz hesabınıza tanımlandı.");
    try { window.history.replaceState({}, document.title, window.location.pathname); } catch (e) {}
  }
});

function renderUserInfo() {
  const walletIdEl = document.getElementById('walletUserId');
  if (tgUser) {
    if (walletIdEl) walletIdEl.textContent = `ID: ${tgUser.id}`;
  } else {
    if (walletIdEl) walletIdEl.textContent = 'ID: 8845484139';
  }
}

async function registerAndSyncUserProfile() {
  if (!tgUser || !hasUserAuth) return false;
  try {
    const res = await fetch(api('/api/me'), {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({ init_data: telegramInitData })
    });
    if (res.ok) {
      const data = await res.json();
      if (data.success && data.user) {
        state.walletBalance = parseFloat(data.user.wallet_balance) || 0;
        state.aiCredits = Number(data.user.ai_credits) || 0;
        state.freeTextRemaining = Number(data.user.free_text_remaining) || 0;
        state.freeImageRemaining = Number(data.user.free_image_remaining) || 0;
        state.orders = Array.isArray(data.user.orders) ? data.user.orders : [];
        state.canSpin = data.user.can_spin ?? true;
        updateBalanceUI();
        renderOrders();
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
  const totalOrdersEl = document.getElementById('totalOrdersCount');
  if (totalOrdersEl) totalOrdersEl.textContent = state.orders.length || 0;
  document.querySelectorAll('.dynamic-ai-credits').forEach(el => {
    el.textContent = Number(state.aiCredits || 0).toLocaleString('tr-TR');
  });
  const creditsEl = document.getElementById('totalCreditsCount');
  if (creditsEl) creditsEl.textContent = Number(state.aiCredits || 0).toLocaleString('tr-TR');
  const quotaText = `${state.freeTextRemaining} mesaj + ${state.freeImageRemaining} görsel`;
  const quotaEl = document.getElementById('dailyQuotaCount');
  if (quotaEl) quotaEl.textContent = `${state.freeTextRemaining}+${state.freeImageRemaining}`;
  const tickerEl = document.getElementById('freeQuotaTicker');
  if (tickerEl) tickerEl.textContent = quotaText;
}

function startBackgroundBalanceSync() {
  setInterval(async () => {
    if (tgUser && hasUserAuth) {
      try {
        const res = await fetch(api('/api/me'), {
          method: 'GET',
          headers: authHeaders()
        });
        if (res.ok) {
          const data = await res.json();
          if (data.success && data.user) {
            const newBal = parseFloat(data.user.wallet_balance) || 0;
            if (newBal !== state.walletBalance) {
              state.walletBalance = newBal;
              updateBalanceUI();
            }
            state.aiCredits = Number(data.user.ai_credits) || 0;
            state.freeTextRemaining = Number(data.user.free_text_remaining) || 0;
            state.freeImageRemaining = Number(data.user.free_image_remaining) || 0;
            updateBalanceUI();
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

async function loadModels() {
  const menu = document.getElementById('modelDropdownMenu');
  try {
    const response = await fetch(api('/api/models'), { headers: authHeaders() });
    const data = await response.json();
    if (!response.ok || !data.success) throw new Error(data.error || 'Model kataloğu alınamadı');
    state.models = Array.isArray(data.models) ? data.models : [];
    const countEl = document.getElementById('verifiedModelCount');
    if (countEl) countEl.textContent = `${Number(data.active_model_count || state.models.length).toLocaleString('tr-TR')} aktif model`;
    if (menu) {
      menu.innerHTML = state.models.map((model, index) => `
        <button type="button" class="model-opt ${index === 0 ? 'active' : ''}" data-model-id="${escapeHtml(model.id)}">
          <span class="opt-icon">${model.icon || (model.is_froxy ? '⚡' : '🤖')}</span>
          <span class="opt-body">
            <span class="opt-title">${escapeHtml(model.name)} ${model.is_froxy ? '<span class="opt-badge">FROXY</span>' : ''}</span>
            <span class="opt-desc">${escapeHtml(model.provider_label || model.provider)} · ${model.is_froxy ? 'Günlük ücretsiz kota' : `~${Number(model.estimated_1k_credits || 0).toLocaleString('tr-TR')} kredi`}</span>
          </span>
        </button>
      `).join('');
      menu.querySelectorAll('[data-model-id]').forEach(button => {
        button.addEventListener('click', () => {
          const model = state.models.find(row => row.id === button.dataset.modelId);
          if (model) selectModel(model.id, model.name, model.icon || (model.is_froxy ? '⚡' : '🤖'));
        });
      });
    }
    const first = state.models.find(model => model.id === state.selectedModel.id) || state.models[0];
    if (first) selectModel(first.id, first.name, first.icon || (first.is_froxy ? '⚡' : '🤖'));
  } catch (error) {
    if (menu) menu.innerHTML = '<div class="model-opt"><span class="opt-body"><span class="opt-title">Model kataloğu kullanılamıyor</span><span class="opt-desc">Biraz sonra tekrar deneyin.</span></span></div>';
    showToast(error.message || 'Model kataloğu alınamadı', '⚠️');
  }
}

// VIEW SWITCHING (Navigation Dock)
function switchView(viewId) {
  triggerHaptic('light');
  state.currentView = viewId;

  // Toggle View Containers
  const views = document.querySelectorAll('.app-view');
  views.forEach(v => {
    v.classList.remove('active');
    if (v.id === viewId) v.classList.add('active');
  });

  // Toggle Dock Buttons
  const dockItems = document.querySelectorAll('.dock-item');
  dockItems.forEach(d => {
    if (d.getAttribute('data-view') === viewId) d.classList.add('active');
    else d.classList.remove('active');
  });

  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// -------------------------------------------------------------
// VIEW 1: CHAT & PLAYGROUND ENGINE
// -------------------------------------------------------------
function toggleModelDropdown() {
  triggerHaptic('light');
  const menu = document.getElementById('modelDropdownMenu');
  if (menu) menu.classList.toggle('show');
}

function selectModel(id, name, icon, desc) {
  triggerHaptic('medium');
  state.selectedModel = { id, name, icon };
  
  const iconEl = document.getElementById('selectedModelIcon');
  const titleEl = document.getElementById('selectedModelTitle');
  const statusEl = document.getElementById('headerModelStatus');

  if (iconEl) iconEl.textContent = icon;
  if (titleEl) titleEl.textContent = name;
  if (statusEl) statusEl.textContent = `⚡ ${name} Aktif`;

  const menu = document.getElementById('modelDropdownMenu');
  if (menu) menu.classList.remove('show');

  showToast(`${name} modeline geçildi!`, icon);
}

function toggleChatFeature(feat) {
  triggerHaptic('light');
  if (feat === 'web') {
    state.webSearchEnabled = false;
    showToast('Canlı web araması yakında açılacak', '🌐');
  } else if (feat === 'reasoning') {
    state.reasoningEnabled = !state.reasoningEnabled;
    const btn = document.getElementById('toggleReasoning');
    if (btn) btn.classList.toggle('active', state.reasoningEnabled);
    showToast(state.reasoningEnabled ? 'Derin Düşünce (Reasoning) Açıldı' : 'Derin Düşünce Kapatıldı', '🧠');
  }
}

function clearChatMessages() {
  triggerHaptic('medium');
  state.chatMessages = [];
  state.chatId = (window.crypto?.randomUUID?.() || `chat-${Date.now()}`);
  const list = document.getElementById('messagesList');
  if (list) list.innerHTML = '';
  showToast('Sohbet temizlendi!', '🗑️');
}

function injectPrompt(promptText) {
  triggerHaptic('light');
  const textarea = document.getElementById('chatInputText');
  if (textarea) {
    textarea.value = promptText;
    autoResizeTextarea(textarea);
    textarea.focus();
  }
}

function autoResizeTextarea(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 120) + 'px';
}

function handleTextareaKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    handleSendMessage();
  }
}

async function handleSendMessage() {
  const textarea = document.getElementById('chatInputText');
  if (!textarea) return;
  const userText = textarea.value.trim();
  if (!userText || state.isGeneratingChat) return;

  textarea.value = '';
  autoResizeTextarea(textarea);
  triggerHaptic('medium');

  // Hide welcome card once conversation starts
  const welcomeCard = document.querySelector('.assistant-welcome-card');
  if (welcomeCard) welcomeCard.style.display = 'none';

  // Append User Message
  appendChatMessage('user', userText);
  state.chatMessages.push({ role: 'user', content: userText });

  // Show Typing Indicator
  state.isGeneratingChat = true;
  const typingEl = document.getElementById('typingIndicator');
  if (typingEl) typingEl.style.display = 'flex';
  scrollToChatBottom();

  let assistantText = '';
  let assistantBubble = null;
  const requestId = window.crypto?.randomUUID?.() || `req-${Date.now()}-${Math.random()}`;
  try {
    const response = await fetch(api('/api/chat'), {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({
        request_id: requestId,
        chat_id: state.chatId,
        model: state.selectedModel.id,
        messages: state.chatMessages,
        max_tokens: 800,
        temperature: state.reasoningEnabled ? 0.55 : 0.75,
        web_search: state.webSearchEnabled
      })
    });
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new Error(payload.error || 'Sohbet isteği başlatılamadı');
    }
    if (!response.body) throw new Error('Akış bağlantısı kurulamadı');
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    while (true) {
      const { value, done } = await reader.read();
      buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
      const frames = buffer.split('\n\n');
      buffer = frames.pop() || '';
      for (const frame of frames) {
        const eventLine = frame.split('\n').find(line => line.startsWith('event:'));
        const dataLine = frame.split('\n').find(line => line.startsWith('data:'));
        if (!dataLine) continue;
        const event = eventLine ? eventLine.slice(6).trim() : 'message';
        const payload = JSON.parse(dataLine.slice(5).trim());
        if (event === 'delta') {
          if (typingEl) typingEl.style.display = 'none';
          if (!assistantBubble) assistantBubble = appendChatMessage('assistant', '');
          assistantText += payload.content || '';
          if (assistantBubble) assistantBubble.innerHTML = formatMarkdown(assistantText);
          scrollToChatBottom();
        } else if (event === 'error') {
          throw new Error(payload.error || 'Model yanıt veremedi');
        }
      }
      if (done) break;
    }
    if (!assistantText) throw new Error('Model boş yanıt verdi');
    state.chatMessages.push({ role: 'assistant', content: assistantText });
    triggerHaptic('success');
    await registerAndSyncUserProfile();
  } catch (error) {
    if (!assistantBubble) assistantBubble = appendChatMessage('assistant', '');
    if (assistantBubble) assistantBubble.innerHTML = formatMarkdown(`⚠️ ${error.message || 'Sohbet sırasında bir hata oluştu.'}`);
    showToast(error.message || 'Sohbet hatası', '❌');
  } finally {
    if (typingEl) typingEl.style.display = 'none';
    state.isGeneratingChat = false;
    scrollToChatBottom();
  }
}

function appendChatMessage(role, content) {
  const list = document.getElementById('messagesList');
  if (!list) return;

  const msgRow = document.createElement('div');
  msgRow.className = `msg-row ${role}`;

  if (role === 'assistant') {
    msgRow.innerHTML = `
      <div class="msg-avatar">
        <img src="assets/froxy_chat_logo_1783808162276.png" alt="Froxy" onerror="this.src='https://cdn-icons-png.flaticon.com/512/4712/4712038.png'">
      </div>
      <div class="msg-bubble">${formatMarkdown(content)}</div>
    `;
  } else {
    msgRow.innerHTML = `
      <div class="msg-bubble">${escapeHtml(content)}</div>
    `;
  }

  list.appendChild(msgRow);
  return msgRow.querySelector('.msg-bubble');
}

function scrollToChatBottom() {
  const scrollContainer = document.getElementById('chatMessagesScroll');
  if (scrollContainer) {
    scrollContainer.scrollTop = scrollContainer.scrollHeight;
  }
}

function formatMarkdown(text) {
  // Simple markdown converter with code blocks
  let html = escapeHtml(text);
  
  // Format code blocks ```...```
  html = html.replace(/```([a-zA-Z]*)\n([\s\S]*?)```/g, (match, lang, code) => {
    return `<pre><code class="language-${lang}">${code.trim()}</code></pre>`;
  });

  // Bold **text**
  html = html.replace(/\*\*(.*?)\*\*/g, '<b>$1</b>');

  // Newlines
  html = html.replace(/\n/g, '<br>');

  return html;
}

function escapeHtml(text) {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function generateBotResponse(prompt, modelId) {
  const p = prompt.toLowerCase();

  if (p.includes('satış') || p.includes('reklam') || p.includes('instagram')) {
    return `🔥 **Froxy AI // Yüksek Dönüşümlü Satış ve Reklam Stratejisi**\n\n1. **Kanca (0-3 sn):** *"Her ay onlarca yapay zeka aboneliğine yüzlerce dolar ödemekten sıkılmadınız mı?"*\n2. **Değer Önerisi:** Froxy AI ile tüm GPT-4o, Claude 3.5 ve Gemini modellerini tek panelden kullandığın kadar krediyle yönet!\n3. **Çağrı (CTA):** *Hemen aşağıdaki Mağaza sekmesinden 1-tıkla lisansını al, anında teslim edilsin.*\n\n💡 *İpucu: Reels videolarında metni ekranda büyük puntolarla vurgulamak izlenme süresini %40 artırır.*`;
  }

  if (p.includes('kod') || p.includes('python') || p.includes('bot')) {
    return `💻 **Python Telegram Botu Hızlı Başlangıç Kodu:**\n\n\`\`\`python\nimport telebot\n\nBOT_TOKEN = "BURAYA_TOKEN_GIRIN"\nbot = telebot.TeleBot(BOT_TOKEN)\n\n@bot.message_handler(commands=['start'])\ndef send_welcome(message):\n    bot.reply_to(message, "⚡ Froxy AI Botuna Hoş Geldiniz! Nasıl yardımcı olabilirim?")\n\nprint("Bot aktif...")\nbot.infinity_polling()\n\`\`\`\n\n🚀 Bu kodu çalıştırmak için terminalinizde \`pip install pyTelegramBotAPI\` komutunu kullanabilirsiniz.`;
  }

  return `🤖 **Froxy AI (${state.selectedModel.name}):**\n\nSorunuzu başarıyla analiz ettim! **${prompt}** konusu hakkında size en doğru ve güncel bilgileri sağlamak için buradayım.\n\nİşlemi bir adım öteye taşımak için:\n• İlgili metin veya görsel üretimi yapabiliriz.\n• Mağazamızdan **ChatGPT Plus** veya **Gemini Ultra** lisansı temin ederek sınırsız hızın keyfini çıkarabilirsiniz!`;
}

// -------------------------------------------------------------
// VIEW 2: IMAGE STUDIO ENGINE
// -------------------------------------------------------------
function setImageStyle(styleKey, btn) {
  triggerHaptic('light');
  state.selectedStyle = styleKey;
  const chips = document.querySelectorAll('.style-chip');
  chips.forEach(c => c.classList.remove('active'));
  if (btn) btn.classList.add('active');
}

function setImageRatio(ratioKey, btn) {
  triggerHaptic('light');
  state.selectedRatio = ratioKey;
  const chips = document.querySelectorAll('.ratio-chips-row .ratio-chip');
  chips.forEach(c => c.classList.remove('active'));
  if (btn) btn.classList.add('active');
}

function enhanceImagePrompt() {
  triggerHaptic('medium');
  const input = document.getElementById('imagePromptInput');
  if (!input) return;
  const current = input.value.trim() || 'Fütüristik yapay zeka robotu';
  input.value = `${current}, ultra-detailed 8K resolution, cinematic lighting, octane render, unreal engine 5, masterpiece, highly intricate`;
  showToast('Prompt sihirli şekilde iyileştirildi!', '✨');
}

async function generateAiImage() {
  const promptInput = document.getElementById('imagePromptInput');
  const prompt = promptInput ? promptInput.value.trim() : '';

  if (!prompt) {
    showToast('Lütfen üretmek istediğiniz görseli tarif edin!', '⚠️');
    return;
  }

  triggerHaptic('heavy');
  state.isGeneratingImage = true;

  const loader = document.getElementById('imageLoaderOverlay');
  const statusTag = document.getElementById('imageStatusTag');
  const imgEl = document.getElementById('generatedImageEl');
  const genBtn = document.getElementById('generateImageBtn');

  if (loader) loader.style.display = 'flex';
  if (statusTag) statusTag.textContent = 'Üretiliyor...';
  if (genBtn) genBtn.disabled = true;

  try {
    const response = await fetch(api('/api/images'), {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({
        request_id: window.crypto?.randomUUID?.() || `img-${Date.now()}`,
        prompt: `${prompt}, ${state.selectedStyle} style`,
        style: state.selectedStyle,
        ratio: state.selectedRatio,
        use_free: state.freeImageRemaining > 0
      })
    });
    const payload = await response.json();
    if (!response.ok || !payload.success) throw new Error(payload.error || 'Görsel işi başlatılamadı');
    const jobId = payload.job.job_id;
    let completed = null;
    for (let attempt = 0; attempt < 80; attempt += 1) {
      await new Promise(resolve => setTimeout(resolve, 1500));
      const poll = await fetch(api(`/api/generation-jobs/${encodeURIComponent(jobId)}`), { headers: authHeaders() });
      const result = await poll.json();
      if (!poll.ok || !result.success) throw new Error(result.error || 'Görsel durumu alınamadı');
      if (result.job.status === 'failed') throw new Error(result.job.error || 'Görsel üretilemedi');
      if (result.job.status === 'completed') {
        completed = result.job;
        break;
      }
      if (statusTag) statusTag.textContent = result.job.status === 'running' ? 'Model çalışıyor...' : 'Sırada...';
    }
    if (!completed?.image_url) throw new Error('Görsel üretimi zaman aşımına uğradı');
    state.lastGeneratedImageUrl = completed.image_url;
    if (imgEl) imgEl.src = completed.image_url;
    if (statusTag) statusTag.textContent = 'Tamamlandı';
    showToast('Görseliniz başarıyla üretildi!', '🎨');
    triggerHaptic('success');
    await registerAndSyncUserProfile();
  } catch (error) {
    if (statusTag) statusTag.textContent = 'Hata';
    showToast(error.message || 'Görsel oluşturulamadı', '❌');
  } finally {
    if (loader) loader.style.display = 'none';
    if (genBtn) genBtn.disabled = false;
    state.isGeneratingImage = false;
  }
}

function downloadGeneratedImage() {
  triggerHaptic('light');
  if (state.lastGeneratedImageUrl) {
    const a = document.createElement('a');
    a.href = state.lastGeneratedImageUrl;
    a.target = '_blank';
    a.download = `froxy-ai-${Date.now()}.jpg`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    showToast('İndirme başlatıldı!', '📥');
  }
}

function openFullscreenImage() {
  triggerHaptic('light');
  if (state.lastGeneratedImageUrl) {
    window.open(state.lastGeneratedImageUrl, '_blank');
  }
}

// -------------------------------------------------------------
// VIEW 3: STORE & LICENSES ENGINE
// -------------------------------------------------------------
async function loadStoreProducts() {
  try {
    const res = await fetch(api('/api/products'));
    const data = await res.json();
    if (data.success && data.products) {
      state.products = data.products;
      renderStoreProducts();
    }
  } catch (e) {
    console.log('Error loading products:', e);
  }
}

function filterStoreCategory(cat, btn) {
  triggerHaptic('light');
  state.selectedCategory = cat;

  const tabs = document.querySelectorAll('.store-tab-btn');
  tabs.forEach(t => t.classList.remove('active'));
  if (btn) btn.classList.add('active');

  renderStoreProducts();
}

function handleStoreSearch(val) {
  state.searchQuery = val.trim().toLowerCase();
  renderStoreProducts();
}

function renderStoreProducts() {
  let list = state.products;

  if (state.selectedCategory !== 'all') {
    list = list.filter(p => p.category === state.selectedCategory);
  }

  if (state.searchQuery) {
    list = list.filter(p =>
      (p.title || '').toLowerCase().includes(state.searchQuery) ||
      (p.description || '').toLowerCase().includes(state.searchQuery) ||
      (p.model_tag || '').toLowerCase().includes(state.searchQuery)
    );
  }

  const grid = document.getElementById('storeProductsGrid');
  if (!grid) return;

  grid.innerHTML = list.map(p => `
    <div class="product-matrix-card">
      <div>
        <div class="card-tag-row">
          <span class="tag-badge">${p.badge || '🔥 POPÜLER'}</span>
          <span class="tag-model">${p.model_tag || 'AI MODEL'}</span>
        </div>

        <div class="product-media-box" onclick="openProductModal('${p.id}')">
          <img src="${p.image || 'assets/froxy_chat_logo_1783808162276.png'}" alt="${p.title}" onerror="this.src='assets/froxy_chat_logo_1783808162276.png'">
        </div>

        <div class="product-title" onclick="openProductModal('${p.id}')">${p.title}</div>
        <div class="product-desc">${p.description || 'Yapay zeka lisansı.'}</div>
      </div>

      <div>
        <div class="product-price-box">
          <span class="price-label-text">FİYAT</span>
          <span class="price-amount">${p.price || formatTL(p.price_num)}</span>
        </div>

        <button class="buy-action-btn" onclick="directBuyProduct('${p.id}')">
          <span>${p.category === 'credits' ? '🪙 AI Kredisi Al' : '💳 Bakiyeyle Satın Al'}</span>
        </button>
      </div>
    </div>
  `).join('');
}

async function directBuyProduct(productId) {
  triggerHaptic('medium');
  const p = state.products.find(item => String(item.id) === String(productId));
  if (!p) return;
  if (p.category === 'credits') {
    await buyCreditPackage(productId);
    return;
  }
  openProductModal(productId);
}

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
        <span class="tag-badge" style="display:inline-block; margin-bottom:8px;">${p.category_label || 'YAPAY ZEKA LİSANSI'}</span>
        <h3 style="font-family: var(--font-heading); font-size: 19px; font-weight: 900; color: #FFF; margin-bottom: 4px;">${p.title}</h3>
        <span class="tag-model" style="font-size:11px;">⚡ Model: ${p.model_tag || 'GPT-4o & Canvas'}</span>
      </div>

      <div style="background: rgba(0,0,0,0.4); border: 1px solid var(--border-glass); border-radius: var(--radius-lg); padding: 14px; margin-bottom: 16px;">
        <div style="font-size: 13px; color: var(--text-secondary); line-height: 1.5; margin-bottom: 12px;">
          ${p.description}
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 11.5px;">
          <div style="background: rgba(0,240,255,0.08); border: 1px solid var(--border-cyan); border-radius: var(--radius-sm); padding: 8px; color:#FFF;">
            ⚡ <b>${p.delivery_label || 'Stoktan otomatik / 1–3 iş günü manuel'}</b>
          </div>
          <div style="background: rgba(16,185,129,0.08); border: 1px solid var(--border-emerald); border-radius: var(--radius-sm); padding: 8px; color:#FFF;">
            🔒 <b>Shopier 3D Secure</b>
          </div>
        </div>
      </div>

      <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom: 16px; padding: 12px 16px; background: var(--bg-card); border-radius: var(--radius-lg); border: 1px solid var(--border-cyan);">
        <span style="color: var(--text-secondary); font-weight: 700;">Toplam Tutar:</span>
        <span style="font-family: var(--font-mono); font-size: 22px; font-weight: 900; color: var(--accent-cyan);">${p.price || formatTL(p.price_num)}</span>
      </div>

      <div style="display:flex; flex-direction:column; gap: 10px;">
        ${p.category === 'credits' ? `
          <button class="buy-action-btn" style="padding:14px; font-size:14px;" onclick="buyCreditPackage('${p.id}')">
            <span>⚡ Shopier ile ${Number(p.ai_credits || 0).toLocaleString('tr-TR')} AI Kredisi Al</span>
          </button>
        ` : `
          <button class="buy-action-btn" style="padding:14px; font-size:14px;" onclick="buyWithWalletBalance('${p.id}')">
            <span>💳 Mağaza Bakiyemle Satın Al (${formatTL(state.walletBalance)})</span>
          </button>
          <small style="color:var(--text-secondary);text-align:center;">Stok yoksa teslimat @FroxyDestekBOT üzerinden 1–3 iş günüdür.</small>
        `}
      </div>
    `;
  }

  if (modal) modal.style.display = 'flex';
}

function closeProductModal() {
  const modal = document.getElementById('productModal');
  if (modal) modal.style.display = 'none';
}

async function buyWithWalletBalance(productId) {
  const p = state.products.find(item => String(item.id) === String(productId));
  if (!p) return;

  const priceNum = p.price_num || parseFloat(p.price) || 0;
  if (state.walletBalance < priceNum) {
    triggerHaptic('warning');
    showToast(`Yetersiz bakiye! Gerekli: ${formatTL(priceNum)}, Bakiyeniz: ${formatTL(state.walletBalance)}`, '⚠️');
    setTimeout(() => {
      closeProductModal();
      switchView('view-wallet');
    }, 1200);
    return;
  }

  triggerHaptic('medium');
  try {
    const res = await fetch(api('/api/user/purchase'), {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({
        product_id: p.id,
        idempotency_key: window.crypto?.randomUUID?.() || `order-${Date.now()}`
      })
    });
    const data = await res.json();
    if (data.success) {
      state.walletBalance = Number.isFinite(Number(data.new_balance)) ? Number(data.new_balance) : state.walletBalance - priceNum;
      closeProductModal();
      const manual = data.order?.status === 'manual_pending';
      showPurchaseSuccessModal(manual ? "Siparişiniz Alındı" : "Siparişiniz Teslim Edildi!", manual ? `${p.title}, 1–3 iş günü içinde @FroxyDestekBOT üzerinden teslim edilecek.` : `${p.title} lisansınız oluşturuldu.`);
      if (tgUser && hasUserAuth) registerAndSyncUserProfile();
    } else {
      showToast(data.error || 'İşlem gerçekleştirilemedi', '❌');
    }
  } catch (e) {
    showToast('Bağlantı hatası oluştu', '❌');
  }
}

async function buyCreditPackage(productId) {
  const p = state.products.find(item => String(item.id) === String(productId));
  if (!p || p.category !== 'credits') return;
  triggerHaptic('medium');
  try {
    const response = await fetch(api('/api/credits/create-checkout'), {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({
        product_id: p.id,
        idempotency_key: window.crypto?.randomUUID?.() || `credit-${Date.now()}`
      })
    });
    const data = await response.json();
    if (!response.ok || !data.success) throw new Error(data.error || 'Ödeme bağlantısı oluşturulamadı');
    showToast(`${Number(data.ai_credits || p.ai_credits || 0).toLocaleString('tr-TR')} AI kredisi için Shopier açılıyor`, '🪙');
    if (tg?.openLink) tg.openLink(data.payment_url);
    else window.open(data.payment_url, '_blank');
  } catch (error) {
    showToast(error.message || 'Kredi paketi başlatılamadı', '❌');
  }
}

// -------------------------------------------------------------
// VIEW 4: AGENTS ENGINE
// -------------------------------------------------------------
function launchAgent(agentKey) {
  triggerHaptic('medium');
  switchView('view-chat');

  if (agentKey === 'copywriter') {
    injectPrompt('Sen uzman bir E-Ticaret ve Viral Reklam metin yazarı olarak çalış. Instagram ve TikTok için yüksek dönüşümlü 3 adet satış kancası ve metin hazırla.');
  } else if (agentKey === 'coder') {
    injectPrompt('Sen kıdemli bir Full-Stack yazılımcısın. Bana modern, temiz ve optimize edilmiş bir Python/Node.js scripti yaz.');
  } else if (agentKey === 'seo') {
    injectPrompt('Sen kıdemli bir SEO uzmanısın. E-ticaret sitemiz için Google 1. sıra hedefli anahtar kelime haritası ve içerik stratejisi oluştur.');
  } else if (agentKey === 'finance') {
    injectPrompt('Sen bir Finansal Pazar ve Kripto analistisin. Güncel trendleri ve risk yönetimi prensiplerini detaylıca özetle.');
  }
}

// -------------------------------------------------------------
// VIEW 5: WALLET & DYNAMIC TOPUP ENGINE
// -------------------------------------------------------------
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

  if (amt < 10) {
    showToast("Minimum yükleme tutarı 10 TL'dir", '⚠️');
    return;
  }

  showToast('Shopier ödeme sayfası açılıyor...', '⚡');
  const btn = document.getElementById('dynamicPayBtn');
  if (btn) btn.disabled = true;

  try {
    const res = await fetch(api('/api/balance/create-dynamic-topup'), {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({
        amount: amt,
        idempotency_key: window.crypto?.randomUUID?.() || `topup-${Date.now()}`
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
    listEl.innerHTML = state.orders.map(o => {
      const statusLabels = { delivered: '✅ Teslim edildi', manual_pending: '⏳ 1–3 iş günü manuel teslimat', processing: '⚙️ İşleniyor', completed: '✅ Tamamlandı' };
      const statusText = statusLabels[o.status] || o.status || 'Hazırlanıyor';
      const created = typeof o.created_at === 'number' ? new Date(o.created_at * 1000).toLocaleString('tr-TR') : (o.created_at || 'Bugün');
      return `
      <div class="order-box">
        <div class="order-head">
          <span>#${o.order_id || o.id || 'FX-1001'}</span>
          <span>${created}</span>
        </div>
        <div style="color:#FFF; font-weight:800; font-size:13.5px;">${o.product_title || o.title || 'Froxy AI Lisansı'}</div>
        <div class="order-code-row">
          <span>${o.license_key || o.credential || statusText}</span>
          ${o.license_key || o.credential ? `<button class="copy-btn" onclick="copyText('${o.license_key || o.credential}')">Kopyala</button>` : `<button class="copy-btn" onclick="openSupportBot()">Destek</button>`}
        </div>
      </div>
    `}).join('');
  }
}

function copyText(txt) {
  if (!txt) return;
  navigator.clipboard.writeText(txt);
  showToast('Bilgiler kopyalandı!', '📋');
}

function openSupportBot() {
  triggerHaptic('light');
  if (tg?.openTelegramLink) {
    tg.openTelegramLink('https://t.me/FroxyDestekBOT');
  } else {
    window.open('https://t.me/FroxyDestekBOT', '_blank');
  }
}

// -------------------------------------------------------------
// LUCKY WHEEL OF FORTUNE
// -------------------------------------------------------------
const wheelPrizes = [
  { label: '₺5 Bakiye', value: 5, color: '#070A14', textColor: '#00F0FF' },
  { label: '₺10 Bakiye', value: 10, color: '#10B981', textColor: '#000000' },
  { label: 'Tekrar Dene', value: 0, color: '#070A14', textColor: '#94A3B8' },
  { label: '₺25 Bakiye', value: 25, color: '#8B5CF6', textColor: '#FFFFFF' },
  { label: '%20 İndirim', value: 'coupon', color: '#070A14', textColor: '#F59E0B' },
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
  const modal = document.getElementById('spinModal');
  if (modal) modal.style.display = 'flex';
}

function closeSpinModal() {
  const modal = document.getElementById('spinModal');
  if (modal) modal.style.display = 'none';
}

function spinWheel() {
  if (isSpinning || !state.canSpin) return;
  isSpinning = true;
  triggerHaptic('heavy');

  const winIndex = Math.floor(Math.random() * wheelPrizes.length);
  const prize = wheelPrizes[winIndex];

  const totalRounds = 5 + Math.floor(Math.random() * 3);
  const sliceAngle = (2 * Math.PI) / wheelPrizes.length;
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

// -------------------------------------------------------------
// SUCCESS MODAL ENGINE
// -------------------------------------------------------------
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

function goToWallet() {
  closeSuccessModal();
  switchView('view-wallet');
}

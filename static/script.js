const UI = {
    statusBadge: document.getElementById('botStatus'),
    statusText: document.querySelector('#botStatus .text'),
    btnStart: document.getElementById('btnStart'),
    btnStop: document.getElementById('btnStop'),
    btnSave: document.getElementById('btnSave'),
    editor: document.getElementById('messageEditor'),
    editor2: document.getElementById('messageEditor2'),
    terminal: document.getElementById('terminalOutput'),
    
    // Stats Elements
    statTotalGroups: document.getElementById('statTotalGroups'),
    statSentMessages: document.getElementById('statSentMessages'),
    statProgress: document.getElementById('statProgress'),
    statBlacklist: document.getElementById('statBlacklist'),
    statAutoDiscovered: document.getElementById('statAutoDiscovered'),
    
    // Support Bot UI Elements
    supportStatusBadge: document.getElementById('supportBotStatus'),
    supportStatusText: document.querySelector('#supportBotStatus .text'),
    btnSupportStart: document.getElementById('btnSupportStart'),
    btnSupportStop: document.getElementById('btnSupportStop'),
    supportTerminal: document.getElementById('supportTerminalOutput'),
    
    // Froxy Bot UI Elements
    froxyStatusBadge: document.getElementById('froxyBotStatus'),
    froxyStatusText: document.querySelector('#froxyBotStatus .text'),
    btnFroxyStart: document.getElementById('btnFroxyStart'),
    btnFroxyStop: document.getElementById('btnFroxyStop'),
    froxyTerminal: document.getElementById('froxyTerminalOutput'),
    cfgFroxyBotToken: document.getElementById('cfgFroxyBotToken'),
    cfgFroxyAdminId: document.getElementById('cfgFroxyAdminId'),
    btnSaveFroxyConfig: document.getElementById('btnSaveFroxyConfig'),
    
    // Config Form Inputs
    cfgBotToken: document.getElementById('cfgBotToken'),
    cfgAdminId: document.getElementById('cfgAdminId'),
    cfgAdStringSession: document.getElementById('cfgAdStringSession'),
    cfgAdStringSession2: document.getElementById('cfgAdStringSession2'),
    cfgAdSleepMin: document.getElementById('cfgAdSleepMin'),
    cfgAdSleepMax: document.getElementById('cfgAdSleepMax'),
    btnSaveConfig: document.getElementById('btnSaveConfig'),
    
    // Blacklist Elements
    newBlacklistGroup: document.getElementById('newBlacklistGroup'),
    blacklistTableBody: document.getElementById('blacklistTableBody'),
    searchBlacklist: document.getElementById('searchBlacklist')
};

// TAB SWITCHING LOGIC
function switchTab(tabName) {
    document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
    document.getElementById('tab-' + tabName).classList.add('active');
    document.getElementById('tabBtn' + tabName.charAt(0).toUpperCase() + tabName.slice(1)).classList.add('active');
    if (tabName === 'blacklist') {
        loadBlacklist();
    }
}

// BLACKLIST MANAGER LOGIC
let blacklistData = [];

async function loadBlacklist() {
    try {
        const res = await fetch('/api/blacklist');
        blacklistData = await res.json();
        renderBlacklist(blacklistData);
    } catch(e) {
        console.error("Error loading blacklist:", e);
    }
}

function renderBlacklist(data) {
    if (!UI.blacklistTableBody) return;
    if (data.length === 0) {
        UI.blacklistTableBody.innerHTML = `
            <tr>
                <td colspan="2" style="text-align: center; padding: 30px; color: #666; font-style: italic; font-size: 0.95rem;">
                    Kara listede hiç grup yok.
                </td>
            </tr>
        `;
        return;
    }
    
    UI.blacklistTableBody.innerHTML = data.map(group => `
        <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
            <td style="padding: 12px 10px; font-family: 'Inconsolata', monospace; font-size: 1.05rem; color: #f3f4f6;">@${group}</td>
            <td style="padding: 12px 10px; text-align: right;">
                <button class="btn danger" onclick="removeFromBlacklist('${group}')" style="padding: 5px 12px; font-size: 0.85rem;">
                    <i class="fa-solid fa-trash-can"></i> Sil
                </button>
            </td>
        </tr>
    `).join('');
}

async function addToBlacklist(event) {
    if (event) event.preventDefault();
    const username = UI.newBlacklistGroup.value.trim();
    if (!username) {
        alert("Lütfen bir grup kullanıcı adı girin.");
        return;
    }
    
    try {
        const res = await fetch('/api/blacklist/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username })
        });
        const data = await res.json();
        if (data.success) {
            UI.newBlacklistGroup.value = '';
            loadBlacklist();
            fetchStats();
        } else {
            alert("Hata: " + data.message);
        }
    } catch(e) {
        alert("Bağlantı hatası!");
    }
}

async function removeFromBlacklist(username) {
    if (!confirm(`@${username} grubunu kara listeden kaldırmak istediğinize emin misiniz?`)) {
        return;
    }
    
    try {
        const res = await fetch('/api/blacklist/remove', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username })
        });
        const data = await res.json();
        if (data.success) {
            loadBlacklist();
            fetchStats();
        } else {
            alert("Hata: " + data.message);
        }
    } catch(e) {
        alert("Bağlantı hatası!");
    }
}

function filterBlacklist() {
    const query = UI.searchBlacklist.value.trim().toLowerCase();
    const filtered = blacklistData.filter(group => group.toLowerCase().includes(query));
    renderBlacklist(filtered);
}


// AD ADVERTISING BOT LOGIC
async function checkStatus() {
    try {
        const res = await fetch('/api/status');
        const data = await res.json();
        updateStatusUI(data.status);
    } catch (e) {
        updateStatusUI('offline');
    }
}

function updateStatusUI(status) {
    UI.statusBadge.className = 'status-badge ' + status;
    
    if (status === 'running') {
        UI.statusText.textContent = 'Çalışıyor';
        UI.btnStart.disabled = true; UI.btnStart.style.opacity = '0.5';
        UI.btnStop.disabled = false; UI.btnStop.style.opacity = '1';
    } else if (status === 'stopped') {
        UI.statusText.textContent = 'Durduruldu';
        UI.btnStart.disabled = false; UI.btnStart.style.opacity = '1';
        UI.btnStop.disabled = true; UI.btnStop.style.opacity = '0.5';
    } else {
        UI.statusText.textContent = 'Bağlantı Yok';
        UI.btnStart.disabled = true; UI.btnStop.disabled = true;
    }
}

async function startBot() {
    UI.btnStart.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Başlatılıyor...';
    const res = await fetch('/api/start', { method: 'POST' });
    const data = await res.json();
    UI.btnStart.innerHTML = '<i class="fa-solid fa-play"></i> Başlat';
    if(data.success) checkStatus();
    else alert("Hata: " + data.message);
}

async function stopBot() {
    UI.btnStop.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Durduruluyor...';
    const res = await fetch('/api/stop', { method: 'POST' });
    const data = await res.json();
    UI.btnStop.innerHTML = '<i class="fa-solid fa-stop"></i> Durdur';
    if(data.success) checkStatus();
    else alert("Hata: " + data.message);
}

async function loadMessage() {
    try {
        const res = await fetch('/api/message');
        const data = await res.json();
        UI.editor.value = data.message;
    } catch(e) {}
    try {
        const res = await fetch('/api/message2');
        const data = await res.json();
        UI.editor2.value = data.message;
    } catch(e) {}
}

async function saveMessage(event) {
    const btn = event.currentTarget;
    const oldHtml = btn.innerHTML;
    
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Kaydediliyor...';
    
    const res = await fetch('/api/message', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ message: UI.editor.value })
    });
    
    const data = await res.json();
    if(data.success) {
        btn.innerHTML = '<i class="fa-solid fa-check"></i> Kaydedildi';
        btn.classList.add('success-state');
        setTimeout(() => {
            btn.innerHTML = oldHtml;
            btn.classList.remove('success-state');
        }, 2000);
    } else {
        btn.innerHTML = '<i class="fa-solid fa-xmark"></i> Hata';
        setTimeout(() => btn.innerHTML = oldHtml, 2000);
        alert("Mesaj kaydedilemedi: " + data.message);
    }
}

async function saveMessage2(event) {
    const btn = event.currentTarget;
    const oldHtml = btn.innerHTML;
    
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Kaydediliyor...';
    
    const res = await fetch('/api/message2', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ message: UI.editor2.value })
    });
    
    const data = await res.json();
    if(data.success) {
        btn.innerHTML = '<i class="fa-solid fa-check"></i> Kaydedildi';
        btn.classList.add('success-state');
        setTimeout(() => {
            btn.innerHTML = oldHtml;
            btn.classList.remove('success-state');
        }, 2000);
    } else {
        btn.innerHTML = '<i class="fa-solid fa-xmark"></i> Hata';
        setTimeout(() => btn.innerHTML = oldHtml, 2000);
        alert("Mesaj kaydedilemedi: " + data.message);
    }
}

// SUPPORT CUSTOMER BOT LOGIC
async function checkSupportStatus() {
    try {
        const res = await fetch('/api/support/status');
        const data = await res.json();
        updateSupportStatusUI(data.status);
    } catch (e) {
        updateSupportStatusUI('offline');
    }
}

function updateSupportStatusUI(status) {
    UI.supportStatusBadge.className = 'status-badge ' + status;
    
    if (status === 'running') {
        UI.supportStatusText.textContent = 'Aktif';
        UI.btnSupportStart.disabled = true; UI.btnSupportStart.style.opacity = '0.5';
        UI.btnSupportStop.disabled = false; UI.btnSupportStop.style.opacity = '1';
    } else if (status === 'stopped') {
        UI.supportStatusText.textContent = 'Durduruldu';
        UI.btnSupportStart.disabled = false; UI.btnSupportStart.style.opacity = '1';
        UI.btnSupportStop.disabled = true; UI.btnSupportStop.style.opacity = '0.5';
    } else {
        UI.supportStatusText.textContent = 'Bağlantı Yok';
        UI.btnSupportStart.disabled = true; UI.btnSupportStop.disabled = true;
    }
}

async function startSupportBot() {
    UI.btnSupportStart.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Başlatılıyor...';
    const res = await fetch('/api/support/start', { method: 'POST' });
    const data = await res.json();
    UI.btnSupportStart.innerHTML = '<i class="fa-solid fa-play"></i> Botu Aktifleştir';
    if(data.success) checkSupportStatus();
    else alert("Hata: " + data.message);
}

async function stopSupportBot() {
    UI.btnSupportStop.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Durduruluyor...';
    const res = await fetch('/api/support/stop', { method: 'POST' });
    const data = await res.json();
    UI.btnSupportStop.innerHTML = '<i class="fa-solid fa-stop"></i> Botu Durdur';
    if(data.success) checkSupportStatus();
    else alert("Hata: " + data.message);
}

// FROXY AI BOT LOGIC
async function checkFroxyStatus() {
    try {
        const res = await fetch('/api/froxy/status');
        const data = await res.json();
        updateFroxyStatusUI(data.status);
    } catch (e) {
        updateFroxyStatusUI('offline');
    }
}

function updateFroxyStatusUI(status) {
    UI.froxyStatusBadge.className = 'status-badge ' + status;
    
    if (status === 'running') {
        UI.froxyStatusText.textContent = 'Aktif';
        UI.btnFroxyStart.disabled = true; UI.btnFroxyStart.style.opacity = '0.5';
        UI.btnFroxyStop.disabled = false; UI.btnFroxyStop.style.opacity = '1';
    } else if (status === 'stopped') {
        UI.froxyStatusText.textContent = 'Durduruldu';
        UI.btnFroxyStart.disabled = false; UI.btnFroxyStart.style.opacity = '1';
        UI.btnFroxyStop.disabled = true; UI.btnFroxyStop.style.opacity = '0.5';
    } else {
        UI.froxyStatusText.textContent = 'Bağlantı Yok';
        UI.btnFroxyStart.disabled = true; UI.btnFroxyStop.disabled = true;
    }
}

async function startFroxyBot() {
    UI.btnFroxyStart.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Başlatılıyor...';
    const res = await fetch('/api/froxy/start', { method: 'POST' });
    const data = await res.json();
    UI.btnFroxyStart.innerHTML = '<i class="fa-solid fa-play"></i> Botu Aktifleştir';
    if(data.success) checkFroxyStatus();
    else alert("Hata: " + data.message);
}

async function stopFroxyBot() {
    UI.btnFroxyStop.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Durduruluyor...';
    const res = await fetch('/api/froxy/stop', { method: 'POST' });
    const data = await res.json();
    UI.btnFroxyStop.innerHTML = '<i class="fa-solid fa-stop"></i> Botu Durdur';
    if(data.success) checkFroxyStatus();
    else alert("Hata: " + data.message);
}

async function loadFroxyConfig() {
    try {
        const res = await fetch('/api/froxy/config');
        const data = await res.json();
        UI.cfgFroxyBotToken.value = data.froxy_bot_token || '';
        UI.cfgFroxyAdminId.value = data.froxy_admin_id || '';
    } catch (e) {
        console.error("Froxy config load error: ", e);
    }
}

async function saveFroxyConfig() {
    const oldHtml = UI.btnSaveFroxyConfig.innerHTML;
    UI.btnSaveFroxyConfig.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Kaydediliyor...';
    
    const configData = {
        froxy_bot_token: UI.cfgFroxyBotToken.value.trim(),
        froxy_admin_id: parseInt(UI.cfgFroxyAdminId.value) || 0
    };
    
    try {
        const res = await fetch('/api/froxy/config', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(configData)
        });
        const data = await res.json();
        if (data.success) {
            UI.btnSaveFroxyConfig.innerHTML = '<i class="fa-solid fa-check"></i> Kaydedildi';
            UI.btnSaveFroxyConfig.classList.add('success-state');
            setTimeout(() => {
                UI.btnSaveFroxyConfig.innerHTML = oldHtml;
                UI.btnSaveFroxyConfig.classList.remove('success-state');
            }, 2000);
        } else {
            throw new Error(data.message);
        }
    } catch(e) {
        UI.btnSaveFroxyConfig.innerHTML = '<i class="fa-solid fa-xmark"></i> Hata';
        setTimeout(() => UI.btnSaveFroxyConfig.innerHTML = oldHtml, 2000);
        alert("Yapılandırma kaydedilemedi: " + e.message);
    }
}

// CONFIGURATION LOGIC
async function loadConfig() {
    try {
        const res = await fetch('/api/config');
        const data = await res.json();
        if (data.bot_token || data.ad_string_session || data.ad_string_session_2 || data.ad_sleep_min) {
            UI.cfgBotToken.value = data.bot_token || '';
            UI.cfgAdminId.value = data.admin_id || '';
            UI.cfgAdStringSession.value = data.ad_string_session || '';
            UI.cfgAdStringSession2.value = data.ad_string_session_2 || '';
            UI.cfgAdSleepMin.value = data.ad_sleep_min || 180;
            UI.cfgAdSleepMax.value = data.ad_sleep_max || 300;
        }
    } catch (e) {
        console.error("Config load error: ", e);
    }
}

async function saveConfig() {
    const oldHtml = UI.btnSaveConfig.innerHTML;
    UI.btnSaveConfig.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Kaydediliyor...';
    
    const configData = {
        bot_token: UI.cfgBotToken.value.trim(),
        admin_id: parseInt(UI.cfgAdminId.value) || 0,
        ad_string_session: UI.cfgAdStringSession.value.trim(),
        ad_string_session_2: UI.cfgAdStringSession2.value.trim(),
        ad_sleep_min: parseInt(UI.cfgAdSleepMin.value) || 180,
        ad_sleep_max: parseInt(UI.cfgAdSleepMax.value) || 300,
    };
    
    try {
        const res = await fetch('/api/config', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(configData)
        });
        const data = await res.json();
        if (data.success) {
            UI.btnSaveConfig.innerHTML = '<i class="fa-solid fa-check"></i> Kaydedildi';
            UI.btnSaveConfig.classList.add('success-state');
            setTimeout(() => {
                UI.btnSaveConfig.innerHTML = oldHtml;
                UI.btnSaveConfig.classList.remove('success-state');
            }, 2000);
        } else {
            throw new Error(data.message);
        }
    } catch(e) {
        UI.btnSaveConfig.innerHTML = '<i class="fa-solid fa-xmark"></i> Hata';
        setTimeout(() => UI.btnSaveConfig.innerHTML = oldHtml, 2000);
        alert("Yapılandırma kaydedilemedi: " + e.message);
    }
}

// COMMON LOG COLORIZER
function colorizeLog(line) {
    if(line.includes('✅') || line.includes('📨')) return `<p class="success">${line}</p>`;
    if(line.includes('❌') || line.includes('🚨') || line.includes('HATA') || line.includes('ERROR') || line.includes('Failed')) return `<p class="error">${line}</p>`;
    if(line.includes('⚠️') || line.includes('🔒') || line.includes('⏳') || line.includes('WARNING') || line.includes('wait')) return `<p class="warning">${line}</p>`;
    if(line.includes('🚀') || line.includes('📢') || line.includes('🔍') || line.includes('INFO') || line.includes('Starting')) return `<p class="info">${line}</p>`;
    return `<p>${line}</p>`;
}

async function fetchLogs() {
    // 1. Fetch Advertising Bot Logs
    try {
        const res = await fetch('/api/logs');
        const data = await res.json();
        
        let html = '';
        if (data.logs.length === 0) {
            html = '<p style="color: #666; text-align: center; margin-top: 50px;">Henüz log yok...</p>';
        } else {
            html = data.logs.map(line => colorizeLog(line)).join('');
        }
        
        const isScrolledToBottom = UI.terminal.scrollHeight - UI.terminal.clientHeight <= UI.terminal.scrollTop + 50;
        UI.terminal.innerHTML = html;
        if (isScrolledToBottom) {
            UI.terminal.scrollTop = UI.terminal.scrollHeight;
        }
    } catch(e) {}
    
    // 2. Fetch Support Bot Logs
    try {
        const res = await fetch('/api/support/logs');
        const data = await res.json();
        
        let html = '';
        if (data.logs.length === 0) {
            html = '<p style="color: #666; text-align: center; margin-top: 50px;">Henüz log yok...</p>';
        } else {
            html = data.logs.map(line => colorizeLog(line)).join('');
        }
        
        const isScrolledToBottom = UI.supportTerminal.scrollHeight - UI.supportTerminal.clientHeight <= UI.supportTerminal.scrollTop + 50;
        UI.supportTerminal.innerHTML = html;
        if (isScrolledToBottom) {
            UI.supportTerminal.scrollTop = UI.supportTerminal.scrollHeight;
        }
    } catch(e) {}
    
    // 3. Fetch Froxy Bot Logs
    try {
        const res = await fetch('/api/froxy/logs');
        const data = await res.json();
        let html = '';
        if (data.logs.length === 0) {
            html = '<p style="color: #666; text-align: center; margin-top: 50px;">Henüz log yok...</p>';
        } else {
            html = data.logs.map(line => colorizeLog(line)).join('');
        }
        const isScrolledToBottom = UI.froxyTerminal.scrollHeight - UI.froxyTerminal.clientHeight <= UI.froxyTerminal.scrollTop + 50;
        UI.froxyTerminal.innerHTML = html;
        if (isScrolledToBottom) {
            UI.froxyTerminal.scrollTop = UI.froxyTerminal.scrollHeight;
        }
    } catch(e) {}
}

async function fetchStats() {
    try {
        const res = await fetch('/api/stats');
        const data = await res.json();
        
        UI.statTotalGroups.textContent = data.total_groups || 0;
        UI.statSentMessages.textContent = data.sent_messages || 0;
        UI.statBlacklist.textContent = data.blacklist_groups || 0;
        if (UI.statAutoDiscovered) {
            UI.statAutoDiscovered.textContent = data.auto_discovered || 0;
        }
        
        if (data.total_groups > 0) {
            const pct = Math.min(100, Math.round((data.done_groups / data.total_groups) * 100));
            UI.statProgress.textContent = pct + '%';
        } else {
            UI.statProgress.textContent = '0%';
        }
    } catch(e) {
        console.error("Error fetching stats:", e);
    }
}

window.onload = () => {
    loadMessage();
    loadConfig();
    loadFroxyConfig();
    
    checkStatus();
    checkSupportStatus();
    checkFroxyStatus();
    fetchLogs();
    fetchStats();
    
    setInterval(checkStatus, 2000);
    setInterval(checkSupportStatus, 2000);
    setInterval(checkFroxyStatus, 2000);
    setInterval(fetchLogs, 1500);
    setInterval(fetchStats, 2000);
};

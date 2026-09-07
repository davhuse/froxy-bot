const nativeFetch = window.fetch;
let panelAdminToken = localStorage.getItem('panelAdminToken') || sessionStorage.getItem('panelAdminToken') || '';

async function adminFetch(input, init = {}) {
    const headers = new Headers(init.headers || {});
    if (panelAdminToken) {
        headers.set('X-Admin-Token', panelAdminToken);
    }
    return await nativeFetch(input, { ...init, headers });
}

function savePanelAdminToken(event) {
    if (event) event.preventDefault();
    const tokenInput = document.getElementById('panelAdminToken');
    if (!tokenInput) return;
    const token = tokenInput.value.trim();
    if (token) {
        panelAdminToken = token;
        localStorage.setItem('panelAdminToken', token);
        sessionStorage.setItem('panelAdminToken', token);
        alert('Yönetim anahtarı kaydedildi!');
    }
}

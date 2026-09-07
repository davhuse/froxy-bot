import re

with open("static/script.js", "r", encoding="utf-8") as f:
    content = f.read()

# Replace adminFetch
old_adminFetch = """async function adminFetch(input, init = {}) {
    if (!panelAdminToken) throw new Error('Yönetim anahtarı gerekli');
    const headers = new Headers(init.headers || {});
    headers.set('X-Admin-Token', panelAdminToken);
    const response = await nativeFetch(input, { ...init, headers });
    if (response.status === 401 || response.status === 503) {
        panelAdminToken = '';
        localStorage.removeItem('panelAdminToken');
        sessionStorage.removeItem('panelAdminToken');
        throw new Error('Yönetim anahtarı geçersiz veya sunucuda yapılandırılmamış');
    }
    return response;
}"""

new_adminFetch = """async function adminFetch(input, init = {}) {
    const headers = new Headers(init.headers || {});
    if (panelAdminToken) headers.set('X-Admin-Token', panelAdminToken);
    return await nativeFetch(input, { ...init, headers });
}"""

content = content.replace(old_adminFetch, new_adminFetch)

with open("static/script.js", "w", encoding="utf-8") as f:
    f.write(content)
print("done")

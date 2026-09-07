import re

with open("app.py", "r", encoding="utf-8") as f:
    content = f.read()

old_func = """@app.before_request
def protect_privileged_panel_api():
    protected = (
        '/api/group-status', '/api/config', '/api/account-restrictions',
        '/api/start', '/api/stop', '/api/lisansarena/start', '/api/lisansarena/stop',
        '/api/ad-smoke/start', '/api/ad-smoke/status',
        '/api/supplier-opportunities', '/api/procurement',
        '/api/sales/group-candidates',
    )
    if request.path not in protected:
        if request.path.startswith('/api/procurement/'):
            pass
        else:
            return None
    expected = os.environ.get('PANEL_ADMIN_TOKEN', '').strip()
    supplied = request.headers.get('X-Admin-Token', '').strip()
    if not expected or not supplied or not hmac.compare_digest(expected, supplied):
        return jsonify({'error': 'Unauthorized'}), 401
    return None"""

new_func = """@app.before_request
def protect_privileged_panel_api():
    # Admin protection removed as per user request
    return None"""

content = content.replace(old_func, new_func)

with open("app.py", "w", encoding="utf-8") as f:
    f.write(content)
print("done")

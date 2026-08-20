#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LisansArena — Standalone Mini App Server (v6.0)
"""

import os
import sys
import socket
from pathlib import Path
from flask import Flask

if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

try:
    from .blueprint import la_bp
except ImportError:
    from blueprint import la_bp

BASE_DIR = Path(__file__).resolve().parent
app = Flask(__name__)
app.register_blueprint(la_bp, url_prefix="")

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

if __name__ == "__main__":
    port = int(os.environ.get("LISANSARENA_PORT", 8081))
    local_ip = get_local_ip()
    print("=" * 60)
    print("  [+] LISANSARENA TELEGRAM MINI APP SUNUCUSU BASLATILDI")
    print(f"  [+] Yerel Baglanti:   http://localhost:{port}")
    print(f"  [+] Yerel Ag (Wi-Fi): http://{local_ip}:{port}")
    print(f"  [+] Shopier Magazasi: https://www.shopier.com/lisansarena")
    print("=" * 60)
    app.run(host="0.0.0.0", port=port, debug=False)

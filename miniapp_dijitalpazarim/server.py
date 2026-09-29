#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dijital Pazarım Telegram Mini App — Backend Server
Serves static SPA files & product listings.
"""

from pathlib import Path
from flask import Flask, send_from_directory

BASE_DIR = Path(__file__).resolve().parent
app = Flask(__name__, static_folder=str(BASE_DIR), static_url_path="")

@app.route("/")
def index():
    return send_from_directory(str(BASE_DIR), "index.html")

@app.route("/<path:path>")
def serve_static(path):
    return send_from_directory(str(BASE_DIR), path)

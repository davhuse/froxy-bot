# FroxyBot: Telegram Community Management & Automation Suite

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-Telegram-blue.svg)](https://telegram.org/)
[![Database](https://img.shields.io/badge/database-Firebase-orange.svg)](https://firebase.google.com/)

FroxyBot is an open-source, production-grade automated management and marketing suite designed for Telegram channels, groups, and communities. Powered by Python, Telethon, and Flask, and synchronized in real-time with Firebase, FroxyBot provides administrators with full control over automated promotion propagation, membership verification, transactional status updates, and blacklisting operations via a local web interface.

---

## 🌟 Key Features

*   **⚡ Automated Message Propagation:** Broadcast scheduled and real-time promotions across designated Telegram groups and channels dynamically.
*   **🔥 Real-time Firebase Sync:** Seamlessly retrieve and push user statuses, premium license subscriptions, and authorization profiles in real-time using Firebase Realtime Database.
*   **💻 Admin Web Control Panel:** A lightweight Flask-based web panel to monitor active sessions, update parameters, examine logs, and configure blacklist databases on the fly.
*   **🔒 Session Management:** Telethon string session and file session mechanisms designed for resilience, preventing rate limits and maintaining persistent authorization.
*   **🛡️ Dynamic Moderation & Triage:** Automatic user and group joins with integrated spam filters, blacklist restrictions, and message-blocking logic.
*   **💳 Payment Provider Integrations:** Built-in callbacks and support for Shopier checkout link automation for automated premium license provisioning.

---

## 🛠️ Technology Stack

*   **Core:** Python 3.10+
*   **Telegram Protocol Client:** Telethon (MTProto API wrapper)
*   **Web Framework:** Flask (HTML5 / CSS3 Admin Dashboard)
*   **Database:** Firebase Admin SDK (Realtime Database Integration)
*   **Task Execution:** Concurrency utilizing standard threading architectures

---

## 📦 Project Structure

```bash
tg-bot-reklam/
├── app.py                     # Flask Web Dashboard and routes
├── froxy_bot.py               # Core Telegram MTProto client and listener
├── otomatik_katil.py          # Auto-joiner and automatic message sender logic
├── firebase_companion.py      # Database helper for Firebase operations
├── bot_config.json.template   # Config template (Copy this to bot_config.json)
├── LICENSE                    # MIT Open Source License
├── requirements.txt           # Python project dependencies
├── static/                    # Dashboard static assets (CSS, JS, Images)
└── templates/                 # HTML templates for the Web Panel
```

---

## 🚀 Getting Started

### 📋 Prerequisites
*   Python 3.10 or higher
*   A Telegram `api_id` and `api_hash` (Obtained from [my.telegram.org](https://my.telegram.org/))
*   A Telegram Bot Token (Obtained from [@BotFather](https://t.me/BotFather))
*   A Firebase project with a Realtime Database enabled and service account credentials.

### ⚙️ Installation

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/davhuse/froxy-bot.git
    cd froxy-bot
    ```

2.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure Environment Details:**
    Copy the template configuration file:
    ```bash
    cp bot_config.json.template bot_config.json
    ```
    Edit `bot_config.json` and insert your credentials:
    ```json
    {
      "bot_token": "YOUR_TELEGRAM_BOT_TOKEN",
      "admin_id": 123456789,
      "ad_string_session": "YOUR_TELEGRAM_STRING_SESSION",
      "shopier_links": {
        "baslangic": "https://www.shopier.com/..."
      }
    }
    ```

4.  **Launch the Web Dashboard:**
    ```bash
    python app.py
    ```

5.  **Run the Automation Daemon:**
    ```bash
    python froxy_bot.py
    ```

---

## 🛡️ Security Disclaimer

**CRITICAL:** Never commit `bot_config.json`, `.session` files, or personal log files to public repositories. These files contain live API credentials and authorization hashes that could compromise your Telegram account. The `.gitignore` provided in this repository is pre-configured to keep these assets secure.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

import requests
from bs4 import BeautifulSoup
import re

def test_telegram_web(username):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    }
    url = f"https://t.me/{username}"
    res = requests.get(url, headers=headers, timeout=10)
    print(f"Status: {res.status_code}")
    soup = BeautifulSoup(res.text, "html.parser")
    
    title = soup.find("div", class_="tgme_page_title")
    title_text = title.text.strip() if title else ""
    
    extra = soup.find("div", class_="tgme_page_extra")
    extra_text = extra.text.strip() if extra else ""
    
    desc = soup.find("div", class_="tgme_page_description")
    desc_text = desc.text.strip() if desc else ""
    
    action_btn = soup.find("a", class_="tgme_action_button_new")
    action_text = action_btn.text.strip() if action_btn else ""
    
    print(f"Title: {title_text}")
    print(f"Extra: {extra_text}")
    print(f"Desc: {desc_text}")
    print(f"Action: {action_text}")
    
    # Check preview messages
    s_url = f"https://t.me/s/{username}"
    res_s = requests.get(s_url, headers=headers, timeout=10)
    soup_s = BeautifulSoup(res_s.text, "html.parser")
    messages = [m.text.strip() for m in soup_s.find_all("div", class_="tgme_widget_message_text")]
    print(f"Preview message count from /s/: {len(messages)}")
    if messages:
        print(f"First message: {messages[0][:150]}")

if __name__ == "__main__":
    test_telegram_web("kuponindirimsatis")
    print("---")
    test_telegram_web("tahaaslan11")

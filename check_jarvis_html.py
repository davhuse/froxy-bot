c = open('templates/jarvis_miniapp.html', encoding='utf-8').read()
print('Length:', len(c))
print('Has charset utf-8:', 'charset="UTF-8"' in c or 'charset="utf-8"' in c or 'charset=UTF-8' in c)

# Check Shopier links in jarvis_miniapp.html
import re
urls = re.findall(r'https?://[^\s"\'<>]+', c)
print(f"Total URLs in jarvis_miniapp.html: {len(urls)}")
for u in set(urls):
    print("  ", u)

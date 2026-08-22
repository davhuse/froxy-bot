import asyncio
import aiohttp
import re
import html as html_parser

async def debug_why():
    candidates = ["kuponceksatis", "kuponhesapsatis", "kuponsat", "kuponkodalimsatimm", "Kuponcekm"]
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    async with aiohttp.ClientSession(headers=headers) as session:
        for u in candidates:
            url = f"https://t.me/{u}"
            async with session.get(url, timeout=7) as resp:
                print(f"\n--- Checking @{u} ---")
                print("Status:", resp.status)
                raw_html = await resp.text()
                
                title_match = re.search(r'<meta\s+property="og:title"\s+content="([^"]*)"', raw_html)
                desc_match = re.search(r'<meta\s+property="og:description"\s+content="([^"]*)"', raw_html)
                extra_match = re.search(r'<div\s+class="tgme_page_extra">([^<]*)</div>', raw_html)
                
                print("title_match:", bool(title_match))
                print("desc_match:", bool(desc_match))
                print("extra_match:", bool(extra_match))
                
                if extra_match:
                    extra = extra_match.group(1).strip()
                    print("extra:", repr(extra))
                    is_group = "members" in extra.lower() or "online" in extra.lower() or "üye" in extra.lower()
                    print("is_group:", is_group)
                    
                    num_match = re.search(r"([\d\s]+)\s*(?:members|üye)", extra.replace("\xa0", " "))
                    print("num_match:", bool(num_match))
                    if num_match:
                        m_cnt = int(num_match.group(1).replace(" ", ""))
                        print("m_cnt:", m_cnt)

if __name__ == '__main__':
    asyncio.run(debug_why())

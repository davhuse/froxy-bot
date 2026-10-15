import hashlib
import html
import io
import json
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

import requests
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps
from zoneinfo import ZoneInfo


BRAND_COLORS = {
    'keyvadi': ('KEYVADI', '#875AF5'),
    'lisansarena': ('LISANSARENA', '#E8A638'),
    'froxy': ('FROXY', '#18B9DC'),
    'dijitalpazarim': ('DIJITAL PAZARIM', '#A268F2'),
    'zeka': ('ZEKA PAZARI', '#6891F8'),
}


class CampaignRateLimited(Exception):
    def __init__(self, seconds):
        self.seconds = max(1, int(seconds))


def caption(title, original, discounted, percent, expires_at):
    expires = datetime.fromtimestamp(float(expires_at), ZoneInfo('Europe/Istanbul'))
    original_amount = money(original)
    discounted_amount = money(discounted)
    saving = max(0, round(original_amount - discounted_amount, 2))
    return (
        f'⚡ <b>SAATİN FIRSATI · %{int(percent)} İNDİRİM</b>\n\n'
        f'📦 <b>{html.escape(str(title)[:180])}</b>\n'
        f'🏷 Normal: <s>{original_amount:.2f} TL</s>\n'
        f'💚 Fırsat: <b>{discounted_amount:.2f} TL</b>\n'
        f'🎁 Kazanç: {saving:.2f} TL\n'
        f'⏰ Bitiş: {expires:%H:%M} · Türkiye saati'
    )


def keyboard(callback, shop_url, notify_off):
    return {'inline_keyboard': [
        [{'text': '🛒 İndirimli Satın Al', 'style': 'success', 'callback_data': callback}],
        [{'text': '🛍 Mağazayı Aç', 'style': 'primary', 'web_app': {'url': shop_url}}],
        [{'text': '🔕 Bildirimleri Kapat', 'callback_data': notify_off}],
    ]}


def money(value):
    normalized = str(value).replace('TL', '').replace('₺', '').replace(' ', '').strip()
    if ',' in normalized:
        normalized = normalized.replace('.', '').replace(',', '.')
    return float(normalized)


def _font(size, bold=True):
    paths = (
        ('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 'C:/Windows/Fonts/segoeuib.ttf', 'C:/Windows/Fonts/arialbd.ttf')
        if bold else
        ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 'C:/Windows/Fonts/segoeui.ttf', 'C:/Windows/Fonts/arial.ttf')
    )
    for path in paths:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            pass
    return ImageFont.load_default()


def _product_image(image_url):
    if not str(image_url).startswith('https://'):
        raise ValueError('Ürün görseli HTTPS adresi değil')
    response = requests.get(image_url, timeout=12)
    response.raise_for_status()
    if len(response.content) > 6_000_000:
        raise ValueError('Ürün görseli fazla büyük')
    image_bytes = response.content
    if b'<svg' in image_bytes[:500]:
        from cairosvg import svg2png

        image_bytes = svg2png(bytestring=image_bytes, output_width=372, output_height=342)
    return Image.open(io.BytesIO(image_bytes)).convert('RGB')


def _fit_title(draw, title, max_width, max_lines=2):
    title = ' '.join(str(title or 'Dijital ürün fırsatı').split())
    for font_size in (30, 28, 26, 24):
        font = _font(font_size * 2)
        words = title.split()
        lines = []
        while words and len(lines) < max_lines:
            line = words.pop(0)
            while words and draw.textlength(line + ' ' + words[0], font=font) <= max_width * 2:
                line += ' ' + words.pop(0)
            lines.append(line)
        for number, line in enumerate(lines):
            if draw.textlength(line, font=font) > max_width * 2:
                while line and draw.textlength(line + '…', font=font) > max_width * 2:
                    line = line[:-1]
                lines[number] = line + '…'
        if words:
            while lines[-1] and draw.textlength(lines[-1] + '…', font=font) > max_width * 2:
                lines[-1] = lines[-1][:-1].rstrip()
            lines[-1] += '…'
        if not words or font_size == 24:
            return lines, font
    return [title[:30]], _font(48)


def _campaign_frames(source, name, accent, title, percent, original, discounted, expires_at, brand=''):
    scale = 2
    width = height = 640
    size = (width * scale, height * scale)
    accent_rgb = tuple(bytes.fromhex(accent.lstrip('#')))
    background = Image.new('RGB', size)
    bg_draw = ImageDraw.Draw(background)
    for y in range(size[1]):
        ratio = y / (size[1] - 1)
        bg_draw.line((0, y, size[0], y), fill=(int(9 + 8 * ratio), int(17 + 10 * ratio), int(32 + 19 * ratio)))
    glow = Image.new('RGBA', size)
    gd = ImageDraw.Draw(glow)
    gd.ellipse((680, -380, 1580, 490), fill=(*accent_rgb, 108))
    gd.ellipse((-420, 750, 400, 1580), fill=(*accent_rgb, 48))
    glow = glow.filter(ImageFilter.GaussianBlur(150))
    background = Image.alpha_composite(background.convert('RGBA'), glow)

    card = Image.new('RGBA', (576 * scale, 276 * scale), '#F8FAFC')
    card_draw = ImageDraw.Draw(card)
    if brand in ('dijitalpazarim','zeka'):
        # Product covers include tiny text and stale prices at this size. Show a
        # crisp app mark in a simple branded tile instead of shrinking the cover.
        from campaign_video import product_mark, _campaign_tile
        assets=Path(__file__).resolve().parent/'static/campaign_video'
        accent_rgb=tuple(bytes.fromhex(accent.lstrip('#')))
        tile=_campaign_tile(title,assets,card.size)
        rounded=Image.new('L',card.size)
        ImageDraw.Draw(rounded).rounded_rectangle((0,0,card.width-1,card.height-1),radius=42,fill=255)
        tile.putalpha(rounded)
        card=tile
        card_draw=ImageDraw.Draw(card)
        card_draw.rounded_rectangle((0,0,card.width-1,card.height-1),radius=42,
                                    outline=(*accent_rgb,230),width=4)
        badge=148*scale
        mark_center_x=round(card.width*.28)
        card_draw.ellipse((mark_center_x-badge//2,card.height//2-badge//2,
                           mark_center_x+badge//2,card.height//2+badge//2),
                          fill=(8,14,29,215),outline=(255,255,255,180),width=3*scale)
        product=product_mark(title,assets).convert('RGBA')
        product=ImageOps.contain(product,(116*scale,116*scale),Image.Resampling.LANCZOS)
        card.alpha_composite(product,(mark_center_x-product.width//2,(card.height-product.height)//2))
    else:
        card_draw.rounded_rectangle((0, 0, card.width - 1, card.height - 1), radius=42, fill='#F8FAFC')
        # Store covers commonly print their standard price in the bottom quarter.
        # Keep the actual product artwork but omit that stale price during a flash sale.
        if source.width >= 500 and .9 <= source.width / source.height <= 1.1:
            source = source.crop((0, 0, source.width, round(source.height * .76)))
        product = ImageOps.contain(source.convert('RGBA'), (536 * scale, 240 * scale), Image.Resampling.LANCZOS)
        card.alpha_composite(product, ((card.width - product.width) // 2, (card.height - product.height) // 2))
    rounded = Image.new('L', card.size)
    ImageDraw.Draw(rounded).rounded_rectangle((0, 0, card.width - 1, card.height - 1), radius=42, fill=255)
    card.putalpha(rounded)
    shadow = Image.new('RGBA', size)
    ImageDraw.Draw(shadow).rounded_rectangle((32 * scale, 151 * scale, 608 * scale, 427 * scale), radius=42,
                                             fill=(0, 0, 0, 145))
    shadow = shadow.filter(ImageFilter.GaussianBlur(25))
    expires = datetime.fromtimestamp(float(expires_at), ZoneInfo('Europe/Istanbul'))
    normal = f'{money(original):,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    deal = f'{money(discounted):,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    frames = []
    for index in range(15):
        phase = index / 14
        canvas = Image.alpha_composite(background.copy(), shadow)
        draw = ImageDraw.Draw(canvas)
        brand_font = _font(17 * scale)
        brand_right = 49 * scale + draw.textlength(name, font=brand_font) + 16 * scale
        draw.rounded_rectangle((32 * scale, 29 * scale, brand_right, 66 * scale),
                               radius=18 * scale, fill='#263149', outline='#52617C', width=2)
        draw.text((49 * scale, 37 * scale), name, font=brand_font, fill='#FFFFFF')
        draw.text((32 * scale, 83 * scale), 'SAATİN FIRSATI', font=_font(43 * scale), fill='#FFFFFF',
                  stroke_width=1, stroke_fill='#FFFFFF')
        draw.rounded_rectangle((494 * scale, 92 * scale, 608 * scale, 140 * scale), radius=18 * scale,
                               fill=(*accent_rgb, 255))
        badge = f'%{int(percent)}'
        bbox = draw.textbbox((0, 0), badge, font=_font(25 * scale))
        draw.text(((551 * scale) - (bbox[2] - bbox[0]) // 2, 100 * scale), badge,
                  font=_font(25 * scale), fill='#FFFFFF')
        # A small image lift gives motion without making the product hard to read.
        lift = round(4 * (1 - min(1, phase * 4))) * scale
        canvas.alpha_composite(card, (32 * scale, 151 * scale + lift))
        if 2 <= index <= 11:
            shimmer = Image.new('RGBA', card.size)
            shine_draw = ImageDraw.Draw(shimmer)
            x = round((-130 + (card.width + 250) * (index - 2) / 9))
            shine_draw.polygon([(x - 75, 0), (x + 15, 0), (x + 135, card.height), (x + 45, card.height)],
                               fill=(255, 255, 255, 50))
            shimmer.putalpha(Image.composite(shimmer.getchannel('A'), Image.new('L', card.size), rounded))
            canvas.alpha_composite(shimmer, (32 * scale, 151 * scale + lift))
        draw = ImageDraw.Draw(canvas)
        lines, title_font = _fit_title(draw, title, 575)
        title_y = 440 * scale
        for line in lines:
            draw.text((33 * scale, title_y), line, font=title_font, fill='#FFFFFF')
            title_y += 34 * scale
        draw.text((34 * scale, 522 * scale), f'Normal {normal} TL', font=_font(18 * scale, False), fill='#ABB8CB')
        old_width = draw.textlength(f'Normal {normal} TL', font=_font(18 * scale, False))
        draw.line((34 * scale, 534 * scale, 34 * scale + old_width, 534 * scale), fill='#ABB8CB', width=2 * scale)
        saving=f'Kazanç {money(original)-money(discounted):.2f} TL'.replace('.',',')
        draw.text((400 * scale, 522 * scale), saving, font=_font(16 * scale), fill='#7BE0B2')
        draw.text((32 * scale, 550 * scale), f'{deal} TL', font=_font(43 * scale), fill='#FFFFFF')
        draw.rounded_rectangle((455 * scale, 558 * scale, 608 * scale, 595 * scale), radius=14 * scale,
                               fill=accent, outline=accent, width=2)
        draw.text((469 * scale, 566 * scale), f'{expires:%H:%M} BİTER', font=_font(17 * scale), fill='#FFFFFF')
        draw.rounded_rectangle((32 * scale, 611 * scale, 608 * scale, 617 * scale), radius=3 * scale,
                               fill='#344057')
        draw.rounded_rectangle((32 * scale, 611 * scale, (32 + round(576 * max(.22, phase))) * scale, 617 * scale),
                               radius=3 * scale, fill=(*accent_rgb, 255))
        frame = canvas.convert('RGB').resize((width, height), Image.Resampling.LANCZOS)
        frames.append(frame.quantize(colors=256, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE))
    return frames


def animation_url(brand, product_id, image_url, percent, original, discounted, expires_at, public_base, static_dir, title=''):
    if brand not in BRAND_COLORS:
        raise ValueError('Bilinmeyen marka')
    name, accent = BRAND_COLORS[brand]
    if brand == 'dijitalpazarim':
        animation, _ = campaign_media_urls(brand, product_id, image_url, percent, original, discounted,
                                           expires_at, public_base, static_dir, title=title)
        return animation
    if brand in ('dijitalpazarim','zeka') and (Path(__file__).resolve().parent/'static/campaign_video'/('flow-blue.mp4' if brand=='zeka' else 'flow-violet.mp4')).is_file():
        fingerprint=hashlib.sha256(json.dumps(['flow-art-v3',brand,str(product_id),image_url,title,percent,original,discounted,expires_at],ensure_ascii=False).encode()).hexdigest()[:24]
        output=Path(static_dir)/'campaigns'/(fingerprint+'.mp4')
        if not output.is_file() or not output.stat().st_size:
            from campaign_video import render
            render(brand,title,None if brand in ('dijitalpazarim','zeka') else _product_image(image_url),percent,original,discounted,expires_at,output)
        return public_base.rstrip('/')+'/static/campaigns/'+quote(output.name)
    fingerprint = hashlib.sha256(json.dumps(['flow-art-v6', brand, str(product_id), image_url, title, percent, original, discounted, expires_at], ensure_ascii=False).encode()).hexdigest()[:24]
    output = Path(static_dir) / 'campaigns' / (fingerprint + '.gif')
    if output.is_file() and output.stat().st_size:
        return public_base.rstrip('/') + '/static/campaigns/' + quote(output.name)
    source = None if brand in ('dijitalpazarim','zeka') else _product_image(image_url)
    output.parent.mkdir(parents=True, exist_ok=True)
    frames = _campaign_frames(source, name, accent, title, percent, original, discounted, expires_at, brand)
    temporary = output.with_suffix('.tmp')
    frames[0].save(temporary, format='GIF', save_all=True, append_images=frames[1:], duration=200, loop=0, optimize=True)
    temporary.replace(output)
    return public_base.rstrip('/') + '/static/campaigns/' + quote(output.name)


def campaign_media_urls(brand, product_id, image_url, percent, original, discounted, expires_at,
                        public_base, static_dir, title=''):
    """Return a campaign video and a matching static poster for DP Telegram fallbacks."""
    if brand != 'dijitalpazarim':
        raise ValueError('Bu medya çifti yalnızca Dijital Pazarım için tanımlı')
    fingerprint = hashlib.sha256(json.dumps(
        ['dp-integrated-v2', brand, str(product_id), str(title), int(percent), original,
         discounted, float(expires_at)], ensure_ascii=False).encode()).hexdigest()[:24]
    directory = Path(static_dir) / 'campaigns'
    video = directory / (fingerprint + '.mp4')
    poster = directory / (fingerprint + '.jpg')
    if not video.is_file() or not video.stat().st_size or not poster.is_file() or not poster.stat().st_size:
        from campaign_video import render, render_poster
        render(brand, title, None, percent, original, discounted, expires_at, video, product_id)
        render_poster(brand, title, None, percent, original, discounted, expires_at, poster, product_id)
    base = public_base.rstrip('/') + '/static/campaigns/'
    return base + quote(video.name), base + quote(poster.name)


def send_campaign_notice(token, chat_id, text, markup, image_url='', gif_url='', *, return_message=False):
    base = f'https://api.telegram.org/bot{token}/'
    methods = []
    if str(gif_url).startswith('https://'):
        methods.append(('sendAnimation', 'animation', gif_url))
    if str(image_url).startswith('https://'):
        methods.append(('sendPhoto', 'photo', image_url))
    methods.append(('sendMessage', '', ''))
    for method, media_key, media_url in methods:
        payload = {'chat_id': int(chat_id), 'parse_mode': 'HTML', 'reply_markup': markup}
        payload['caption' if media_key else 'text'] = text
        if media_key:
            payload[media_key] = media_url
        try:
            response = requests.post(base + method, json=payload, timeout=25)
            data = response.json()
        except (requests.RequestException, ValueError) as error:
            raise CampaignRateLimited(30) from error
        if response.status_code == 429:
            raise CampaignRateLimited(data.get('parameters', {}).get('retry_after', 30))
        if response.status_code >= 500:
            raise CampaignRateLimited(30)
        if data.get('ok'):
            if return_message:
                result = data.get('result') or {}
                return {
                    'ok': True,
                    'message_id': result.get('message_id'),
                    'media': bool(media_key),
                }
            return True
        if response.status_code == 403:
            return False
    return False

import argparse
import json
import mimetypes
import os
import ssl
import time
import urllib.error
import urllib.request
import uuid


API_BASE = "https://api.shopier.com/v1"
TMPFILES_UPLOAD_URL = "https://tmpfiles.org/api/v1/upload"
IMAGE_DIR = os.path.join(os.path.dirname(__file__), "shopier_images_v2")
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "bot_config.json")


def load_token():
    token = os.environ.get("SHOPIER_KEYVADI_ACCESS_TOKEN", "").strip()
    if not token:
        raise RuntimeError("SHOPIER_KEYVADI_ACCESS_TOKEN ortam degiskeni bulunamadi")
    return token


def api_request(token, method, path, payload=None):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        API_BASE + path,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token.strip()}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        },
    )
    with urllib.request.urlopen(request, context=ssl.create_default_context(), timeout=60) as response:
        body = response.read().decode("utf-8")
        return json.loads(body) if body else {}


def upload_to_tmpfiles(image_path):
    boundary = "----KeyVadiBoundary" + uuid.uuid4().hex
    filename = os.path.basename(image_path)
    content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    with open(image_path, "rb") as handle:
        image_bytes = handle.read()
    prefix = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: {content_type}\r\n\r\n"
    ).encode("utf-8")
    suffix = f"\r\n--{boundary}--\r\n".encode("utf-8")
    request = urllib.request.Request(
        TMPFILES_UPLOAD_URL,
        data=prefix + image_bytes + suffix,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "User-Agent": "Mozilla/5.0",
        },
    )
    with urllib.request.urlopen(request, context=ssl.create_default_context(), timeout=120) as response:
        result = json.loads(response.read().decode("utf-8"))
    page_url = result.get("data", {}).get("url", "")
    if not page_url:
        raise RuntimeError(f"tmpfiles yukleme yaniti gecersiz: {result}")
    return page_url.replace("tmpfiles.org/", "tmpfiles.org/dl/")


def discover_images():
    discovered = {}
    for filename in os.listdir(IMAGE_DIR):
        if not filename.lower().endswith((".png", ".jpg", ".jpeg", ".bmp")):
            continue
        product_id = filename.split("_", 1)[0]
        if product_id.isdigit():
            discovered[product_id] = os.path.join(IMAGE_DIR, filename)
    return discovered


def update_product_image(token, product_id, image_path):
    old_product = api_request(token, "GET", f"/products/{product_id}")
    old_media = old_product.get("media") or []
    image_url = upload_to_tmpfiles(image_path)
    updated = api_request(
        token,
        "PUT",
        f"/products/{product_id}",
        {"media": [{"type": "image", "url": image_url, "placement": 1}]},
    )
    new_media = updated.get("media") or []
    return {
        "id": product_id,
        "title": old_product.get("title", ""),
        "oldMediaCount": len(old_media),
        "newMediaCount": len(new_media),
        "sourceUrl": image_url,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ids", nargs="*", help="Yalnizca belirtilen urun ID'lerini guncelle")
    args = parser.parse_args()
    token = load_token()
    images = discover_images()
    if args.ids:
        wanted = set(args.ids)
        images = {product_id: path for product_id, path in images.items() if product_id in wanted}
    if not images:
        raise RuntimeError("Guncellenecek gorsel bulunamadi")

    failures = []
    print(f"Toplam {len(images)} urun gorseli guncellenecek.")
    for index, (product_id, image_path) in enumerate(sorted(images.items()), 1):
        try:
            result = update_product_image(token, product_id, image_path)
            print(f"[{index}/{len(images)}] OK {product_id} {result['title']} (medya: {result['oldMediaCount']} -> {result['newMediaCount']})")
        except Exception as exc:
            failures.append((product_id, str(exc)))
            print(f"[{index}/{len(images)}] HATA {product_id}: {exc}")
        time.sleep(0.35)

    if failures:
        print("Basarisiz urunler:")
        for product_id, error in failures:
            print(f"- {product_id}: {error}")
        raise SystemExit(1)
    print("Tum urun gorselleri basariyla guncellendi.")


if __name__ == "__main__":
    main()

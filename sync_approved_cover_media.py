"""Upload regenerated covers and attach them to existing Shopier listings."""

from __future__ import annotations

import json
import mimetypes
import ssl
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parent
API = "https://api.shopier.com/v1"
TOKENS = ROOT / "extracted_all_render_envs.json"


def api_request(token: str, method: str, path: str, payload: dict | None = None) -> dict:
    body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "User-Agent": "tg-bot-reklam-cover-sync/1.0",
    }
    if body is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(API + path, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, context=ssl.create_default_context(), timeout=60) as response:
            raw = response.read().decode("utf-8", errors="replace").strip()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"Shopier {method} {path} HTTP {exc.code}: {detail}") from exc


def upload(path: Path) -> str:
    boundary = "----CodexCover" + uuid.uuid4().hex
    data = path.read_bytes()
    content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    prefix = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{path.name}"\r\n'
        f"Content-Type: {content_type}\r\n\r\n"
    ).encode("utf-8")
    suffix = f"\r\n--{boundary}--\r\n".encode("utf-8")
    request = urllib.request.Request(
        "https://tmpfiles.org/api/v1/upload",
        data=prefix + data + suffix,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}", "User-Agent": "Mozilla/5.0"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, context=ssl.create_default_context(), timeout=120) as response:
            payload = json.loads(response.read().decode("utf-8"))
        url = str((payload.get("data") or {}).get("url") or "").strip()
        if url:
            return url.replace("tmpfiles.org/", "tmpfiles.org/dl/", 1)
    except Exception:
        pass

    # Uguu is used as a fallback when tmpfiles is rate-limited.
    boundary = "----CodexCover" + uuid.uuid4().hex
    prefix = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="files[]"; filename="{path.name}"\r\n'
        f"Content-Type: {content_type}\r\n\r\n"
    ).encode("utf-8")
    request = urllib.request.Request(
        "https://uguu.se/upload",
        data=prefix + data + f"\r\n--{boundary}--\r\n".encode("utf-8"),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}", "User-Agent": "Mozilla/5.0"},
        method="POST",
    )
    with urllib.request.urlopen(request, context=ssl.create_default_context(), timeout=120) as response:
        payload = json.loads(response.read().decode("utf-8"))
    files = payload.get("files") or []
    url = str((files[0] if files else {}).get("url") or "").strip()
    if not url:
        raise RuntimeError(f"public upload URL missing for {path.name}")
    return url.replace("tmpfiles.org/", "tmpfiles.org/dl/", 1)


def product_rows() -> list[tuple[str, str, Path, str]]:
    rows: list[tuple[str, str, Path, str]] = []
    for brand, db_path, env_key in (
        ("keyvadi", ROOT / "miniapp" / "products_db.json", "SHOPIER_KEYVADI_ACCESS_TOKEN"),
        ("lisansarena", ROOT / "miniapp_lisansarena" / "products_db.json", "SHOPIER_LISANSARENA_ACCESS_TOKEN"),
    ):
        for product in json.loads(db_path.read_text(encoding="utf-8")):
            image = str(product.get("image") or "")
            if "v7_" not in image:
                continue
            shopier_id = str(product.get("id") or "")
            if brand == "lisansarena":
                shopier_id = str(product.get("shopier_product_id") or "")
            if not shopier_id.isdigit():
                # Historical Turna records have no individual Shopier ID.
                continue
            path = ROOT / ("miniapp" if brand == "keyvadi" else "miniapp_lisansarena") / image
            if path.exists():
                rows.append((brand, shopier_id, path, env_key))
    return rows


def main() -> int:
    raw_secrets = json.loads(TOKENS.read_text(encoding="utf-8"))
    # The Render export keeps one environment object per service.  Prefer the
    # current service, then fall back to the first object containing the key.
    secrets = raw_secrets.get("froxy-bot-1 (CURRENT)") if isinstance(raw_secrets, dict) else None
    if not isinstance(secrets, dict):
        secrets = raw_secrets if isinstance(raw_secrets, dict) else {}
    if not secrets.get("SHOPIER_KEYVADI_ACCESS_TOKEN") or not secrets.get("SHOPIER_LISANSARENA_ACCESS_TOKEN"):
        for value in (raw_secrets.values() if isinstance(raw_secrets, dict) else []):
            if isinstance(value, dict) and value.get("SHOPIER_KEYVADI_ACCESS_TOKEN") and value.get("SHOPIER_LISANSARENA_ACCESS_TOKEN"):
                secrets = value
                break
    rows = product_rows()
    results = []
    failures = []
    print(f"Shopier kapak eşlemesi başlıyor: {len(rows)} ilan")
    for index, (brand, product_id, image, env_key) in enumerate(rows, 1):
        try:
            token = str(secrets.get(env_key) or "").strip()
            if not token:
                raise RuntimeError(f"{env_key} missing")
            image_url = upload(image)
            body = api_request(token, "PUT", f"/products/{product_id}", {"media": [{"type": "image", "url": image_url, "placement": 1}]})
            results.append({"brand": brand, "id": product_id, "image": str(image), "media": body.get("media") or []})
            print(f"[{index}/{len(rows)}] OK {brand} {product_id}")
        except Exception as exc:
            failures.append({"brand": brand, "id": product_id, "image": str(image), "error": str(exc)})
            print(f"[{index}/{len(rows)}] HATA {brand} {product_id}: {exc}")
        time.sleep(0.25)
    (ROOT / "approved_cover_media_results.json").write_text(json.dumps({"updated": results, "failed": failures}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Güncellendi: {len(results)} | Hata: {len(failures)}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

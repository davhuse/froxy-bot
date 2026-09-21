"""Upload local campaign cover PNGs to a temporary public image URL."""

from __future__ import annotations

import json
import mimetypes
import uuid
from pathlib import Path
from urllib.request import Request, urlopen

from campaign_catalog import CAMPAIGNS
from sync_campaign_shopier import ROOT


def upload(path: Path) -> str:
    boundary = "----CodexCampaign" + uuid.uuid4().hex
    data = path.read_bytes()
    header = (
        f"--{boundary}\r\n"
        f"Content-Disposition: form-data; name=\"files[]\"; filename=\"{path.name}\"\r\n"
        f"Content-Type: {mimetypes.guess_type(path.name)[0] or 'application/octet-stream'}\r\n\r\n"
    ).encode("utf-8")
    body = header + data + f"\r\n--{boundary}--\r\n".encode("utf-8")
    request = Request(
        "https://uguu.se/upload",
        data=body,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "User-Agent": "tg-bot-reklam-cover-upload/1.0",
        },
        method="POST",
    )
    with urlopen(request, timeout=60) as response:
        result = json.loads(response.read().decode("utf-8"))
    files = result.get("files") or []
    url = str((files[0] if files else {}).get("url") or "").strip()
    if not url:
        raise RuntimeError(f"tmpfiles URL dönmedi: {result}")
    return url.replace("tmpfiles.org/", "tmpfiles.org/dl/", 1)


def main() -> int:
    mapping = {}
    for key, campaign in CAMPAIGNS.items():
        path = ROOT / "miniapp" / "assets" / campaign["image"]
        mapping[key] = upload(path)
        print(f"{key}: {mapping[key]}")
    (ROOT / "campaign_media_urls.json").write_text(
        json.dumps(mapping, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Compact multi-provider inference gateway for the Froxy Mini App."""

from __future__ import annotations

import base64
import json
import math
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Iterable
from urllib.parse import quote

import requests


class GatewayError(RuntimeError):
    pass


def _first_key(*names: str) -> str:
    for name in names:
        raw = os.environ.get(name, "").strip()
        if not raw:
            continue
        for candidate in raw.replace("\r", "\n").replace(",", "\n").splitlines():
            value = candidate.strip()
            if value:
                return value
    return ""


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class Provider:
    slug: str
    label: str
    base_url: str
    key_names: tuple[str, ...]
    model_path: str = "/models"
    chat_path: str = "/chat/completions"
    auth_header: str = "Authorization"
    auth_prefix: str = "Bearer "

    @property
    def key(self) -> str:
        return _first_key(*self.key_names)


class FroxyGateway:
    CATALOG_TTL = 15 * 60

    def __init__(self, session: requests.Session | None = None):
        self.session = session or requests.Session()
        self._lock = threading.RLock()
        self._catalog: list[dict[str, Any]] = []
        self._models: dict[str, dict[str, Any]] = {}
        self._refreshed_at = 0.0
        self._provider_status: dict[str, dict[str, Any]] = {}

    @staticmethod
    def providers() -> list[Provider]:
        openai_base = os.environ.get("OPENAI_CHAT_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        providers = [
            Provider("openrouter", "OpenRouter", "https://openrouter.ai/api/v1", ("OPENROUTER_API_KEY", "OPENROUTER_API_KEYS")),
            Provider("groq", "Groq", "https://api.groq.com/openai/v1", ("GROQ_API_KEY", "GROQ_API_KEYS")),
            Provider("nvidia", "NVIDIA", "https://integrate.api.nvidia.com/v1", ("NVIDIA_API_KEY",)),
            Provider("together", "Together", "https://api.together.xyz/v1", ("TOGETHER_API_KEY", "TOGETHER_API_KEYS")),
            Provider("cerebras", "Cerebras", "https://api.cerebras.ai/v1", ("CEREBRAS_API_KEY",)),
            Provider("sambanova", "SambaNova", "https://api.sambanova.ai/v1", ("SAMBANOVA_API_KEY",)),
            Provider("gemini", "Google Gemini", "https://generativelanguage.googleapis.com/v1beta/openai", ("GEMINI_API_KEY", "GEMINI_API_KEYS")),
            Provider("openai", "OpenAI", openai_base, ("OPENAI_CHAT_KEY", "OPENAI_API_KEY")),
            Provider("aimlapi", "AI/ML API", "https://api.aimlapi.com/v1", ("AIMLAPI_KEY",)),
            Provider("huggingface", "Hugging Face", "https://router.huggingface.co/v1", ("HF_TOKEN", "HUGGINGFACE_API_KEY")),
        ]
        account_id = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "").strip()
        if account_id:
            providers.append(Provider(
                "cloudflare",
                "Cloudflare Workers AI",
                f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1",
                ("CLOUDFLARE_API_TOKEN",),
            ))
        return providers

    @staticmethod
    def _headers(provider: Provider) -> dict[str, str]:
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        headers[provider.auth_header] = f"{provider.auth_prefix}{provider.key}"
        if provider.slug == "openrouter":
            headers["HTTP-Referer"] = os.environ.get("FROXY_PUBLIC_URL", "https://froxyai.com")
            headers["X-Title"] = "Froxy AI Telegram"
        return headers

    def _fetch_provider(self, provider: Provider) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        started = time.time()
        try:
            response = self.session.get(
                f"{provider.base_url}{provider.model_path}",
                headers=self._headers(provider),
                timeout=(4, 10),
            )
            if response.status_code != 200:
                return [], {
                    "provider": provider.slug,
                    "healthy": False,
                    "status": response.status_code,
                    "latency_ms": int((time.time() - started) * 1000),
                }
            payload = response.json()
            rows = payload if isinstance(payload, list) else payload.get("data", payload.get("models", []))
            if not isinstance(rows, list):
                rows = []
            normalized = [self._normalize_model(provider, row) for row in rows if isinstance(row, dict)]
            normalized = [row for row in normalized if row and self._is_chat_model(row)]
            return normalized, {
                "provider": provider.slug,
                "healthy": bool(normalized),
                "status": 200,
                "models": len(normalized),
                "latency_ms": int((time.time() - started) * 1000),
            }
        except (requests.RequestException, ValueError, TypeError):
            return [], {
                "provider": provider.slug,
                "healthy": False,
                "status": "unreachable",
                "latency_ms": int((time.time() - started) * 1000),
            }

    @staticmethod
    def _normalize_model(provider: Provider, raw: dict[str, Any]) -> dict[str, Any] | None:
        model_id = str(raw.get("id") or raw.get("name") or "").strip()
        if not model_id:
            return None
        pricing = raw.get("pricing") if isinstance(raw.get("pricing"), dict) else {}
        prompt = _float(pricing.get("prompt", pricing.get("input", raw.get("input_cost_per_token"))), -1.0)
        completion = _float(pricing.get("completion", pricing.get("output", raw.get("output_cost_per_token"))), -1.0)
        image = _float(pricing.get("image", raw.get("image_cost")), -1.0)
        known_pricing = prompt >= 0 and completion >= 0
        is_free = (
            model_id.endswith(":free")
            or (known_pricing and prompt == 0 and completion == 0)
        )
        architecture = raw.get("architecture") if isinstance(raw.get("architecture"), dict) else {}
        modality = str(architecture.get("modality") or raw.get("modality") or "text->text")
        public_id = f"{provider.slug}/{model_id}"
        name = str(raw.get("name") or raw.get("display_name") or model_id)
        context = int(_float(raw.get("context_length", raw.get("context_window", 0)), 0))
        return {
            "id": public_id,
            "provider_model_id": model_id,
            "name": name,
            "provider": provider.slug,
            "provider_label": provider.label,
            "context_length": context,
            "modality": modality,
            "supports_vision": "image" in modality.lower(),
            "is_free": is_free,
            "known_pricing": known_pricing,
            "prompt_usd_per_token": max(0.0, prompt),
            "completion_usd_per_token": max(0.0, completion),
            "image_usd": max(0.0, image),
            "is_froxy": False,
        }

    @staticmethod
    def _is_chat_model(model: dict[str, Any]) -> bool:
        model_id = str(model.get("provider_model_id", "")).lower()
        denied = (
            "whisper", "speech", "tts", "guard", "moderation", "embedding",
            "embed-", "rerank", "audio-preview", "transcribe",
        )
        return not any(fragment in model_id for fragment in denied)

    def refresh_catalog(self, force: bool = False) -> list[dict[str, Any]]:
        with self._lock:
            if self._catalog and not force and time.time() - self._refreshed_at < self.CATALOG_TTL:
                return list(self._catalog)

        configured = [provider for provider in self.providers() if provider.key]
        all_models: list[dict[str, Any]] = []
        statuses: dict[str, dict[str, Any]] = {}
        with ThreadPoolExecutor(max_workers=min(6, max(1, len(configured)))) as pool:
            futures = {pool.submit(self._fetch_provider, provider): provider for provider in configured}
            for future in as_completed(futures):
                models, status = future.result()
                all_models.extend(models)
                statuses[status["provider"]] = status

        unique: dict[str, dict[str, Any]] = {}
        for model in all_models:
            unique[model["id"]] = model

        aliases = self._build_aliases(list(unique.values()))
        # Paid models without a reliable price are intentionally withheld. Free
        # models are reachable through the curated Froxy aliases so their quota
        # can be controlled consistently.
        billable = [m for m in unique.values() if m.get("known_pricing") and not m.get("is_free")]
        visible = aliases + sorted(billable, key=lambda row: (row["provider_label"], row["name"].lower()))
        models_by_id = {m["id"]: m for m in unique.values()}
        models_by_id.update({m["id"]: m for m in aliases})
        with self._lock:
            self._catalog = visible
            self._models = models_by_id
            self._provider_status = statuses
            self._refreshed_at = time.time()
        return list(visible)

    def _build_aliases(self, models: list[dict[str, Any]]) -> list[dict[str, Any]]:
        preferred_fragments = [
            "llama-3.1-8b", "llama-3.3-70b", "gemma-", "qwen", "gpt-oss", "mistral",
        ]
        free_provider_slugs = {
            item.strip() for item in os.environ.get(
                "FROXY_FREE_PROVIDERS", "groq,nvidia,cerebras,openrouter"
            ).split(",") if item.strip()
        }
        candidates = [m for m in models if m.get("is_free") or m.get("provider") in free_provider_slugs]
        candidates.sort(key=lambda row: (
            0 if any(fragment in row["provider_model_id"].lower() for fragment in preferred_fragments) else 1,
            0 if row["provider"] == "groq" else 1,
            row["name"].lower(),
        ))

        explicit = [
            ("froxy-fast", "Froxy Hızlı", "⚡", os.environ.get("FROXY_ALIAS_FAST", "")),
            ("froxy-smart", "Froxy Akıllı", "🧠", os.environ.get("FROXY_ALIAS_SMART", "")),
            ("froxy-vision", "Froxy Vision", "👁️", os.environ.get("FROXY_ALIAS_VISION", "")),
        ]
        selected: list[dict[str, Any]] = []
        used: set[str] = set()
        for index, (alias_id, label, icon, configured_target) in enumerate(explicit):
            target = next((m for m in models if m["id"] == configured_target), None)
            if target is None:
                pool = [m for m in candidates if m["id"] not in used]
                if alias_id == "froxy-vision":
                    vision = [m for m in pool if m.get("supports_vision")]
                    target = vision[0] if vision else None
                else:
                    target = (pool or candidates or models)[0] if (pool or candidates or models) else None
            if target is None:
                continue
            used.add(target["id"])
            fallbacks = [m["id"] for m in candidates if m["id"] != target["id"]][:4]
            selected.append({
                "id": alias_id,
                "name": label,
                "icon": icon,
                "provider": "froxy",
                "provider_label": "Froxy Modelleri",
                "provider_model_id": target["provider_model_id"],
                "target_public_id": target["id"],
                "fallback_targets": fallbacks,
                "context_length": target.get("context_length", 0),
                "modality": target.get("modality", "text->text"),
                "supports_vision": target.get("supports_vision", False),
                "is_free": True,
                "known_pricing": True,
                "prompt_usd_per_token": 0.0,
                "completion_usd_per_token": 0.0,
                "is_froxy": True,
                "description": "Günlük ücretsiz kota ile kullanılabilen, otomatik yedeklemeli Froxy modeli.",
            })
            if index == 1 and len(selected) >= 2 and not any(m.get("supports_vision") for m in candidates):
                # A third text-only alias adds noise when no real vision model is healthy.
                continue
        return selected[:3]

    def provider_status(self) -> dict[str, dict[str, Any]]:
        self.refresh_catalog()
        with self._lock:
            return json.loads(json.dumps(self._provider_status))

    def public_catalog(self) -> dict[str, Any]:
        rows = self.refresh_catalog()
        public = []
        for row in rows:
            item = {key: value for key, value in row.items() if key not in {
                "target_public_id", "fallback_targets", "provider_model_id",
                "prompt_usd_per_token", "completion_usd_per_token", "image_usd",
            }}
            item["estimated_1k_credits"] = self.estimate_credits(row, 600, 400)
            public.append(item)
        return {
            "models": public,
            "count": len(public),
            "active_provider_count": sum(1 for row in self._provider_status.values() if row.get("healthy")),
            "verified_total": sum(int(row.get("models", 0) or 0) for row in self._provider_status.values() if row.get("healthy")),
            "refreshed_at": int(self._refreshed_at),
        }

    def get_model(self, public_id: str) -> dict[str, Any]:
        self.refresh_catalog()
        with self._lock:
            model = self._models.get(str(public_id))
        if not model:
            raise GatewayError("Model aktif değil veya fiyatı doğrulanamadı")
        return dict(model)

    @staticmethod
    def _pricing_config() -> tuple[float, float, float]:
        usd_try = max(1.0, _float(os.environ.get("FROXY_USD_TRY_RATE"), 42.0))
        margin_multiplier = max(1.0, _float(os.environ.get("FROXY_RETAIL_MULTIPLIER"), 2.0))
        credit_try = max(0.000001, _float(os.environ.get("FROXY_CREDIT_TRY_VALUE"), 0.001))
        return usd_try, margin_multiplier, credit_try

    def estimate_credits(self, model: dict[str, Any], input_tokens: int, output_tokens: int) -> int:
        if model.get("is_froxy"):
            return 0
        usd = (
            max(0, int(input_tokens)) * _float(model.get("prompt_usd_per_token"))
            + max(0, int(output_tokens)) * _float(model.get("completion_usd_per_token"))
        )
        usd_try, multiplier, credit_try = self._pricing_config()
        return max(1, int(math.ceil((usd * usd_try * multiplier) / credit_try)))

    def reservation_for_chat(self, model: dict[str, Any], messages: list[dict[str, Any]], max_tokens: int) -> int:
        chars = sum(len(str(row.get("content", ""))) for row in messages)
        input_tokens = max(1, int(math.ceil(chars / 3.6)))
        return self.estimate_credits(model, input_tokens, max_tokens)

    def actual_chat_credits(self, model: dict[str, Any], usage: dict[str, Any], input_text: str, output_text: str) -> int:
        prompt_tokens = int(usage.get("prompt_tokens") or usage.get("input_tokens") or math.ceil(len(input_text) / 3.6))
        completion_tokens = int(usage.get("completion_tokens") or usage.get("output_tokens") or math.ceil(len(output_text) / 3.6))
        return self.estimate_credits(model, prompt_tokens, completion_tokens)

    def _provider_for_model(self, model: dict[str, Any]) -> Provider:
        provider = next((p for p in self.providers() if p.slug == model.get("provider")), None)
        if not provider or not provider.key:
            raise GatewayError("Model sağlayıcısı kullanılamıyor")
        return provider

    def _target_candidates(self, model: dict[str, Any]) -> list[dict[str, Any]]:
        if not model.get("is_froxy"):
            return [model]
        ids = [model.get("target_public_id"), *(model.get("fallback_targets") or [])]
        result = []
        with self._lock:
            for target_id in ids:
                target = self._models.get(str(target_id))
                if target and target.get("provider") != "froxy":
                    result.append(dict(target))
        return result

    def stream_chat(
        self,
        model: dict[str, Any],
        messages: list[dict[str, Any]],
        *,
        max_tokens: int = 800,
        temperature: float = 0.7,
    ) -> Iterable[dict[str, Any]]:
        last_error = "Model yanıt vermedi"
        for target in self._target_candidates(model):
            provider = self._provider_for_model(target)
            payload = {
                "model": target["provider_model_id"],
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stream": True,
                "stream_options": {"include_usage": True},
            }
            try:
                response = self.session.post(
                    f"{provider.base_url}{provider.chat_path}",
                    headers=self._headers(provider),
                    json=payload,
                    stream=True,
                    timeout=(8, 100),
                )
                if response.status_code >= 400:
                    last_error = f"{provider.label} HTTP {response.status_code}"
                    response.close()
                    continue
                emitted = False
                usage: dict[str, Any] = {}
                for raw_line in response.iter_lines(decode_unicode=True):
                    line = (raw_line or "").strip()
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        event = json.loads(data)
                    except ValueError:
                        continue
                    if isinstance(event.get("usage"), dict):
                        usage = event["usage"]
                    choices = event.get("choices") or []
                    if not choices:
                        continue
                    delta = choices[0].get("delta") or {}
                    content = delta.get("content")
                    if isinstance(content, str) and content:
                        emitted = True
                        yield {"type": "delta", "content": content}
                response.close()
                if emitted:
                    yield {
                        "type": "provider_done",
                        "usage": usage,
                        "provider": provider.slug,
                        "provider_model": target["provider_model_id"],
                    }
                    return
                last_error = f"{provider.label} boş yanıt verdi"
            except requests.RequestException:
                last_error = f"{provider.label} bağlantı hatası"
        raise GatewayError(last_error)

    def image_credit_cost(self) -> int:
        usd = max(0.0001, _float(os.environ.get("FROXY_IMAGE_COST_USD"), 0.0019))
        usd_try, multiplier, credit_try = self._pricing_config()
        return max(1, int(math.ceil((usd * usd_try * multiplier) / credit_try)))

    def generate_image(self, prompt: str, width: int = 512, height: int = 512) -> dict[str, Any]:
        attempts = [
            self._image_openai,
            self._image_together,
            self._image_cloudflare,
            self._image_runware,
            self._image_pollinations,
        ]
        errors = []
        for operation in attempts:
            try:
                result = operation(prompt, width, height)
                if result:
                    return result
            except GatewayError as exc:
                errors.append(str(exc))
            except requests.RequestException as exc:
                errors.append(f"{operation.__name__} bağlantı hatası: {type(exc).__name__}")
            except (ValueError, TypeError, KeyError) as exc:
                errors.append(f"{operation.__name__} geçersiz yanıtı: {type(exc).__name__}")
        raise GatewayError(errors[-1] if errors else "Çalışan görsel sağlayıcısı bulunamadı")

    def _image_openai(self, prompt: str, width: int, height: int) -> dict[str, Any] | None:
        key = _first_key("OPENAI_IMAGE_KEY", "OPENAI_API_KEY")
        if not key:
            return None
        base = os.environ.get("OPENAI_IMAGE_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        model = os.environ.get("OPENAI_IMAGE_MODEL", "gpt-image-1-mini")
        response = self.session.post(
            f"{base}/images/generations",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": model, "prompt": prompt, "size": f"{width}x{height}", "n": 1},
            timeout=(8, 120),
        )
        return self._decode_image_response(response, "openai", model)

    def _image_together(self, prompt: str, width: int, height: int) -> dict[str, Any] | None:
        key = _first_key("TOGETHER_API_KEY", "TOGETHER_API_KEYS")
        if not key:
            return None
        model = os.environ.get("FROXY_TOGETHER_IMAGE_MODEL", "stabilityai/stable-diffusion-xl-base-1.0")
        response = self.session.post(
            "https://api.together.xyz/v1/images/generations",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": model, "prompt": prompt, "width": width, "height": height, "steps": 4, "n": 1},
            timeout=(8, 120),
        )
        return self._decode_image_response(response, "together", model)

    def _image_cloudflare(self, prompt: str, width: int, height: int) -> dict[str, Any] | None:
        token = _first_key("CLOUDFLARE_API_TOKEN")
        account = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "").strip()
        if not token or not account:
            return None
        model = os.environ.get("FROXY_CLOUDFLARE_IMAGE_MODEL", "@cf/black-forest-labs/flux-1-schnell")
        response = self.session.post(
            f"https://api.cloudflare.com/client/v4/accounts/{account}/ai/run/{quote(model, safe='@/-')} ".strip(),
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"prompt": prompt, "width": width, "height": height, "num_steps": 4},
            timeout=(8, 120),
        )
        if response.status_code >= 400:
            raise GatewayError(f"Cloudflare görsel HTTP {response.status_code}")
        content_type = response.headers.get("Content-Type", "")
        if content_type.startswith("image/"):
            return self._bytes_image(response.content, content_type, "cloudflare", model)
        try:
            payload = response.json()
            image = (payload.get("result") or {}).get("image")
            if image:
                return {"image_url": f"data:image/png;base64,{image}", "provider": "cloudflare", "model": model}
        except ValueError:
            pass
        raise GatewayError("Cloudflare görsel yanıtı okunamadı")

    def _image_runware(self, prompt: str, width: int, height: int) -> dict[str, Any] | None:
        key = _first_key("RUNWARE_API_KEY", "RUNWARE_API_KEYS")
        if not key:
            return None
        model = os.environ.get("FROXY_RUNWARE_IMAGE_MODEL", "bfl:5@1")
        width = max(512, min(1024, int(round(width / 64.0) * 64)))
        height = max(512, min(1024, int(round(height / 64.0) * 64)))
        task_id = f"froxy-{int(time.time())}-{threading.get_ident()}"
        response = self.session.post(
            "https://api.runware.ai/v1",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json=[{
                "taskType": "imageInference",
                "taskUUID": task_id,
                "model": model,
                "positivePrompt": prompt,
                "width": width,
                "height": height,
                "steps": 4,
                "numberResults": 1,
                "outputType": "URL",
            }],
            timeout=(8, 120),
        )
        if response.status_code >= 400:
            raise GatewayError(f"Runware görsel HTTP {response.status_code}")
        try:
            payload = response.json()
        except ValueError as exc:
            raise GatewayError("Runware görsel yanıtı okunamadı") from exc
        rows = payload.get("data", []) if isinstance(payload, dict) else payload
        first = rows[0] if isinstance(rows, list) and rows else {}
        if first.get("error") or first.get("errorMessage"):
            raise GatewayError(str(first.get("errorMessage") or first.get("error"))[:180])
        url = first.get("imageURL") or first.get("imageUrl")
        if not url and isinstance(first.get("images"), list) and first["images"]:
            url = first["images"][0]
        if not url:
            raise GatewayError("Runware boş görsel yanıtı verdi")
        return {"image_url": url, "provider": "runware", "model": model}

    def _image_pollinations(self, prompt: str, width: int, height: int) -> dict[str, Any] | None:
        key = _first_key("POLLINATIONS_API_KEY", "POLLINATIONS_KEY")
        if not key:
            return None
        model = os.environ.get("FROXY_POLLINATIONS_MODEL", "flux")
        url = f"https://gen.pollinations.ai/image/{quote(prompt, safe='')}"
        response = self.session.get(
            url,
            params={"model": model, "width": width, "height": height, "nologo": "true", "key": key},
            timeout=(8, 120),
        )
        if response.status_code >= 400:
            raise GatewayError(f"Pollinations görsel HTTP {response.status_code}")
        return self._bytes_image(response.content, response.headers.get("Content-Type", "image/jpeg"), "pollinations", model)

    @staticmethod
    def _bytes_image(content: bytes, content_type: str, provider: str, model: str) -> dict[str, Any]:
        if not content or len(content) > 700_000:
            raise GatewayError("Görsel çıktısı kalıcı kayıt sınırını aştı")
        mime = content_type.split(";", 1)[0] if content_type.startswith("image/") else "image/jpeg"
        encoded = base64.b64encode(content).decode("ascii")
        return {"image_url": f"data:{mime};base64,{encoded}", "provider": provider, "model": model}

    def _decode_image_response(self, response: requests.Response, provider: str, model: str) -> dict[str, Any]:
        if response.status_code >= 400:
            raise GatewayError(f"{provider} görsel HTTP {response.status_code}")
        try:
            payload = response.json()
        except ValueError as exc:
            raise GatewayError(f"{provider} görsel yanıtı okunamadı") from exc
        data = payload.get("data") or []
        if not data:
            raise GatewayError(f"{provider} boş görsel yanıtı verdi")
        first = data[0]
        if first.get("url"):
            return {"image_url": first["url"], "provider": provider, "model": model}
        encoded = first.get("b64_json") or first.get("b64")
        if encoded:
            if len(encoded) > 950_000:
                raise GatewayError("Görsel çıktısı kalıcı kayıt sınırını aştı")
            return {"image_url": f"data:image/png;base64,{encoded}", "provider": provider, "model": model}
        raise GatewayError(f"{provider} görsel URL'si döndürmedi")

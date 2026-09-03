"""Compact multi-provider inference gateway for the Froxy Mini App."""

from __future__ import annotations

import base64
import json
import math
import os
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from io import BytesIO
from typing import Any, Iterable
from urllib.parse import quote, urlparse

import requests
from PIL import Image


class GatewayError(RuntimeError):
    def __init__(self, message: str, status_code: Any = None):
        super().__init__(message)
        self.status_code = status_code


PROVIDER_LOGOS = {
    "froxy": "assets/froxy_logo.png",
    "openai": "assets/provider_openai.svg",
    "anthropic": "assets/provider_anthropic.svg",
    "google": "assets/provider_google.svg",
    "gemini": "assets/provider_google.svg",
    "meta": "assets/provider_meta.svg",
    "groq": "assets/provider_groq.svg",
    "nvidia": "assets/provider_nvidia.svg",
    "together": "assets/provider_together.svg",
    "cerebras": "assets/provider_cerebras.svg",
    "sambanova": "assets/provider_sambanova.svg",
    "openrouter": "assets/provider_openrouter.svg",
    "cloudflare": "assets/provider_cloudflare.svg",
    "huggingface": "assets/provider_huggingface.svg",
    "aimlapi": "assets/provider_aimlapi.svg",
    "runware": "assets/provider_runware.svg",
    "pollinations": "assets/provider_pollinations.svg",
    "mistral": "assets/provider_mistral.svg",
    "xai": "assets/provider_xai.svg",
    "deepseek": "assets/provider_deepseek.svg",
    "stability": "assets/provider_stability.svg",
    "modal": "assets/provider_modal.svg",
}


def _model_brand(provider_slug: str, model_id: str, name: str) -> str:
    value = f"{model_id} {name}".lower()
    if "anthropic" in value or "claude" in value:
        return "anthropic"
    if "openai" in value or "gpt-" in value or "o1-" in value or "o3-" in value:
        return "openai"
    if "google" in value or "gemini" in value or "gemma" in value:
        return "google"
    if "meta-llama" in value or "llama" in value:
        return "meta"
    return provider_slug if provider_slug in PROVIDER_LOGOS else ""


def _first_key(*names: str) -> str:
    keys = _all_keys(*names)
    return keys[0] if keys else ""


def _all_keys(*names: str) -> list[str]:
    """Return de-duplicated credentials without ever exposing them publicly."""
    result: list[str] = []
    for name in names:
        raw = os.environ.get(name, "").strip()
        if not raw:
            continue
        for candidate in raw.replace("\r", "\n").replace(",", "\n").splitlines():
            value = candidate.strip()
            if value and value not in result:
                result.append(value)
    return result


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

    @property
    def keys(self) -> list[str]:
        return _all_keys(*self.key_names)


class FroxyGateway:
    CATALOG_TTL = 15 * 60

    def __init__(self, session: requests.Session | None = None):
        self.session = session or requests.Session()
        self._lock = threading.RLock()
        self._catalog: list[dict[str, Any]] = []
        self._models: dict[str, dict[str, Any]] = {}
        self._refreshed_at = 0.0
        self._provider_status: dict[str, dict[str, Any]] = {}
        self._key_indexes: dict[str, int] = {}
        self._runtime_health: dict[str, dict[str, Any]] = {}

    def _ordered_keys(self, provider: Provider) -> list[str]:
        keys = provider.keys
        if len(keys) < 2:
            return keys
        with self._lock:
            start = self._key_indexes.get(provider.slug, 0) % len(keys)
            self._key_indexes[provider.slug] = (start + 1) % len(keys)
        return keys[start:] + keys[:start]

    def _record_runtime(self, slug: str, ok: bool, *, status: Any = None, latency_ms: int = 0) -> None:
        now = int(time.time())
        with self._lock:
            previous = self._runtime_health.get(slug, {})
            failures = 0 if ok else int(previous.get("consecutive_failures", 0) or 0) + 1
            cooldown = 0
            if not ok:
                if status in {401, 403}:
                    cooldown = now + 600
                elif status == 429:
                    cooldown = now + 45
                elif failures >= 2:
                    cooldown = now + min(300, 20 * failures)
            self._runtime_health[slug] = {
                "runtime_healthy": bool(ok),
                "last_runtime_status": status or ("ok" if ok else "error"),
                "last_runtime_at": now,
                "last_runtime_latency_ms": max(0, int(latency_ms or 0)),
                "consecutive_failures": failures,
                "cooldown_until": cooldown,
            }

    def _provider_available(self, slug: str) -> bool:
        with self._lock:
            state = self._runtime_health.get(slug, {})
        return int(state.get("cooldown_until", 0) or 0) <= int(time.time())

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
            Provider("gemini", "Google Gemini", "https://generativelanguage.googleapis.com/v1beta/openai", ("GEMINI_API_KEY", "GEMINI_API_KEYS", "GOOGLE_API_KEY")),
            Provider("openai", "OpenAI", openai_base, ("OPENAI_CHAT_KEY", "OPENAI_API_KEY")),
            Provider("aimlapi", "AI/ML API", "https://api.aimlapi.com/v1", ("AIMLAPI_KEY",)),
            Provider("huggingface", "Hugging Face", "https://router.huggingface.co/v1", ("HF_TOKEN", "HUGGINGFACE_API_KEY")),
            Provider("mistral", "Mistral AI", "https://api.mistral.ai/v1", ("MISTRAL_API_KEY",)),
            Provider("fireworks", "Fireworks AI", "https://api.fireworks.ai/inference/v1", ("FIREWORKS_API_KEY",)),
            Provider("xai", "xAI", "https://api.x.ai/v1", ("XAI_API_KEY",)),
            Provider("deepseek", "DeepSeek", "https://api.deepseek.com", ("DEEPSEEK_API_KEY",)),
            Provider("chutes", "Chutes", "https://llm.chutes.ai/v1", ("CHUTES_API_KEY",)),
            Provider("evolink", "Evolink", "https://direct.evolink.ai/v1", ("EVOLINK_API_KEY", "EVOLINK_API_KEYS")),
            Provider("hcnsec", "HCNSEC", "https://api.hcnsec.cn/v1", ("HCNSEC_API_KEY", "HCNSEC_API_KEYS")),
            Provider("freemodel", "FreeModel", "https://api.freemodel.dev/v1", ("FREEMODEL_API_KEY", "FREEMODEL_API_KEYS")),
            Provider("shenfeng", "Shenfeng", "https://api.shenfengwl.fun/v1", ("SHENFENG_GEMINI_KEY", "SHENFENG_OPENAI_KEY")),
            Provider("guicore", "GuiCore", os.environ.get("GUICORE_BASE_URL", "https://api.guicore.com/v1").rstrip("/"), ("GUICORE_CLAUDE_KEY", "GUICORE_GEMINI_KEY")),
            Provider("pollinations", "Pollinations", "https://gen.pollinations.ai/v1", ("POLLINATIONS_API_KEY", "POLLINATIONS_API_KEYS", "POLLINATIONS_KEY")),
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
    def _headers(provider: Provider, key: str | None = None) -> dict[str, str]:
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        headers[provider.auth_header] = f"{provider.auth_prefix}{key or provider.key}"
        if provider.slug == "openrouter":
            headers["HTTP-Referer"] = os.environ.get("FROXY_PUBLIC_URL", "https://froxyai.com")
            headers["X-Title"] = "Froxy AI Telegram"
        return headers

    def _fetch_provider(self, provider: Provider) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        started = time.time()
        last_status: Any = "unreachable"
        for key in self._ordered_keys(provider):
            try:
                response = self.session.get(
                    f"{provider.base_url}{provider.model_path}",
                    headers=self._headers(provider, key),
                    timeout=(4, 10),
                )
                last_status = response.status_code
                if response.status_code != 200:
                    response.close()
                    if response.status_code in {401, 403, 429}:
                        continue
                    break
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
                last_status = "unreachable"
                continue
        return [], {
            "provider": provider.slug,
            "healthy": False,
            "status": last_status,
            "models": 0,
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
        # Together's /models endpoint reports token prices per million tokens,
        # while the OpenAI-compatible providers expose dollars per token. Keep
        # one canonical internal unit so the public credit estimates and the
        # reservation/settlement path cannot overcharge Together models by 1e6.
        if provider.slug == "together":
            prompt /= 1_000_000
            completion /= 1_000_000
            if image >= 0:
                image /= 1_000_000
        known_pricing = prompt >= 0 and completion >= 0
        is_free = (
            model_id.endswith(":free")
            or (known_pricing and prompt == 0 and completion == 0)
        )
        architecture = raw.get("architecture") if isinstance(raw.get("architecture"), dict) else {}
        modality = str(architecture.get("modality") or raw.get("modality") or "text->text")
        public_id = f"{provider.slug}/{model_id}"
        name = str(raw.get("name") or raw.get("display_name") or model_id)
        brand = _model_brand(provider.slug, model_id, name)
        context = int(_float(raw.get("context_length", raw.get("context_window", 0)), 0))
        return {
            "id": public_id,
            "provider_model_id": model_id,
            "name": name,
            "provider": provider.slug,
            "provider_label": provider.label,
            "provider_logo": PROVIDER_LOGOS.get(brand, ""),
            "capabilities": ["chat", *( ["vision"] if "image" in modality.lower() else [])],
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
            "embed-", "rerank", "audio-preview", "transcribe", "orpheus",
        )
        if any(fragment in model_id for fragment in denied):
            return False
        modality = str(model.get("modality") or "text->text").lower()
        return "text" in modality.rsplit("->", 1)[-1]

    def refresh_catalog(self, force: bool = False) -> list[dict[str, Any]]:
        with self._lock:
            if self._catalog and not force and time.time() - self._refreshed_at < self.CATALOG_TTL:
                return list(self._catalog)

        providers = self.providers()
        configured = [provider for provider in providers if provider.key]
        all_models: list[dict[str, Any]] = []
        statuses: dict[str, dict[str, Any]] = {
            provider.slug: {
                "provider": provider.slug,
                "healthy": False,
                "configured": bool(provider.key),
                "models": 0,
                "status": "not_configured" if not provider.key else "checking",
            }
            for provider in providers
        }
        with ThreadPoolExecutor(max_workers=min(6, max(1, len(configured)))) as pool:
            futures = {pool.submit(self._fetch_provider, provider): provider for provider in configured}
            for future in as_completed(futures):
                models, status = future.result()
                all_models.extend(models)
                status["configured"] = True
                statuses[status["provider"]] = status

        if not all_models:
            # A static card is not an active model. Hiding unavailable models
            # prevents users spending quota/credits on an impossible request.
            visible: list[dict[str, Any]] = []
            models_by_id: dict[str, dict[str, Any]] = {}
            with self._lock:
                self._catalog = visible
                self._models = models_by_id
                self._provider_status = statuses
                self._refreshed_at = time.time()
            return list(visible)

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

    @staticmethod
    def _default_fallback_models() -> list[dict[str, Any]]:
        return [
            {
                "id": "froxy-fast",
                "provider_model_id": "froxy-fast",
                "name": "Froxy Hızlı",
                "provider": "froxy",
                "provider_label": "Froxy Modelleri",
                "provider_logo": PROVIDER_LOGOS.get("froxy", ""),
                "capabilities": ["chat"],
                "context_length": 128000,
                "modality": "text->text",
                "supports_vision": False,
                "is_free": True,
                "known_pricing": True,
                "prompt_usd_per_token": 0.0,
                "completion_usd_per_token": 0.0,
                "is_froxy": True,
                "description": "Günlük ücretsiz kota ile kullanılabilen ultra hızlı Froxy modeli.",
            },
            {
                "id": "froxy-smart",
                "provider_model_id": "froxy-smart",
                "name": "Froxy Akıllı",
                "provider": "froxy",
                "provider_label": "Froxy Modelleri",
                "provider_logo": PROVIDER_LOGOS.get("froxy", ""),
                "capabilities": ["chat", "vision"],
                "context_length": 128000,
                "modality": "text+image->text",
                "supports_vision": True,
                "is_free": True,
                "known_pricing": True,
                "prompt_usd_per_token": 0.0,
                "completion_usd_per_token": 0.0,
                "is_froxy": True,
                "description": "Gelişmiş akıl yürütme ve analiz yeteneğine sahip ücretsiz akıllı model.",
            },
            {
                "id": "openai/gpt-4o",
                "provider_model_id": "gpt-4o",
                "name": "GPT-4o (Omni)",
                "provider": "openai",
                "provider_label": "OpenAI",
                "provider_logo": PROVIDER_LOGOS.get("openai", ""),
                "capabilities": ["chat", "vision"],
                "context_length": 128000,
                "modality": "text+image->text",
                "supports_vision": True,
                "is_free": False,
                "known_pricing": True,
                "prompt_usd_per_token": 2.5e-06,
                "completion_usd_per_token": 1e-05,
                "estimated_1k_credits": 125,
                "is_froxy": False,
            },
            {
                "id": "anthropic/claude-3-5-sonnet",
                "provider_model_id": "claude-3-5-sonnet-20241022",
                "name": "Claude 3.5 Sonnet",
                "provider": "anthropic",
                "provider_label": "Anthropic",
                "provider_logo": PROVIDER_LOGOS.get("anthropic", ""),
                "capabilities": ["chat", "vision"],
                "context_length": 200000,
                "modality": "text+image->text",
                "supports_vision": True,
                "is_free": False,
                "known_pricing": True,
                "prompt_usd_per_token": 3e-06,
                "completion_usd_per_token": 1.5e-05,
                "estimated_1k_credits": 150,
                "is_froxy": False,
            },
            {
                "id": "google/gemini-1.5-pro",
                "provider_model_id": "gemini-1.5-pro",
                "name": "Google Gemini 1.5 Pro",
                "provider": "google",
                "provider_label": "Google",
                "provider_logo": PROVIDER_LOGOS.get("google", ""),
                "capabilities": ["chat", "vision"],
                "context_length": 1000000,
                "modality": "text+image->text",
                "supports_vision": True,
                "is_free": False,
                "known_pricing": True,
                "prompt_usd_per_token": 1.25e-06,
                "completion_usd_per_token": 5e-06,
                "estimated_1k_credits": 90,
                "is_froxy": False,
            },
            {
                "id": "meta/llama-3.3-70b",
                "provider_model_id": "llama-3.3-70b-instruct",
                "name": "Meta Llama 3.3 70B",
                "provider": "meta",
                "provider_label": "Meta AI",
                "provider_logo": PROVIDER_LOGOS.get("meta", ""),
                "capabilities": ["chat"],
                "context_length": 128000,
                "modality": "text->text",
                "supports_vision": False,
                "is_free": False,
                "known_pricing": True,
                "prompt_usd_per_token": 5.9e-07,
                "completion_usd_per_token": 7.9e-07,
                "estimated_1k_credits": 45,
                "is_froxy": False,
            }
        ]

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
            if alias_id == "froxy-vision" and target and not target.get("supports_vision"):
                target = None
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
            fallback_pool = candidates
            if alias_id == "froxy-vision":
                fallback_pool = [m for m in candidates if m.get("supports_vision")]
            fallbacks = [m["id"] for m in fallback_pool if m["id"] != target["id"]][:4]
            selected.append({
                "id": alias_id,
                "name": label,
                "icon": icon,
                "provider": "froxy",
                "provider_label": "Froxy Modelleri",
                "provider_logo": PROVIDER_LOGOS["froxy"],
                "capabilities": ["chat", *( ["vision"] if target.get("supports_vision") else [])],
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
            statuses = json.loads(json.dumps(self._provider_status))
            runtime = json.loads(json.dumps(self._runtime_health))
        image_providers = {row["provider"] for row in self.image_models() if row.get("active")}
        for slug, status in statuses.items():
            status["capabilities"] = ["chat", *( ["image"] if slug in image_providers else [])]
            status["provider_logo"] = PROVIDER_LOGOS.get(slug, "")
            if slug in runtime:
                status.update(runtime[slug])
                if int(runtime[slug].get("cooldown_until", 0) or 0) > int(time.time()):
                    status["healthy"] = False
        for slug in image_providers - set(statuses):
            statuses[slug] = {"provider": slug, "healthy": self._provider_available(slug), "configured": True, "models": 0, "capabilities": ["image"], "provider_logo": PROVIDER_LOGOS.get(slug, ""), **runtime.get(slug, {})}
        return statuses

    def public_catalog(self) -> dict[str, Any]:
        rows = self.refresh_catalog()
        public = []
        for row in rows:
            if row.get("is_froxy"):
                if not any(self._provider_available(target.get("provider", "")) for target in self._target_candidates(row)):
                    continue
            elif not self._provider_available(str(row.get("provider") or "")):
                continue
            item = {key: value for key, value in row.items() if key not in {
                "target_public_id", "fallback_targets", "provider_model_id",
                "prompt_usd_per_token", "completion_usd_per_token", "image_usd",
            }}
            item["estimated_1k_credits"] = self.estimate_credits(row, 600, 400)
            public.append(item)
        return {
            "models": public,
            "count": len(public),
            # This is the only number appropriate for the Mini App: every
            # listed model is both healthy and selectable at this moment.
            "active_model_count": len(public),
            "active_provider_count": sum(1 for slug, row in self._provider_status.items() if row.get("healthy") and self._provider_available(slug)),
            # Kept for operational monitoring; this includes provider catalog
            # entries intentionally hidden when their price is not reliable.
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
            if not self._provider_available(provider.slug):
                continue
            for key in self._ordered_keys(provider):
                started = time.time()
                emitted = False
                response = None
                try:
                    payload = {
                        "model": target["provider_model_id"],
                        "messages": messages,
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                        "stream": True,
                    }
                    provider_model_id = str(target["provider_model_id"]).lower()
                    if provider.slug == "groq" and "qwen" in provider_model_id:
                        payload["reasoning_effort"] = "none"
                    elif provider.slug == "groq" and "gpt-oss" in provider_model_id:
                        payload["reasoning_effort"] = "low"
                        payload["include_reasoning"] = False
                    response = self.session.post(
                        f"{provider.base_url}{provider.chat_path}",
                        headers=self._headers(provider, key),
                        json=payload,
                        stream=True,
                        timeout=(8, 100),
                    )
                    if response.status_code >= 400:
                        status = response.status_code
                        last_error = f"{provider.label} HTTP {status}"
                        self._record_runtime(provider.slug, False, status=status, latency_ms=int((time.time() - started) * 1000))
                        response.close()
                        if status in {401, 403, 408, 409, 429} or status >= 500:
                            continue
                        break
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
                        if isinstance(content, list):
                            content = "".join(
                                str(part.get("text") or "")
                                for part in content
                                if isinstance(part, dict) and part.get("type") in {"text", "output_text"}
                            )
                        if isinstance(content, str) and content:
                            emitted = True
                            yield {"type": "delta", "content": content}
                    response.close()
                    if emitted:
                        self._record_runtime(provider.slug, True, status=200, latency_ms=int((time.time() - started) * 1000))
                        yield {
                            "type": "provider_done",
                            "usage": usage,
                            "provider": provider.slug,
                            "provider_model": target["provider_model_id"],
                        }
                        return
                    last_error = f"{provider.label} boş yanıt verdi"
                    self._record_runtime(provider.slug, False, status="empty", latency_ms=int((time.time() - started) * 1000))
                except GatewayError as exc:
                    last_error = str(exc)
                    self._record_runtime(provider.slug, False, status="gateway_error", latency_ms=int((time.time() - started) * 1000))
                except requests.RequestException:
                    last_error = f"{provider.label} bağlantı hatası"
                    self._record_runtime(provider.slug, False, status="connection_error", latency_ms=int((time.time() - started) * 1000))
                finally:
                    if response is not None:
                        response.close()
                # Once bytes reached the user, switching providers would append
                # a second answer to a partial first answer. Fail and refund.
                if emitted:
                    raise GatewayError(last_error)
        raise GatewayError(last_error)

    def image_credit_cost(self) -> int:
        usd = max(0.0001, _float(os.environ.get("FROXY_IMAGE_COST_USD"), 0.0019))
        usd_try, multiplier, credit_try = self._pricing_config()
        return max(1, int(math.ceil((usd * usd_try * multiplier) / credit_try)))

    def image_models(self) -> list[dict[str, Any]]:
        cost = self.image_credit_cost()
        account = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "").strip()
        configured = {
            "openai": bool(_all_keys("OPENAI_IMAGE_KEYS", "OPENAI_IMAGE_KEY", "OPENAI_API_KEY")),
            "together": bool(_all_keys("TOGETHER_API_KEYS", "TOGETHER_API_KEY")),
            "cloudflare": bool(account and _all_keys("CLOUDFLARE_API_TOKEN")),
            "runware": bool(_all_keys("RUNWARE_API_KEYS", "RUNWARE_API_KEY")),
            "pollinations": bool(_all_keys("POLLINATIONS_API_KEYS", "POLLINATIONS_API_KEY", "POLLINATIONS_KEY")),
            "aimlapi": bool(_all_keys("AIMLAPI_KEY")),
            "stability": bool(_all_keys("STABILITY_API_KEYS", "STABILITY_API_KEY")),
            "google": bool(_all_keys("GEMINI_API_KEYS", "GEMINI_API_KEY", "GOOGLE_API_KEY")),
            "evolink": bool(_all_keys("EVOLINK_API_KEYS", "EVOLINK_API_KEY")),
            "imagegpt": bool(_all_keys("IMAGEGPT_API_KEY")),
            "modal": bool(os.environ.get("MODAL_IMAGE_ENDPOINT", "").strip()),
        }
        definitions = [
            ("openai-gpt-image", "OpenAI GPT Image", "openai", os.environ.get("FROXY_OPENAI_IMAGE_MODEL", "gpt-image-1"), cost),
            ("openai-dall-e-3", "OpenAI DALL-E 3", "openai", "dall-e-3", cost),
            ("together-flux-schnell", "Together FLUX.1 Schnell", "together", "black-forest-labs/FLUX.1-schnell", 40),
            ("together-juggernaut-flux", "Together Juggernaut FLUX", "together", "Rundiffusion/Juggernaut-Lightning-Flux", 30),
            ("together-qwen-image", "Together Qwen Image", "together", "Qwen/Qwen-Image", 90),
            ("together-flux2-dev", "Together FLUX.2 Dev", "together", "black-forest-labs/FLUX.2-dev", 220),
            ("together-imagen4-fast", "Together Imagen 4 Fast", "together", "google/imagen-4.0-fast", 300),
            ("together-flux-kontext-pro", "Together FLUX.1 Kontext Pro", "together", "black-forest-labs/FLUX.1-kontext-pro", 600),
            ("together-flux2-pro", "Together FLUX.2 Pro", "together", "black-forest-labs/FLUX.2-pro", 450),
            ("together-gemini-flash-image", "Together Gemini Flash Image", "together", "google/flash-image-2.5", 600),
            ("together-qwen-image-pro", "Together Qwen Image 2 Pro", "together", "Qwen/Qwen-Image-2.0-Pro", 1000),
            ("together-gemini-pro-image", "Together Gemini 3 Pro Image", "together", "google/gemini-3-pro-image", 1800),
            ("cf-sdxl", "Cloudflare SDXL", "cloudflare", "@cf/stabilityai/stable-diffusion-xl-base-1.0", cost),
            ("cf-sdxl-lightning", "Cloudflare SDXL Lightning", "cloudflare", "@cf/bytedance/stable-diffusion-xl-lightning", cost),
            ("cf-dreamshaper-lcm", "Cloudflare DreamShaper 8 LCM", "cloudflare", "@cf/lykon/dreamshaper-8-lcm", cost),
            ("cf-flux-klein", "Cloudflare FLUX.2 Klein", "cloudflare", "@cf/black-forest-labs/flux-2-klein-4b", cost),
            ("runware-flux", "Runware FLUX", "runware", "bfl:5@1", cost),
            ("runware-sdxl", "Runware SDXL", "runware", "runware:101@1", cost),
            ("pollinations-zimage", "Pollinations Z-Image", "pollinations", "zimage", cost),
            ("pollinations-flux", "Pollinations FLUX", "pollinations", "flux", cost),
            ("pollinations-gptimage", "Pollinations GPT Image", "pollinations", "gptimage", cost),
            ("pollinations-nanobanana", "Pollinations Nano Banana", "pollinations", "nanobanana", cost),
            ("aiml-flux", "AI/ML API FLUX", "aimlapi", "flux-pro", cost),
            ("aiml-nano", "AI/ML API Nano Banana", "aimlapi", "google/gemini-3.1-flash-image", cost),
            ("stability-core", "Stability Core", "stability", "core", 2520),
            ("stability-ultra", "Stability Ultra", "stability", "ultra", 6720),
            ("gemini-2.5-flash-image", "Gemini 2.5 Flash Image", "google", "gemini-2.5-flash-image", 300),
            ("gemini-3.1-flash-image", "Gemini 3.1 Flash Image", "google", "gemini-3.1-flash-image", 600),
            ("gemini-3-pro-image", "Gemini 3 Pro Image", "google", "gemini-3-pro-image", 1800),
            ("imagen-4-fast", "Google Imagen 4 Fast", "google", "imagen-4.0-fast-generate-001", 300),
            ("imagen-4", "Google Imagen 4", "google", "imagen-4.0-generate-001", 900),
            ("imagen-4-ultra", "Google Imagen 4 Ultra", "google", "imagen-4.0-ultra-generate-001", 1800),
            ("imagegpt-free", "ImageGPT FLUX Schnell", "imagegpt", "FLUX-SCHNELL", 15),
            ("modal-sdxl", "Modal GPU SDXL", "modal", "modal-sdxl", cost),
            ("modal-local-sd", "Modal Local SD", "modal", "modal-local-sd", cost),
            ("modal-cloud-gpu", "Modal Cloud GPU", "modal", "modal-cloud-gpu", cost),
            ("modal-dreamshaper", "Modal DreamShaper", "modal", "modal-dreamshaper", cost),
            ("modal-realisticvision", "Modal Realistic Vision", "modal", "modal-realisticvision", cost),
            ("modal-a1111-compatible", "Modal A1111 Compatible", "modal", "modal-a1111-compatible", cost),
            ("evolink-img-z-image-turbo", "EvoLink Z-Image Turbo", "evolink", "z-image-turbo", 30),
            ("evolink-img-wan2.5-text-to-image", "EvoLink Wan 2.5", "evolink", "wan2.5-text-to-image", 120),
            ("evolink-img-gemini-3.1-flash-lite-image", "EvoLink Gemini 3.1 Flash Lite Image", "evolink", "gemini-3.1-flash-lite-image", 180),
            ("evolink-img-gemini-3.1-flash-image", "EvoLink Gemini 3.1 Flash Image", "evolink", "gemini-3.1-flash-image", 300),
            ("evolink-img-gpt-image-2", "EvoLink GPT Image 2", "evolink", "gpt-image-2", 300),
            ("evolink-img-gpt-image-1.5", "EvoLink GPT Image 1.5", "evolink", "gpt-image-1.5", 250),
            ("evolink-img-doubao-seedream-5.0-lite", "EvoLink Seedream 5 Lite", "evolink", "doubao-seedream-5.0-lite", 220),
            ("evolink-img-doubao-seedream-4.5", "EvoLink Seedream 4.5", "evolink", "doubao-seedream-4.5", 240),
            ("evolink-img-nano-banana-2-lite-beta", "EvoLink Nano Banana 2 Lite", "evolink", "nano-banana-2-lite-beta", 150),
        ]
        return [{
            "id": public_id,
            "name": name,
            "provider": provider,
            "provider_label": {"google": "Google", "aimlapi": "AI/ML API", "imagegpt": "ImageGPT"}.get(provider, provider.title()),
            "provider_logo": PROVIDER_LOGOS.get(provider, ""),
            "provider_model": model,
            "capabilities": ["text-to-image"],
            "estimated_credits": estimated,
            "active": bool(configured.get(provider) and self._provider_available(provider)),
        } for public_id, name, provider, model, estimated in definitions]

    def get_image_model(self, public_id: str) -> dict[str, Any]:
        model = next((row for row in self.image_models() if row["id"] == str(public_id) and row.get("active")), None)
        if not model:
            raise GatewayError("Görsel modeli aktif değil")
        return model

    @staticmethod
    def _image_key_names(provider: str) -> tuple[str, ...]:
        return {
            "openai": ("OPENAI_IMAGE_KEYS", "OPENAI_IMAGE_KEY", "OPENAI_API_KEY"),
            "together": ("TOGETHER_API_KEYS", "TOGETHER_API_KEY"),
            "cloudflare": ("CLOUDFLARE_API_TOKEN",),
            "runware": ("RUNWARE_API_KEYS", "RUNWARE_API_KEY"),
            "pollinations": ("POLLINATIONS_API_KEYS", "POLLINATIONS_API_KEY", "POLLINATIONS_KEY"),
            "aimlapi": ("AIMLAPI_KEY",),
            "stability": ("STABILITY_API_KEYS", "STABILITY_API_KEY"),
            "google": ("GEMINI_API_KEYS", "GEMINI_API_KEY", "GOOGLE_API_KEY"),
            "evolink": ("EVOLINK_API_KEYS", "EVOLINK_API_KEY"),
            "imagegpt": ("IMAGEGPT_API_KEY",),
            "modal": ("MODAL_IMAGE_AUTH_TOKEN", "MODAL_AUTH_TOKEN"),
        }.get(provider, ())

    def _ordered_image_keys(self, provider: str) -> list[str | None]:
        names = self._image_key_names(provider)
        keys = _all_keys(*names)
        if provider == "modal" and not keys:
            return [None]
        if len(keys) < 2:
            return list(keys)
        synthetic = Provider(provider, provider, "", names)
        return self._ordered_keys(synthetic)

    def generate_image(self, prompt: str, width: int = 512, height: int = 512, model_id: str | None = None) -> dict[str, Any]:
        operations = {
            "openai": self._image_openai,
            "together": self._image_together,
            "cloudflare": self._image_cloudflare,
            "runware": self._image_runware,
            "pollinations": self._image_pollinations,
            "aimlapi": self._image_aimlapi,
            "stability": self._image_stability,
            "google": self._image_google,
            "evolink": self._image_evolink,
            "imagegpt": self._image_imagegpt,
            "modal": self._image_modal,
        }
        active_models = [row for row in self.image_models() if row.get("active")]
        if model_id:
            selected = self.get_image_model(model_id)
            ceiling = int(selected.get("estimated_credits") or self.image_credit_cost())
            active_models = [row for row in active_models if row["id"] == selected["id"] or int(row.get("estimated_credits") or 0) <= ceiling]
            active_models.sort(key=lambda row: (0 if row["id"] == selected["id"] else 1, int(row.get("estimated_credits") or 0)))
        errors = []
        for image_model in active_models:
            if not self._provider_available(image_model["provider"]):
                continue
            operation = operations[image_model["provider"]]
            for key in self._ordered_image_keys(image_model["provider"]):
                started = time.time()
                try:
                    result = operation(prompt, width, height, image_model.get("provider_model"), key)
                    if result:
                        result["estimated_credits"] = int(image_model.get("estimated_credits") or self.image_credit_cost())
                        self._record_runtime(image_model["provider"], True, status=200, latency_ms=int((time.time() - started) * 1000))
                        return result
                except GatewayError as exc:
                    errors.append(str(exc))
                    status = getattr(exc, "status_code", "gateway_error")
                    self._record_runtime(image_model["provider"], False, status=status, latency_ms=int((time.time() - started) * 1000))
                except requests.RequestException as exc:
                    errors.append(f"{operation.__name__} bağlantı hatası: {type(exc).__name__}")
                    self._record_runtime(image_model["provider"], False, status="connection_error", latency_ms=int((time.time() - started) * 1000))
                except (ValueError, TypeError, KeyError) as exc:
                    errors.append(f"{operation.__name__} geçersiz yanıtı: {type(exc).__name__}")
                    self._record_runtime(image_model["provider"], False, status="invalid_response", latency_ms=int((time.time() - started) * 1000))
        raise GatewayError(errors[-1] if errors else "Çalışan görsel sağlayıcısı bulunamadı")

    def _image_openai(self, prompt: str, width: int, height: int, model_override: str | None = None, key_override: str | None = None) -> dict[str, Any] | None:
        key = key_override or _first_key("OPENAI_IMAGE_KEYS", "OPENAI_IMAGE_KEY", "OPENAI_API_KEY")
        if not key:
            return None
        base = os.environ.get("OPENAI_IMAGE_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        model = model_override or os.environ.get("FROXY_OPENAI_IMAGE_MODEL", "gpt-image-1")
        if width == height:
            size = "1024x1024"
        elif width > height:
            size = "1792x1024" if model == "dall-e-3" else "1536x1024"
        else:
            size = "1024x1792" if model == "dall-e-3" else "1024x1536"
        response = self.session.post(
            f"{base}/images/generations",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": model, "prompt": prompt, "size": size, "n": 1},
            timeout=(8, 120),
        )
        return self._decode_image_response(response, "openai", model)

    def _image_together(self, prompt: str, width: int, height: int, model_override: str | None = None, key_override: str | None = None) -> dict[str, Any] | None:
        key = key_override or _first_key("TOGETHER_API_KEYS", "TOGETHER_API_KEY")
        if not key:
            return None
        model = model_override or os.environ.get("FROXY_TOGETHER_IMAGE_MODEL", "black-forest-labs/FLUX.1-schnell")
        fast_models = {"black-forest-labs/FLUX.1-schnell", "Rundiffusion/Juggernaut-Lightning-Flux"}
        body: dict[str, Any] = {"model": model, "prompt": prompt, "width": width, "height": height}
        if model in fast_models:
            body["steps"] = 4
        if model != "google/gemini-3-pro-image":
            body["n"] = 1
        response = self.session.post(
            "https://api.together.xyz/v1/images/generations",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json=body,
            timeout=(8, 120),
        )
        return self._decode_image_response(response, "together", model)

    def _image_cloudflare(self, prompt: str, width: int, height: int, model_override: str | None = None, key_override: str | None = None) -> dict[str, Any] | None:
        token = key_override or _first_key("CLOUDFLARE_API_TOKEN")
        account = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "").strip()
        if not token or not account:
            return None
        model = model_override or os.environ.get("FROXY_CLOUDFLARE_IMAGE_MODEL", "@cf/black-forest-labs/flux-1-schnell")
        body = {"prompt": prompt, "width": width, "height": height}
        if "flux" in model:
            body["steps"] = 4
        else:
            body["num_steps"] = 4 if "lightning" in model else 20
        url = f"https://api.cloudflare.com/client/v4/accounts/{account}/ai/run/{quote(model, safe='@/-')}"
        if "flux-2-klein" in model:
            response = self.session.post(
                url,
                headers={"Authorization": f"Bearer {token}", "Accept": "image/*"},
                files={"prompt": (None, prompt), "width": (None, str(width)), "height": (None, str(height))},
                timeout=(8, 120),
            )
        else:
            response = self.session.post(
                url,
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json=body,
                timeout=(8, 120),
            )
        if response.status_code >= 400:
            raise GatewayError(f"Cloudflare görsel HTTP {response.status_code}", response.status_code)
        content_type = response.headers.get("Content-Type", "")
        if content_type.startswith("image/"):
            return self._bytes_image(response.content, content_type, "cloudflare", model)
        try:
            payload = response.json()
            image = (payload.get("result") or {}).get("image")
            if image:
                return self._base64_image(image, "cloudflare", model)
        except ValueError:
            pass
        raise GatewayError("Cloudflare görsel yanıtı okunamadı")

    def _image_runware(self, prompt: str, width: int, height: int, model_override: str | None = None, key_override: str | None = None) -> dict[str, Any] | None:
        key = key_override or _first_key("RUNWARE_API_KEYS", "RUNWARE_API_KEY")
        if not key:
            return None
        model = model_override or os.environ.get("FROXY_RUNWARE_IMAGE_MODEL", "bfl:5@1")
        width = max(512, min(1024, int(round(width / 64.0) * 64)))
        height = max(512, min(1024, int(round(height / 64.0) * 64)))
        task_id = str(uuid.uuid4())
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
                "deliveryMethod": "sync",
            }],
            timeout=(8, 120),
        )
        if response.status_code >= 400:
            raise GatewayError(f"Runware görsel HTTP {response.status_code}", response.status_code)
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
        image_url = str(url)
        parsed = urlparse(image_url)
        if parsed.scheme not in {"https", "http"} or not parsed.netloc:
            raise GatewayError("Runware geçersiz görsel URL'si döndürdü")
        return {"image_url": image_url, "provider": "runware", "model": model}

    def _image_pollinations(self, prompt: str, width: int, height: int, model_override: str | None = None, key_override: str | None = None) -> dict[str, Any] | None:
        key = key_override or _first_key("POLLINATIONS_API_KEYS", "POLLINATIONS_API_KEY", "POLLINATIONS_KEY")
        if not key:
            return None
        model = model_override or os.environ.get("FROXY_POLLINATIONS_MODEL", "zimage")
        response = self.session.post(
            "https://gen.pollinations.ai/v1/images/generations",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "prompt": prompt,
                "size": f"{width}x{height}",
                "n": 1,
                "response_format": "url",
            },
            timeout=(8, 120),
        )
        return self._decode_image_response(response, "pollinations", model)

    def _image_aimlapi(self, prompt: str, width: int, height: int, model_override: str | None = None, key_override: str | None = None) -> dict[str, Any] | None:
        key = key_override or _first_key("AIMLAPI_KEY")
        if not key:
            return None
        model = model_override or "flux-pro"
        response = self.session.post(
            "https://api.aimlapi.com/v1/images/generations",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": model, "prompt": prompt, "n": 1, "size": f"{width}x{height}"},
            timeout=(8, 120),
        )
        return self._decode_image_response(response, "aimlapi", model)

    def _image_stability(self, prompt: str, width: int, height: int, model_override: str | None = None, key_override: str | None = None) -> dict[str, Any] | None:
        key = key_override or _first_key("STABILITY_API_KEYS", "STABILITY_API_KEY")
        if not key:
            return None
        model = "ultra" if model_override == "ultra" else "core"
        response = self.session.post(
            f"https://api.stability.ai/v2beta/stable-image/generate/{model}",
            headers={"Authorization": f"Bearer {key}", "Accept": "image/*"},
            files={
                "prompt": (None, prompt),
                "output_format": (None, "jpeg"),
                "aspect_ratio": (None, "16:9" if width > height else "9:16" if height > width else "1:1"),
            },
            timeout=(8, 120),
        )
        if response.status_code >= 400:
            raise GatewayError(f"Stability görsel HTTP {response.status_code}", response.status_code)
        return self._bytes_image(response.content, response.headers.get("Content-Type", ""), "stability", model)

    @staticmethod
    def _aspect_ratio(width: int, height: int) -> str:
        ratio = width / max(1, height)
        if ratio >= 1.65:
            return "16:9"
        if ratio >= 1.25:
            return "4:3"
        if ratio <= 0.62:
            return "9:16"
        if ratio <= 0.82:
            return "4:5"
        return "1:1"

    def _image_google(self, prompt: str, width: int, height: int, model_override: str | None = None, key_override: str | None = None) -> dict[str, Any] | None:
        key = key_override or _first_key("GEMINI_API_KEYS", "GEMINI_API_KEY", "GOOGLE_API_KEY")
        if not key:
            return None
        model = model_override or "gemini-3.1-flash-image"
        aspect = self._aspect_ratio(width, height)
        if model.startswith("imagen-"):
            response = self.session.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{quote(model, safe='.-')}:predict",
                headers={"x-goog-api-key": key, "Content-Type": "application/json"},
                json={"instances": [{"prompt": prompt}], "parameters": {"sampleCount": 1, "aspectRatio": aspect}},
                timeout=(8, 120),
            )
            if response.status_code >= 400:
                raise GatewayError(f"Google Imagen HTTP {response.status_code}", response.status_code)
            try:
                payload = response.json()
                prediction = (payload.get("predictions") or [{}])[0]
                encoded = prediction.get("bytesBase64Encoded") or (prediction.get("image") or {}).get("bytesBase64Encoded")
            except (ValueError, TypeError, IndexError) as exc:
                raise GatewayError("Google Imagen yanıtı okunamadı") from exc
            return self._base64_image(encoded, "google", model) if encoded else None

        response = self.session.post(
            f"https://generativelanguage.googleapis.com/v1/models/{quote(model, safe='.-')}:generateContent",
            headers={"x-goog-api-key": key, "Content-Type": "application/json"},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "responseModalities": ["Image"],
                    "responseFormat": {"image": {"aspectRatio": aspect}},
                },
            },
            timeout=(8, 120),
        )
        if response.status_code >= 400:
            raise GatewayError(f"Google görsel HTTP {response.status_code}", response.status_code)
        try:
            payload = response.json()
            parts = (((payload.get("candidates") or [{}])[0].get("content") or {}).get("parts") or [])
            image = next((part.get("inlineData") or part.get("inline_data") for part in parts if part.get("inlineData") or part.get("inline_data")), None)
            encoded = (image or {}).get("data")
        except (ValueError, TypeError, IndexError) as exc:
            raise GatewayError("Google görsel yanıtı okunamadı") from exc
        if not encoded:
            raise GatewayError("Google boş görsel yanıtı verdi")
        return self._base64_image(encoded, "google", model)

    def _image_evolink(self, prompt: str, width: int, height: int, model_override: str | None = None, key_override: str | None = None) -> dict[str, Any] | None:
        key = key_override or _first_key("EVOLINK_API_KEYS", "EVOLINK_API_KEY")
        if not key:
            return None
        model = model_override or "z-image-turbo"
        aspect = self._aspect_ratio(width, height)
        body: dict[str, Any] = {"model": model, "prompt": prompt, "size": aspect, "n": 1}
        if model == "wan2.5-text-to-image":
            body["size"] = f"{max(512, width)}x{max(512, height)}"
        elif model.startswith("doubao-seedream-"):
            body["quality"] = "2K"
        elif model.startswith(("gemini-3.1-flash", "nano-banana-2-lite")):
            body["quality"] = "1K"
        elif model.startswith("gpt-image-"):
            body["quality"] = "low"
        created_response = self.session.post(
            "https://api.evolink.ai/v1/images/generations",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json", "Accept": "application/json"},
            json=body,
            timeout=(8, 60),
        )
        if created_response.status_code >= 400:
            raise GatewayError(f"EvoLink görsel HTTP {created_response.status_code}", created_response.status_code)
        try:
            created = created_response.json()
        except ValueError as exc:
            raise GatewayError("EvoLink görsel yanıtı okunamadı") from exc
        task_id = created.get("id") or (created.get("data") or {}).get("id")
        if not task_id:
            immediate = self._image_result_from_payload(created, "evolink", model)
            if immediate:
                return immediate
            raise GatewayError("EvoLink iş kimliği döndürmedi")
        deadline = time.time() + 240
        while time.time() < deadline:
            time.sleep(3)
            task_response = self.session.get(
                f"https://api.evolink.ai/v1/tasks/{quote(str(task_id), safe='')}",
                headers={"Authorization": f"Bearer {key}", "Accept": "application/json"},
                timeout=(8, 30),
            )
            if task_response.status_code >= 400:
                raise GatewayError(f"EvoLink görev HTTP {task_response.status_code}", task_response.status_code)
            task = task_response.json()
            status = str(task.get("status") or (task.get("data") or {}).get("status") or "").lower()
            if status in {"failed", "error", "cancelled"}:
                raise GatewayError("EvoLink görsel işi başarısız oldu")
            if status in {"completed", "succeeded", "success"}:
                result = self._image_result_from_payload(task, "evolink", model)
                if result:
                    return result
                raise GatewayError("EvoLink tamamlandı ancak görsel döndürmedi")
        raise GatewayError("EvoLink görsel işi zaman aşımına uğradı", 408)

    def _image_imagegpt(self, prompt: str, width: int, height: int, model_override: str | None = None, key_override: str | None = None) -> dict[str, Any] | None:
        key = key_override or _first_key("IMAGEGPT_API_KEY")
        if not key:
            return None
        model = model_override or "FLUX-SCHNELL"
        response = self.session.post(
            "https://api.imagegpt.online/generate/text-image",
            headers={"x-api-key": key, "Content-Type": "application/json"},
            json={"prompt": prompt, "model": model, "width": width, "height": height, "outputType": "url", "outputFormat": "png"},
            timeout=(8, 120),
        )
        if response.status_code >= 400:
            raise GatewayError(f"ImageGPT HTTP {response.status_code}", response.status_code)
        try:
            payload = response.json()
        except ValueError as exc:
            raise GatewayError("ImageGPT yanıtı okunamadı") from exc
        result = self._image_result_from_payload(payload, "imagegpt", model)
        if not result:
            raise GatewayError("ImageGPT boş görsel yanıtı verdi")
        return result

    def _image_modal(self, prompt: str, width: int, height: int, model_override: str | None = None, key_override: str | None = None) -> dict[str, Any] | None:
        endpoint = os.environ.get("MODAL_IMAGE_ENDPOINT", "").strip()
        if not endpoint:
            return None
        model = model_override or "modal-sdxl"
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if key_override:
            headers["Authorization"] = f"Bearer {key_override}"
        response = self.session.post(
            endpoint,
            headers=headers,
            json={"prompt": prompt, "model": model, "width": width, "height": height, "steps": 18, "guidance_scale": 0},
            timeout=(8, 360),
        )
        if response.status_code >= 400:
            raise GatewayError(f"Modal görsel HTTP {response.status_code}", response.status_code)
        try:
            payload = response.json()
        except ValueError as exc:
            raise GatewayError("Modal görsel yanıtı okunamadı") from exc
        result = self._image_result_from_payload(payload, "modal", model)
        if not result:
            raise GatewayError("Modal boş görsel yanıtı verdi")
        return result

    def _image_result_from_payload(self, payload: Any, provider: str, model: str) -> dict[str, Any] | None:
        if not isinstance(payload, dict):
            return None
        candidates: list[Any] = [payload]
        data = payload.get("data")
        if isinstance(data, dict):
            candidates.append(data)
        elif isinstance(data, list):
            candidates.extend(data[:2])
        for key in ("result", "output"):
            value = payload.get(key)
            if isinstance(value, dict):
                candidates.append(value)
            elif isinstance(value, list):
                candidates.extend(value[:2])
            elif isinstance(value, str):
                candidates.append({"url": value})
        results = payload.get("results")
        if isinstance(results, list):
            candidates.extend({"url": value} if isinstance(value, str) else value for value in results[:2])
        images = payload.get("images")
        if isinstance(images, list):
            candidates.extend({"url": value} if isinstance(value, str) else value for value in images[:2])
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            url = candidate.get("image_url") or candidate.get("imageUrl") or candidate.get("url")
            if url:
                parsed = urlparse(str(url))
                if parsed.scheme in {"https", "http"} and parsed.netloc:
                    return {"image_url": str(url), "provider": provider, "model": str(candidate.get("model") or model)}
            encoded = candidate.get("b64_json") or candidate.get("b64") or candidate.get("base64") or candidate.get("image")
            if isinstance(encoded, str) and not encoded.startswith(("http://", "https://")):
                return self._base64_image(encoded.split(",", 1)[-1], provider, model)
        return None

    @staticmethod
    def _compact_image(content: bytes, limit: int = 680_000) -> tuple[bytes, str]:
        if len(content) <= limit:
            return content, ""
        try:
            with Image.open(BytesIO(content)) as source:
                image = source.convert("RGB")
                image.thumbnail((1536, 1536), Image.Resampling.LANCZOS)
                for quality in (88, 82, 76, 70, 64, 58):
                    output = BytesIO()
                    image.save(output, format="JPEG", quality=quality, optimize=True, progressive=True)
                    compact = output.getvalue()
                    if len(compact) <= limit:
                        return compact, "image/jpeg"
                image.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
                output = BytesIO()
                image.save(output, format="JPEG", quality=55, optimize=True, progressive=True)
                compact = output.getvalue()
                if len(compact) <= limit:
                    return compact, "image/jpeg"
        except Exception as exc:
            raise GatewayError("Görsel çıktısı güvenli boyuta dönüştürülemedi") from exc
        raise GatewayError("Görsel çıktısı kalıcı kayıt sınırını aştı")

    @classmethod
    def _bytes_image(cls, content: bytes, content_type: str, provider: str, model: str) -> dict[str, Any]:
        if not content:
            raise GatewayError(f"{provider} boş görsel döndürdü")
        content, compact_mime = cls._compact_image(content)
        mime = content_type.split(";", 1)[0].lower()
        if compact_mime:
            mime = compact_mime
        signatures = {
            "image/png": content.startswith(b"\x89PNG\r\n\x1a\n"),
            "image/jpeg": content.startswith(b"\xff\xd8\xff"),
            "image/webp": content.startswith(b"RIFF") and content[8:12] == b"WEBP",
        }
        if mime not in signatures or not signatures[mime]:
            raise GatewayError(f"{provider} geçerli bir görsel döndürmedi")
        encoded = base64.b64encode(content).decode("ascii")
        return {"image_url": f"data:{mime};base64,{encoded}", "provider": provider, "model": model}

    @classmethod
    def _base64_image(cls, encoded: str, provider: str, model: str) -> dict[str, Any]:
        if not isinstance(encoded, str) or len(encoded) > 16_000_000:
            raise GatewayError("Görsel çıktısı boyut sınırını aştı")
        try:
            raw = base64.b64decode(encoded, validate=True)
        except (ValueError, TypeError) as exc:
            raise GatewayError(f"{provider} geçersiz base64 görsel döndürdü") from exc
        raw, compact_mime = cls._compact_image(raw)
        if compact_mime:
            mime = compact_mime
        elif raw.startswith(b"\x89PNG\r\n\x1a\n"):
            mime = "image/png"
        elif raw.startswith(b"\xff\xd8\xff"):
            mime = "image/jpeg"
        elif raw.startswith(b"RIFF") and raw[8:12] == b"WEBP":
            mime = "image/webp"
        else:
            raise GatewayError(f"{provider} geçerli bir görsel döndürmedi")
        encoded = base64.b64encode(raw).decode("ascii")
        return {"image_url": f"data:{mime};base64,{encoded}", "provider": provider, "model": model}

    def _decode_image_response(self, response: requests.Response, provider: str, model: str) -> dict[str, Any]:
        if response.status_code >= 400:
            raise GatewayError(f"{provider} görsel HTTP {response.status_code}", response.status_code)
        try:
            payload = response.json()
        except ValueError as exc:
            raise GatewayError(f"{provider} görsel yanıtı okunamadı") from exc
        data = payload.get("data") or []
        if not data:
            raise GatewayError(f"{provider} boş görsel yanıtı verdi")
        first = data[0]
        if first.get("url"):
            image_url = str(first["url"])
            parsed = urlparse(image_url)
            if parsed.scheme not in {"https", "http"} or not parsed.netloc:
                raise GatewayError(f"{provider} geçersiz görsel URL'si döndürdü")
            return {"image_url": image_url, "provider": provider, "model": model}
        encoded = first.get("b64_json") or first.get("b64")
        if encoded:
            return self._base64_image(encoded, provider, model)
        raise GatewayError(f"{provider} görsel URL'si döndürmedi")

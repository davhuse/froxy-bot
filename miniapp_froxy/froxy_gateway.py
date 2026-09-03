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
from typing import Any, Iterable
from urllib.parse import quote, urlparse

import requests


class GatewayError(RuntimeError):
    pass


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
        image_providers = {row["provider"] for row in self.image_models() if row.get("active")}
        for slug, status in statuses.items():
            status["capabilities"] = ["chat", *( ["image"] if slug in image_providers else [])]
            status["provider_logo"] = PROVIDER_LOGOS.get(slug, "")
        for slug in image_providers - set(statuses):
            statuses[slug] = {"provider": slug, "healthy": True, "configured": True, "models": 0, "capabilities": ["image"], "provider_logo": PROVIDER_LOGOS.get(slug, "")}
        return statuses

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
            # This is the only number appropriate for the Mini App: every
            # listed model is both healthy and selectable at this moment.
            "active_model_count": len(public),
            "active_provider_count": sum(1 for row in self._provider_status.values() if row.get("healthy")),
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
            try:
                provider = self._provider_for_model(target)
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
                    yield {
                        "type": "provider_done",
                        "usage": usage,
                        "provider": provider.slug,
                        "provider_model": target["provider_model_id"],
                    }
                    return
                last_error = f"{provider.label} boş yanıt verdi"
            except GatewayError as exc:
                last_error = str(exc)
            except requests.RequestException:
                last_error = f"{provider.label} bağlantı hatası"
        raise GatewayError(last_error)

    def image_credit_cost(self) -> int:
        usd = max(0.0001, _float(os.environ.get("FROXY_IMAGE_COST_USD"), 0.0019))
        usd_try, multiplier, credit_try = self._pricing_config()
        return max(1, int(math.ceil((usd * usd_try * multiplier) / credit_try)))

    def image_models(self) -> list[dict[str, Any]]:
        cost = self.image_credit_cost()
        account = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "").strip()
        openai = bool(_first_key("OPENAI_IMAGE_KEY", "OPENAI_IMAGE_KEYS", "OPENAI_API_KEY"))
        together = bool(_first_key("TOGETHER_API_KEY", "TOGETHER_API_KEYS"))
        cloudflare = bool(account and _first_key("CLOUDFLARE_API_TOKEN"))
        runware = bool(_first_key("RUNWARE_API_KEY", "RUNWARE_API_KEYS"))
        pollinations = bool(_first_key("POLLINATIONS_API_KEY", "POLLINATIONS_API_KEYS", "POLLINATIONS_KEY"))
        aimlapi = bool(_first_key("AIMLAPI_KEY"))
        stability = bool(_first_key("STABILITY_API_KEY", "STABILITY_API_KEYS"))
        definitions = [
            ("openai-gpt-image", "OpenAI GPT Image", "openai", os.environ.get("FROXY_OPENAI_IMAGE_MODEL", "gpt-image-1"), openai, cost),
            ("openai-dall-e-3", "OpenAI DALL-E 3", "openai", "dall-e-3", openai, cost),
            ("together-flux-schnell", "Together FLUX.1 Schnell", "together", "black-forest-labs/FLUX.1-schnell", together, 40),
            ("together-juggernaut-flux", "Together Juggernaut FLUX", "together", "Rundiffusion/Juggernaut-Lightning-Flux", together, 30),
            ("together-qwen-image", "Together Qwen Image", "together", "Qwen/Qwen-Image", together, 90),
            ("together-flux2-dev", "Together FLUX.2 Dev", "together", "black-forest-labs/FLUX.2-dev", together, 220),
            ("cf-flux-schnell", "Cloudflare FLUX.1 Schnell", "cloudflare", "@cf/black-forest-labs/flux-1-schnell", cloudflare, cost),
            ("cf-sdxl", "Cloudflare SDXL", "cloudflare", "@cf/stabilityai/stable-diffusion-xl-base-1.0", cloudflare, cost),
            ("cf-sdxl-lightning", "Cloudflare SDXL Lightning", "cloudflare", "@cf/bytedance/stable-diffusion-xl-lightning", cloudflare, cost),
            ("cf-dreamshaper-lcm", "Cloudflare DreamShaper 8 LCM", "cloudflare", "@cf/lykon/dreamshaper-8-lcm", cloudflare, cost),
            ("runware-flux", "Runware FLUX", "runware", "bfl:5@1", runware, cost),
            ("runware-sdxl", "Runware SDXL", "runware", "runware:101@1", runware, cost),
            ("pollinations-zimage", "Pollinations Z-Image", "pollinations", "zimage", pollinations, cost),
            ("pollinations-flux", "Pollinations FLUX", "pollinations", "flux", pollinations, cost),
            ("pollinations-gptimage", "Pollinations GPT Image", "pollinations", "gptimage", pollinations, cost),
            ("pollinations-nanobanana", "Pollinations Nano Banana", "pollinations", "nanobanana", pollinations, cost),
            ("aiml-flux", "AI/ML API FLUX", "aimlapi", "flux-pro", aimlapi, cost),
            ("aiml-nano", "AI/ML API Nano Banana", "aimlapi", "google/gemini-3.1-flash-image", aimlapi, cost),
            ("stability-core", "Stability Core", "stability", "core", stability, cost),
            ("stability-ultra", "Stability Ultra", "stability", "ultra", stability, cost),
        ]
        return [{
            "id": public_id,
            "name": name,
            "provider": provider,
            "provider_label": name.split(" Image", 1)[0],
            "provider_logo": PROVIDER_LOGOS.get(provider, ""),
            "provider_model": model,
            "capabilities": ["text-to-image"],
            "estimated_credits": estimated,
            "active": active,
        } for public_id, name, provider, model, active, estimated in definitions]

    def get_image_model(self, public_id: str) -> dict[str, Any]:
        model = next((row for row in self.image_models() if row["id"] == str(public_id) and row.get("active")), None)
        if not model:
            raise GatewayError("Görsel modeli aktif değil")
        return model

    def generate_image(self, prompt: str, width: int = 512, height: int = 512, model_id: str | None = None) -> dict[str, Any]:
        operations = {
            "openai": self._image_openai,
            "together": self._image_together,
            "cloudflare": self._image_cloudflare,
            "runware": self._image_runware,
            "pollinations": self._image_pollinations,
            "aimlapi": self._image_aimlapi,
            "stability": self._image_stability,
        }
        active_models = [row for row in self.image_models() if row.get("active")]
        if model_id:
            selected = self.get_image_model(model_id)
            active_models.sort(key=lambda row: 0 if row["id"] == selected["id"] else 1)
        attempts = [(operations[row["provider"]], row) for row in active_models]
        errors = []
        for operation, image_model in attempts:
            try:
                result = operation(prompt, width, height, image_model.get("provider_model"))
                if result:
                    return result
            except GatewayError as exc:
                errors.append(str(exc))
            except requests.RequestException as exc:
                errors.append(f"{operation.__name__} bağlantı hatası: {type(exc).__name__}")
            except (ValueError, TypeError, KeyError) as exc:
                errors.append(f"{operation.__name__} geçersiz yanıtı: {type(exc).__name__}")
        raise GatewayError(errors[-1] if errors else "Çalışan görsel sağlayıcısı bulunamadı")

    def _image_openai(self, prompt: str, width: int, height: int, model_override: str | None = None) -> dict[str, Any] | None:
        key = _first_key("OPENAI_IMAGE_KEY", "OPENAI_IMAGE_KEYS", "OPENAI_API_KEY")
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

    def _image_together(self, prompt: str, width: int, height: int, model_override: str | None = None) -> dict[str, Any] | None:
        key = _first_key("TOGETHER_API_KEY", "TOGETHER_API_KEYS")
        if not key:
            return None
        model = model_override or os.environ.get("FROXY_TOGETHER_IMAGE_MODEL", "black-forest-labs/FLUX.1-schnell")
        response = self.session.post(
            "https://api.together.xyz/v1/images/generations",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": model, "prompt": prompt, "width": width, "height": height, "steps": 4, "n": 1},
            timeout=(8, 120),
        )
        return self._decode_image_response(response, "together", model)

    def _image_cloudflare(self, prompt: str, width: int, height: int, model_override: str | None = None) -> dict[str, Any] | None:
        token = _first_key("CLOUDFLARE_API_TOKEN")
        account = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "").strip()
        if not token or not account:
            return None
        model = model_override or os.environ.get("FROXY_CLOUDFLARE_IMAGE_MODEL", "@cf/black-forest-labs/flux-1-schnell")
        body = {"prompt": prompt, "width": width, "height": height}
        if "flux" in model:
            body["steps"] = 4
        else:
            body["num_steps"] = 4 if "lightning" in model else 20
        response = self.session.post(
            f"https://api.cloudflare.com/client/v4/accounts/{account}/ai/run/{quote(model, safe='@/-')} ".strip(),
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=body,
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
                return self._base64_image(image, "cloudflare", model)
        except ValueError:
            pass
        raise GatewayError("Cloudflare görsel yanıtı okunamadı")

    def _image_runware(self, prompt: str, width: int, height: int, model_override: str | None = None) -> dict[str, Any] | None:
        key = _first_key("RUNWARE_API_KEY", "RUNWARE_API_KEYS")
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
        image_url = str(url)
        parsed = urlparse(image_url)
        if parsed.scheme not in {"https", "http"} or not parsed.netloc:
            raise GatewayError("Runware geçersiz görsel URL'si döndürdü")
        return {"image_url": image_url, "provider": "runware", "model": model}

    def _image_pollinations(self, prompt: str, width: int, height: int, model_override: str | None = None) -> dict[str, Any] | None:
        key = _first_key("POLLINATIONS_API_KEY", "POLLINATIONS_API_KEYS", "POLLINATIONS_KEY")
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

    def _image_aimlapi(self, prompt: str, width: int, height: int, model_override: str | None = None) -> dict[str, Any] | None:
        key = _first_key("AIMLAPI_KEY")
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

    def _image_stability(self, prompt: str, width: int, height: int, model_override: str | None = None) -> dict[str, Any] | None:
        key = _first_key("STABILITY_API_KEY", "STABILITY_API_KEYS")
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
            raise GatewayError(f"Stability görsel HTTP {response.status_code}")
        return self._bytes_image(response.content, response.headers.get("Content-Type", ""), "stability", model)

    @staticmethod
    def _bytes_image(content: bytes, content_type: str, provider: str, model: str) -> dict[str, Any]:
        if not content or len(content) > 700_000:
            raise GatewayError("Görsel çıktısı kalıcı kayıt sınırını aştı")
        mime = content_type.split(";", 1)[0].lower()
        signatures = {
            "image/png": content.startswith(b"\x89PNG\r\n\x1a\n"),
            "image/jpeg": content.startswith(b"\xff\xd8\xff"),
            "image/webp": content.startswith(b"RIFF") and content[8:12] == b"WEBP",
        }
        if mime not in signatures or not signatures[mime]:
            raise GatewayError(f"{provider} geçerli bir görsel döndürmedi")
        encoded = base64.b64encode(content).decode("ascii")
        return {"image_url": f"data:{mime};base64,{encoded}", "provider": provider, "model": model}

    @staticmethod
    def _base64_image(encoded: str, provider: str, model: str) -> dict[str, Any]:
        if not isinstance(encoded, str) or len(encoded) > 950_000:
            raise GatewayError("Görsel çıktısı kalıcı kayıt sınırını aştı")
        try:
            raw = base64.b64decode(encoded, validate=True)
        except (ValueError, TypeError) as exc:
            raise GatewayError(f"{provider} geçersiz base64 görsel döndürdü") from exc
        if raw.startswith(b"\x89PNG\r\n\x1a\n"):
            mime = "image/png"
        elif raw.startswith(b"\xff\xd8\xff"):
            mime = "image/jpeg"
        elif raw.startswith(b"RIFF") and raw[8:12] == b"WEBP":
            mime = "image/webp"
        else:
            raise GatewayError(f"{provider} geçerli bir görsel döndürmedi")
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
            image_url = str(first["url"])
            parsed = urlparse(image_url)
            if parsed.scheme not in {"https", "http"} or not parsed.netloc:
                raise GatewayError(f"{provider} geçersiz görsel URL'si döndürdü")
            return {"image_url": image_url, "provider": provider, "model": model}
        encoded = first.get("b64_json") or first.get("b64")
        if encoded:
            return self._base64_image(encoded, provider, model)
        raise GatewayError(f"{provider} görsel URL'si döndürmedi")

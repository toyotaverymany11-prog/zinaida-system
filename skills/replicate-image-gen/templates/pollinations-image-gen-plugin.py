"""Pollinations.ai image generation provider — Hermes Agent plugin.

Рабочий шаблон image_gen провайдера для Hermes Agent.
Полностью бесплатно, без API ключа.

Установка:
1. Скопировать в ~/.hermes/plugins/image_gen/pollinations/__init__.py
2. Создать ~/.hermes/plugins/image_gen/pollinations/plugin.yaml:
   ---
   kind: backend
   name: pollinations
   ---
3. Добавить в config.yaml:
   image_gen:
     provider: pollinations
     model: sana
   plugins:
     enabled:
       - pollinations
4. Перезапустить Gateway:
   pkill -f hermes-gateway; sleep 2; cd /usr/local/lib/hermes-agent && npx hermes gateway start --daemon
"""

from __future__ import annotations

import logging
import os
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

from agent.image_gen_provider import (
    DEFAULT_ASPECT_RATIO,
    ImageGenProvider,
    error_response,
    success_response,
)

logger = logging.getLogger(__name__)

POLLINATIONS_BASE = "https://image.pollinations.ai/prompt"

POLLINATIONS_MODELS = {
    "sana": {
        "display": "Sana (быстрая, бесплатно)",
        "speed": "<1с",
        "strengths": "Очень быстрая, базовое качество",
        "price": "бесплатно",
    },
    "flux": {
        "display": "FLUX (бесплатно)",
        "speed": "~5с",
        "strengths": "Лучшее качество из доступных",
        "price": "бесплатно",
    },
    "turbo": {
        "display": "Turbo (быстрая)",
        "speed": "~2с",
        "strengths": "Быстрая, среднее качество",
        "price": "бесплатно",
    },
}


class PollinationsImageGenProvider(ImageGenProvider):
    @property
    def name(self) -> str:
        return "pollinations"

    @property
    def display_name(self) -> str:
        return "Pollinations.ai (бесплатно)"

    def is_available(self) -> bool:
        return True  # Всегда доступен — не требует ключа

    def list_models(self) -> List[Dict[str, Any]]:
        return [
            {"id": mid, "display": m["display"], "speed": m["speed"],
             "strengths": m["strengths"], "price": m["price"]}
            for mid, m in POLLINATIONS_MODELS.items()
        ]

    def default_model(self) -> Optional[str]:
        return "sana"

    def get_setup_schema(self) -> Dict[str, Any]:
        return {
            "name": "Pollinations.ai",
            "badge": "free",
            "tag": "Бесплатная генерация без API ключа",
            "env_vars": [],
        }

    def capabilities(self) -> Dict[str, Any]:
        return {"modalities": ["text"], "max_reference_images": 0}

    def generate(
        self,
        prompt: str,
        aspect_ratio: str = DEFAULT_ASPECT_RATIO,
        *,
        image_url: Optional[str] = None,
        reference_image_urls: Optional[List[str]] = None,
        model: Optional[str] = None,
        seed: Optional[int] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        if image_url or reference_image_urls:
            return error_response(
                "Pollinations.ai не поддерживает img2img",
                provider="pollinations", prompt=prompt)

        ar_map = {"square": ("1024", "1024"), "landscape_16_9": ("1280", "720"),
                  "portrait_16_9": ("720", "1280")}
        w, h = ar_map.get(aspect_ratio, ("1024", "1024"))

        model_id = model or "sana"
        params = {
            "width": w, "height": h,
            "seed": str(seed) if seed else str(abs(hash(prompt)) % 99999),
            "model": model_id,
        }
        url = f"{POLLINATIONS_BASE}/{urllib.parse.quote(prompt)}?{urllib.parse.urlencode(params)}"

        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "Hermes-Pollinations-Plugin/1.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                image_data = resp.read()

            if not image_data or len(image_data) < 100:
                return error_response(
                    "Пустой ответ от Pollinations.ai",
                    provider="pollinations", prompt=prompt)

            import tempfile
            tmp = tempfile.NamedTemporaryFile(
                suffix=".jpg", prefix="pollinations_", delete=False)
            tmp.write(image_data)
            tmp.close()

            return success_response(
                image_path=tmp.name, provider="pollinations",
                prompt=prompt, model=model_id)

        except urllib.error.HTTPError as exc:
            return error_response(
                f"Pollinations HTTP {exc.code}: {exc.reason}",
                provider="pollinations", prompt=prompt)
        except Exception as exc:
            logger.error("Pollinations error: %s", exc, exc_info=True)
            return error_response(
                f"Pollinations ошибка: {exc}",
                provider="pollinations", prompt=prompt)


def register(ctx) -> None:
    ctx.register_image_gen_provider(PollinationsImageGenProvider())

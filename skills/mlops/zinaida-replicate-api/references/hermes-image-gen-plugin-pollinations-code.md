# Pollinations.ai Hermes image_gen плагин — код и конфиг

**Путь:** `/root/.hermes/plugins/image_gen/pollinations/`
**Дата:** 2026-07-10

## plugin.yaml
```yaml
kind: backend
name: pollinations
```

## __init__.py (полный код)
```python
"""Pollinations.ai image generation backend for Hermes."""
from __future__ import annotations
import logging, urllib.request, urllib.parse, tempfile
from typing import Any, Dict, List, Optional
from agent.image_gen_provider import (
    DEFAULT_ASPECT_RATIO, ImageGenProvider,
)
logger = logging.getLogger(__name__)
POLLINATIONS_BASE = "https://image.pollinations.ai/prompt"

class PollinationsImageGenProvider(ImageGenProvider):
    @property
    def name(self) -> str: return "pollinations"
    @property
    def display_name(self) -> str: return "Pollinations.ai (бесплатно)"
    def is_available(self) -> bool: return True
    def list_models(self):
        return [
            {"id": "sana", "display": "Sana", "speed": "<1с", "strengths": "быстро", "price": "бесплатно"},
            {"id": "flux", "display": "FLUX", "speed": "~5с", "strengths": "качество", "price": "бесплатно"},
            {"id": "turbo", "display": "Turbo", "speed": "~2с", "strengths": "быстро", "price": "бесплатно"},
        ]
    def default_model(self) -> Optional[str]: return "sana"

    def generate(self, prompt: str, aspect_ratio: str = DEFAULT_ASPECT_RATIO, **kwargs):
        try:
            w, h = {"square": ("1024","1024"), "landscape": ("1280","720"), "portrait": ("720","1280")}.get(aspect_ratio, ("1024","1024"))
            model = kwargs.get("model", "sana")
            url = f"{POLLINATIONS_BASE}/{urllib.parse.quote(prompt)}?width={w}&height={h}&model={model}"
            req = urllib.request.Request(url, headers={"User-Agent": "Hermes/1.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = resp.read()
            tmp = tempfile.NamedTemporaryFile(suffix=".jpg", prefix="poll_", delete=False)
            tmp.write(data); tmp.close()
            return {"success": True, "image": tmp.name, "model": model, "prompt": prompt,
                    "aspect_ratio": aspect_ratio, "provider": "pollinations"}
        except Exception as exc:
            logger.error("Pollinations error: %s", exc, exc_info=True)
            return {"success": False, "error": str(exc), "provider": "pollinations", "prompt": prompt}

def register(ctx) -> None:
    ctx.register_image_gen_provider(PollinationsImageGenProvider())
```

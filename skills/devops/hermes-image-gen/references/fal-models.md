# FAL.ai Models — Hermes Image Generation

Поддерживаются через встроенный FAL провайдер
(`/usr/local/lib/hermes-agent/plugins/image_gen/fal/`).

## Model Table (из документации Hermes 10.07.2026)

| Model ID | Speed | Strengths | Price |
|---|---|---|---|
| `fal-ai/flux-2/klein/9b` *(default)* | <1s | Fast, crisp text | $0.006/MP |
| `fal-ai/flux-2-pro` | ~6s | Studio photorealism | $0.03/MP |
| `fal-ai/z-image/turbo` | ~2s | Bilingual EN/CN, 6B | $0.005/MP |
| `fal-ai/nano-banana-pro` | ~8s | Gemini 3 Pro, text | $0.15/image (1K) |
| `fal-ai/gpt-image-1.5` | ~15s | Prompt adherence | $0.034/image |
| `fal-ai/gpt-image-2` | ~20s | SOTA text + CJK, photorealism | $0.04–0.06/image |
| `fal-ai/ideogram/v3` | ~5s | Best typography | $0.03–0.09/image |
| `fal-ai/recraft/v4/pro/text-to-image` | ~8s | Design, brand systems | $0.25/image |
| `fal-ai/qwen-image` | ~12s | LLM-based, complex text | $0.02/MP |
| `fal-ai/krea/v2/medium/text-to-image` | ~15–25s | Illustration, anime, painting | $0.030–0.035/image |
| `fal-ai/krea/v2/large/text-to-image` | ~25–60s | Photorealism, raw textures | $0.060–0.065/image |

## Aspect Ratios

| Agent input | flux/z-image/qwen/recraft/ideogram | nano-banana-pro | gpt-image-1.5 | gpt-image-2 |
|---|---|---|---|---|
| `landscape` | `landscape_16_9` | `16:9` | 1536×1024 | 1024×768 |
| `square` | `square_hd` | `1:1` | 1024×1024 | 1024×1024 |
| `portrait` | `portrait_16_9` | `9:16` | 1024×1536 | 768×1024 |

## Setup

1. `FAL_KEY` в env или
2. Nous Portal subscription (gateway прокси)

## Image-to-Image

FAL модели с поддержкой `/edit`: flux-2/klein/9b, flux-2-pro, nano-banana-pro,
gpt-image-1.5, gpt-image-2, ideogram/v3, qwen-image.

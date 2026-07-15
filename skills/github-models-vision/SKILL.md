---
name: github-models-vision
description: GitHub Models vision провайдер. gpt-4o-mini через models.github.ai/inference для просмотра картинок. Требуется PAT со scope models:read.
---

# GitHub Models Vision

## Статус: РАБОТАЕТ
GitHub Models vision работает! (ранее не работал из-за отсутствия scope models:read на токене)

## Требования
- **Токен:** GitHub Personal Access Token со scope `models:read`
- **Endpoint:** `https://models.github.ai/inference/chat/completions`
- **Модель:** `gpt-4o-mini` (бесплатно ~150 запросов/день)

## Формат запроса (OpenAI-совместимый)
```python
import urllib.request, json, base64, ssl

TOKEN = "ghp_..."  # PAT со scope models:read

with open("photo.jpg", "rb") as f:
    b64 = base64.b64encode(f.read()).decode()

payload = json.dumps({
    "model": "gpt-4o-mini",
    "messages": [{"role": "user", "content": [
        {"type": "text", "text": "Что на фото?"},
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
    ]}],
    "stream": False
}).encode()

req = urllib.request.Request(
    "https://models.github.ai/inference/chat/completions",
    data=payload,
    headers={
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
)
resp = urllib.request.urlopen(req, timeout=30)
result = json.loads(resp.read())
print(result["choices"][0]["message"]["content"])
```

## Сравнение с Ollama Cloud
| Параметр | GitHub Models | Ollama Cloud |
|----------|---------------|--------------|
| Модель | gpt-4o-mini | gemma3:27b |
| Скорость | 1-2 сек | 1.5-2 сек |
| Сжатие | Не нужно | Нужно (PNG->JPEG) |
| Лимит | ~150/день | Бесплатно, мягкий лимит |
| Качество | Отличное | Хорошее |

## Проблемы
- **Токен без scope models:read** — выдаёт 404/401. Решение: создать новый PAT на github.com/settings/tokens со scope `models:read`
- **404 unknown_model** — модель не найдена. Проверить название модели и endpoint URL.

# GitHub Models — Working Configuration Reference

## Authentication
- **Эндпоинт:** `https://models.github.ai/inference/chat/completions`
- **Токен:** GitHub Personal Access Token (classic) со скоупом `models:read` (обязательно с мая 2025)
- **Формат:** OpenAI-совместимый

## Проверка токена
```bash
curl -s -X POST "https://models.github.ai/inference/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"model":"gpt-4o-mini","messages":[{"role":"user","content":"ok"}],"max_tokens":5}'
```
Должен вернуть HTTP 200.

## Модели и лимиты
| Модель | ID | Лимит/день | Назначение |
|--------|-----|-----------|------------|
| GPT-4o mini | `gpt-4o-mini` | ~150 | Рутина, vision, быстрые ответы |
| GPT-4o | `gpt-4o` | ~50 | Сложные задачи, качественный vision |

Лимиты раздельные на каждую модель. При превышении — HTTP 429.

## Vision (просмотр картинок)
Скрипт: `/opt/zinaida/scripts/github_vision.py`
```bash
python3 /opt/zinaida/scripts/github_vision.py /путь/к/картинке.png "Описание"
```
Скрипт читает `GITHUB_TOKEN` из `/opt/zinaida/config/secrets.env` или `/root/.hermes/.env`.

## Настройка в Hermes config.yaml
```yaml
custom_providers:
  - name: github-models
    api_key: "$GITHUB_TOKEN"  # читается из .env
    base_url: "https://models.github.ai/inference"
    model: "gpt-4o-mini"
    models:
      gpt-4o-mini: { context_length: 128000 }
      gpt-4o: { context_length: 128000 }

auxiliary:
  vision:
    provider: github-models
    model: gpt-4o-mini
    base_url: "https://models.github.ai/inference"
    api_key: "$GITHUB_TOKEN"
```

## Известные проблемы
- `***` в командах terminal — это маскировка вывода Hermes, не плейсхолдер для подстановки
- Для vision_analyze требуется перезапуск сессии после настройки auxiliary.vision
- Ключ должен быть в `.bashrc` (`export GITHUB_TOKEN=...`) и `.env` чтобы процесс Hermes его видел

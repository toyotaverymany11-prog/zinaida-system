# GitHub Models — настройка и устранение неполадок

## Проблема: 401 Unauthorized

**Причина:** Токен (PAT) не имеет скоупа `models:read`. Обычные PAT без этого скоупа дают 401 даже если живы и работают для Git.

**Решение:** Создать новый PAT с `models:read`:
1. GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Generate new token (classic)
3. Отметить `models:read` (обязательно), `read:user` (желательно)
4. Срок: No expiration
5. Сгенерировать, скопировать токен (начинается на `ghp_`)

## Как добавить провайдера в config.yaml

```yaml
custom_providers:
  - name: github-models
    api_key: "ghp_твой_токен"
    base_url: https://models.github.ai/inference
    models:
      gpt-4o-mini:
        context_length: 128000
      gpt-4o:
        context_length: 128000

auxiliary:
  vision:
    provider: github-models
    model: gpt-4o-mini
    base_url: https://models.github.ai/inference
    api_key: "ghp_твой_токен"
    timeout: 120
```

## ВАЖНО: `***` — не подстановка!
`***` в командах — это маскировка вывода Hermes, НЕ подстановка секрета.
Когда пишешь `export GITHUB_TOKEN=***` — в файл запишется буквально `***`, а не токен.
Всегда пиши ПОЛНЫЙ токен в командах. Hermes сам замаскирует его в выводе.

## Правильные эндпоинты
- **Правильный:** `https://models.github.ai/inference/chat/completions`
- **Неправильные:** `models.inference.ai.azure.com` (старый Azure endpoint)
- **Проверка:** `curl -s -X POST https://models.github.ai/inference/chat/completions -H "Authorization: Bearer ghp_ТОКЕН" -d '{"model":"gpt-4o-mini","messages":[{"role":"user","content":"ok"}],"max_tokens":5}'`

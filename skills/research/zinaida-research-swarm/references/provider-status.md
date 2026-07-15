# Provider Status (проверено 10.07.2026)

## LLM — ЖИВЫЕ

| Провайдер | Ключ | Где лежит | Endpoint | Модель | Стоимость | Примечание |
|-----------|------|-----------|----------|--------|-----------|------------|
| Mistral | MISTRAL_API_KEY | config/secrets.env | api.mistral.ai/v1 | mistral-small-latest | Бесплатно (500K/мес) | 3 ключа, все живые |
| Mistral | MISTRAL_API_KEY_2 | config/secrets.env | api.mistral.ai/v1 | mistral-small-latest | Бесплатно | Жив |
| Mistral | MISTRAL_API_KEY_3 | config/secrets.env | api.mistral.ai/v1 | mistral-small-latest | Бесплатно | Жив |
| GitHub Models | GITHUB_TOKEN | /root/.hermes/.env | models.inference.ai.azure.com | gpt-4o-mini | Бесплатно (~150/день) | Жив |
| DeepSeek | DEEPSEEK_API_KEY | /opt/zinaida/.env | api.deepseek.com | deepseek-chat | $0.27/M in, $1.10/M out | Жив. ТОЛЬКО Раунд 4 (синтез) + Раунд 2 (оценка). НЕ агент сбора. НЕ Раунд 3. НЕ Flash. |
| Ollama | OLLAMA_API_KEY_1..3 | config/secrets.env | ollama.com/v1 | gemma3:27b | Условно-бесплатно | 3 ключа, все живые (резерв) |

## LLM — МЁРТВЫЕ

| Провайдер | Ключ | Где лежит | Причина | Дата |
|-----------|------|-----------|---------|------|
| OpenRouter | OPENROUTER_KEY | meta_agent/.env | IP сервера заблокирован (403 security policy) | 10.07.2026 |
| GigaChat | GIGACHAT_CLIENT_SECRET | /opt/zinaida/.env | OAuth 400, схема устарела | 10.07.2026 |
| GitHub Models (второй) | GREG_GITHUB_TOKEN | meta_agent/.env | 401 Unauthorized | 10.07.2026 |

## Поисковые API

| Сервис | Ключ | Где лежит | Endpoint | Лимит | Скорость |
|--------|------|-----------|----------|-------|----------|
| Tavily | TAVILY_API_KEY | /root/.hermes/.env | api.tavily.com/search | 1000/мес бесплатно | ~2.1s |
| Brave Search | BRAVE_API_KEY | НЕТ КЛЮЧА | api.search.brave.com | 2000/мес бесплатно | ~0.8s |

## Другие сервисы

| Сервис | Статус | Путь |
|--------|--------|------|
| Telegram-бот (@DCHP_Shtab_bot) | ✅ Жив | /opt/zinaida/telegram_bot/ |
| OneDrive rclone | ✅ Жив | rclone-onedrive.service |
| Caddy | ✅ Жив | caddy.service |
| Vision proxy (порт 8901) | ✅ Жив | /opt/zinaida/scripts/vision_proxy_8901.py |

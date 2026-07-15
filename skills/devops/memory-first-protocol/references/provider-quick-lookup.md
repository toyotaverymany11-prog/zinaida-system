# Провайдеры — быстрый справочник (актуально на 12.07.2026)

## Ollama
- **URL:** `https://ollama.com/v1/chat/completions` (НЕ cloud.ollama.com!)
- **Ключи из meta_agent/.env:** OLLAMA_API_KEY, OLLAMA_API_KEY_2, GREG_OLLAMA_KEY
- **OLLAMA_API_KEY_3 НЕ СУЩЕСТВУЕТ** — не использовать
- **Бесплатные модели:** gemma3:4b, ministral-3:3b
- **Платные (НЕ ИСПОЛЬЗОВАТЬ):** gemma3:27b
- **Ошибка ConnectError:** URL неправильный

## GigaChat
- **OAuth2, НЕ Bearer!** Два шага: токен → запрос
- **URL auth:** https://ngw.devices.sberbank.ru:9443/api/v2/oauth
- **URL chat:** https://gigachat.devices.sberbank.ru/api/v1/chat/completions
- **Модель:** GigaChat (бесплатная текстовая, по умолчанию)
- **SSL:** самоподписанный → ssl._create_unverified_context()
- **Rate limit:** ~1 запрос в 3-5 сек, пауза обязательна
- **НЕ ИСПОЛЬЗОВАТЬ httpx** — даёт 429. Только urllib.request
- **402 Payment Required** — ежемесячный бесплатный лимит исчерпан

## Mistral
- **URL:** https://api.mistral.ai/v1/chat/completions
- **3 ключа из meta_agent/.env:** MISTRAL_API_KEY, MISTRAL_API_KEY_2, MISTRAL_API_KEY_3
- **Модель:** mistral-large-latest (бесплатно)
- **Проблема 429:** rate limit — подождать, использует ротацию ключей

## DeepSeek
- **URL:** https://api.deepseek.com/v1/chat/completions
- **Ключ из /opt/zinaida/.env:** DEEPSEEK_API_KEY (живой, $17.45)
- **Systemd ключ МЁРТВЫЙ:** читать через open().read(), не os.getenv()
- **Модели:** deepseek-chat (Flash, $0.27/M), deepseek-reasoner (Pro, $1.42/M)

## GitHub Models
- **URL:** https://models.inference.ai.azure.com/chat/completions?api-version=2024-10-21
- **Ключ из /root/.hermes/.env:** GITHUB_TOKEN
- **Модель:** gpt-4o-mini (бесплатно)

## Роутеры
| Роутер | Порт | Модели | Провайдеры |
|--------|------|--------|------------|
| Zinaida-Router | 8002 | Zinaida-Router, deepseek-chat | FREE: Mistral→Ollama. DeepSeek=fallback |
| Zina2-Router | 8003 | Zina2-Router | DeepSeek Flash/Pro/V3 |
| Zina2-Router v2 | 8005 | 8005-* | DeepSeek + Ollama + Server RAG |

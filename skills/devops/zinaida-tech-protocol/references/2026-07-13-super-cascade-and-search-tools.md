# Super Cascade 8005 v2.1 — фиксы и статус поиска (13.07.2026)

## Проблема: Mistral слишком самоуверен
Mistral отвечал с self-confidence 75-95, блокируя gpt-4o. На технические вопросы Mistral тупил, но был самоуверен (confidence 95 при длине ответа 7 символов).
**Фикс:** Порог в `router_8005_v2.py` поднят с 75 → 95.
```python
if mistral_text and confidence >= 95:  # было >= 75
```

## Актуальный каскад
1. Ollama — приветствия/короткие (бесплатно)
2. Mistral — только если confidence ≥ 95 (бесплатно)
3. gpt-4o через GitHub — основной для обычных запросов (бесплатно, 2 ключа)
4. DeepSeek Flash — если бесплатные не справились ($0.27/M)
5. DeepSeek Pro — экстрим ($1.42/M)

## Статус поисковых инструментов
| Инструмент | Статус на 13.07 | Альтернатива |
|-----------|----------------|--------------|
| Tavily (web_search/web_extract) | ❌ 432 — лимит 1000/мес исчерпан | DuckDuckGo |
| DuckDuckGo (ddgs) | ✅ бесплатно, безлимит | — |
| Browser (browser_navigate) | ✅ работает | — |
| GitHub API | ✅ работает через browser | — |

## Telegram bot эволюция
1. Изначально: bot.py → 8002 (голый Gemini, без system prompt)
2. Переключено на 8003 (DeepSeek Flash/Pro)
3. Переключено на Gateway 8642 (Hermes Studio) — 404, gateway не умеет custom провайдеры
4. **Финально:** bot.py → напрямую http://127.0.0.1:8005/v1/chat/completions с system prompt из SOUL.md
5. System prompt = SOUL.md + инструкция по планировщику
6. История диалога: хранится в JSON файле, последние 20 сообщений

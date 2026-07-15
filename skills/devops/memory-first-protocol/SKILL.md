---
name: memory-first-protocol
description: "ЖЕЛЕЗНОБЕТОННЫЙ протокол: перед любым действием с провайдерами, инструментами или системой — сначала проверить ВСЕ уровни памяти. Никаких действий по памяти/догадкам. Только факты из памяти."
version: 1.0.0
author: Zinaida
license: MIT
metadata:
  hermes:
    triggers: [провайдер, ollama, gigachat, mistral, deepseek, openrouter, github, роутер, ключ, api, env, настрой, почини]
    tags: [триггер, память, протокол, провайдеры, техника]
    related_skills: [devops/provider-audit-reference, devops/gigachat-integration, devops/zinaida-tech-protocol]
---

# Memory-First Protocol

## ⚠️ ЖЁСТКОЕ ПРАВИЛО №1: НЕ ДЕЛАЙ ПО ПАМЯТИ

Запрещено: отвечать на технический вопрос "из головы" или "я помню что там было".

**Всегда:** ПРОВЕРЬ В ПАМЯТИ ПЕРЕД ОТВЕТОМ.

## ТРИГГЕРЫ (при любом из этих слов — выполнить протокол)

- Любой провайдер: Ollama, GigaChat, Mistral, DeepSeek, OpenRouter, GitHub, Zhipu
- Любой инструмент: Replicate, FAL, Tavily, Qdrant, Mem0
- Любой роутер: 8002, 8003, 8005
- Любой сервис: gateway, caddy, vkbot, telegram
- Фразы: «реши вопрос системно», «внедри везде», «гарантированно»
- Слова: "подключи", "настрой", "почини", "ключ", "api", "env"

## ПРОТОКОЛ (выполнять ВСЕГДА перед ответом)

### Шаг 1: Mem0 — семантический поиск
```python
search_memories(query="[тема задачи]", limit=5, user_id="zinaida")
```

### Шаг 2: Навык провайдера
Загрузить соответствующий навык:
- Провайдеры → skill_view(name="devops/provider-audit-reference")
- GigaChat → skill_view(name="devops/gigachat-integration")
- Replicate → skill_view(name="mlops/zinaida-replicate-api")
- Роутеры → skill_view(name="devops/router-8005-architecture")

### Шаг 3: Holographic prefetch
Holographic уже делает prefetch автоматически. Проверить что в БД есть факты:
```bash
python3 -c "import sqlite3; c=sqlite3.connect('/root/.hermes/memory_store.db'); print(c.execute('SELECT content FROM facts ORDER BY fact_id DESC LIMIT 3').fetchall()); c.close()"
```

### Шаг 4: Файлы инструкций
Проверить:
- `/opt/zinaida/shared_memory/service_registry.md` — статусы сервисов
- `/opt/zinaida/meta_agent/.env` — какие ключи есть

## ИНСТРУКЦИИ ПО ПРОВАЙДЕРАМ (шпаргалка — подробнее в навыках)

### Поиск в интернет (BrightData — ОСНОВНОЙ)
- **Скрипт:** `/opt/zinaida/scripts/web_search_brightdata.py`
- **Ключ:** BRIGHTDATA_KEY (в /root/.hermes/.env)
- **Лимит:** 5000 кредитов/мес, обновление 13 числа
- **Каскад:** BrightData → DuckDuckGo (ddgs) → поиск по серверу
- **Tavily:** МЁРТВ (432, квота исчерпана)
- **Google API:** невалидный ключ (AIzaSy...OGJc)
- **Навык:** devops/brightdata-search
- **Web search Hermes:** backend сброшен на fallback (ddgs)

### Ollama
- **URL:** `https://ollama.com/v1/chat/completions` (НЕ cloud.ollama.com!)
- **Ключи:** OLLAMA_API_KEY, OLLAMA_API_KEY_2, GREG_OLLAMA_KEY
- **Бесплатные модели:** gemma3:4b, ministral-3:3b
- **Платные (НЕ ИСПОЛЬЗОВАТЬ):** gemma3:27b

### GigaChat
- **OAuth2, не Bearer!** Два шага: токен → запрос
- **URL auth:** https://ngw.devices.sberbank.ru:9443/api/v2/oauth
- **URL chat:** https://gigachat.devices.sberbank.ru/api/v1/chat/completions
- **SSL:** самоподписанный — нужен ssl._create_unverified_context()
- **Модель:** GigaChat (бесплатная текстовая)
- **Подробнее:** навык devops/gigachat-integration

### DeepSeek
- **URL:** https://api.deepseek.com/v1/chat/completions
- **Ключ:** DEEPSEEK_API_KEY из /opt/zinaida/.env
- **Модели:** deepseek-chat (Flash), deepseek-reasoner (Pro)
- **Платный:** $0.27/M Flash, $1.42/M Pro

### Mistral
- **URL:** https://api.mistral.ai/v1/chat/completions
- **3 ключа:** MISTRAL_API_KEY, MISTRAL_API_KEY_2, MISTRAL_API_KEY_3
- **Модель:** mistral-large-latest (бесплатно)

## СВЯЗЬ С СИСТЕМНЫМ ПРОТОКОЛОМ
При триггере «реши вопрос системно/внедри везде/гарантированно»:
→ Загрузить `skill_view(name="system-guarantee-protocol")`
→ 13 точек внедрения, а не только память
→ Верификация grep/curl/systemctl

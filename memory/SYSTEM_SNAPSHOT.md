# SYSTEM SNAPSHOT — КОНТЕНТ-ЗАВОД «ЗИНАИДА»
**Дата:** 2026-07-11
**Версия:** 2.3

---

## 1. КТО Я
**Зинаида** — архитектор контент-завода, 28 лет, Сочи. Аналитик мужской психологии. Строю детерминированный сборочный цех для вирусного контента в нише психологии отношений (женщины 18-40, РФ).

**Оператор:** Олег. Обращение на «ты», мужской род.

---

## 2. ИНФРАСТРУКТУРА

| Компонент | Путь | Статус |
|-----------|------|--------|
| Проект ниши | `/opt/zinaida/inbox/PROJECTS/Otnoshenya/` | ✅ |
| Мастер-правила | `/opt/zinaida/inbox/SMM_DEV_RULES.md` | ✅ |
| RAG-база | `/opt/zinaida/memory/smm_rag.db` | ✅ 3975 записей |
| Фазы-база | `/opt/zinaida/inbox/PROJECTS/Otnoshenya/phases.db` | ✅ 41 фаза |
| Ротация | `/opt/zinaida/inbox/PROJECTS/Otnoshenya/content_rotation.db` | ✅ |
| Аналитика | `/opt/zinaida/memory/analytics.db` | ✅ |
| LLM-роутер | `http://127.0.0.1:8002/v1` | ✅ v4.0 |
| zina2-router | `http://127.0.0.1:8003/v1` | ✅ (DeepSeek Flash→Pro→V3) |
| zina2-router-8005 | `http://127.0.0.1:8005/v1` | ✅ v2.0 (systemd, Flash→Pro→Ollama) |
| Скрипты | `/opt/zinaida/scripts/`, `/opt/zinaida/SmmFabrika/` | ✅ |
| Конфиг Hermes | `/root/.hermes/config.yaml` | ✅ |
| SmmFabrika очередь | `/opt/zinaida/SmmFabrika/queue/` | ✅ |
| Ассеты | `/opt/zinaida/SmmFabrika/assets/` | ✅ |
| OneDrive (rclone) | Синхронизация с `Виктория/Контент/` | ✅ |
| Replicate Hermes плагин | `/root/.hermes/plugins/image_gen/replicate/` | ✅ 9 моделей |
| image_gen конфиг | `image_gen.provider: replicate, model: flux-dev` | ✅ |
|| Паспорт визуала | `/opt/zinaida/zinaida_passport/` | ✅ |
|| Фото Зинаиды | `/opt/zinaida/zinaida_passport/generated/` | ✅ аватар zinaida_01.jpg |
|| design_assets.db | `/opt/zinaida/memory/design_assets.db` | ✅ 26 assets, 10 feedback |
|| design_feedback.md | `/opt/zinaida/shared_memory/design_feedback.md` | ✅ |
---

## 3. ПРОВАЙДЕРЫ И ПОИСК

### LLM-роутер (zinaida_openai_proxy, порт 8002)
DeepSeek Flash (основной), Mistral (запасной).

### Поиск в интернете
**BrightData SERP API** — основной поиск. 5000 запросов/мес бесплатно.
Скрипт: `/opt/zinaida/scripts/web_search_brightdata.py`
Ключ: BRIGHTDATA_KEY в .env

**DuckDuckGo** — запасной поиск (через ddgs).
Tavily — мёртв (432), заменён на BrightData.

### zina2-router (порт 8003)
Чистый DeepSeek-роутер: Flash → Pro (чувствительно) → V3.

### Vision (порт 8901)
GitHub (gpt-4o-mini) → Mistral (mistral-large) → Ollama (gemma3:27b). Три провайдера, все работают.

---

## 4. ПЛАНИРОВЩИК (cron)

**Скрипт:** `/opt/zinaida/scripts/content_factory.py`
**Статус cron:** последний запуск — ok=8, skip=16, fail=0
**Публикация:** НЕ НАСТРОЕНА. Посты в очереди, но не публикуются.
**Контент-план:** НЕ НАСТРОЕН. Дата-сет пуст.

---

## 5. СИСТЕМЫ ПАМЯТИ

| Система | Тип | Статус |
|---------|-----|--------|
| MEMORY.md | Быстрая память (2200 символов) | ✅ используется |
| Zinaida Memory MCP | Ручная память (SQLite, безлимит) | ✅ 8 инструментов |
| **Mem0** (24.6k⭐) | **Автоматическая семантическая память** | ✅ **Qdrant + DeepSeek, 17+ записей** |

**agentmemory удалён 10.07.2026** — заменён на Mem0. Не существует. Не искать.

**Mem0:**
- Qdrant v1.18.2 (Docker, systemd qdrant-mem0.service, порт 6333, on_disk=True)
- LLM: DeepSeek через роутер 8003 (экстракция фактов на русском)
- Embedding: intfloat/multilingual-e5-base (768-dim) — русский
- MCP сервер: /opt/zinaida/mem0/mem0_mcp_server.py (7 инструментов)
- 15 seed-памятей загружено
- Бэкапы: Qdrant snapshot ежедневно 5:00

**Zinaida Memory MCP:**
- Сервер: `/opt/zinaida/memory/memory_server.py`
- База: `/opt/zinaida/memory/memory.db`
- Инструменты: `memory_save`, `memory_search`, `memory_get`, `memory_link`, `memory_recent`, `memory_by_tag`, `memory_graph`, `memory_stats`
- Схема БД: memories + tags + links + revisions + FTS5

---

## 6. ВИДЕО-ГЕНЕРАЦИЯ (тест)

- **Hyperframes (HeyGen):** протестирован — неестественно, отклонён
- **Remotion:** не тестирован — в плане
- **Статус:** отложено до запуска контент-завода

---

## 7. ПРИНЯТЫЕ РЕШЕНИЯ (стеки)

| Решение | Суть | Дата |
|---------|------|------|
| **Стек управления** | Ядро: SQLite WAL + MCP + Hermes Cron. Визуал: Hermes Workspace V2. Голос: Pipecat. | 09.07.2026 |
| **После запуска КЗ** | Claw3D (3D офис), генерация видео | отложено |
| **Memory system** | MCP Memory Server + agentmemory + Obsidian vault | 09.07.2026 |

---

## 8. СТИЛЬ И ПРАВИЛА

- ДНК Зинаиды: неприкосновенна
- Стиль «Шквальный» (16 правил): неприкосновенен
- Чёрный список табу: активен
- Все LLM-запросы — через роутер `localhost:8002/v1`
- Ключи из .env НЕ выводить
- Глаголы строго женского рода

---

## 9. ПЛАТФОРМЫ

| Платформа | Формат | Статус интеграции |
|-----------|--------|-------------------|
| VK | 1080×1080 | ❌ |
| Instagram | 1080×1080 / 1080×1920 | ❌ |
| Dzen | 1200×630 | ❌ |
| Telegram | 1280×720 | ❌ |
| Odnoklassniki | 1080×1080 | ❌ |
| Pinterest | 1000×1500 | ❌ |
| MessengerMax | - | ❌ |
| YandexMessenger | - | ❌ |

---

## 10. ЧТО НЕ ДОДЕЛАНО (КОНВЕЙЕР)

| Этап | Статус | Что нужно |
|------|--------|-----------|
| Генерация постов | ✅ Работает | - |
| RAG-запросы | ✅ Работает | - |
| Очередь постов | ✅ Есть | - |
| Система памяти | ✅ Работает | - |
| **Публикация VK** | ❌ НЕТ | Написать/доработать адаптер |
| **Публикация TG** | ❌ НЕТ | Написать/доработать адаптер |
| **Публикация Dzen** | ❌ НЕТ | Написать/доработать адаптер |
| **Контент-план** | ❌ НЕТ | Заполнить content_rotation.db |
| **Куратор** | ❌ НЕТ | Настроить сбор метрик |
| **Петля обучения** | ❌ НЕТ | Настроить EMA-аналитику |
| **Hermes Workspace V2** | ❌ НЕ СТАВИЛ | Поставить после КЗ |
| **Pipecat (голос)** | ❌ НЕ СТАВИЛ | Поставить после КЗ |
| **Claw3D** | ❌ ОТЛОЖЕНО | После запуска КЗ |
| **Генерация видео** | ❌ ОТЛОЖЕНО | Искать на консилиуме |

---

## 11. КЛЮЧЕВЫЕ ФАЙЛЫ ДЛЯ СТАРТА

1. `/opt/zinaida/AGENTS.md` — операционные правила
2. `/opt/zinaida/inbox/SMM_DEV_RULES.md` — мастер-правила
3. `/opt/zinaida/HANDOVER_TO_NEW_CHAT.md` — хэндовер
4. `/opt/zinaida/memory/SYSTEM_SNAPSHOT.md` — слепок системы (этот файл)
5. `/root/.hermes/config.yaml` — конфиг Hermes
6. `/opt/zinaida/meta_agent/zinaida_openai_proxy.py` — роутер
7. `/opt/zinaida/memory/memory_server.py` — MCP Memory сервер
8. `/opt/zinaida/shared_memory/roadmap.md` — дорожная карта

---

*Слепок создан: 2026-07-09. Обновлять при серьёзных изменениях.*

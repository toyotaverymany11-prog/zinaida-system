---
name: transfer-system
description: "ПОЛНЫЙ ПЕРЕНОС ВСЕЙ СИСТЕМЫ. Два режима: (1) Олег пишет «перенос» → показать дамп, ждать решения. (2) Передача новому агенту → интерактивная установка: спросить Telegram/темы/ключи/GitHub. Скрипт: transfer_system_builder.py"
version: 2.0.0
metadata:
  hermes:
    triggers: [перенос]
    tags: [триггер, перенос, система, дамп, гитхаб, хэндовер]
    related_skills: [system-guarantee-protocol, zinaida-operations, zinaida-tech-protocol, memory-first-protocol]
author: Zinaida-System
tags: [триггер, перенос, система, полный-аудит, github, хэндовер]
triggers:
  - перенос
  - перенос системы
  - system transfer
  - полный перенос
  - передать систему
---

# ПОЛНЫЙ ПЕРЕНОС СИСТЕМЫ (Transfer Protocol)

## 🚨 ЖЁСТКИЙ ТРИГГЕР: ПЕРВОЕ СЛОВО «ПЕРЕНОС»

### РЕЖИМ 1: ОЛЕГ ПИШЕТ «ПЕРЕНОС» — ТОЛЬКО ДАМП
Первое слово «перенос» от Олега.

НЕМЕДЛЕННО:
1. MEDIA:/opt/zinaida/design/transfer_activate.gif
2. `terminal(command="python3 /opt/zinaida/scripts/transfer_system_builder.py")`
3. Показать Олегу полный дамп системы
4. **НИЧЕГО НЕ ЗАПУСКАТЬ.** Ждать решения Олега: что переносить, что не трогать

### РЕЖИМ 2: ПЕРЕДАЧА НОВОМУ АГЕНТУ — ИНТЕРАКТИВНАЯ УСТАНОВКА
Когда система передаётся другому человеку — агент проводит интерактивную настройку (см. раздел ИНТЕРАКТИВНАЯ УСТАНОВКА ниже).

## КЛЮЧЕВОЕ ПРАВИЛО: АБСОЛЮТНАЯ ПОЛНОТА

**НЕЛЬЗЯ упустить ничего.** Система «ПЕРЕНОС» должна поднять ВСЁ, что есть на сервере. Ни одна фишка, ни один триггер, ни один навык не должен остаться вне слепка.

Если есть сомнение «это важно или нет?» — ВКЛЮЧИТЬ. Лучше лишнее, чем пропущенное.

## ЧТО СОБИРАЕТ ПЕРЕНОС (полный реестр)

### 1. ДНК И ЛИЧНОСТЬ (4 файла)
- `SOUL.md` — ядро персонажа, мировоззрение, тон, табу
- `AGENTS.md` — операционные правила, протоколы, триггеры
- `MEMORY.md` — долговременная память
- `USER.md` — профиль Олега (предпочтения, запреты, поправки)

### 2. ВСЕ ТРИГГЕРЫ (первое слово = команда)
| Триггер | Что делает | Где описан |
|---------|-----------|-----------|
| **техник** | Полная диагностика 8 зон | AGENTS.md, навык zinaida-tech-protocol |
| **маркетинг** | Маркетинг-активация + воронка + Todoist | SOUL.md, навык marketing-guide-2026 |
| **писатель** | Конвейер генерации постов | Навык zinaida-writer-startup, oleg-writing-rules |
| **дизайнер/design** | Визуал, шрифты, карусель | Навык designer, brand-font-zinaida |
| **telegram/телеграм** | Статус бота | AGENTS.md |
| **глубокое исследование** | 4-раундовый оркестратор | SOUL.md, навык multi-agent-deep-research |
| **карусель** | Инструмент создания каруселей | Навык carousel |
| **реши системно** | 13-точечное внедрение | Навык system-guarantee-protocol |
| **запомни/зафиксируй** | 6-точечная фиксация | AGENTS.md |
| **перенос** | Этот навык — сбор всей системы | Навык transfer-system |

### 3. ВСЕ НАВЫКИ (полный инвентарь ~130 навыков)

**Категории навыков на сервере:**

**Zinaida/Копирайтинг (13 навыков):**
- `zinaida-writer-startup` — протокол писателя
- `zinaida-context-startup` — контекстная архитектура
- `zinaida-operations` — операционные правила
- `oleg-writing-rules` — мастер-файл правил Олега
- `zinaida-content-factory` — обучение (архив)
- `writing-training-2026-07-11` — тренировки
- `brand-font-zinaida` — шрифт бренда
- `carousel` — карусель
- `evreyka-style` — стиль Вики Рипа
- `copywriting` — копирайтинг
- `designer` — дизайн
- `zinaida-character-startup` — разработка персонажа
- `marketing-guide-2026` — полный гайд маркетинга

**DevOps/Инфраструктура (10+ навыков):**
- `zinaida-tech-protocol` — технический протокол
- `memory-first-protocol` — память прежде всего
- `system-guarantee-protocol` — гарант внедрения
- `production-change-protocol` — изменения production
- `provider-audit-reference` — аудит провайдеров
- `router-8005-architecture` — архитектура 8005
- `zinaida-n8n-kill` — убийство n8n
- `ufw-port-security` — безопасность портов
- `brightdata-search` — поиск BrightData
- `hermes-group-chat` — Group Chat Hermes
- `hermes-group-chat-agent` — GC агенты
- `hermes-studio-diagnostics` — диагностика
- `gigachat-integration` — GigaChat
- `hermes-image-gen` — генерация изображений
- `hermes-display-tool-progress` — display tool progress
- `tavily-search` — Tavily (мёртв)
- `webhook-subscriptions` — вебхуки
- `zinaida-promise-protocol` — протокол обещаний
- `provider-master-trigger` — триггер провайдеров
- `deep-research-agent-checklist` — чек-лист агентов

**Разработка (20+ навыков):**
- `subagent-driven-development` — разработка через сабагентов
- `test-driven-development` — TDD
- `systematic-debugging` — системная отладка
- `simplify-code` — упрощение кода
- `requesting-code-review` — код-ревью
- `spike` — прототипирование
- `plan` — планирование
- `writing-plans` — написание планов
- `claude-code`, `codex`, `opencode` — делегирование
- `kanban-codex-lane`, `kanban-orchestrator`, `kanban-worker` — Kanban
- `superpowers` — суперсилы
- `hermes-agent` — конфиг Hermes
- `hermes-agent-skill-authoring` — создание навыков
- `python-debugpy`, `node-inspect-debugger` — отладка
- `debugging-hermes-tui-commands` — отладка TUI

**Исследования (6+ навыков):**
- `multi-agent-deep-research` — мульти-агентное исследование
- `zinaida-research-swarm` — исследовательский рой
- `deep-research-agent-checklist` — чек-лист
- `consilium-collect` — утренний консилиум
- `arxiv`, `polymarket`, `blogwatcher`, `llm-wiki`

**Дизайн/Видео (~15 навыков):**
- `design-md`, `sketch`, `claude-design`, `excalidraw`
- `ascii-art`, `ascii-video`, `p5js`, `pixel-art`
- `architecture-diagram`, `markdown-viewer`, `humanizer`
- `comfyui`, `remotion`, `hyperframes`
- `baoyu-comic`, `baoyu-infographic`, `baoyu-article-illustrator`
- `ai-video-generation`, `grok-image-to-video`
- `replicate-image-gen`, `apikey-image-gen`
- `popular-web-designs`

**ML/AI (8+ навыков):**
- `llama-cpp`, `vllm`, `obliteratus`
- `huggingface-hub`, `weights-and-biases`, `lm-evaluation-harness`
- `dspy`, `segment-anything`, `audiocraft`
- `zinaida-replicate-api`, `mcp-memory-system`

**Платформы/Интеграции (15+ навыков):**
- `todoist-planner`, `notion`, `airtable`, `linear`
- `obsidian`, `google-workspace`, `nano-pdf`
- `spotify`, `xurl`, `himalaya`
- `youtube-content`, `gif-search`, `heartmula`, `songsee`
- `maps`, `powerpoint`, `ocr-and-documents`
- `teams-meeting-pipeline`, `jupyter-live-kernel`

**Медиа/MCP (5 навыков):**
- `native-mcp` — MCP клиент
- `media-use` — медиа ОС
- `github-models-vision` — Vision провайдер
- `mcp-memory-system` — три уровня памяти

**Безопасность/Тестирование:**
- `godmode` — ред-тейминг
- `dogfood` — QA
- `quality-assurance-pipeline` — качество ответов

### 4. ИНФРАСТРУКТУРА

**3 роутера:**
| Роутер | Порт | Файл | Сервис | Назначение |
|--------|------|------|--------|-----------|
| Zinaida-Router | 8002 | `/opt/zinaida/meta_agent/zinaida_openai_proxy.py` | `zinaida-router.service` | Бесплатные провайдеры (Mistral → GitHub) |
| Zina2-Router | 8003 | `/opt/zinaida/meta_agent/zina2_router.py` | `zina2-router.service` | DeepSeek Flash → Pro |
| 8005 Super Cascade | 8005 | `/opt/zinaida/meta_agent/router_8005_v2.py` | `zina2-router-8005.service` | Полный каскад (НЕ ТРОГАТЬ!) |

**5 провайдеров (статус на 15.07.2026):**
| Провайдер | Статус | Ключи | Модели |
|-----------|--------|-------|--------|
| DeepSeek | ✅ Работает | 1 ключ (в .env) | Flash (deepseek-chat), Pro (deepseek-reasoner) |
| Mistral | ✅ Работает | 3 ключа | mistral-large-latest (бесплатно) |
| GitHub Models | ✅ Работает | 2 токена | gpt-4o-mini (бесплатно, 15 RPM) |
| Ollama | ❌ 401 | 3 ключа (мертвы) | gemma3:4b, ministral-3:3b |
| GigaChat | ❌ SSL | OAuth2 | GigaChat |

**Базы данных:**
- `phases.db` — 41 фаза отношений
- `smm_rag.db` — 3975 записей FTS
- `content_rotation.db` — ротация контента
- `analytics.db` — метрики, EMA
- `smm_factory.db` — фабрика контента
- `puls_validation.db` — валидация пульса
- `memory_store.db` — Holographic memory

**Systemd сервисы (активные):**
- `zinaida-router.service` (8002)
- `zina2-router.service` (8003)
- `zina2-router-8005.service` (8005 — НЕ ТРОГАТЬ)
- `zinaida-telegram-bot.service` (@DCHP_Shtab_bot)
- `zinaida-core.service` (legacy)
- `caddy.service` (Caddy)
- `hermes-gateway.service` (Gateway)
- `hermes-web-ui.service` (Hermes Studio v0.6.28)
- `zinaida-weekly-backup.timer` (еженедельный бэкап)

**Docker контейнеры:**
- `qdrant` — Mem0 векторная БД
- `redis` — Mem0 кэш

**Дополнительно:**
- `zinaida-sync.service` — однодрайв синк
- `vision proxy` (8901) — прокси для vision
- `UFW` — порты 2222, 80, 443, 5000

### 5. ЖЕЛЕЗНЫЕ ПРОТОКОЛЫ

| Протокол | Описание | Где хранится |
|----------|---------|-------------|
| Правило №0 (обещания) | Сказала «сделаю» → делаю до конца, без переключений | AGENTS.md, SOUL.md, навык zinaida-promise-protocol |
| Правило тестирования | 3 проверки перед «готово» (компонент → интеграция → Telegram/веб) | AGENTS.md, SOUL.md |
| Memory-first protocol | Перед любым действием с провайдерами — сначала память | Навык memory-first-protocol |
| System-guarantee-protocol | «Реши системно» → 13 точек внедрения | Навык system-guarantee-protocol |
| Production-change-protocol | Изменение production — бэкап → сторонка → тест → интеграция | Навык production-change-protocol |
| Запрет редактирования production | НЕ через sed/echo/python, только через MCP API и CLI | SOUL.md |
| Дата-правило | Перед любой датой — `date` из системы | AGENTS.md |
| 6-точечная фиксация | «запомни/зафиксируй» → Mem0 + Hermes + навык + SOUL + AGENTS + updates_log | AGENTS.md |

### 6. ПРОЕКТЫ

**Otnoshenya (контент-завод):**
- `/opt/zinaida/projects/Otnoshenya/marketing/` — 26 файлов: воронка, метрики, платформы, монетизация, user_journeys, позиционирование, паспорт, стиль, PAS, тарифы, CTA-библиотека
- `/opt/zinaida/projects/Otnoshenya/product/` — 8 файлов: обзор, карта, тех-слепок, readiness, финансы, unit-economics
- `/opt/zinaida/projects/Otnoshenya/design/` — дизайн-файлы
- `/opt/zinaida/projects/Otnoshenya/pisatel/` — писатель (14_WRITER_FORMATION.md и др.)
- `/opt/zinaida/projects/Otnoshenya/legal/` — 06_claims_safety.md
- `/opt/zinaida/projects/Otnoshenya/copywriting/` — копирайтинг
- `/opt/zinaida/projects/Otnoshenya/carousel/` — карусели

**6 инструментов Лаборатории отношений:**
| Инструмент | Марк. название | Ключ. слово | Токены |
|-----------|---------------|------------|-------|
| Детектив | ПРОФАЙЛЕР | ДЕТЕКТИВ | 12 |
| Телепат | ПРЕДИКТОР | ТЕЛЕПАТ | 8 |
| Тренажёр | ДУЭЛЬ | ТРЕНАЖЁР | 15 |
| Радар | СКАНЕР | РАДАР | 12 |
| Паттерны | ДОСЬЕ | ПАТТЕРНЫ | 1+2 |
| Разбор | ЭКСПЕРТИЗА | РАЗБОР | 18 |

**Тарифы (предв.):** Start 490₽/250ток, Plus 1290₽/750ток, Max 2990₽/1800ток

**SmmGlobal:**
- `/opt/zinaida/inbox/PROJECTS/SmmGlobal/` — глобальный SMM проект

### 7. МЕТРИКИ 2026

- Saves: 40% (в 3× ценнее лайков)
- DM Shares: 35% (в 3-5× ценнее лайков)
- Watch Time: 15%
- Comments: 7%
- Likes: 3%
- FAS отсрочка до конца 2026
- Conversion: median 2.35%, top 11.45%
- Цели воронки: пост→TG 5-10%, TG→paywall 15-25%, free→paid 8-12%, retention M2 ≥ 60%

### 8. КЛЮЧЕВЫЕ ДИРЕКТОРИИ

```
/opt/zinaida/
├── memory/ — память + БД + слепки
│   ├── SYSTEM_SNAPSHOT.md — живой слепок (читай перед стартом!)
│   ├── handover_writer_next_chat.md — хэндовер писателя
│   ├── oleg_writing_rules_master.md — правила Олега
│   ├── phases.db, smm_rag.db, analytics.db
│   └── unified_memory.db
├── meta_agent/ — роутеры, прокси
│   ├── zinaida_openai_proxy.py (8002)
│   ├── zina2_router.py (8003)
│   └── router_8005_v2.py (8005 — НЕ ТРОГАТЬ!)
├── scripts/ — ~40 скриптов
│   ├── tech_diagnostic.py — диагностика 8 зон
│   ├── deep_research_orchestrator.py — оркестратор исследований
│   ├── marketing_activate.sh — маркетинг-активация
│   ├── transfer_collect.sh — сбор системы для переноса (этот навык)
│   ├── post_analyzer.py — анализатор постов
│   └── ...
├── todoist_integration/ — Todoist + напоминания
├── telegram_bot/ — Telegram-бот
├── projects/Otnoshenya/ — проект Отношения
├── SmmFabrika/ — фабрика контента
├── design/ — дизайн-файлы
├── sandbox/ — песочница
└── shared_memory/ — shared память
```

## ИНТЕРАКТИВНАЯ УСТАНОВКА ДЛЯ НОВОГО АГЕНТА

Когда система передаётся другому человеку — агент проводит шаги:

**ШАГ 1 — Telegram:** «Нужен свой бот. Зарегистрируй через @BotFather, дай токен.»
**ШАГ 2 — Темы:** «Что будешь исследовать? Консилиум настрою под тебя.»
**ШАГ 3 — DeepSeek:** «Ключ с api.deepseek.com. Принесёшь — подключу роутер 8003.»
**ШАГ 4 — GitHub:** «Куда выгрузить? Дай ссылку на репозиторий.»
**ШАГ 5 — Выбор:** «Что нужно? Контент-завод? Аналитика? Планировщик? VK?»
**ШАГ 6 — Финало:** Telegram ❌ | DeepSeek ❌ | GitHub ❌ | Темы ❌ | Выбор ❌ (0%)

## ФАЙЛЫ
- Скрипт сборщика: `/opt/zinaida/scripts/transfer_system_builder.py`
- Директория дампов: `/opt/zinaida/outbox/transfer_system/`
- GIF анимации: `/opt/zinaida/design/transfer_activate.gif`

### 9. ПРИНЦИПЫ ПЕРЕНОСА

1. **Всё или ничего.** Нельзя собрать «основное» и надеяться что остальное подтянется. Каждый файл, каждый навык, каждый триггер — вручную проверен.
2. **Выгрузка на GitHub.** Как делали с Фёдором: собираем дамп → заливаем в репозиторий → Олег скачивает в новом чате.
3. **После переноса — тест.** Проверить что новый чат реально поднял все триггеры (написать «техник», «маркетинг», «писатель» — каждое должно сработать).
4. **Ничего не забыть.** Есть сомнение — включай. Лучше 10 лишних ссылок чем 1 пропущенная фишка.

## ⚠️ УРОК: ДОВЕРЯЙ НО ПРОВЕРЯЙ (15.07.2026)
Первая версия transfer_system_builder.py дала НЕВЕРНЫЕ цифры:
- Показала ~130 навыков → реально **147**
- Показала 6 БД → реально **29**
- Показала 9 systemd → реально **17**
- Упустила целиком: **VK ботов, Group Chat (15 скриптов), Voice Assistant, Character docs, Design passport**

**Почему:** один shallow `find -maxdepth 2` пропустил половину инфраструктуры. Скрипты в `scripts/`, GC агенты, voice assistant, character docs — все лежат глубже.

**Правило для любых будущих аудитов:** минимум 3 разных инструмента проверки. Никогда не полагаться на один `find` или одно `ls`. Использовать:
1. `systemctl`, `ss`, `docker ps` — системные утилиты
2. `find -maxdepth 4` с несколькими exclude — файловые системы
3. `os.walk` с подсчётом — навыки, скрипты, базы

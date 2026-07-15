# РЕФЕРЕНСЫ — БАЗЫ, ИССЛЕДОВАНИЯ, ИНСТРУМЕНТЫ

## БАЗЫ ДАННЫХ

| Что | Путь | Размер | Содержит |
|-----|------|--------|----------|
| **RAG-база знаний** | `/opt/zinaida/memory/smm_rag.db` | 8.2 MB | 3975 записей по психологии отношений, мужской психологии, поведению |
| **Фазы отношений** | `/opt/zinaida/inbox/PROJECTS/Otnoshenya/phases.db` | 56 KB | 41 фаза: описание, боли, хуки, CTA |
| **Ротация контента** | `/opt/zinaida/inbox/PROJECTS/Otnoshenya/content_rotation.db` | 20 KB | План публикаций |
| **Аналитика** | `/opt/zinaida/memory/analytics.db` | — | Метрики постов, EMA-веса |

**RAG-запрос:** `python3 /opt/zinaida/scripts/rag_query.py "текст запроса"`
Либо прямой SQL: `sqlite3 /opt/zinaida/memory/smm_rag.db "SELECT * FROM chunks WHERE content LIKE '%текст%'"`

**Запрос фаз:** `sqlite3 /opt/zinaida/inbox/PROJECTS/Otnoshenya/phases.db "SELECT * FROM phases WHERE id = N"`

---

## БИБЛИОТЕКИ КОНТЕНТА

| Библиотека | Путь | Что там |
|-----------|------|---------|
| **CTA-шаблоны** | `/opt/zinaida/inbox/PROJECTS/Otnoshenya/cta_library/` | identity, micro_commitment, open_loop — по 3 шт на тему (ghosting, marriage, silence) |
| **Хуки** | `/opt/zinaida/inbox/PROJECTS/Otnoshenya/hooks/templates/` | Шаблоны хуков по механикам |
| **Микро-истории** | `/opt/zinaida/inbox/PROJECTS/Otnoshenya/micro_stories/` | 6 историй по фазам A-F (тревога) |
| **Валидированные хуки** | `/opt/zinaida/inbox/validated_hooks_matrix.md` | Матрица проверенных хуков |
| **Экземпляры постов** | `/opt/zinaida/inbox/PROJECTS/Otnoshenya/exemplars/` | Примеры удачных постов |

---

## ПРАВИЛА И ПРОТОКОЛЫ

| Файл | Путь | Что содержит |
|------|------|-------------|
| Мастер-правила | `/opt/zinaida/inbox/SMM_DEV_RULES.md` | Архитектура, чёрный список, протокол атомарности |
| Ядро контент-фабрики | `/opt/zinaida/inbox/PROJECTS/Otnoshenya/SMM_FACTORY_CORE.md` | 7 слоёв сборки, Token Budgeting, порядок отрезания |
| Манифест проекта | `/opt/zinaida/inbox/PROJECTS/Otnoshenya/MASTER_MANIFEST.md` | Полная карта проекта |
| Дорожная карта | `/opt/zinaida/inbox/PROJECTS/Otnoshenya/MASTER_ROADMAP.md` | Планы развития |
| AGENTS.md (общий) | `/opt/zinaida/AGENTS.md` | Жёсткие правила для всех агентов |
| AGENTS.md (проект) | `/opt/zinaida/inbox/PROJECTS/Otnoshenya/AGENTS.md` | Архитектура и стратегия |
| Паспорт Зинаиды | `/opt/zinaida/shared_memory/ZINAIDA_PASSPORT.md` | Внешность, стиль, личность |

---

## СИСТЕМНЫЕ КОМПОНЕНТЫ

| Компонент | Путь/Порт | Описание |
|-----------|-----------|----------|
| **Роутер Zina2 (основной)** | `http://127.0.0.1:8003/v1` | DeepSeek Pro — генерация контента |
| **Роутер Zinaida** | `http://127.0.0.1:8002/v1` | GigaChat/Mistral fallback |
| **Контент-фабрика** | `/opt/zinaida/SmmFabrika/content_factory.py` | Пакетная генерация постов |
| **Очередь публикации** | `/opt/zinaida/SmmFabrika/queue/` | Готовые посты по платформам |
| **Ассеты** | `/opt/zinaida/SmmFabrika/assets/` | Фото, шрифты |
| **Дашборд слепка** | `/opt/zinaida/memory/SYSTEM_SNAPSHOT.md` | Живой статус системы |
| **Лог обновлений** | `/opt/zinaida/shared_memory/updates_log.md` | История изменений |
| **Лог ошибок** | `/opt/zinaida/ERROR_LOG` | Хроника падений |

---

## ПАПКА ПРОЕКТА — ВСЕ ТЕМЫ

```
/opt/zinaida/projects/Otnoshenya/
├── design/         — дизайн (Лера)
├── pisatel/        ← ВЫ ЗДЕСЬ
├── copywriting/    — копирайтинг (легаси)
└── marketing/      — маркетинг и публикация

### Файлы папки писателя

| Файл | Содержит |
|------|----------|
| `00_README.md` | Главный манифест — 14 разделов |
| `01_style_scheme.md` | 16 правил стиля «Шквальный» |
| `02_blacklist.md` | 18 категорий, 200+ запрещённых фраз |
| `03_references.md` | Ссылки на базы, команды, инструменты |
| `04_platforms.md` | Карта 8 платформ с форматами |
| `05_statistics_base.md` | 30+ фактов для хуков с готовыми формулировками |
| `06_phases_map.md` | 35+ подфаз от А1 до Е5 с хуками и болями |
```

---

## ПОЛЕЗНЫЕ КОМАНДЫ

```bash
# Поиск в RAG
sqlite3 /opt/zinaida/memory/smm_rag.db "SELECT content FROM chunks WHERE content LIKE '%ключевое слово%' LIMIT 5"

# Скрипт RAG-запроса
python3 /opt/zinaida/scripts/rag_query.py "текст запроса"

# Посмотреть фазу отношений
sqlite3 /opt/zinaida/inbox/PROJECTS/Otnoshenya/phases.db "SELECT * FROM phases WHERE name LIKE '%тревог%'"

# Посмотреть готовые посты в очереди
ls /opt/zinaida/SmmFabrika/queue/Telegram/

# Системный слепок
cat /opt/zinaida/memory/SYSTEM_SNAPSHOT.md
```

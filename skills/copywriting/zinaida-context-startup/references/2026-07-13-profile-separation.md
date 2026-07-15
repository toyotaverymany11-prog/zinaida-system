# Hermes Profile Separation Architecture (Профильная изоляция)

Дата: 13.07.2026
Проект: Разделение профилей для Зинаиды (контент-завод vs разработка персонажа)

## Проблема

Один агент Hermes работал с двумя разными проектами:
1. **Контент-завод** — писать посты, делать картинки/карусели, SMM
2. **Разработка персонажа** — проектировать AI-персонажа, промпты, продукт, архитектуру

Оба проекта про Зинаиду, но контексты НЕ должны смешиваться. Навыки, память, ДНК — разные.

## Решение: Профили Hermes

У Hermes есть **профили** — полностью изолированные окружения. Каждый профиль имеет:
- Свою SOUL.md (ДНК)
- Свои AGENTS.md (роли, доступы, запреты)
- Свой .hermes.md (протоколы работы)
- Свою MEMORY.md (цели и прогресс)
- Свои навыки (skills/enabled в config.yaml)
- Свои custom_providers (роутеры, модели)
- Свои cron-задачи
- Свои сессии (state.db)

## Структура

```
~/.hermes/profiles/
├── default/             # Контент-завод (основной профиль)
│   ├── SOUL.md
│   ├── AGENTS.md
│   ├── skills/
│   └── config.yaml*     # если нет — использует ~/.hermes/config.yaml
├── zinaida/             # Разработка персонажа
│   ├── SOUL.md
│   ├── AGENTS.md
│   ├── .hermes.md
│   ├── MEMORY.md
│   ├── config.yaml      # полная копия с собственными настройками
│   └── skills/          # только нужные навыки
└── agent2/              # Кодер (Григорий)
    ├── ...              # аналогично
```

## Как настроить новый профиль

### 1. Создать директорию
```bash
mkdir -p ~/.hermes/profiles/<name>/
cd ~/.hermes/profiles/<name>/
```

### 2. Записать SOUL.md
Ядро идентичности: кто ты, твоя роль, границы. Полная ДНК профиля.

### 3. Записать AGENTS.md
Роли, доступы (READ/WRITE к каким директориям), запреты, правила работы.

### 4. Записать .hermes.md
Операционные протоколы: диагностика, тестирование, чёрный список.

### 5. Записать MEMORY.md
Текущие цели, загруженные документы, архитектурные решения, todo.

### 6. Настроить config.yaml
```yaml
custom_providers:
  - api_key: <key>
    base_url: http://<host>:<port>/v1
    model: <model-name>
    name: <provider-name>
model:
  default: <model-name>
  provider: custom:<provider-name>
skills:
  enabled:
    - skill-name-1
    - skill-name-2
terminal:
  cwd: /path/to/workspace
```

### 7. Создать workspace
```bash
mkdir -p /path/to/workspace/{docs,memory,decisions,specs}
```

### 8. Настроить навыки
Только те, что нужны для задач профиля. Удалить лишние из `~/.hermes/profiles/<name>/skills/`.

## Контекстная изоляция

**Как это работает:**
- Каждый профиль загружает свою SOUL.md/AGENTS.md при старте
- Memory tool (Hermes memory) — глобальная, видна всем профилям. Нужно помечать какие записи к какому профилю.
- Mem0 — можно изолировать по user_id/agent_id
- Сессии — изолированы (у каждого профиля свой state.db)
- Навыки — изолированы (только enabled в конфиге)

**Как переключаться:**
- В веб-интерфейсе: выбор агента = выбор профиля
- В CLI: `hermes config set profile <name>` + `/reset`

## Практический пример (13.07.2026)

### default (контент-завод)
- SOUL.md: «инженер-архитектор стратегических глубин»
- Навыки: copywriting, carousel, designer, zinaida-context-startup
- Рабочая папка: /opt/zinaida/inbox/PROJECTS/Otnoshenya/
- Провайдер: Zinaida-Router (8002)

### zinaida (разработка персонажа)
- SOUL.md: «архитектор AI-персонажа и продуктовый дизайнер»
- Навыки: autonomous-ai-agents, devops, research, github, zinaida-character-startup
- Рабочая папка: /opt/zinaida/character/
- Провайдер: 8005-Enhanced (универсальный роутер)

### agent2 (Григорий-кодер)
- SOUL.md: «инженер-разработчик мультиагентной системы»
- Навыки: software-development, devops, github
- Рабочая папка: /opt/zinaida/sandbox/
- Провайдер: deepseek-chat

## Ограничения

- Профили не видят сессии друг друга (session_search не работает между профилями)
- Memory tool — глобальный, могут быть коллизии если два профиля пишут одно и то же
- Для полной изоляции данных пользователя — нужна отдельная БД на профиль
- При переключении профиля — гейтвей перезапускается (теряются фоновые процессы)

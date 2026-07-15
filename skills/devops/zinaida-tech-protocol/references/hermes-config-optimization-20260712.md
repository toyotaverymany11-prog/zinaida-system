# Hermes Config Optimization — кейс Техник 9 (12.07.2026)

## Контекст

Олег попросил провести глубокое исследование: «что мы упускаем в Hermes,
какие современные технологии не используем, что усилит нашу работу».

Был запущен deep_research_orchestrator.py с темой Hermes Agent/Studio.
Исследование выявило несколько направлений, часть — BS (не знало что у нас
уже есть), часть — реально ценные.

## Что проверили и отклонили

### Hindsight (Vectorize.io)
- **Точность:** 94.6% на LongMemEval vs 67.6% у Mem0
- **Цена:** $15/мес за retain (облачная версия). Есть локальная self-hosted.
- **Вердикт:** Платный. Наш Mem0 + Holographic дают то же самое бесплатно.
  Точность 67.6% нас устраивает для текущих задач. Не внедрять.

### OpenViking (Volcengine)
- **Суть:** Open-source Context Database. Файловая система для памяти,
  не векторное хранилище. Экономия 80-90% токенов (многоуровневый поиск).
- **Вердикт:** Полная замена Qdrant. Новый сервер, перенос данных,
  риск дестабилизации памяти. Не окупает трудозатраты. Не внедрять.

### Hermes Cron
- **Суть:** Встроенный cron в Hermes с `no_agent mode` (бесплатно,
  изолированные сессии). Команды: `hermes cron create`, `hermes cron list`.
- **Вердикт:** Systemd таймеры работают и надёжны. Hermes cron —
  ещё один слой, который может упасть. Не внедрять.

### Composio MCP Gateway
- **Суть:** 1000+ интеграций (Slack, Notion, GitHub, Jira) через MCP.
- **Вердикт:** РФ блокировки. Не будет работать стабильно. Не внедрять.

## Что внедрили

### 1. memory.provider: holographic

**До:** `memory.provider: ''` — автоматической памяти нет.
Mem0 только через ручной MCP вызов.

**После:** `memory.provider: holographic` — автоматическая экстракция
и инжекция фактов. Локальный SQLite, без API ключей.

**Команда:** `hermes memory setup holographic`

**Проверка:** `hermes memory status` → Provider: holographic ✅

**Важно:** `hermes memory setup mem0` — это облачный API (app.mem0.ai),
не наш локальный Qdrant. Не путать.

### 2. delegation.provider: mistral

**До:** `delegation.model: ''` — суб-агенты на DeepSeek (дорого).

**После:**
- `delegation.provider: mistral`
- `delegation.model: mistral-large-latest`
- `delegation.subagent_auto_approve: true`

**Команды:**
```bash
hermes config set delegation.provider mistral
hermes config set delegation.model mistral-large-latest
hermes config set delegation.subagent_auto_approve true
```

### 3. auxiliary.compression.provider: mistral

**До:** `auxiliary.compression.provider: auto` — DeepSeek сжимает сам себя.

**После:** Mistral сжимает контекст для DeepSeek.

**Команды:**
```bash
hermes config set auxiliary.compression.provider mistral
hermes config set auxiliary.compression.model mistral-large-latest
hermes config set auxiliary.compression.timeout 120
```

## Полезные команды

```bash
# Статус памяти
hermes memory status

# Просмотр секций конфига
hermes config show memory
hermes config show delegation
hermes config show auxiliary

# MCP серверы
hermes mcp list

# Установка значений
hermes config set <section.key> <value>
```

## Доступные провайдеры памяти (встроенные в Hermes v0.6.28)

Устанавливаются через `hermes memory setup <provider>`:
- `holographic` — локальный SQLite, без ключей ✅
- `mem0` — облачный API, требует `MEM0_API_KEY`
- `hindsight` — API key / local ($15/мес retain)
- `openviking` — API key / local (бесплатно)
- `honcho` — API key / local
- `byterover` — требует API key
- `retaindb` — API key / local
- `supermemory` — требует API key

## Итог

Из 8 исследованных направлений внедрены 3:
1. Автоматическая память (holographic)
2. Дешёвые суб-агенты (mistral delegation)
3. Сжатие контекста (mistral compression)

Остальные 5 отклонены с обоснованием (платные/риск/блокировки РФ).

# Техник 9 — Deep Research: Hermes Agent неиспользуемые возможности (12.07.2026)

## Контекст
Олег попросил проанализировать, что мы не используем в Hermes Agent из современных возможностей.
Проведено глубокое исследование (4 агента, 4 раунда). Полный отчёт:
`/opt/zinaida/sandbox/deep_research/20260712_091000_Hermes_Agent_и_Hermes_Studio___неиспольз/final_report.md`

## ВНЕДРЕНО (реально усилило, без рисков)

| Изменение | Команда | Эффект |
|-----------|---------|--------|
| **memory.provider: holographic** | `hermes memory setup holographic` | Авто-экстракция/инжекция фактов. Без API ключей |
| **delegation.provider: mistral** | `hermes config set delegation.provider mistral` | Суб-агенты на Mistral, не жрут DeepSeek |
| **delegation.model: mistral-large-latest** | `hermes config set delegation.model mistral-large-latest` | Дешёвая модель для фоновых задач |
| **subagent_auto_approve: true** | `hermes config set delegation.subagent_auto_approve true` | Без подтверждений |
| **model.default: deepseek-chat** | `hermes config set model.default "deepseek-chat"` | Починило gateway (падал с Zinaida-Router) |

## ОТКЛОНЕНО (с обоснованием)

| Идея | Причина |
|------|---------|
| **Hindsight** (94.6% точность памяти) | $15/мес платный. Holographic + Mem0 достаточно |
| **OpenViking** (80-90% экономии токенов) | Замена Qdrant — риск дестабилизации |
| **Hermes Cron** (вместо systemd) | systemd надёжнее |
| **Auxiliary.compression: mistral** | 8002 роутер путается при выборе модели для стрима |

## НАЙДЕНО В ХОДЕ РАБОТЫ

### 3 падающих Hermes cron jobs (paused):
1. **Lera watcher** — every 5m — `Provider returned an empty stream`
2. **Lera task processor** — every 3m — та же ошибка
3. **consilium-collect** — daily 6:00 — та же ошибка

Причина: модель `Zinaida-Router` не стримится. После фикса model.default на deepseek-chat — починится. После возобновления cron — проверить.

### Gateway не поднимался после restart:
Причина: cron job успевал запуститься ДО того как gateway стартовал → фейл → systemd restart loop.
Фикс: systemctl kill → reset-failed → start (не restart).

## Финал
- Диск: 75% → 52% (освобождено ~10G)
- Gateway: active, 0 ошибок
- Все 7 сервисов: active

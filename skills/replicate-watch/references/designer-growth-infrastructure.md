# Инфраструктура профиля дизайнера (Леры)

## Профиль Hermes
- **Имя профиля**: `lera`
- **Gateway**: запущен, model Zinaida-Router (порт 8002)
- **Порт API**: 8645
- **Роль**: дизайнер-визуализатор (обложки, фоны, карусели, генерация лиц)

## SOUL.md — личность
Файл: `/root/.hermes/profiles/lera/SOUL.md`
- Лера, 24 года, из Краснодара
- Женский род (дизайнер — девушка)
- Отвечает за визуал, НЕ за тексты (это Зинаида) и НЕ за код (это agent2)

## Навыки (skills.enabled)
- `generate-magazine-cover` — обложки
- `generate-quote` — цитаты-провокации
- `generate-scene` — кино-сцены
- `study-replicate` — изучение моделей Replicate
- `compare-face-models` — сравнение моделей для лиц
- `apikey-image-gen` — генерация через Hermes Web UI
- `tavily-search` — веб-поиск через Tavily
- `replicate-watch` — ежедневный мониторинг (текущий skill)

## Приоритет провайдеров
1. **Replicate API** (основной) — FLUX Dev, Recraft V3, Ideogram V3
2. **GigaChat** (резерв) — двухэтапно
3. **FusionBrain** (Kandinsky) — резерв
4. Фирменный градиент — аварийно

## Веб-поиск
- Tavily подключён через корневой config.yaml (`web.backend: tavily`)
- Ключ: `TAVILY_API_KEY` в `/root/.hermes/.env`
- Навык: `tavily-search`

## База знаний
- `/opt/zinaida/shared_memory/lera_research/` — дайджесты, находки
- `/opt/zinaida/shared_memory/approved_designs/` — одобренные визуалы

## Формат дайджеста (ежедневно)
Файл: `lera_research/DIGEST_YYYY-MM-DD.md`
```
# Дайджест 2026-07-08
## Новые модели
## Что узнала
## Что стоит попробовать
## Техники по коже/лицам
```

## Делегирование через Kanban
- Зинаида создаёт задачу с assignee=lera
- Лера подхватывает, делает 3 варианта, кладёт в queue/
- Если важная находка — создаёт Kanban-задачу Зинаиде с тегом #консилиум

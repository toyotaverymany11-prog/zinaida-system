# Маркетинг — полный аудит и карта источников (13.07.2026)

## ЧТО ПРОИЗОШЛО

Олег сказал «маркетинг» — я начала собирать данные из системы. В процессе выяснилось, что:
1. В `/opt/zinaida/projects/Otnoshenya/marketing/` уже существует полная маркетинговая папка (5 файлов)
2. Research-файлы с маркетинговой информацией разбросаны по knowledge/
3. Карточки соцсетей лежат в OneDrive (`/opt/zinaida/inbox/Контент/_social/`)
4. session_search не нашла явных записей Олега про воронку — архитектура воронки зафиксирована в файлах проекта

## ЧТО НЕ НАЙДЕНО (но Олег утверждает что обсуждал в Писателе)

- **Писатель 5/6 сессии:** содержат обсуждение стиля постов, структуры А, CTA, боли — НО не содержат явного описания воронки «с каких соцсетей куда ведём». Воронка НЕ обсуждалась в этих сессиях — обсуждались только форматы постов и инструменты.
- **Документ с конкретными каналами продаж:** не найден. ROADMAP.md — в статусе «план/ожидание» (Фаза 5 и 6).

## АРХИТЕКТУРА ВОРОНКИ (из project/marketing/)

```
Instagram/VK (прогрев. карусели, длинные посты, Reels)
       ↓ лид-магнит (чек-лист под фазу)
Telegram (канал + бот — основной канал конверсии)
       ↓ сегментация по фазе через бота
Автоворонка → чек-лист → серия писем (3-5 дней)
       ↓ на 7-й день трипвайер 99₽
Основной продукт (подписка 990₽/мес)

MessengerMax — альтернатива Telegram для тех, кто его не любит
```

## КЛЮЧЕВЫЕ МАРКЕТИНГОВЫЕ ФАЙЛЫ И ИХ ГДЕ

| Файл | Путь | Что содержит |
|------|------|-------------|
| Манифест маркетинга | `/opt/zinaida/projects/Otnoshenya/marketing/00_README.md` | Воронка, статус 8 платформ, KPI, риски |
| Воронка 2026 | `/opt/zinaida/projects/Otnoshenya/marketing/01_funnel.md` | Полная воронка, 6 сценариев автоворонок |
| Метрики | `/opt/zinaida/projects/Otnoshenya/marketing/02_metrics.md` | KPI, бизнес-метрики, EMA-формулы |
| Тактики по платформам | `/opt/zinaida/projects/Otnoshenya/marketing/03_platforms_marketing.md` | Форматы, расписание, что работает/нет |
| Монетизация | `/opt/zinaida/projects/Otnoshenya/marketing/04_monetization.md` | Трипвайер 99₽, подписка 990₽, unit-экономика |
| Авторская адаптация | `/opt/zinaida/projects/Otnoshenya/marketing/05_authors_strategy.md` | Адаптация зарубежных авторов |
| Research 3 | `/opt/zinaida/inbox/PROJECTS/Otnoshenya/knowledge/research_3.md` | Виральный код, алгоритмы 2026, психология хуков |
| Research 14 | `/opt/zinaida/inbox/PROJECTS/Otnoshenya/knowledge/research_14_product_full.md` | Продукт, УТП, цены, онбординг |
| Research 2 | `/opt/zinaida/inbox/PROJECTS/Otnoshenya/knowledge/research_2.md` | Конкуренты (3 класса), дифференциация |
| Research 6 | `/opt/zinaida/inbox/PROJECTS/Otnoshenya/knowledge/research_6.md` | Legal, 152-ФЗ, Algospeak, дисклеймеры |
| Аудит рынка | `/opt/zinaida/inbox/PROJECTS/Otnoshenya/knowledge/market_audit_2026_06.md` | Топ-3 темы (152к, 98к, 85к), словарь боли 28 фраз |
| Цифровой рынок РФ | `/opt/zinaida/inbox/PROJECTS/Otnoshenya/knowledge/extraresearch/digitalru.md` | VK (57% женщины), Telegram (экспертиза), алгоритмы |
| Валидированные хуки | `/opt/zinaida/inbox/PROJECTS/Otnoshenya/knowledge/validated_hooks_matrix.md` | 30+ хуков по фазам с оценкой силы |
| Банк хуков | `/opt/zinaida/inbox/PROJECTS/Otnoshenya/knowledge/hooks_bank.md` | 35 коротких хуков |
| Карточки соцсетей | `/opt/zinaida/inbox/Контент/_social/vkontakte.md` и другие | Статус каждой соцсети, URL, API |
| Посты (TG) | `/opt/zinaida/inbox/Контент/Telegram/YYYY-MM-DD/` | ~30 готовых постов |
| Посты (VK) | `/opt/zinaida/inbox/Контент/VK/YYYY-MM-DD/` | ~15 готовых постов |
| ROADMAP | `/opt/zinaida/inbox/PROJECTS/Otnoshenya/ROADMAP.md` | Фазы проекта, статус публикации |

## СТАТУС ПЛАТФОРМ (13.07.2026)

| Платформа | Статус | Подписчики | Посты готовы | Опубликовано |
|-----------|--------|-----------|-------------|-------------|
| VK (aipsiholog) | ✅ открыта | 5 | ~15 | **0** |
| Telegram (бот) | ✅ бот активен | только Олег | ~30 | **0** |
| Instagram | ⬜ | — | — | — |
| Дзен | ⬜ | — | — | — |
| OK | ⬜ | — | — | — |
| Pinterest | ⬜ | — | — | — |
| MessengerMax | ⬜ | — | — | — |
| YandexMessenger | ⬜ | — | 3 | **0** |

## БОЛЬШИЕ РАЗРЫВЫ (7 шт)

1. **Публикация:** 45+ постов, 0 опубликовано
2. **Telegram-канал:** есть бот, нет канала
3. **Платный трафик:** VK Ads, Яндекс.Директ — 0
4. **Петля аналитики:** Curator не запущен, EMA не работает
5. **Онбординг:** не реализован
6. **Трипвайер:** 99₽ нигде не продаётся
7. **Контент-план:** пустой

## ЧТО ТРЕБУЕТ УТОЧНЕНИЯ ОТ ОЛЕГА

- Какая соцсеть ведёт на какой канал продаж (явно не описано)
- Где точка монетизации (закрытый чат? бот? подписка?)
- Как распределены роли платформ (VK = охват, TG = конверсия, и т.д.)

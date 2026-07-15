# Audience Research Compendium — Zinaida Content Factory

## Top Search Volumes (Russian Women 18-40, 2025-2026)

Data aggregated from: T-J.ru (Tinkoff Journal), ВЦИОМ, Яндекс Wordstat, Forbes Woman, Gazeta.ru, internal `market_audit_2026_06.md`, `phases.db` (41 phases), `smm_rag.db` (3975 records).

### Pain Point Ranking by Search Volume

| Pain Topic | Monthly Searches | Trend | Phase | Tool CTA |
|------------|-----------------|-------|-------|----------|
| Как пережить расставание | 393k | +62% over 5y | Д, А3 | Телепат/Детектив |
| Почему он молчит/отдаляется | 152k | +22% | Г1, А6, Б6 | Телепат/Детектив |
| Измены: как распознать/что делать | 124k | stable | Г3, В | Детектив/Радар |
| Не зовёт замуж/не определяется | 98k | +15% | Б6, В, Е | Телепат |
| Гостинг/хлебные крошки | 85k | +30% | А, Б | Детектив/Телепат |
| Ссоры на ровном месте | high | — | Г2, В | Симулятор конфликта |
| Тревога/одиночество | 70k+ | +20% | все | Радар |

### Internal Data Sources

| Source | Path | Content |
|--------|------|---------|
| Market audit | `/opt/zinaida/inbox/PROJECTS/Otnoshenya/knowledge/market_audit_2026_06.md` | Top 3 topics: молчание 152k, не зовёт 98k, гостинг 85k |
| Pain lexicon | `/opt/zinaida/inbox/PROJECTS/Otnoshenya/knowledge/pain_lexicon.json` | 28 pain phrases ready to use |
| Hooks lexicon | `/opt/zinaida/inbox/PROJECTS/Otnoshenya/knowledge/hooks_lexicon.json` | Ready hook phrases by phase |
| Stats mechanics | `/opt/zinaida/inbox/PROJECTS/Otnoshenya/stats/mechanics/` | 54 stat files (ghosting 63%, divorce 70%, etc.) |
| Phases DB | `/opt/zinaida/inbox/PROJECTS/Otnoshenya/phases.db` | 41 phases A1-E5, each with pain points |
| RAG DB | `/opt/zinaida/memory/smm_rag.db` | 3975 chunks (FTS5 searchable) |
| Content plan (jul) | `/root/.hermes-web-ui/upload/default/c5914a9f832485fe.txt` | 4-week plan, 66 units (before tool integration) |
| SMM research (IG) | `/opt/zinaida/inbox/e1e62e7cfed61887.docx` | 214k chars — full IG relaunch guide 2026 |
| Tools TZ | `/opt/zinaida/inbox/a4c22f6aa68f05a7.pdf` | Full spec for 5 interactive tools |

### 2026 Algorithm Metrics

| Metric | Weight | Post type |
|--------|--------|-----------|
| Saves | 40% | Reference/checklist posts |
| DM Shares | 35% | Embarrassment/recognition posts |
| Watch Time | 15% | Long-form, serialized |
| Comments | 7% | Controversial questions |
| Likes | 3% | Almost irrelevant |

### Key External Research (Verified)

- **31%** of Russians have consulted a psychologist (НАФИ)
- **393k/month** searches for "как пережить расставание" (+62% in 5 years)
- **818k/month** searches for "депрессия" (Яндекс Wordstat, 2023)
- **32%** of couples report the first serious fight happens in the first 6 months
- **70%** of marriages in Russia end in divorce (Росстат 2025)
- **63%** have experienced ghosting (ВЦИОМ 2024)
- **53%** of married men admit to infidelity

### Seasonality Notes

- Peak searches for "депрессия": November-December
- Breakup searches: January (post-holiday), March, September
- "Как пережить расставание" — non-seasonal, continues growing independent of events

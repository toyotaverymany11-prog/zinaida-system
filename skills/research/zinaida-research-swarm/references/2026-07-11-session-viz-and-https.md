# Сессия 11.07.2026 — Визуализация, HTTPS, плагин

## Плагин Hermes Studio — не работает для кастомных вкладок
- Hermes Studio v0.6.28 **НЕ поддерживает** кастомные Dashboard Plugin вкладки в боковой панели
- Плагины, установленные через `hermes plugins install`, регистрируются в **Hermes Agent Dashboard** (порт 9119), а не в Studio
- Mindscape (southy404/hermes-mindscape) — единственный работающий dashboard plugin, но он встроен через SDK
- Наш плагин `deep-research-agents` был удалён после проверки (не работал в Studio)
- **Вывод:** для Studio — только текст, MEDIA-картинки, внешние HTTPS-ссылки

## HTTPS-доступ к отчётам (Caddy)
- Домен: zinadchdp.duckdns.org
- splash-страница: `/research/deep_research_splash.html` → `/opt/zinaida/deep_research_splash.html`
- отчёты: `/research/sandbox/deep_research/{folder}/report.html` → `/opt/zinaida/sandbox/deep_research/{folder}/report.html`
- Права: chmod 644 на html-файлы (Caddy не может читать 600 от root)

## User corrections
1. **Время:** Не называть сроки не открыв код. «2-3 дня» = триггер гнева.
2. **Прогресс:** [⚡] статусы каждые 5-10 минут. Если молчу >10 мин — не работаю.
3. **Плагин писался 4 минуты, не часы.** Завышенные оценки бесят Олега.
4. **Agent Atlas** — отслеживается в арсенале, напоминалка на 25.07
5. **Mission Control** — клонирован в /opt/mission-control/, но не развёрнут (порт 8648 занят)

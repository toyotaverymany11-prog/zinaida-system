# Deep Research: визуализация и триггер (10.07.2026)

## HTML-визуализация (report.html)

Функция `generate_html_report()` добавлена в `/opt/zinaida/scripts/deep_research.py`.

- Вызывается автоматически после `save_results()` в `main()`
- Создаёт `report.html` рядом с `final_report.md`
- Размер: ~29KB (всё inline, без внешних зависимостей)
- Тёмная тема (#0a0a0f фон), зелёные рамки для живых агентов (#1a4a1a)
- 4 карточки агентов с авто-подгонкой (CSS grid)
- Лента дебатов: из вопросов агентов (раунд 2)
- Добивка: ответы с источниками
- Вердикт DeepSeek: markdown -> HTML (## -> h2, ### -> h3, - -> •)

```python
html_path = generate_html_report(
    topic, report_path.parent, summaries,
    questions_data, followup_answers,
    report_text
)
```

## Mindscape плагин

Установлен: `hermes plugins install southy404/hermes-mindscape --enable`
Путь: `/root/.hermes/plugins/mindscape/`
Требует рестарта gateway: `hermes gateway restart`

## Триггер «глубокое исследование» — 4 слоя защиты

Для 100% срабатывания в новом чате триггер прописан в 4 местах:

1. **SOUL.md** (`/root/.hermes/SOUL.md`) — раздел 11. Читается при старте ЛЮБОЙ сессии default профиля. Самый надёжный уровень.
2. **.hermes.md** (`/root/.hermes/.hermes.md`) — загружается как контекст профиля
3. **AGENTS.md** (`/opt/zinaida/AGENTS.md`) — читается по протоколу загрузки
4. **Built-in memory** (Mem0) — семантический поиск

Текст триггера во всех файлах:
- «глубокое исследование» от Олега → НЕМЕДЛЕННО python3 /opt/zinaida/scripts/deep_research_orchestrator.py
- Без вопросов. Без ожиданий. Сразу запуск.

## Визуальный протокол

При запуске «глубокое исследование» — обязательные рамки в чате:

```
════════════════════════════════════
🔬 ЗАПУСК ГЛУБОКОГО ИССЛЕДОВАНИЯ
════════════════════════════════════

[01/04] 🔍 Сбор... ✅ Mistral ✅ GitHub ✅ Ollama ✅ Mistral2
[02/04] ❓ Вопросы... ✅ 
[03/04] 🎯 Добивка... ✅ N вопросов за X сек
[04/04] 🧠 Синтез DeepSeek Pro... ✅ 

📄 Отчёт: .../final_report.md
🖥️  Визуализация: .../report.html

════════════════════════════════════
✅ ИССЛЕДОВАНИЕ ЗАВЕРШЕНО
════════════════════════════════════
```

## Исправление: путь к отчёту в оркестраторе

Был баг: `deep_research_orchestrator.py` не находил путь к отчёту из-за regex.
Фикс: поиск `Отчёт:` построчно, взятие `/абсолютный/путь/файла.md` через `\S+\.md`.

```python
for line in output.split("\n"):
    if "Отчёт:" in line and ".md" in line:
        m = re.search(r"Отчёт:\s*(/\S+\.md)", line)
        if m:
            report_path = m.group(1)
            break
```

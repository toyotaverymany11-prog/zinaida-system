# Протокол «писатель отношения» (дополнение к zinaida-operations)

## Когда применяется
Триггер «писатель отношения» / «писатель отношение2» / «писатель отношения новая сессия» в НОВОМ чате.

## Что происходит
НЕ спрашивать «что делать?». НЕ писать «поняла, какая задача?». СРАЗУ:

1. Читать HANDOVER (`/opt/zinaida/HANDOVER_TO_NEW_CHAT.md`)
2. Читать живой слепок (`/opt/zinaida/memory/SYSTEM_SNAPSHOT.md`)
3. Проверить роутеры: curl 8002/8003/8005 (должны быть 200)
4. SQL-запросы во все 4 БД: phases.db (41 фаза), smm_rag.db (3975 записей), content_rotation.db, analytics.db
5. Прочитать pisatel-файлы (`/opt/zinaida/projects/Otnoshenya/pisatel/`)
6. Запустить архитектурные скрипты:
   - `python3 /opt/zinaida/scripts/post_architect.py --theme "тема" --platform "VK"` (таймаут 90с)
   - `python3 /opt/zinaida/scripts/compile_writer_context.py --theme "тема" --platform "VK"` (таймаут 90с)
7. Показать сводку со ✅ по каждому источнику
8. После сводки спросить «пишем пост?»

## Что НЕЛЬЗЯ делать
- Писать текст поста без явной команды «напиши пост»/«сгенерируй»
- Генерировать картинки
- Публиковать
- Менять production-конфиги

## Полный протокол
См. навык `zinaida-context-startup` — все детали и исключения.

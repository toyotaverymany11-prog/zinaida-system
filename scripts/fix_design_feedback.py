#!/usr/bin/env python3
"""
ФИКСАЦИЯ ФИДБЕКА ОЛЕГА ПО ДИЗАЙНУ
Вызывать НЕМЕДЛЕННО после любой оценки Олегом любой картинки.
Пример:
  python3 fix_design_feedback.py /opt/zinaida/cover_v5.jpg praise "охуенный вариант"
  python3 fix_design_feedback.py /opt/zinaida/cover_v2.jpg reject "говно собачье"
  python3 fix_design_feedback.py /opt/zinaida/something.jpg wip "чуть докрутить шрифт"

verdict: praise | approved | reject | wip | not_shown
"""
import sqlite3, sys, os, json, datetime

DB = '/opt/zinaida/memory/design_assets.db'

VERDICTS = {'praise', 'approved', 'reject', 'wip', 'not_shown'}
# praise = сказал что нравится/охуенно
# approved = утвердил для публикации
# reject = сказал что говно/пиздец/не надо
# wip = нужно доработать
# not_shown = сгенерировала но не показала

def main():
    if len(sys.argv) < 3:
        print('❌ Использование:')
        print('  python3 fix_design_feedback.py <file_path> <verdict> ["цитата Олега"]')
        print(f'  verdict: {", ".join(sorted(VERDICTS))}')
        sys.exit(1)

    file_path = sys.argv[1]
    verdict = sys.argv[2].lower()
    oleg_quote = sys.argv[3] if len(sys.argv) > 3 else ''

    if verdict not in VERDICTS:
        print(f'❌ Неверный вердикт: {verdict}. Допустимые: {", ".join(sorted(VERDICTS))}')
        sys.exit(1)

    if not os.path.exists(file_path):
        print(f'❌ Файл не найден: {file_path}')
        sys.exit(1)

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    # Ищем или создаём запись ассета
    c.execute('SELECT id, status FROM assets WHERE file_path = ?', (file_path,))
    row = c.fetchone()

    now = datetime.datetime.now().isoformat()

    if row:
        asset_id, current_status = row
        print(f'📌 Найден существующий asset id={asset_id}, статус={current_status}')
    else:
        # Авто-регистрация: создаём запись с минимумом данных
        fname = os.path.basename(file_path)
        fsize = os.path.getsize(file_path)
        c.execute('''INSERT INTO assets (file_path, file_name, date_generated, size_bytes, status)
                      VALUES (?, ?, ?, ?, ?)''',
                   (file_path, fname, now, fsize, verdict))
        asset_id = c.lastrowid
        print(f'🆕 Создан новый asset id={asset_id}')

    # Записываем фидбек
    c.execute('''INSERT INTO feedback (asset_id, verdict, oleg_quote, date_feedback, chat_id)
                  VALUES (?, ?, ?, ?, ?)''',
               (asset_id, verdict, oleg_quote, now, os.environ.get('HERMES_CHAT_ID', '')))

    # Обновляем статус ассета
    new_status = verdict
    # Но approved перезаписывает всё
    if verdict == 'approved':
        new_status = 'approved'
    elif verdict == 'reject':
        new_status = 'rejected'
    elif verdict == 'praise' and row and row[1] not in ('approved', 'rejected'):
        new_status = 'praised'
    elif verdict == 'wip':
        new_status = 'wip'

    c.execute('UPDATE assets SET status = ? WHERE id = ?', (new_status, asset_id))
    c.execute('''INSERT INTO generation_log (asset_id, action, details)
                  VALUES (?, 'feedback', ?)''',
               (asset_id, f'verdict={verdict} quote="{oleg_quote}"'))

    conn.commit()
    conn.close()

    # Символ для быстрого считывания
    symbols = {'praise': '👏', 'approved': '✅', 'reject': '❌', 'wip': '🔧', 'not_shown': '📁'}
    s = symbols.get(verdict, '❓')
    print(f'{s} Фидбек записан! asset #{asset_id}: {verdict}')
    if oleg_quote:
        print(f'   Цитата: "{oleg_quote}"')

if __name__ == '__main__':
    main()

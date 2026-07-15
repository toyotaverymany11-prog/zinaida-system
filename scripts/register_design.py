#!/usr/bin/env python3
"""
РЕГИСТРАЦИЯ НОВОЙ ГЕНЕРАЦИИ В design_assets.db
Вызывать ПОСЛЕ каждой генерации картинки (через Replicate, image_generate и т.д.)
Пример:
  python3 register_design.py /opt/zinaida/something.png --model flux-dev --prompt "..." --type cover --tags "vk,skyline"
"""
import sqlite3, sys, os, argparse, datetime, hashlib

DB = '/opt/zinaida/memory/design_assets.db'

ASSET_TYPES = {'cover', 'portrait', 'quote', 'scene', 'avatar', 'post', 'carousel', 'other'}
PLATFORMS = {'vk', 'ig', 'dzen', 'tg', 'ok', 'pinterest', 'mm', 'ym', 'all'}

def main():
    parser = argparse.ArgumentParser(description='Зарегистрировать новую генерацию')
    parser.add_argument('file_path', help='Путь к файлу')
    parser.add_argument('--model', default='unknown', help='Модель Replicate')
    parser.add_argument('--prompt', default='', help='Промпт')
    parser.add_argument('--type', dest='asset_type', default='other', choices=ASSET_TYPES,
                        help='Тип ассета')
    parser.add_argument('--ratio', default='', help='Соотношение сторон')
    parser.add_argument('--tags', default='', help='Теги через запятую')
    parser.add_argument('--platform', default='all', choices=PLATFORMS, help='Платформа')
    parser.add_argument('--status', default='not_shown', choices=['pending', 'not_shown', 'praised', 'approved', 'rejected', 'wip'],
                        help='Начальный статус')

    args = parser.parse_args()

    if not os.path.exists(args.file_path):
        print(f'❌ Файл не найден: {args.file_path}')
        sys.exit(1)

    fname = os.path.basename(args.file_path)
    fsize = os.path.getsize(args.file_path)
    now = datetime.datetime.now().isoformat()
    prompt_hash = hashlib.md5(args.prompt.encode()).hexdigest()[:12] if args.prompt else ''

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    # Проверка на дубликат
    c.execute('SELECT id, status FROM assets WHERE file_path = ?', (args.file_path,))
    row = c.fetchone()
    if row:
        print(f'⚠️ Файл уже зарегистрирован как asset #{row[0]}, статус={row[1]}')
        print('   Используй fix_design_feedback.py для обновления фидбека')
        conn.close()
        return

    c.execute('''INSERT INTO assets 
        (file_path, file_name, model, prompt, prompt_hash, aspect_ratio, 
         platform, asset_type, date_generated, size_bytes, tags, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (args.file_path, fname, args.model, args.prompt, prompt_hash,
         args.ratio, args.platform, args.asset_type, now, fsize, args.tags, args.status))

    asset_id = c.lastrowid

    c.execute('''INSERT INTO generation_log (asset_id, action, details)
                  VALUES (?, 'generated', ?)''',
               (asset_id, f'model={args.model} type={args.asset_type} tags="{args.tags}"'))

    conn.commit()
    conn.close()

    print(f'✅ Зарегистрирован asset #{asset_id}: {fname}')
    print(f'   {args.model} | {args.asset_type} | {fsize} bytes | статус: {args.status}')
    if args.tags:
        print(f'   теги: {args.tags}')

if __name__ == '__main__':
    main()

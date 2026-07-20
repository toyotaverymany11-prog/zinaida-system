#!/usr/bin/env python3
"""
compile_writer_context.py — Компилятор контекста для писателя
Собирает все правила из разрозненных файлов в единый промпт перед написанием поста.

Использование:
  python3 compile_writer_context.py --theme "гостинг" --platform "VK"
  → выдаёт единый контекст: стиль + ЧС + статистика + CTA + платформа
"""

import json
import sqlite3
import argparse
import os
from pathlib import Path

BASE = Path("/opt/zinaida")
PISATEL = BASE / "projects/Otnoshenya/pisatel"
INBOX = BASE / "inbox/PROJECTS/Otnoshenya"
KNOWLEDGE = INBOX / "knowledge"

def read_md_section(filepath, max_lines=100):
    """Читает первые N строк .md файла"""
    path = Path(filepath)
    if not path.exists():
        return f"[ФАЙЛ НЕ НАЙДЕН: {filepath}]"
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        lines = []
        for i, line in enumerate(f):
            if i >= max_lines:
                break
            lines.append(line.rstrip())
    return '\n'.join(lines)

def read_json(filepath):
    """Читает JSON файл"""
    path = Path(filepath)
    if not path.exists():
        return None
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        return json.load(f)

def get_phase_data(theme):
    """Ищет фазу по теме в phases.db"""
    db_path = INBOX / "phases.db"
    if not db_path.exists():
        return f"[phases.db не найдена]"
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    try:
        c.execute("SELECT name, description FROM phases WHERE name LIKE ? LIMIT 3", (f'%{theme}%',))
        rows = c.fetchall()
        if rows:
            result = "\n".join([f"  {r[0]}: {r[1][:200]}" for r in rows])
        else:
            result = f"  Фазы по теме '{theme}' не найдены. Держать весь список:"
            c.execute("SELECT name, description FROM phases LIMIT 5")
            result += "\n" + "\n".join([f"  {r[0]}: {r[1][:100]}" for r in c.fetchall()])
    except Exception as e:
        result = f"  Ошибка: {e}"
    conn.close()
    return result

def get_rag_chunks(theme, limit=3):
    """Делает RAG-запрос к smm_rag.db"""
    db_path = BASE / "memory/smm_rag.db"
    if not db_path.exists():
        return f"[smm_rag.db не найдена]"
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    try:
        c.execute(
            "SELECT content FROM smm_knowledge_fts WHERE smm_knowledge_fts MATCH ? LIMIT ?",
            (theme, limit)
        )
        rows = c.fetchall()
        if rows:
            result = "\n\n".join([r[0][:300] for r in rows])
        else:
            result = f"  RAG-чанков по '{theme}' не найдено"
    except Exception as e:
        result = f"  Ошибка RAG: {e}"
    conn.close()
    return result

def get_cta_templates(theme):
    """Ищет CTA-шаблоны под тему"""
    cta_dir = INBOX / "cta_library"
    templates = []
    if cta_dir.exists():
        for f in sorted(cta_dir.glob("*.md")):
            templates.append(f.name)
    if templates:
        return "  Доступные CTA-шаблоны:\n    " + "\n    ".join(templates)
    return "  CTA-шаблонов не найдено"

def get_statistics(theme):
    """Ищет подходящие статистики"""
    stats_dir = INBOX / "stats/mechanics"
    result = []
    if stats_dir.exists():
        for f in sorted(stats_dir.glob("*.md")):
            with open(f, 'r', encoding='utf-8', errors='replace') as fh:
                content = fh.read(500)
                if theme.lower() in content.lower():
                    result.append(f"\n--- {f.name} ---\n{content[:300]}")
    if result:
        return "  Статистики по теме:\n" + "\n".join(result[:3])
    return "  Статистики по теме не найдены"

def get_platform_spec(platform="VK"):
    """Возвращает спецификацию платформы"""
    specs = {
        "VK": """VK (2026):
- Длина: 2000-5000 знаков
- Картинка: 1080×1080 ОБЯЗАТЕЛЬНА
- Хештеги: 3-5
- Лучшее время: будни 19:00-23:00
- Нельзя: «подписывайся», «лайкни», «репостни»
- Алгоспик: измена→«смотрит налево», секс→«близость»
- Алгоритм: скорость первой реакции критична
- Авторский контент > репосты (87% пабликов растут быстрее)""",
        "TG": """Telegram:
- Длина: до 4096 знаков
- Картинка: 1280×720 опционально
- Лучшая платформа для DM Shares
- Можно форматирование: жирный, курсив
- Лучшее время: 20:00-23:00""",
        "Dzen": """Dzen (2026):
- Длина: 3000+ знаков (статьи)
- Картинка: 1200×630
- Первые 3 абзаца — критические (видны в ленте)
- SEO-заголовок: кликбейтный но правдивый
- Трафик идёт месяцами""",
        "OK": """Odnoklassniki:
- Аудитория: 35+ женщины, регионы
- Длина: до 8000 знаков
- Не заходит: молодёжный сленг""",
        "Pinterest": """Pinterest:
- Поисковая система, не соцсеть
- 80% женщины 25-45
- Формат: 2:3, 1000×1500
- Пин живёт годами"""
    }
    return specs.get(platform, "Платформа не описана")

def get_cta_architecture():
    """Возвращает CTA-архитектуру"""
    cta_path = BASE / "shared_memory/cta_architecture_v2.md"
    if cta_path.exists():
        with open(cta_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        # Вырезаем только матрицу и шаблоны
        lines = content.split('\n')
        result = []
        capture = False
        for line in lines:
            if 'МАТРИЦА ФАЗА' in line or 'CTA-ШАБЛОНЫ' in line:
                capture = True
            if 'ОТВЕТ НА ВОПРОС' in line:
                capture = False
            if capture:
                result.append(line)
        return '\n'.join(result[:100])
    return "[cta_architecture_v2.md не найден]"

def get_hooks(theme):
    """Ищет хуки в hooks_lexicon и validated_hooks_matrix"""
    lexicon = read_json(KNOWLEDGE / "hooks_lexicon.json")
    result = []
    if lexicon and "hooks_lexicon" in lexicon:
        for h in lexicon["hooks_lexicon"]:
            phrase = h.get("phrase", "")
            if theme.lower() in phrase.lower():
                result.append(f"  [{h.get('type','')}] {phrase}")
    if not result:
        # fallback на validated_hooks_matrix
        matrix_path = KNOWLEDGE / "validated_hooks_matrix.md"
        if matrix_path.exists():
            with open(matrix_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            # Ищем секцию с темой
            for line in content.split('\n'):
                if theme.lower() in line.lower() and ('|' in line):
                    result.append(f"  {line}")
    return result if result else ["  Хуки по теме не найдены"]

def get_algospeak():
    """Возвращает algospeak словарь"""
    d = read_json(KNOWLEDGE / "algospeak_dict.json")
    if d:
        return json.dumps(d, ensure_ascii=False, indent=2)
    return "{}"

def get_pain_phrases(theme):
    """Ищет фразы боли по теме"""
    d = read_json(KNOWLEDGE / "pain_lexicon.json")
    if d and "phrases" in d:
        matched = [p for p in d["phrases"] if theme.lower() in p.lower()]
        if matched:
            return "  Фразы боли:\n    " + "\n    ".join(matched[:10])
    return "  Фразы боли не найдены"

def compile_context(theme, platform="VK"):
    """Собирает полный контекст для писателя"""
    sep = "─" * 60
    context = []
    context.append(f"КОНТЕКСТ ДЛЯ НАПИСАНИЯ ПОСТА")
    context.append(f"Тема: {theme}")
    context.append(f"Платформа: {platform}")
    context.append(f"Дата: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}")
    context.append("")
    
    # 1. Стиль Шквальный (из 01_style_scheme.md)
    context.append(sep)
    context.append("БЛОК 1: СТИЛЬ ШКВАЛЬНЫЙ (16 правил)")
    context.append(sep)
    style = read_md_section(PISATEL / "01_style_scheme.md", 50)
    context.append(style[:2000])
    context.append("")
    
    # 2. Чёрный список
    context.append(sep)
    context.append("БЛОК 2: ЧЁРНЫЙ СПИСОК (18 блоков, 200+ фраз)")
    context.append(sep)
    bl = read_json(KNOWLEDGE / "blacklist_patterns.json")
    if bl and "blacklist" in bl:
        for b in bl["blacklist"]:
            context.append(f"  {b['id']} {b['name']}: {', '.join(b['patterns'][:3])}...")
    context.append("")
    
    # 3. Фаза
    context.append(sep)
    context.append("БЛОК 3: ФАЗА ОТНОШЕНИЙ")
    context.append(sep)
    context.append(get_phase_data(theme))
    context.append("")
    
    # 4. Статистика
    context.append(sep)
    context.append("БЛОК 4: СТАТИСТИКА ДЛЯ ХУКА")
    context.append(sep)
    context.append(get_statistics(theme))
    context.append("")
    
    # 5. RAG-чанки
    context.append(sep)
    context.append("БЛОК 5: RAG-ЗНАНИЯ ПО ТЕМЕ")
    context.append(sep)
    context.append(get_rag_chunks(theme))
    context.append("")
    
    # 6. Хуки
    context.append(sep)
    context.append("БЛОК 6: ХУКИ ДЛЯ ТЕМЫ")
    context.append(sep)
    hooks = get_hooks(theme)
    for h in hooks:
        context.append(h)
    context.append("")
    
    # 7. Боль
    context.append(sep)
    context.append("БЛОК 7: СЛОВАРЬ БОЛИ")
    context.append(sep)
    context.append(get_pain_phrases(theme))
    context.append("")
    
    # 8. CTA
    context.append(sep)
    context.append("БЛОК 8: CTA-АРХИТЕКТУРА")
    context.append(sep)
    cta_templates = get_cta_templates(theme)
    context.append(cta_templates)
    cta_arch = get_cta_architecture()
    if cta_arch:
        context.append(cta_arch[:1500])
    context.append("")
    
    # 9. Платформа
    context.append(sep)
    context.append(f"БЛОК 9: ПЛАТФОРМА {platform}")
    context.append(sep)
    context.append(get_platform_spec(platform))
    context.append("")
    
    # 10. Алгоспик
    context.append(sep)
    context.append("БЛОК 10: АЛГОСПИК (замена триггерных слов)")
    context.append(sep)
    context.append(get_algospeak())
    context.append("")
    
    # 11. Чёрный список JSON
    context.append(sep)
    context.append("БЛОК 11: ЧЁРНЫЙ СПИСОК JSON (18 блоков)")
    context.append(sep)
    bl2 = read_json(KNOWLEDGE / "blacklist_patterns.json")
    if bl2 and "blacklist" in bl2:
        for b in bl2["blacklist"]:
            context.append(f"  {b['id']} {b['name']}: ЗАПРЕЩЕНЫ фразы: {', '.join(b['patterns'][:5])}")
    context.append("")
    
    return '\n'.join(context)

def main():
    parser = argparse.ArgumentParser(description="Компилятор контекста для писателя")
    parser.add_argument("--theme", "-t", default="гостинг", help="Тема поста")
    parser.add_argument("--platform", "-p", default="VK", help="Платформа (VK/TG/Dzen/OK/Pinterest)")
    args = parser.parse_args()
    
    context = compile_context(args.theme, args.platform)
    print(context)
    
    # Сохраняем в файл для использования
    output_file = BASE / "memory/writer_context_latest.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(context)
    print(f"\n{'='*60}")
    print(f"Контекст сохранён в {output_file}")

if __name__ == "__main__":
    main()

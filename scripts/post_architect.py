#!/usr/bin/env python3
"""
post_architect.py — Архитектор поста
Строит карту поста: фаза → хук → метафора → инструмент → CTA → платформа → open loop

Использование:
  python3 post_architect.py --theme "гостинг" --platform "VK"
  → выдаёт готовую архитектурную карту для написания
"""

import json
import sqlite3
import argparse
from pathlib import Path

BASE = Path("/opt/zinaida")
INBOX = BASE / "inbox/PROJECTS/Otnoshenya"
KNOWLEDGE = INBOX / "knowledge"

# Матрица фаза → инструмент → формат → ключевое слово
PHASE_TOOL_MATRIX = {
    "неопределённость":     {"tool": "Детектив", "keyword": "РАССЛЕДУЙ", "format": "Улики"},
    "отдаляется":           {"tool": "Детектив", "keyword": "УЛИКИ", "format": "Улики"},
    "молчит":               {"tool": "Детектив", "keyword": "УЛИКИ", "format": "Улики"},
    "странное":             {"tool": "Телепат", "keyword": "ПРЕДСКАЖИ", "format": "Сценарии"},
    "конфликт":             {"tool": "Симулятор", "keyword": "ТРЕНАЖЁР", "format": "Ролевая игра"},
    "ссора":                {"tool": "Симулятор", "keyword": "ДИАЛОГ", "format": "Ролевая игра"},
    "избегание":            {"tool": "Радар", "keyword": "КАРТА", "format": "Карта эмоций"},
    "паттерн":              {"tool": "Коллекция", "keyword": "ПАТТЕРНЫ", "format": "Коллекция"},
    "измена":               {"tool": "Детектив", "keyword": "УЛИКИ", "format": "Расследование"},
    "гостинг":              {"tool": "Телепат", "keyword": "СЦЕНАРИЙ", "format": "Предсказание"},
    "хлебные крошки":       {"tool": "Коллекция", "keyword": "КРОШКИ", "format": "Коллекция"},
    "повторяется":          {"tool": "Коллекция", "keyword": "ПАТТЕРНЫ", "format": "Коллекция"},
    "чувств":               {"tool": "Радар", "keyword": "КАРТА", "format": "Карта"},
    "разрыв":               {"tool": "Детектив", "keyword": "ДЕЛО", "format": "Дело"},
    "ушёл":                 {"tool": "Детектив", "keyword": "ДЕЛО", "format": "Дело"},
}

# Форматы постов
FORMATS = {
    "Улики":           "Сериал-расследование: день за днём, улика за уликой. Хорошо для тем где нужно показать прогрессию.",
    "Сценарии":        "3 варианта развития событий: скорее всего / возможно / маловероятно. Для неопределённости.",
    "Ролевая игра":    "Подготовка к разговору: что сказать, как сказать, что не говорить. Для конфликтов.",
    "Карта эмоций":    "Разбор его эмоционального ландшафта: доминанты, триггеры, слепые зоны.",
    "Коллекция":       "Долгосрочный сбор наблюдений. Для тем где важна картина со временем.",
    "Расследование":   "Сбор улик + гипотезы + вердикт. Для тем где нужно 'докопаться до истины'.",
    "Предсказание":    "Прогноз поведения + follow-up через 3 дня. Для неопределённых ситуаций.",
    "Дело":            "Закрытие эпизода: анализ + выводы + что делать дальше. Для точек невозврата.",
}

# Open Loops (анонсы следующего поста)
OPEN_LOOPS = {
    "гостинг": "Завтра разберу: почему он возвращается после исчезновения — и стоит ли его ждать.",
    "измена": "Завтра: 3 признака что он изменяет — не очевидных, но работающих.",
    "молчит": "Завтра: что происходит после его возвращения — и почему он снова пропадёт.",
    "конфликт": "Завтра: 3 фразы которые нельзя говорить в ссоре — они убивают отношения.",
    "отдаляется": "Завтра: почему он отдаляется именно когда всё хорошо — психология избегания.",
    "паттерн": "Завтра: почему ты выбираешь одинаковых мужчин — и как это остановить.",
    "чувств": "Завтра: как понять что он действительно чувствует — по 3 невербальным сигналам.",
    "повторяется": "Завтра: цикл сближения-отдаления — как из него выйти.",
    "разрыв": "Завтра: первые 72 часа после расставания — что делать и чего не делать.",
}

def get_phase(theme):
    """Определяет фазу по теме"""
    db_path = INBOX / "phases.db"
    if not db_path.exists():
        return None, "Не удалось определить"
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    try:
        c.execute("SELECT name, description FROM phases WHERE name LIKE ? LIMIT 1", (f'%{theme[:5]}%',))
        row = c.fetchone()
        if row:
            return row[0], row[1][:200]
    except:
        pass
    conn.close()
    return None, "Авто-определение: извлеки из phases.db"

def find_tool(theme):
    """Находит подходящий инструмент по теме"""
    theme_lower = theme.lower()
    for key, value in PHASE_TOOL_MATRIX.items():
        if key in theme_lower or theme_lower in key:
            return value
    # fallback — Детектив
    return {"tool": "Детектив", "keyword": "РАССЛЕДУЙ", "format": "Расследование"}

def get_cta_template(tool_name, keyword, platform):
    """Генерирует CTA-шаблон для инструмента"""
    if platform == "VK":
        return f"""Хочешь разобраться что происходит на самом деле?
У меня есть инструмент «{tool_name}». Он [{{
    "Детектив": "собирает улики, анализирует паттерны и выносит вердикт",
    "Телепат": "прогнозирует его поведение по 3 сценариям и проверяет через 3 дня",
    "Симулятор": "тренирует сложный разговор в безопасной среде и разбирает ошибки",
    "Радар": "строит карту его эмоций, триггеров и слепых зон",
    "Коллекция": "собирает наблюдения в систему с уровнями и бонусами"
}}[tool_name]]
Напиши «{keyword}» в комментариях — я пришлю ссылку.
Или напиши в личку — отвечу лично.
-> Забрать бесплатно в Telegram или MessengerMax"""
    elif platform == "TG":
        return f"""Напиши «{keyword}» в комментариях под этим постом — я пришлю ссылку на инструмент «{tool_name}».
Или напиши мне в личку.
-> Бесплатно"""
    return "CTA для платформы не настроен"

def get_metafora(theme):
    """Подбирает метафору для темы"""
    metafory = {
        "гостинг": "ты как лайк на его сторис — он видит, но не реагирует",
        "измена": "он как телефон в беззвучном — всё включено, но ты не слышишь",
        "молчит": "ты как микроволновка — греешься, пока он в холодильнике",
        "конфликт": "вы как два процессора — каждый считает что прав, а система виснет",
        "отдаляется": "он как файл без сохранения — был, а когда закрыл — пропал",
    }
    for key, meta in metafory.items():
        if key in theme.lower():
            return meta
    return "подбери бытовую метафору из hooks_lexicon.json"

def build_architecture(theme, platform="VK"):
    """Строит полную архитектуру поста"""
    sep = "═══════════════════════════════════════════"
    result = []
    result.append(sep)
    result.append(f"  АРХИТЕКТУРА ПОСТА")
    result.append(f"  Тема: {theme}")
    result.append(f"  Платформа: {platform}")
    result.append(f"  Дата: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}")
    result.append(sep)
    result.append("")
    
    # Шаг 1: Фаза
    phase_name, phase_desc = get_phase(theme)
    result.append(f"[ФАЗА: {phase_name or '?'}]")
    result.append(f"  {phase_desc}")
    result.append("")
    
    # Шаг 2: Инструмент
    tool_info = find_tool(theme)
    result.append(f"ИНСТРУМЕНТ CTA: {tool_info['tool']}")
    result.append(f"  Ключевое слово: «{tool_info['keyword']}»")
    result.append(f"  Формат поста: {tool_info['format']}")
    result.append(f"  Описание формата: {FORMATS.get(tool_info['format'], '')}")
    result.append("")
    
    # Шаг 3: Хук
    result.append("ХУК (1-3 строки):")
    result.append("  Первый символ — цифра или факт")
    result.append("  Микро-боль + бетон-маркер (время/действие/артефакт)")
    result.append("  Без «давайте разберёмся», «в мире где»")
    result.append("  Примеры из validated_hooks_matrix.md по теме")
    result.append("")
    
    # Шаг 4: Метафора
    meta = get_metafora(theme)
    result.append(f"МЕТАФОРА:")
    result.append(f"  {meta}")
    result.append("  (проверить по Б14: не из списка запрещённых аналогий)")
    result.append("")
    
    # Шаг 5: Структура тела
    result.append("ТЕЛО ПОСТА (Narrativa Architecture):")
    result.append("  TENSION (10-20 строк):")
    result.append("    - Микро-сценарий: узнаваемый, с конкретными маркерами")
    result.append("    - 1 термин из нейробиологии + бытовой перевод")
    result.append("    - Маятник: плюс → минус → плюс")
    result.append("    - Честный минус ДО совета")
    result.append("")
    result.append("  PAYOFF (3-5 строк):")
    result.append("    - Конкретное действие, не абстракция")
    result.append("    - 2-3 варианта поведения")
    result.append("    - Без поп-психологии (Б7)")
    result.append("")
    
    # Шаг 6: CTA
    result.append("CTA (5-8 строк):")
    result.append(get_cta_template(tool_info['tool'], tool_info['keyword'], platform))
    result.append("")
    
    # Шаг 7: Open Loop
    open_loop = OPEN_LOOPS.get(theme.lower(), "Завтра разберу [тема следующего поста]. Подпишись — я предупрежу.")
    result.append(f"OPEN LOOP:")
    result.append(f"  {open_loop}")
    result.append("")
    
    # Шаг 8: Проверки
    result.append(sep)
    result.append("ПРОВЕРКИ ПЕРЕД НАПИСАНИЕМ:")
    result.append(sep)
    result.append("  □ Запущен compile_writer_context.py?")
    result.append("  □ Фаза определена? [ФАЗА: X]")
    result.append("  □ Хук проверен на уникальность (не из чёрного списка)?")
    result.append("  □ Метафора проверена по Б14?")
    result.append("  □ Инструмент привязан к фазе?")
    result.append("  □ CTA с ключевым словом и ссылкой?")
    result.append("  □ Open Loop вписывается в контент-план недели?")
    result.append("  □ Платформа учтена (длина, формат, алгоспик)?")
    result.append("")
    
    return '\n'.join(result)

def main():
    parser = argparse.ArgumentParser(description="Архитектор поста")
    parser.add_argument("--theme", "-t", default="гостинг", help="Тема поста")
    parser.add_argument("--platform", "-p", default="VK", help="Платформа")
    args = parser.parse_args()
    
    arch = build_architecture(args.theme, args.platform)
    print(arch)
    
    # Сохраняем
    output_file = BASE / "memory/post_architecture_latest.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(arch)
    print(f"Архитектура сохранена в {output_file}")

if __name__ == "__main__":
    main()

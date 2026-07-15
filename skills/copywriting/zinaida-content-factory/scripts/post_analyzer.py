#!/usr/bin/env python3
"""Агент-анализатор поста перед выпуском.
Проверяет текст на AI-паттерны по чек-листу.
Запускать: python3 /opt/zinaida/scripts/post_analyzer.py "текст поста"
"""

import sys
import re


def check_text(text: str) -> dict:
    results = {"passed": [], "failed": [], "warnings": []}
    
    # 1-2. Длинные и средние тире
    if "—" in text:
        results["failed"].append("❌ ДЛИННОЕ ТИРЕ: найдено «—». Заменить на дефис «-».")
    else:
        results["passed"].append("✅ Длинные тире: не найдены")
    if "–" in text:
        results["failed"].append("❌ СРЕДНЕЕ ТИРЕ: найдено «–». Заменить на дефис «-».")
    else:
        results["passed"].append("✅ Средние тире: не найдены")
    
    # 3. Многоточия
    if re.findall(r'\.\.\.\s*[A-ZА-Я]|\.\.\.\s*$', text):
        results["warnings"].append("⚠️ МНОГОТОЧИЕ: в конце предложений")
    else:
        results["passed"].append("✅ Многоточия: норма")
    
    # 4. Паттерн "это не Х, а/это Y" в одном предложении
    pattern_not_x_y = re.findall(r'это\s+(?:не|нe)\s+[^.]{5,50}?,\s+(?:это|а)\s+', text, re.IGNORECASE | re.DOTALL)
    pattern_not_but = re.findall(r'(?:не|нe)\s+\w{2,8}\s*[,\s]+а\s+\w{2,8}\s*[,.]', text, re.IGNORECASE)
    all_patterns = pattern_not_x_y + pattern_not_but
    if all_patterns:
        results["failed"].append(f"❌ ПАТТЕРН «ЭТО НЕ Х, ЭТО Y»: {len(all_patterns)} совпадений. Пример: «{all_patterns[0][:80]}...»")
    else:
        results["passed"].append("✅ Паттерн «это не Х, это Y»: не найден")
    
    # 5-13. Разные AI-паттерны
    checks = {
        "ВВОДНЫЙ ШУМ": ['давайте разберёмся', 'важно отметить', 'стоит понимать', 'на сегодняшний день', 'в современном мире'],
        "УСИЛИТЕЛЬ": ['не просто', 'больше чем просто', 'не только но и', 'скрытый потенциал'],
        "ПОП-ПСИХОЛОГИЯ": ['работай над собой', 'коммуникация — ключ', 'устанавливай границы', 'ты молодец', 'всё будет хорошо'],
        "СТРУКТУРНАЯ ЗАПАДНЯ": ['три пункта', 'пять признаков', 'представь себе'],
        "МЕТА-КОММЕНТАРИЙ": ['как я упоминала', 'как уже было сказано', 'вот что я предлагаю', 'перейдём к шагу'],
        "САМОРЕФЕРЕНЦИЯ": ['как языковая модель', 'как искусственный интеллект', 'нейросеть'],
        "КАНЦЕЛЯРИТ": ['оптимизировать', 'бесшовная интеграция', 'синергия', 'комплексный подход'],
        "АНАЛОГИЯ-ПУСТЫШКА": ['как езда на велосипеде', 'мозг — компьютер', 'как бабочки в животе'],
    }
    for name, phrases in checks.items():
        found = False
        for phrase in phrases:
            if phrase.lower() in text.lower():
                results["failed"].append(f'❌ {name}: «{phrase}»')
                found = True
                break
        if not found:
            results["passed"].append(f"✅ {name}: не найден{'а' if name.endswith('А') else ''}")
    
    # 14. Длина
    chars = len(text)
    if chars < 1500:
        results["warnings"].append(f"⚠️ ДЛИНА: {chars} зн. Для VK нужно минимум 2000.")
    else:
        results["passed"].append(f"✅ Длина: {chars} знаков")
    
    # 15. Первая строка про отношения
    first_line = text.strip().split('\n')[0]
    relation_words = ['он', 'она', 'ты', 'отношен', 'любов', 'встреч', 'свидан', 'парень', 'мужчин']
    if any(w in first_line.lower() for w in relation_words):
        results["passed"].append("✅ Первая строка: про отношения")
    else:
        results["warnings"].append("⚠️ ПЕРВАЯ СТРОКА: не содержит отсылок к отношениям")
    
    # 16. Запрещённые CTA-фразы (из истории правок)
    forbidden = ['по косточкам', 'ни один ai', 'ни один ассистент', 'ни один компаньон', 'это не гадание', 'это не таро', 'пришлю ссылку']
    for phrase in forbidden:
        if phrase.lower() in text.lower():
            results["failed"].append(f'❌ ЗАПРЕЩЁННАЯ ФРАЗА: «{phrase}»')
    
    # 17. Ссылки на исследования (проверить что не как доказательство)
    research_patterns = [r'исследован[иея]\s+\d{4}', r'нейробиолог', r'психолог\w+\s+из', r'университет']
    for pattern in research_patterns:
        if re.search(pattern, text):
            results["warnings"].append("⚠️ ССЫЛКА НА ИССЛЕДОВАНИЕ: проверь что цифра бьёт, а не доказывает")
            break
    else:
        results["passed"].append("✅ Исследования: цитаты как удар, не как доказательство")
    
    return results


def main():
    if len(sys.argv) < 2:
        text = sys.stdin.read().strip()
    else:
        text = ' '.join(sys.argv[1:])
    if not text:
        print("❌ Нет текста для анализа")
        sys.exit(1)
    results = check_text(text)
    print("╔═══════════════════════════════════════════╗")
    print("║  АНАЛИЗАТОР ПОСТА ПЕРЕД ВЫПУСКОМ        ║")
    print("╚═══════════════════════════════════════════╝")
    if results["failed"]:
        print("\n🔴 НАЙДЕНЫ ОШИБКИ:")
        for item in results["failed"]:
            print(f"  {item}")
    if results["warnings"]:
        print("\n🟡 ПРЕДУПРЕЖДЕНИЯ:")
        for item in results["warnings"]:
            print(f"  {item}")
    if results["passed"]:
        print("\n🟢 ПРОЙДЕНО:")
        for item in results["passed"]:
            print(f"  {item}")
    total = len(results["passed"]) + len(results["failed"]) + len(results["warnings"])
    print(f"\n{'━' * 47}")
    print(f"  Проверок: {total} | Ошибок: {len(results['failed'])} | Предупреждений: {len(results['warnings'])}")
    if results["failed"]:
        print(f"  ❌ ВЕРДИКТ: НЕ ВЫПУСКАТЬ. Исправь ошибки.")
        sys.exit(1)
    else:
        print(f"  ✅ ВЕРДИКТ: МОЖНО ВЫПУСКАТЬ. Текст прошёл проверку.")


if __name__ == "__main__":
    main()

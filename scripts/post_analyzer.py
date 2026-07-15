#!/usr/bin/env python3
"""Агент-анализатор поста перед выпуском.
Проверяет текст на AI-паттерны по чек-листу.
Запускать: python3 /opt/zinaida/scripts/post_analyzer.py "текст поста"
"""

import sys
import re
import json


def check_text(text: str) -> dict:
    results = {
        "passed": [],
        "failed": [],
        "warnings": []
    }
    
    # 1. Длинные тире
    if "—" in text:
        results["failed"].append("❌ ДЛИННОЕ ТИРЕ: найдено «—». Заменить на дефис «-».")
    else:
        results["passed"].append("✅ Длинные тире: не найдены")
    
    # 2. Средние тире
    if "–" in text:
        results["failed"].append("❌ СРЕДНЕЕ ТИРЕ: найдено «–». Заменить на дефис «-».")
    else:
        results["passed"].append("✅ Средние тире: не найдены")
    
    # 3. Многоточия в конце предложений (не внутри)
    ellipsis_end = re.findall(r'\.\.\.\s*[A-ZА-Я]|\.\.\.\s*$', text)
    if ellipsis_end:
        results["warnings"].append("⚠️ МНОГОТОЧИЕ: найдено в конце предложений (могут быть ок для ритма)")
    else:
        results["passed"].append("✅ Многоточия: норма")
    
    # "не партнёром, а реаниматологом" — нормальный стилистический приём, не AI-паттерн
    # Ловим только плоские конструкции: "это не X, а/это Y" с явным "это" в начале
    pattern_not_x_y = re.findall(r'это\s+(?:не|нe)\s+[^.]{5,50}?,\s+(?:это|а)\s+', text, re.IGNORECASE | re.DOTALL)
    # "не X, а Y" — только для коротких конструкций
    pattern_not_but = re.findall(r'(?:не|нe)\s+\w{2,8}\s*[,\s]+а\s+\w{2,8}\s*[,.]', text, re.IGNORECASE)
    all_patterns = pattern_not_x_y + pattern_not_but
    if all_patterns:
        results["failed"].append(f"❌ ПАТТЕРН «ЭТО НЕ Х, ЭТО Y»: {len(all_patterns)} совпадений. Пример: «{all_patterns[0][:80]}...»")
    else:
        results["passed"].append("✅ Паттерн «это не Х, это Y»: не найден")
    
    # 4.5. Паттерн «я не говорю тебе Х, я говорю Y» / «я не буду говорить Х, я скажу Y»
    # Ловит: "я не говорю тебе Х. Я говорю Y" и "я не буду говорить Х, я скажу Y"
    pattern_not_say = re.findall(r'(?:я\s+не\s+(?:говорю|буду(?:т)?\s+говорить|скажу)\s+тебе[^.]{0,60}[.?!]?\s*(?:я\s+)?(?:говорю|скажу|знаю|предлагаю))', text, re.IGNORECASE | re.DOTALL)
    if pattern_not_say:
        results["failed"].append(f"❌ ПАТТЕРН «Я НЕ ГОВОРЮ Х, Я ГОВОРЮ Y»: {len(pattern_not_say)} совпадений. Пример: «{pattern_not_say[0][:80]}...»")
    else:
        results["passed"].append("✅ Паттерн «я не говорю Х, я говорю Y»: не найден")
    
    # 4.6. Паттерн «это не то, что ты думаешь»
    pattern_not_what_you_think = re.findall(r'(?:это\s+не\s+то\s*,\s*что\s+ты\s+думаешь|не\s+то\s*,\s*что\s+ты\s+думаешь)', text, re.IGNORECASE)
    if pattern_not_what_you_think:
        results["failed"].append(f"❌ ПАТТЕРН «ЭТО НЕ ТО, ЧТО ТЫ ДУМАЕШЬ»: {len(pattern_not_what_you_think)} совпадений")
    else:
        results["passed"].append("✅ Паттерн «это не то, что ты думаешь»: не найден")
    
    # 5. Вводный шум
    noise_phrases = [
        'давайте разберёмся', 'важно отметить', 'стоит понимать',
        'как известно', 'подводя итог', 'итак,', 'в мире современных',
        'на сегодняшний день', 'в современном мире'
    ]
    for phrase in noise_phrases:
        if phrase.lower() in text.lower():
            results["failed"].append(f'❌ ВВОДНЫЙ ШУМ: «{phrase}»')
            break
    else:
        results["passed"].append("✅ Вводный шум: не найден")
    
    # 6. Усилители
    amplifiers = ['не просто', 'больше чем просто', 'не только но и', 'скрытый потенциал']
    for phrase in amplifiers:
        if phrase.lower() in text.lower():
            results["failed"].append(f'❌ УСИЛИТЕЛЬ: «{phrase}»')
            break
    else:
        results["passed"].append("✅ Усилители: не найдены")
    
    # 7. Поп-психология
    pop_psych = ['работай над собой', 'коммуникация — ключ', 'устанавливай границы',
                 'ты молодец', 'всё будет хорошо', 'ты не одна', 'ты сильная']
    for phrase in pop_psych:
        if phrase.lower() in text.lower():
            results["failed"].append(f'❌ ПОП-ПСИХОЛОГИЯ: «{phrase}»')
            break
    else:
        results["passed"].append("✅ Поп-психология: не найдена")
    
    # 8. Структурные западни
    traps = ['три пункта', 'пять признаков', 'представь себе', 'pro tip', 'лайфхак']
    for phrase in traps:
        if phrase.lower() in text.lower():
            results["failed"].append(f'❌ СТРУКТУРНАЯ ЗАПАДНЯ: «{phrase}»')
            break
    else:
        results["passed"].append("✅ Структурные западни: не найдены")
    
    # 9. Мета-комментарии
    meta = ['как я упоминала', 'как уже было сказано', 'вот что я предлагаю',
            'перейдём к шагу', 'как я говорила']
    for phrase in meta:
        if phrase.lower() in text.lower():
            results["failed"].append(f'❌ МЕТА-КОММЕНТАРИЙ: «{phrase}»')
            break
    else:
        results["passed"].append("✅ Мета-комментарии: не найдены")
    
    # 10. Самореференция
    self_ref = ['как языковая модель', 'как AI', 'как искусственный интеллект',
                'я не человек', 'нейросеть']
    for phrase in self_ref:
        if phrase.lower() in text.lower():
            results["failed"].append(f'❌ САМОРЕФЕРЕНЦИЯ: «{phrase}»')
            break
    else:
        results["passed"].append("✅ Самореференция: не найдена")
    
    # 11. Канцелярит
    bureaucratese = ['оптимизировать', 'бесшовная интеграция', 'синергия',
                     'комплексный подход', 'эффективное решение']
    for phrase in bureaucratese:
        if phrase.lower() in text.lower():
            results["failed"].append(f'❌ КАНЦЕЛЯРИТ: «{phrase}»')
            break
    else:
        results["passed"].append("✅ Канцелярит: не найден")
    
    # 12. Аналогии-пустышки
    empty_analogies = ['как езда на велосипеде', 'мозг — компьютер', 'отношения — это труд',
                       'как бабочки в животе', 'любовь как']
    for phrase in empty_analogies:
        if phrase.lower() in text.lower():
            results["failed"].append(f'❌ АНАЛОГИЯ-ПУСТЫШКА: «{phrase}»')
            break
    else:
        results["passed"].append("✅ Аналогии-пустышки: не найдены")
    
    # 13. Проверка длины
    chars = len(text)
    if chars < 1500:
        results["warnings"].append(f"⚠️ ДЛИНА: {chars} зн. Для VK нужно минимум 2000.")
    elif chars > 15000:
        results["warnings"].append(f"⚠️ ДЛИНА: {chars} зн. Для VK макс 15000.")
    else:
        results["passed"].append(f"✅ Длина: {chars} знаков")
    
    # 14. Первая строка - сразу про отношения?
    first_line = text.strip().split('\n')[0]
    relation_words = ['он', 'она', 'ты', 'отношен', 'любов', 'встреч', 'свидан',
                      'парень', 'мужчин', 'девушк', 'женщин', 'брак', 'развод']
    if not any(w in first_line.lower() for w in relation_words):
        results["warnings"].append("⚠️ ПЕРВАЯ СТРОКА: не содержит явных отсылок к отношениям")
    else:
        results["passed"].append("✅ Первая строка: про отношения")
    
    # 15. Запрещённые CTA-фразы (из истории правок)
    forbidden_cta = [
        'по косточкам',
        'ни один ai', 'ни один ассистент', 'ни один компаньон',
        'это не гадание', 'это не таро',
        'пришлю ссылку',
    ]
    for phrase in forbidden_cta:
        if phrase.lower() in text.lower():
            results["failed"].append(f'❌ ЗАПРЕЩЁННАЯ ФРАЗА: «{phrase}»')

    # 16. Проверка на "ссылку на исследование как доказательство"
    research_patterns = [
        r'исследован[иея] [0-9]{4} года',
        r'учён[ые]е из',
        r'нейробиолог[и] из',
        r'психолог\w+ из',
        r'университет\w+ \w+',
    ]
    for pattern in research_patterns:
        if re.search(pattern, text):
            results["warnings"].append("⚠️ ССЫЛКА НА ИССЛЕДОВАНИЕ: проверь что цифра бьёт, а не доказывает")
            break
    else:
        results["passed"].append("✅ Исследования: цитаты не найдены (или уже как удар)")
    
    return results


def main():
    if len(sys.argv) < 2:
        text = sys.stdin.read().strip()
    else:
        text = sys.argv[1]
    
    if not text:
        print("❌ Нет текста для анализа")
        sys.exit(1)
    
    results = check_text(text)
    
    print("╔═══════════════════════════════════════════╗")
    print("║  АНАЛИЗАТОР ПОСТА ПЕРЕД ВЫПУСКОМ        ║")
    print("╚═══════════════════════════════════════════╝")
    print()
    
    if results["failed"]:
        print("🔴 НАЙДЕНЫ ОШИБКИ:")
        for item in results["failed"]:
            print(f"  {item}")
        print()
    
    if results["warnings"]:
        print("🟡 ПРЕДУПРЕЖДЕНИЯ:")
        for item in results["warnings"]:
            print(f"  {item}")
        print()
    
    if results["passed"]:
        print("🟢 ПРОЙДЕНО:")
        for item in results["passed"]:
            print(f"  {item}")
        print()
    
    total_checks = len(results["passed"]) + len(results["failed"]) + len(results["warnings"])
    fail_count = len(results["failed"])
    
    print(f"━" * 47)
    print(f"  Проверок: {total_checks} | Ошибок: {fail_count} | Предупреждений: {len(results['warnings'])}")
    
    if fail_count > 0:
        print(f"  ❌ ВЕРДИКТ: НЕ ВЫПУСКАТЬ. Исправь ошибки.")
        sys.exit(1)
    else:
        print(f"  ✅ ВЕРДИКТ: МОЖНО ВЫПУСКАТЬ. Текст прошёл проверку.")


if __name__ == "__main__":
    main()

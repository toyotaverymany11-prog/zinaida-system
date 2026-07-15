#!/usr/bin/env python3
"""
Проверка кириллицы на сгенерированной картинке.
Использует Tesseract OCR для распознавания текста и сравнения с ожидаемым.

Использование:
  python3 check_cyrillic.py <путь_к_картинке> <ожидаемый_текст>
  
Пример:
  python3 check_cyrillic.py /opt/zinaida/design/generated/v1_chuzhoy_zapah.jpg "ЧУЖОЙ ЗАПАХ"
"""

import sys
import os
import json

try:
    from PIL import Image
    import pytesseract
except ImportError:
    print("❌ ОШИБКА: не установлены Pillow или pytesseract")
    sys.exit(1)

def check_cyrillic(image_path, expected_text):
    """Проверяет, что на картинке написан ожидаемый русский текст."""
    
    if not os.path.exists(image_path):
        return {
            "status": "ERROR",
            "error": f"Файл не найден: {image_path}",
            "passed": False
        }
    
    # Открываем изображение
    img = Image.open(image_path)
    
    # Распознаём русский текст через Tesseract
    # --psm 6: считать единым текстовым блоком
    # -c tessedit_char_whitelist: только кириллица + латиница для сравнения
    custom_config = r'--psm 6 -l rus'
    recognized_text = pytesseract.image_to_string(img, config=custom_config).strip()
    
    # Очищаем от лишних пробелов и переносов
    recognized_clean = ' '.join(recognized_text.split()).upper()
    expected_clean = ' '.join(expected_text.upper().split())
    
    # Точное совпадение
    exact_match = recognized_clean == expected_clean
    
    # Побуквенное сравнение (ищем отличия)
    chars_ok = True
    char_issues = []
    if not exact_match:
        # Проверяем вхождение ключевых слов
        expected_words = expected_clean.split()
        found_words = []
        missing_words = []
        for word in expected_words:
            if word in recognized_clean:
                found_words.append(word)
            else:
                missing_words.append(word)
        
        # Побуквенная проверка опционально
        for i, ch in enumerate(expected_clean):
            if i < len(recognized_clean):
                if ch != recognized_clean[i]:
                    # Проверяем не латинская ли буква вместо русской
                    lat_variants = {
                        'A': 'А', 'B': 'В', 'C': 'С', 'E': 'Е',
                        'H': 'Н', 'K': 'К', 'M': 'М', 'O': 'О',
                        'P': 'Р', 'T': 'Т', 'X': 'Х', 'Y': 'У'
                    }
                    real_ch = recognized_clean[i]
                    expected_ch = ch
                    
                    if real_ch in lat_variants and lat_variants[real_ch] == expected_ch:
                        char_issues.append(f"Позиция {i}: '{expected_ch}' (кир) написана как '{real_ch}' (лат)")
                    elif real_ch in lat_variants.values() and expected_ch in lat_variants and list(lat_variants.keys())[list(lat_variants.values()).index(expected_ch)] == real_ch:
                        # Латинская вместо кириллической
                        pass
                    else:
                        char_issues.append(f"Позиция {i}: ожидалось '{expected_ch}', распознано '{real_ch}'")
            else:
                char_issues.append(f"Позиция {i}: ожидалось '{ch}', но текст закончился")
    
    # Формируем результат
    result = {
        "status": "OK" if exact_match else "WARNING",
        "image": image_path,
        "expected": expected_clean,
        "recognized": recognized_clean,
        "exact_match": exact_match,
        "found_words": found_words if not exact_match else expected_words,
        "missing_words": missing_words if not exact_match else [],
        "char_issues": char_issues,
        "passed": exact_match
    }
    
    return result

def main():
    if len(sys.argv) < 3:
        print("Использование: python3 check_cyrillic.py <картинка> <ожидаемый_текст>")
        print("Пример: python3 check_cyrillic.py /opt/zinaida/design/generated/test.jpg \"ЧУЖОЙ ЗАПАХ\"")
        sys.exit(1)
    
    image_path = sys.argv[1]
    expected_text = sys.argv[2]
    
    result = check_cyrillic(image_path, expected_text)
    
    # Вывод
    print(f"\n{'='*60}")
    print(f"🔍 ПРОВЕРКА КИРИЛЛИЦЫ НА КАРТИНКЕ")
    print(f"{'='*60}")
    print(f"📷 Файл: {result['image']}")
    print(f"📝 Ожидалось: {result['expected']}")
    print(f"📝 Распознано: {result['recognized']}")
    print(f"{'='*60}")
    
    if result['exact_match']:
        print(f"✅ ТЕКСТ СОВПАДАЕТ ПОБУКВЕННО!")
    else:
        print(f"⚠️ ТЕКСТ НЕ СОВПАДАЕТ!")
        if result['char_issues']:
            print(f"\n🔴 Проблемные символы:")
            for issue in result['char_issues']:
                print(f"   {issue}")
        if result['missing_words']:
            print(f"\n🔴 Не найдены слова: {', '.join(result['missing_words'])}")
        if result['found_words']:
            print(f"✅ Найдены слова: {', '.join(result['found_words'])}")
    
    print(f"{'='*60}")
    print(f"Вердикт: {'✅ ПРОЙДЕН' if result['passed'] else '❌ НЕ ПРОЙДЕН - генерировать заново или Способ Б'}")
    
    return 0 if result['passed'] else 1

if __name__ == '__main__':
    sys.exit(main())

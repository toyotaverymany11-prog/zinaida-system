#!/usr/bin/env python3
"""
Проверка кириллицы на сгенерированной картинке.
Использует Tesseract OCR + Mistral Pixtral для перекрёстной верификации.

Использование:
  python3 check_cyrillic.py <путь_к_картинке> <ожидаемый_текст>

Пример:
  python3 check_cyrillic.py /opt/zinaida/design/generated/test.jpg "ЧУЖОЙ ЗАПАХ"

Зависимости: pip install Pillow pytesseract requests
Системные: apt install tesseract-ocr tesseract-ocr-rus
"""

import sys
import os
import json
import requests

try:
    from PIL import Image
    import pytesseract
except ImportError:
    print("❌ ОШИБКА: не установлены Pillow или pytesseract")
    print("pip install Pillow pytesseract")
    sys.exit(1)

def check_via_vision(image_path, expected_text):
    """Проверка через vision_analyze - возвращает распознанный текст."""
    # Этот метод вызывается извне - агент смотрит картинку через vision_analyze
    # Здесь возвращаем промпт для агента
    return f"""
⚠️ ЗАПРОС НА ПРОВЕРКУ:
1. Открой картинку через vision_analyze: {image_path}
2. Запроси: "Перечисли ВСЕ буквы на картинке по одной через запятую. 
   Каждая буква - кириллица или латиница? Напиши реально написанный текст."
3. Сравни с ожидаемым: "{expected_text}"
"""


def check_via_tesseract(image_path, expected_text):
    """Проверка через Tesseract OCR (не гарантирует для Didone шрифта)."""
    if not os.path.exists(image_path):
        return {"status": "ERROR", "error": f"Файл не найден: {image_path}"}
    
    img = Image.open(image_path)
    recognized = pytesseract.image_to_string(img, config='--psm 6 -l rus').strip()
    recognized_clean = ' '.join(recognized.split()).upper()
    expected_clean = ' '.join(expected_text.upper().split())
    
    return {
        "method": "tesseract",
        "recognized": recognized_clean,
        "expected": expected_clean,
        "match": recognized_clean == expected_clean
    }


def check_via_pixtral(image_url, expected_text, mistral_key=None):
    """Проверка через Mistral Pixtral API."""
    if not mistral_key:
        # Пробуем прочитать из .env
        env_paths = [
            '/opt/zinaida/config/secrets.env',
            '/root/.hermes/.env',
            '/opt/zinaida/meta_agent/.env'
        ]
        for path in env_paths:
            if os.path.exists(path):
                with open(path) as f:
                    for line in f:
                        if 'MISTRAL' in line and 'API' in line and '=' in line:
                            mistral_key = line.split('=')[1].strip().strip("'\"").strip('"')
                            break
                if mistral_key:
                    break
    
    if not mistral_key:
        return {"status": "ERROR", "error": "Нет Mistral API ключа"}
    
    try:
        resp = requests.post(
            'https://api.mistral.ai/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {mistral_key}',
                'Content-Type': 'application/json'
            },
            json={
                'model': 'pixtral-12b-2409',
                'messages': [{
                    'role': 'user',
                    'content': [
                        {'type': 'text', 'text': f'Read the Russian text on this image. '
                         f'List each character one by one. Is each character proper Cyrillic '
                         f'or a Latin letter? The expected text is "{expected_text}". '
                         f'What exact text do you see?'},
                        {'type': 'image_url', 'image_url': {'url': image_url}}
                    ]
                }],
                'max_tokens': 300
            },
            timeout=30
        )
        
        if resp.status_code == 200:
            result = resp.json()
            text = result['choices'][0]['message']['content']
            return {"method": "pixtral", "result": text[:500], "status": "OK"}
        else:
            return {"status": "ERROR", "error": f"HTTP {resp.status_code}: {resp.text[:200]}"}
    
    except Exception as e:
        return {"status": "ERROR", "error": str(e)}


def main():
    if len(sys.argv) < 3:
        print("Использование:")
        print("  python3 check_cyrillic.py <картинка> <ожидаемый_текст>")
        print()
        print("Запуск через агента:")
        print("  check_via_vision('/opt/zinaida/design/generated/test.jpg', 'ЧУЖОЙ ЗАПАХ')")
        sys.exit(1)
    
    image_path = sys.argv[1]
    expected = sys.argv[2]
    
    print(f"{'='*60}")
    print(f"🔍 ПРОВЕРКА КИРИЛЛИЦЫ")
    print(f"{'='*60}")
    print(f"📷 Файл: {image_path}")
    print(f"📝 Ожидается: {expected}")
    print(f"{'='*60}")
    
    # Tesseract (если файл локальный)
    if os.path.exists(image_path):
        t_result = check_via_tesseract(image_path, expected)
        print(f"\n📖 Tesseract: {t_result.get('recognized', 'N/A')}")
        print(f"   Совпадение: {'✅' if t_result.get('match') else '❌'}")
    
    # Инструкция для агента
    print(f"\n\n{check_via_vision(image_path, expected)}")
    
    return 0

if __name__ == '__main__':
    main()

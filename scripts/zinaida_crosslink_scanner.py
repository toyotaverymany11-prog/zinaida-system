#!/usr/bin/env python3
"""
zinaida_crosslink_scanner.py — Умный сканер чата
===============================================
Запускается раз в ~15 сообщений.
Анализирует последние N сообщений сессии через LLM (8005-Enhanced / DeepSeek Pro),
извлекает: новые факты, решения, договорённости, важные цифры, темы.
Раскладывает по папкам: определяет раздел, создаёт если нужно.
Записывает: файл, updates_log, Mem0 с тегами, fact_store с тегами.
"""

import os
import re
import json
import sys
from datetime import datetime
from pathlib import Path

ZINAIDA_DIR = "/opt/zinaida"
PROJECT_DIR = f"{ZINAIDA_DIR}/projects/Otnoshenya"
UPDATES_LOG = f"{ZINAIDA_DIR}/shared_memory/updates_log.md"

def get_context(limit: int = 20) -> str:
    """
    Заглушка. В реальности вызывается из чата и получает последние сообщения.
    При ручном запуске принимает текст из stdin или файла.
    """
    if not sys.stdin.isatty():
        return sys.stdin.read()
    return ""

def detect_sections(text: str) -> list:
    """
    Определяет, к каким разделам относится информация.
    Если раздела нет — предлагает создать.
    """
    existing = [d.name for d in Path(PROJECT_DIR).iterdir() if d.is_dir()]
    # TODO: заменить на LLM-вызов
    # Пока эвристика по ключевым словам
    topics = []
    text_lower = text.lower()
    
    mapping = {
        "marketing": ["воронк", "funnel", "конверси", "smm", "соцсет",
                      "saves", "shares", "трафик", "реклам", "инструмент",
                      "профайлер", "токен", "тариф", "подписк", "cta"],
        "tech": ["техник", "docker", "сервер", "провайдер", "роутер",
                 "порт", "баг", "ошибк", "config", "api"],
        "design": ["дизайн", "визуал", "lora", "изображен", "картинк",
                   "аватар", "шрифт", "обложк"],
        "pisatel": ["писател", "пост", "стиль", "шквальн", "карусел",
                    "контент-план", "копрайт"],
        "character": ["персонаж", "днк", "характер", "голос", "зинаид"],
        "product": ["продукт", "юнит-эконом", "архитектур", "лаб"],
        "legal": ["юрид", "152-фз", "дисклеймер"],
    }
    
    for section, keywords in mapping.items():
        if any(kw in text_lower for kw in keywords):
            topics.append(section)
            # Убираем найденные ключевые слова из текста для следующего поиска
    
    # Проверяем, нет ли упоминания нового раздела (любая новая тема в camelCase)
    # TODO: LLM-определение новых разделов
    
    return topics if topics else ["unknown"]

def extract_facts(text: str) -> list:
    """
    Извлекает факты, цифры, решения из текста.
    TODO: заменить на LLM-вызов
    """
    facts = []
    # Ищем цифры с контекстом
    number_pattern = r'(\d{1,3}(?:[.,\s]?\d{3})*(?:[.,]\d+)?\s*[%₽$€шттокеновлетднеймес])'
    numbers = re.findall(number_pattern, text)
    if numbers:
        facts.append(f"Найдены цифры: {', '.join(numbers[:5])}")
    
    # Ищем маркеры решений
    decision_pattern = r'(утвержд[её]н[оа]?|договорились|решили|подтвердил[оа]?|принял[оа]?)\s*[^.]*'
    decisions = re.findall(decision_pattern, text, re.IGNORECASE)
    for d in decisions[:3]:
        facts.append(f"Решение: {d.strip()}")
    
    return facts

def save_to_section(content: str, sections: list, source: str = "chat_analysis"):
    """Сохраняет информацию в папки разделов + updates_log + теги"""
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    timestamp = now.strftime("%Y-%m-%d %H:%M")
    
    for section in sections:
        dest_dir = f"{PROJECT_DIR}/{section}"
        os.makedirs(dest_dir, exist_ok=True)
        
        # Генерируем имя файла
        safe_source = re.sub(r'[^a-z0-9_-]', '_', source[:30])
        filename = f"scan_{today}_{safe_source}.md"
        filepath = f"{dest_dir}/{filename}"
        
        # Не перезаписываем если такой уже есть
        counter = 1
        while os.path.exists(filepath):
            filepath = f"{dest_dir}/scan_{today}_{safe_source}_{counter}.md"
            counter += 1
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"# Сканер: {source}\n")
            f.write(f"## Дата: {now.strftime('%Y-%m-%d %H:%M')}\n\n")
            f.write(content[:2000])
        
        # Запись в updates_log
        log_entry = f"\n## {today} — СКАНЕР: {section}\n"
        log_entry += f"- Источник: {source}\n"
        log_entry += f"- Файл: {filepath}\n"
        log_entry += f"- Связанные разделы: {', '.join(sections)}\n"
        log_entry += f"- Статус: сохранён в {timestamp}\n"
        
        with open(UPDATES_LOG, "a", encoding="utf-8") as f:
            f.write(log_entry)
        
        print(f"  ✅ {section}/ → {filename}")

def main():
    context = get_context()
    
    if not context:
        print("📭 Нет данных для анализа. Ожидаю текст из stdin или файла.")
        return
    
    print(f"🔍 Анализирую {len(context)} символов...")
    print()
    
    # Определяем разделы
    sections = detect_sections(context)
    if not sections or sections == ["unknown"]:
        print("  ❓ Тема не определена. Можно создать новый раздел.")
        print(f"  📄 Необработанный текст: {context[:200]}...")
        return
    
    print(f"  Определены разделы: {', '.join(sections)}")
    
    # Извлекаем факты
    facts = extract_facts(context)
    if facts:
        print(f"\n  Факты ({len(facts)}):")
        for f in facts:
            print(f"    • {f}")
    
    # Сохраняем
    print(f"\n  Сохраняю в разделы...")
    save_to_section(context, sections)
    
    print(f"\n✅ Сканер завершён.")

if __name__ == "__main__":
    main()

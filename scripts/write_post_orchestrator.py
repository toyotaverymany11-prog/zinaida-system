#!/usr/bin/env python3
"""
write_post_orchestrator.py — Единый оркестратор написания поста.

⚠️ ИЗОЛЯЦИЯ: этот оркестратор работает ТОЛЬКО с новым конвейером.
СМ. `/opt/zinaida/projects/Otnoshenya/pisatel/14_WRITER_FORMATION.md`

ЗАПРЕЩЕНО использовать старые файлы как источник правил:
  - 01_style_scheme.md (содержит «цифра первой» — говно)
  - 08_creative_examples.md (содержит «01:47», AI-паттерны)
  - 10_SYSTEM_WRITING.md (устарел полностью)
  - 11_WRITING_TRAINING_20260711.md (только структура, не типы начал)

11 шагов, 3 исследования (2 глубоких + 1 контроль).

Запуск:
  python3 write_post_orchestrator.py "тема" --instrument "Телепат" --platform "VK"

Шаги:
  1. Выбрать тему
  2. Определить инструмент
  → ИССЛЕДОВАНИЕ №1: deep_research (4 агента в интернет)
  3. Выбрать тип начала
  4. Написать Блок 1 — начало
  5. Написать Блок 2 — легитимность
  6. Написать Блок 3 — тело
  7. Написать Блок 4-5 — подвод + CTA
  → ИССЛЕДОВАНИЕ №2: server_research (4 агента на сервер)
  8. Дописать/усилить по результатам
  → КОНТРОЛЬ КАЧЕСТВА: post_analyzer
  9. Внести правки
  10. Финальная проверка (6 блоков)
  11. Готово
"""

import argparse
import subprocess
import sys
import os
from pathlib import Path

SCRIPTS = Path("/opt/zinaida/scripts")
MEMORY = Path("/opt/zinaida/memory")
PISATEL = Path("/opt/zinaida/projects/Otnoshenya/pisatel")


def step(msg: str):
    print(f"\n{'='*60}")
    print(f"  {msg}")
    print(f"{'='*60}")


def run_cmd(cmd: list, timeout: int = 120) -> bool:
    """Запускает команду, возвращает True если успешно"""
    print(f"  > {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.stdout:
            print(result.stdout[-1500:] if len(result.stdout) > 1500 else result.stdout)
        if result.stderr:
            print(f"  STDERR: {result.stderr[-500:]}")
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print("  ⚠️ Таймаут")
        return False
    except Exception as e:
        print(f"  ❌ Ошибка: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Оркестратор написания поста")
    parser.add_argument("theme", help="Тема поста")
    parser.add_argument("--instrument", default="", help="Целевой инструмент")
    parser.add_argument("--platform", default="VK", help="Платформа (VK/TG/etc)")
    parser.add_argument("--skip-research-1", action="store_true", help="Пропустить исследование №1")
    parser.add_argument("--skip-research-2", action="store_true", help="Пропустить исследование №2")
    args = parser.parse_args()

    theme = args.theme
    instrument = args.instrument
    platform = args.platform

    print(f"""
╔════════════════════════════════════════════════════╗
║     ОРКЕСТРАТОР НАПИСАНИЯ ПОСТА                    ║
║     11 шагов · 3 исследования                      ║
╚════════════════════════════════════════════════════╝
Тема: {theme}
Инструмент: {instrument or "будет определён"}
Платформа: {platform}
""")

    # ─── ШАГ 1 ───
    step("ШАГ 1: Тема определена")
    print(f"  Тема: {theme}")

    # ─── ШАГ 2 ───
    step("ШАГ 2: Инструмент")
    if not instrument:
        print("  Инструмент не указан. Определи его перед запуском.")
        print("  Используй: --instrument Телепат / Детектив / Тренажёр / Радар / Коллекция / Разобраться")
        return
    print(f"  Инструмент: {instrument}")
    
    # Определяем ключевое слово
    keyword_map = {
        "Телепат": "СЦЕНАРИЙ",
        "Детектив": "УЛИКИ",
        "Тренажёр": "ТРЕНАЖЁР",
        "Тренажер": "ТРЕНАЖЁР",
        "Радар": "КАРТА",
        "Коллекция": "ПАТТЕРНЫ",
        "Разобраться": "РАЗБОР"
    }
    keyword = keyword_map.get(instrument, "КЛЮЧЕВОЕ_СЛОВО")

    # ─── ИССЛЕДОВАНИЕ №1 ───
    if not args.skip_research_1:
        step("🔬 ИССЛЕДОВАНИЕ №1: 4 агента в интернет (сбор базы)")
        print("  Запускаю deep_research_orchestrator...")
        ok = run_cmd([
            sys.executable,
            str(SCRIPTS / "deep_research_orchestrator.py"),
            f"{theme}: научные данные, типы, причины, нейробиология, статистика, источники"
        ], timeout=300)
        if ok:
            print("  ✅ Исследование №1 завершено")
        else:
            print("  ⚠️ Исследование №1 не завершилось (таймаут/ошибка). Продолжаем.")
    else:
        print("  ⏭ Исследование №1 пропущено")

    # ─── ШАГ 3-7: Написание ───
    step("ШАГ 3-7: Написание поста")
    print("  Теперь напиши пост вручную, используя:")
    print(f"  - Тип начала (1-4) под тему")
    print(f"  - Данные из Исследования №1 (если есть)")
    print(f"  - Инструмент: {instrument}, ключевое слово: {keyword}")
    print(f"  - Платформа: {platform}")
    print(f"\n  После написания сохрани пост в файл и запусти:")
    print(f"  python3 write_post_orchestrator.py \"{theme}\" --instrument \"{instrument}\" --stage 2")
    print()

    # Если аргумент --stage 2, продолжаем после черновика
    if "--stage" not in " ".join(sys.argv):
        print("  Чтобы продолжить после написания черновика, добавь --stage 2")
        return

    # ─── ИССЛЕДОВАНИЕ №2 ───
    if not args.skip_research_2:
        step("🔬 ИССЛЕДОВАНИЕ №2: 4 агента на сервер (усиление)")
        print("  Запускаю server_research...")
        cmd = [sys.executable, str(SCRIPTS / "server_research.py"), theme]
        if instrument:
            cmd += ["--instrument", instrument]
        ok = run_cmd(cmd, timeout=60)
        if ok:
            print("  ✅ Исследование №2 завершено")
        else:
            print("  ⚠️ Ошибка исследования №2")
    else:
        print("  ⏭ Исследование №2 пропущено")

    # ─── ШАГ 8: Дописать ───
    step("ШАГ 8: Усиление поста")
    print("  Внеси правки на основе Исследования №2 (если есть)")
    print("  Данные в: /opt/zinaida/memory/server_research_latest.txt")

    # ─── КОНТРОЛЬ КАЧЕСТВА ───
    step("🔬 КОНТРОЛЬ КАЧЕСТВА: post_analyzer")
    print("  (запустится после того как укажешь файл с постом)")
    print()
    print("  Запусти: python3 /opt/zinaida/scripts/post_analyzer.py \"$(cat post.md)\"")
    print("  или: python3 /opt/zinaida/scripts/post_analyzer.py \"текст поста\"")

    # ─── ШАГ 10: Финальная проверка ───
    step("ШАГ 10: Финальная проверка (6 блоков)")
    checklist = f"""
  □ Начало — нет запретов (не описание, не время, не бытовуха)
  □ Тип начала — правильный (1-4)
  □ Инструмент — {instrument}, CTA ведёт к нему
  □ Легитимность — есть научная база
  □ Чёрный список — чист
  □ AI-паттерны — чисто (нет «это не X это Y», нет ложных классификаций)
"""
    print(checklist)

    step("ШАГ 11: ✅ ГОТОВО")
    print(f"  Пост по теме «{theme}» готов к показу Олегу.")


if __name__ == "__main__":
    main()

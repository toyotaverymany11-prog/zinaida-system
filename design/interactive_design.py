#!/usr/bin/env python3
# ═══════════════════════════════════════════════════════════
# INTERACTIVE_DESIGN.PY — Интерактивный дизайнер контент-завода Зинаида
# ═══════════════════════════════════════════════════════════
# Расположение: /opt/zinaida/design/interactive_design.py
# Запуск: python3 /opt/zinaida/design/interactive_design.py
# ═══════════════════════════════════════════════════════════

import os
import sys
import json
import yaml
import time
import hashlib
from datetime import datetime
from pathlib import Path

# Пути
DESIGN_ROOT = Path("/opt/zinaida/design")
CONFIG_PATH = DESIGN_ROOT / "config.yaml"
TEMPLATES_DIR = DESIGN_ROOT / "templates"
GENERATED_DIR = DESIGN_ROOT / "generated"
APPROVED_DIR = DESIGN_ROOT / "approved"
PASSPORT_DIR = DESIGN_ROOT / "passport"
REFERENCES_DIR = DESIGN_ROOT / "references"
SECRETS_FILE = Path("/opt/zinaida/config/secrets.env")

# ─── Загрузка конфигурации ───
def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def load_secrets():
    secrets = {}
    if SECRETS_FILE.exists():
        with open(SECRETS_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    secrets[k.strip()] = v.strip()
    return secrets

def get_replicate_client():
    secrets = load_secrets()
    token = secrets.get("REPLICATE_API_TOKEN", "")
    if not token:
        print("❌ REPLICATE_API_TOKEN не найден в secrets.env!")
        sys.exit(1)
    os.environ["REPLICATE_API_TOKEN"] = token
    import replicate
    return replicate.Client(api_token=token)

# ─── Загрузка шаблона ───
def load_template(variant):
    mapping = {
        "1": "cover_magazine.txt",
        "2": "quote_provocation.txt",
        "3": "scene_emotional.txt",
    }
    tpl_file = TEMPLATES_DIR / mapping.get(variant, "")
    if not tpl_file.exists():
        print(f"❌ Шаблон {tpl_file} не найден!")
        return None
    with open(tpl_file, "r", encoding="utf-8") as f:
        return f.read()

# ─── Генерация изображения ───
def generate_image(client, config, variant, prompt, size="1080x1080"):
    w, h = size.split("x")
    batch_dir = GENERATED_DIR / f"batch_{datetime.now().strftime('%Y%m%d')}"
    batch_dir.mkdir(parents=True, exist_ok=True)

    models_cfg = config["models"]
    if variant in ("1", "2"):
        model_id = models_cfg["text_heavy"]["id"]
        model_name = models_cfg["text_heavy"]["name"]
        price = models_cfg["text_heavy"]["price_per_image"]
    elif variant == "3":
        model_id = models_cfg["photorealistic"]["id"]
        model_name = models_cfg["photorealistic"]["name"]
        price = models_cfg["photorealistic"]["price_per_image"]
    else:
        model_id = models_cfg["drafts"]["id"]
        model_name = models_cfg["drafts"]["name"]
        price = models_cfg["drafts"]["price_per_image"]

    print(f"\n🎨 Генерация через {model_name} ({model_id})")
    print(f"💰 Стоимость: ~${price}")
    print(f"📐 Размер: {size}")
    print(f"📝 Промпт: {prompt[:100]}...")
    print("⏳ Генерирую...")

    try:
        input_params = {"prompt": prompt, "width": int(w), "height": int(h)}

        # Для FLUX dev + LoRA добавляем LoRA
        if variant == "3" and "lora" in models_cfg["photorealistic"]:
            lora_url = models_cfg["photorealistic"]["lora"]
            input_params["hf_lora"] = lora_url
            print(f"🔗 LoRA: {lora_url}")

        output = client.run(model_id, input=input_params)

        # Обработка результата
        if isinstance(output, list):
            image_url = str(output[0])
        elif hasattr(output, 'url'):
            image_url = output.url
        else:
            image_url = str(output)

        # Скачиваем изображение
        ts = datetime.now().strftime("%H%M%S")
        variant_names = {"1": "magazine", "2": "quote", "3": "scene"}
        filename = f"v{variant}_{variant_names.get(variant, 'unknown')}_{ts}.png"
        filepath = batch_dir / filename

        import urllib.request
        urllib.request.urlretrieve(image_url, str(filepath))

        print(f"✅ Сохранено: {filepath}")
        print(f"🔗 URL: {image_url}")

        # Логируем генерацию
        log_generation(variant, prompt, str(filepath), model_id, price)

        return str(filepath)

    except Exception as e:
        print(f"❌ Ошибка генерации: {e}")
        return None

def log_generation(variant, prompt, filepath, model, price):
    log_file = GENERATED_DIR / "generation_log.jsonl"
    entry = {
        "timestamp": datetime.now().isoformat(),
        "variant": variant,
        "prompt": prompt,
        "file": filepath,
        "model": model,
        "price_usd": price,
        "status": "generated"
    }
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

# ─── Промпт-билдер ───
def build_prompt_v1(headline, subheadline=""):
    """Вариант 1: Журнальная обложка"""
    prompt = (
        f'A premium magazine cover design for social media post. '
        f'Large bold text "{headline}" in elegant high-contrast Didone serif font, '
        f'white color, thin serifs, bold vertical strokes, taking 70% of the image area. '
        f'Background: darkened photo of a confident elegant woman with dark hair '
        f'and auburn tips, wearing a white shirt, looking at camera with slight smile. '
        f'The woman is semi-transparent, serving as background texture (30% opacity). '
        f'Dark gradient overlay from top. Color palette: black, white text, '
        f'bordeaux (#8B0000) subtle accent. Style: luxury fashion magazine cover, '
        f'Vogue aesthetic. Professional typography. Clean minimalist layout.'
    )
    if subheadline:
        prompt += f' Small sans-serif subtitle "{subheadline}" at the bottom.'
    return prompt

def build_prompt_v2(quote, palette=1):
    """Вариант 2: Цитата-провокация"""
    palettes = {
        1: ("deep bordeaux (#5C1A1A)", "white"),
        2: ("warm beige (#F5E6D0)", "dark brown (#3D2B1F)"),
        3: ("black (#1A1A1A)", "gold (#C9A84C)"),
        4: ("deep blue (#1B2A4A)", "white"),
    }
    bg, fg = palettes.get(palette, palettes[1])
    prompt = (
        f'Minimalist quote design for social media. {bg} solid color background. '
        f'Text "{quote}" in elegant serif font (Cormorant Garamond style, italic), '
        f'{fg} color, centered, medium size, taking 80% of image area. '
        f'Below the quote, small sans-serif text "— Зинаида" aligned right. '
        f'At the bottom center, a small diamond symbol as logo. '
        f'Thin horizontal line above the author name. '
        f'Clean, sophisticated, editorial look. No photos, no illustrations. '
        f'Only typography and color.'
    )
    return prompt

def build_prompt_v3(scene_type, subtitle=""):
    """Вариант 3: Кино-сцена"""
    scenes = {
        "1": ("A man in his 30s sitting alone on the edge of a bed, back to camera, "
              "dim warm evening light from window, contemplative mood"),
        "2": ("A man in his 30s looking at his phone in a dark room, face lit by "
              "phone screen glow, expression of regret, soft warm ambient light"),
        "3": ("A couple sitting back to back on a couch, emotional distance, "
              "warm evening interior light, moody atmosphere"),
        "4": ("A man's hand reaching out towards camera, warm golden light, "
              "soft focus, intimate close-up, gentle mood"),
        "5": ("A man standing by a window, harsh shadows on face, arms crossed, "
              "cold blue-grey light, controlling posture, tense atmosphere"),
    }
    scene_desc = scenes.get(scene_type, scenes["1"])
    prompt = (
        f'Cinematic photorealistic scene. {scene_desc}. '
        f'Color palette: warm amber, brown, golden tones. '
        f'Shallow depth of field, bokeh background. '
        f'Shot on 85mm lens, golden hour lighting. '
        f'Style: documentary photography, NOT glossy or artificial. '
        f'Film grain texture, cinematic color grading.'
    )
    if subtitle:
        prompt += f' Small text "{subtitle}" in top left corner, small white sans-serif.'
    return prompt

# ─── Одобрение ───
def approve_image(filepath):
    src = Path(filepath)
    if not src.exists():
        print(f"❌ Файл {filepath} не найден!")
        return
    dest = APPROVED_DIR / "posts" / src.name
    import shutil
    shutil.copy2(str(src), str(dest))
    print(f"✅ Одобрено и скопировано в: {dest}")

    # Обновляем лог
    log_file = GENERATED_DIR / "generation_log.jsonl"
    if log_file.exists():
        lines = log_file.read_text(encoding="utf-8").strip().split("\n")
        updated = []
        for line in lines:
            entry = json.loads(line)
            if entry.get("file") == filepath:
                entry["status"] = "approved"
            updated.append(json.dumps(entry, ensure_ascii=False))
        log_file.write_text("\n".join(updated) + "\n", encoding="utf-8")

def reject_image(filepath):
    src = Path(filepath)
    if not src.exists():
        print(f"❌ Файл {filepath} не найден!")
        return
    dest = GENERATED_DIR / "rejected" / src.name
    import shutil
    shutil.move(str(src), str(dest))
    print(f"🗑 Отклонено и перемещено в: {dest}")

# ─── Статистика ───
def show_stats():
    log_file = GENERATED_DIR / "generation_log.jsonl"
    if not log_file.exists():
        print("📊 Нет данных о генерациях.")
        return
    lines = log_file.read_text(encoding="utf-8").strip().split("\n")
    total = len(lines)
    total_cost = 0
    approved = 0
    by_variant = {"1": 0, "2": 0, "3": 0}
    for line in lines:
        entry = json.loads(line)
        total_cost += entry.get("price_usd", 0)
        if entry.get("status") == "approved":
            approved += 1
        v = entry.get("variant", "?")
        by_variant[v] = by_variant.get(v, 0) + 1

    print(f"\n📊 СТАТИСТИКА ГЕНЕРАЦИЙ")
    print(f"{'═' * 40}")
    print(f"  Всего генераций: {total}")
    print(f"  Одобрено: {approved}")
    print(f"  Потрачено: ${total_cost:.3f}")
    print(f"  По вариантам:")
    print(f"    Журнал (В1): {by_variant.get('1', 0)}")
    print(f"    Цитата (В2): {by_variant.get('2', 0)}")
    print(f"    Сцена  (В3): {by_variant.get('3', 0)}")

# ─── Главное меню ───
def main_menu():
    config = load_config()
    print("\n" + "═" * 60)
    print("  🎨 КОНТЕНТ-ЗАВОД ЗИНАИДА — ДИЗАЙНЕР")
    print("═" * 60)
    print()
    print("  1. 📰 Журнальная обложка (Вариант 1)")
    print("  2. 💬 Цитата-провокация (Вариант 2)")
    print("  3. 🎬 Кино-сцена (Вариант 3)")
    print("  4. 📋 Показать шаблон промпта")
    print("  5. ✅ Одобрить изображение")
    print("  6. 🗑  Отклонить изображение")
    print("  7. 📊 Статистика")
    print("  8. 🔧 Проверить Replicate API")
    print("  9. 📁 Показать структуру папок")
    print("  0. 🚪 Выход")
    print()
    return input("  Выбор ▸ ").strip()

def check_api():
    try:
        client = get_replicate_client()
        # Простая проверка — список моделей
        print("✅ Replicate API подключён!")
        print(f"   Токен: ...{os.environ.get('REPLICATE_API_TOKEN', '')[-8:]}")
        return True
    except Exception as e:
        print(f"❌ Ошибка API: {e}")
        return False

def show_tree():
    print("\n📁 СТРУКТУРА /opt/zinaida/design/")
    print("═" * 50)
    for root, dirs, files in os.walk(DESIGN_ROOT):
        level = root.replace(str(DESIGN_ROOT), "").count(os.sep)
        indent = "  " * level
        basename = os.path.basename(root)
        print(f"{indent}📂 {basename}/")
        subindent = "  " * (level + 1)
        for f in sorted(files):
            size = os.path.getsize(os.path.join(root, f))
            if size > 1024*1024:
                sz = f"{size/1024/1024:.1f}MB"
            elif size > 1024:
                sz = f"{size/1024:.1f}KB"
            else:
                sz = f"{size}B"
            print(f"{subindent}📄 {f} ({sz})")

def run():
    print("\n🚀 Запуск интерактивного дизайнера контент-завода Зинаида...")
    config = load_config()

    while True:
        choice = main_menu()

        if choice == "1":
            print("\n📰 ВАРИАНТ 1: ЖУРНАЛЬНАЯ ОБЛОЖКА")
            headline = input("  Заголовок (2-4 слова, ЗАГЛАВНЫЕ): ").strip()
            if not headline:
                headline = "ОН МОЛЧИТ"
            sub = input("  Подзаголовок (Enter = пропустить): ").strip()
            size = input("  Размер (1=1080x1080, 2=1080x1350) [1]: ").strip()
            size = "1080x1350" if size == "2" else "1080x1080"
            prompt = build_prompt_v1(headline, sub)
            print(f"\n📝 Промпт:\n{prompt}\n")
            confirm = input("  Генерировать? (y/n) [y]: ").strip().lower()
            if confirm != "n":
                client = get_replicate_client()
                generate_image(client, config, "1", prompt, size)

        elif choice == "2":
            print("\n💬 ВАРИАНТ 2: ЦИТАТА-ПРОВОКАЦИЯ")
            quote = input("  Цитата: ").strip()
            if not quote:
                quote = "Если он не звонит, это и есть его ответ"
            print("  Палитра:")
            print("    1. Бордовый фон / белый текст")
            print("    2. Бежевый фон / коричневый текст")
            print("    3. Чёрный фон / золотой текст")
            print("    4. Синий фон / белый текст")
            pal = input("  Выбор [1]: ").strip()
            pal = int(pal) if pal in ("1","2","3","4") else 1
            prompt = build_prompt_v2(quote, pal)
            print(f"\n📝 Промпт:\n{prompt}\n")
            confirm = input("  Генерировать? (y/n) [y]: ").strip().lower()
            if confirm != "n":
                client = get_replicate_client()
                generate_image(client, config, "2", prompt)

        elif choice == "3":
            print("\n🎬 ВАРИАНТ 3: КИНО-СЦЕНА")
            print("  Типы сцен:")
            print("    1. Одиночество (мужчина на кровати)")
            print("    2. Раскаяние (мужчина с телефоном)")
            print("    3. Разрыв (пара спиной)")
            print("    4. Нежность (рука тянется)")
            print("    5. Токсичность (мужчина у окна)")
            st = input("  Выбор [1]: ").strip()
            if st not in ("1","2","3","4","5"):
                st = "1"
            subtitle = input("  Подпись в углу (Enter = без текста): ").strip()
            prompt = build_prompt_v3(st, subtitle)
            print(f"\n📝 Промпт:\n{prompt}\n")
            confirm = input("  Генерировать? (y/n) [y]: ").strip().lower()
            if confirm != "n":
                client = get_replicate_client()
                generate_image(client, config, "3", prompt, "1080x1350")

        elif choice == "4":
            v = input("  Какой шаблон? (1/2/3): ").strip()
            tpl = load_template(v)
            if tpl:
                print(f"\n{tpl}")

        elif choice == "5":
            filepath = input("  Путь к файлу: ").strip()
            approve_image(filepath)

        elif choice == "6":
            filepath = input("  Путь к файлу: ").strip()
            reject_image(filepath)

        elif choice == "7":
            show_stats()

        elif choice == "8":
            check_api()

        elif choice == "9":
            show_tree()

        elif choice == "0":
            print("\n👋 До встречи!\n")
            break

        else:
            print("❓ Неизвестная команда")

if __name__ == "__main__":
    run()

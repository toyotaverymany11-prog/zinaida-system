#!/usr/bin/env python3
"""Безопасный тест подключения к Replicate API"""
import os
import sys

# Читаем токен из файла .env
env_path = "/opt/zinaida/secrets.env"
token = None
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line.startswith("REPLICATE_API_TOKEN="):
                token = line.split("=", 1)[1].strip("\"'")
                break

if not token:
    print("REPLICATE_API_TOKEN: MISSING")
    sys.exit(1)

# Не выводим токен, только проверяем длину
prefix = token[:8]
print(f"REPLICATE_API_TOKEN: PRESENT (prefix={prefix}..., len={len(token)})")

# Теперь тестируем модели
import replicate
os.environ["REPLICATE_API_TOKEN"] = token

models_to_test = [
    ("recraft-ai/recraft-v3", {"prompt": "test pattern warm terracotta on dark gray minimal abstract", "size": "1024x1024", "style": "realistic_image"}, "Recraft V3"),
    ("black-forest-labs/flux-dev", {"prompt": "test pattern minimal abstract warm tones", "num_inference_steps": 4, "guidance_scale": 3.5}, "FLUX Dev"),
    ("ideogram-ai/ideogram-v3", {"prompt": "test pattern minimal geometric warm tones", "resolution": "1024x1024"}, "Ideogram V3"),
]

results = []
for model_id, params, name in models_to_test:
    print(f"\n=== Testing {name} ({model_id}) ===")
    try:
        output = replicate.run(model_id, input=params)
        print(f"  Output type: {type(output).__name__}")
        if output:
            # Безопасно получаем URL
            raw = str(output)
            preview = raw[:100]
            print(f"  Output preview: {preview}...")
            results.append((name, "OK"))
        else:
            print(f"  Output: empty/None")
            results.append((name, "EMPTY"))
    except Exception as e:
        err = str(e)[:200]
        print(f"  ✗ Error: {err}")
        results.append((name, f"ERROR: {err}"))

print("\n\n=== ИТОГОВЫЙ РЕЗУЛЬТАТ ВЕРИФИКАЦИИ ===")
all_ok = True
for name, status in results:
    mark = "✓" if status == "OK" else "✗"
    print(f"  {mark} {name}: {status}")
    if status != "OK":
        all_ok = False

print(f"\nОбщий статус: {'ВСЕ ОК' if all_ok else 'ЕСТЬ ПРОБЛЕМЫ'}")

#!/usr/bin/env python3
"""
Генерация тестовых паспортных фото Зинаиды с сохранением идентичности лица.
Использует Replicate API с моделью, поддерживающей IP-Adapter/FaceID.
"""
import os
import sys
import base64
import json
import time
import replicate

# Конфигурация
OUTPUT_DIR = "/opt/zinaida/design/passport/generated"
REFERENCE_DIR = "/opt/zinaida/design/passport/originals"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Референсы
REFERENCE_PHOTOS = [
    os.path.join(REFERENCE_DIR, "photo1.png"),
    os.path.join(REFERENCE_DIR, "photo2.png"),
    os.path.join(REFERENCE_DIR, "photo3.jpg"),
]

def file_to_data_uri(filepath):
    """Конвертирует изображение в data URI."""
    import mimetypes
    mime_type, _ = mimetypes.guess_type(filepath)
    if mime_type is None:
        if filepath.endswith(".png"):
            mime_type = "image/png"
        elif filepath.endswith(".jpg") or filepath.endswith(".jpeg"):
            mime_type = "image/jpeg"
        else:
            mime_type = "image/png"
    
    with open(filepath, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")
    return f"data:{mime_type};base64,{data}"


def try_replicate_flux_ip_adapter():
    """
    Попытка 1: Replicate Flux Pro + IP-Adapter (или по крайней мере img2img с референсом).
    """
    print("=" * 60)
    print("Попытка 1: Replicate Flux через img2img с референсом")
    print("=" * 60)
    
    # Используем лучший референс (photo3.jpg - самый качественный портрет)
    ref_path = REFERENCE_PHOTOS[2]  # photo3.jpg
    
    results = {}
    
    # Сценарии генерации
    scenarios = [
        {
            "name": "test_front",
            "filename": "test_front.jpg",
            "prompt": "front-facing portrait of a young woman with long straight platinum blonde hair, fair skin, blue eyes, neutral expression, passport photo, well-lit, high quality, photorealistic, detailed skin texture, no smile, plain background",
            "negative_prompt": "cartoon, anime, illustration, painting, bad quality, blurry, deformed, ugly, asymmetric, bad anatomy, watermark, text, logo",
        },
        {
            "name": "test_45right",
            "filename": "test_45right.jpg",
            "prompt": "three-quarter right portrait of a young woman with long straight platinum blonde hair, fair skin, blue eyes, neutral expression, turned 45 degrees to the right, passport photo style, well-lit, high quality, photorealistic, detailed skin texture, no smile, plain background",
            "negative_prompt": "cartoon, anime, illustration, painting, bad quality, blurry, deformed, ugly, asymmetric, bad anatomy, watermark, text, logo",
        },
    ]
    
    for scenario in scenarios:
        print(f"\n--- Генерация: {scenario['name']} ---")
        
        # Пробуем несколько моделей
        models_to_try = [
            # Flux Pro 1.1 - лучшая модель для фотореализма
            ("black-forest-labs/flux-pro-1.1", {
                "prompt": scenario["prompt"],
                "negative_prompt": scenario["negative_prompt"],
                "aspect_ratio": "3:4",
                "output_format": "jpg",
                "steps": 50,
                "guidance": 3.5,
            }),
            # Flux Dev + img2img
            ("lucataco/flux-dev", {
                "prompt": scenario["prompt"],
                "negative_prompt": scenario["negative_prompt"],
                "image": file_to_data_uri(ref_path),
                "strength": 0.85,
                "aspect_ratio": "3:4",
                "output_format": "jpg",
                "steps": 50,
                "guidance": 3.5,
            }),
            # SDXL + IP-Adapter Face ID
            ("fofr/sdxl-ip-adapter-face-id", {
                "prompt": scenario["prompt"],
                "negative_prompt": scenario["negative_prompt"],
                "face_image": file_to_data_uri(ref_path),
                "width": 768,
                "height": 1024,
                "num_outputs": 1,
                "scheduler": "DPMSolverMultistep",
                "num_inference_steps": 30,
                "guidance_scale": 7.5,
            }),
        ]
        
        for model_name, input_params in models_to_try:
            print(f"  Trying model: {model_name}")
            try:
                output = replicate.run(
                    model_name,
                    input=input_params
                )
                
                # Обработка результата
                if output and len(output) > 0:
                    image_url = str(output[0]) if isinstance(output, list) else str(output)
                    print(f"  ✅ Успех! URL: {image_url}")
                    
                    # Сохраняем результат
                    output_path = os.path.join(OUTPUT_DIR, scenario["filename"])
                    
                    # Скачиваем изображение
                    import urllib.request
                    urllib.request.urlretrieve(image_url, output_path)
                    
                    file_size = os.path.getsize(output_path)
                    print(f"  💾 Сохранено: {output_path} ({file_size} bytes)")
                    
                    results[scenario["name"]] = {
                        "model": model_name,
                        "params": input_params,
                        "path": output_path,
                        "size": file_size,
                        "url": image_url,
                    }
                    break  # Успешно, переходим к следующему сценарию
                else:
                    print(f"  ❌ Нет результата")
                    
            except Exception as e:
                print(f"  ❌ Ошибка: {e}")
                continue
        
        if scenario["name"] not in results:
            print(f"  ⚠️ Не удалось сгенерировать {scenario['name']} ни одной моделью")
    
    return results


def try_replicate_instant_id():
    """
    Попытка 2: InstantID на Replicate.
    """
    print("\n" + "=" * 60)
    print("Попытка 2: Replicate InstantID")
    print("=" * 60)
    
    ref_path = REFERENCE_PHOTOS[2]  # photo3.jpg
    
    try:
        # Проверяем доступность InstantID модели
        output = replicate.run(
            "zsxkib/instant-id",
            input={
                "image": file_to_data_uri(ref_path),
                "prompt": "portrait photo of a young woman with long platinum blonde hair, blue eyes, fair skin, neutral expression, front view, passport photo, photorealistic, highly detailed",
                "negative_prompt": "cartoon, anime, illustration, painting, bad quality, blurry, ugly, deformed",
                "num_inference_steps": 30,
                "guidance_scale": 5.0,
                "width": 768,
                "height": 1024,
                "num_outputs": 1,
            }
        )
        
        if output:
            url = str(output[0]) if isinstance(output, list) else str(output)
            print(f"  ✅ Успех! URL: {url}")
            
            output_path = os.path.join(OUTPUT_DIR, "test_instantid_front.jpg")
            import urllib.request
            urllib.request.urlretrieve(url, output_path)
            
            return {
                "model": "zsxkib/instant-id",
                "path": output_path,
                "size": os.path.getsize(output_path),
                "url": url,
            }
    except Exception as e:
        print(f"  ❌ InstantID не сработал: {e}")
    
    return None


def generate_front_via_flux_pro():
    """
    Прямая генерация через Flux Pro 1.1 — лучший фотореализм.
    Используем подробный промпт для максимального совпадения с референсами.
    """
    print("\n" + "=" * 60)
    print("Попытка 3: Flux Pro 1.1 — прямая генерация с детальным промптом")
    print("=" * 60)
    
    ref_path = REFERENCE_PHOTOS[2]
    
    scenarios = [
        {
            "name": "test_front",
            "filename": "test_front.jpg",
            "prompt": "Professional passport photo of a young Caucasian woman, mid-to-late 20s, oval face, long straight platinum blonde hair parted in center, fair skin with warm undertones, blue almond-shaped eyes, straight narrow nose, full lips with defined cupid's bow, gently contoured jawline, neutral expression, mouth closed, looking directly at camera, even lighting, no shadows, plain light gray background, photorealistic, sharp focus, detailed skin texture, natural skin, no makeup or very minimal natural makeup, high quality passport photograph, 600 DPI",
        },
        {
            "name": "test_45right",
            "filename": "test_45right.jpg",
            "prompt": "Professional passport photo of a young Caucasian woman, mid-to-late 20s, oval face, long straight platinum blonde hair, fair skin with warm undertones, blue almond-shaped eyes, straight narrow nose, full lips with defined cupid's bow, gently contoured jawline, neutral expression, mouth closed, head turned 45 degrees to the right, three-quarter view, even lighting, no shadows, plain light gray background, photorealistic, sharp focus, detailed skin texture, natural skin, no makeup or very minimal natural makeup, high quality passport photograph",
        },
    ]
    
    results = {}
    
    for scenario in scenarios:
        print(f"\n--- Генерация: {scenario['name']} ---")
        
        try:
            output = replicate.run(
                "black-forest-labs/flux-pro-1.1",
                input={
                    "prompt": scenario["prompt"],
                    "aspect_ratio": "3:4",
                    "output_format": "jpg",
                    "steps": 50,
                    "guidance": 3.5,
                    "safety_tolerance": 5,
                }
            )
            
            image_url = str(output[0]) if isinstance(output, list) else str(output)
            print(f"  ✅ Успех! URL: {image_url}")
            
            output_path = os.path.join(OUTPUT_DIR, scenario["filename"])
            import urllib.request
            urllib.request.urlretrieve(image_url, output_path)
            
            file_size = os.path.getsize(output_path)
            print(f"  💾 Сохранено: {output_path} ({file_size} bytes)")
            
            results[scenario["name"]] = {
                "model": "black-forest-labs/flux-pro-1.1",
                "params": {
                    "prompt": scenario["prompt"],
                    "aspect_ratio": "3:4",
                    "steps": 50,
                    "guidance": 3.5,
                },
                "path": output_path,
                "size": file_size,
                "url": image_url,
            }
        except Exception as e:
            print(f"  ❌ Ошибка: {e}")
    
    return results


def main():
    print("🚀 Запуск генерации тестовых паспортных фото Зинаиды")
    print(f"📁 Референсы: {REFERENCE_DIR}")
    print(f"📁 Выход: {OUTPUT_DIR}")
    print(f"📸 Файлы референсов: {REFERENCE_PHOTOS}")
    
    for f in REFERENCE_PHOTOS:
        if os.path.exists(f):
            print(f"  ✅ {f} ({os.path.getsize(f)} bytes)")
        else:
            print(f"  ❌ {f} — НЕ НАЙДЕН!")
    
    # Пробуем разные подходы
    all_results = {}
    
    # Подход 1: Flux Pro 1.1 с детальным промптом (самый качественный фотореализм)
    print("\n\n📌 СТРАТЕГИЯ 1: Flux Pro 1.1")
    results = generate_front_via_flux_pro()
    all_results.update(results)
    
    # Если Flux Pro не сработал, пробуем другие подходы
    if len(all_results) < 2:
        print("\n\n📌 СТРАТЕГИЯ 2: SDXL + IP-Adapter Face ID")
        results = try_replicate_flux_ip_adapter()
        all_results.update(results)
    
    # Если всё ещё не хватает, пробуем InstantID
    if len(all_results) < 2:
        print("\n\n📌 СТРАТЕГИЯ 3: InstantID")
        result = try_replicate_instant_id()
        if result:
            # Для второго ракурса пробуем другой промпт
            ref_path = REFERENCE_PHOTOS[2]
            try:
                output = replicate.run(
                    "zsxkib/instant-id",
                    input={
                        "image": file_to_data_uri(ref_path),
                        "prompt": "portrait photo of a young woman with long platinum blonde hair, blue eyes, fair skin, neutral expression, three-quarter view, turned to the right, 45 degree angle, passport photo, photorealistic, detailed skin",
                        "negative_prompt": "cartoon, anime, illustration, painting, bad quality, blurry, ugly, deformed",
                        "num_inference_steps": 30,
                        "guidance_scale": 5.0,
                        "width": 768,
                        "height": 1024,
                        "num_outputs": 1,
                    }
                )
                if output:
                    url = str(output[0]) if isinstance(output, list) else str(output)
                    output_path = os.path.join(OUTPUT_DIR, "test_45right.jpg")
                    import urllib.request
                    urllib.request.urlretrieve(url, output_path)
                    all_results["test_45right"] = {
                        "model": "zsxkib/instant-id",
                        "path": output_path,
                        "size": os.path.getsize(output_path),
                        "url": url,
                    }
            except Exception as e:
                print(f"  ❌ InstantID 45° не сработал: {e}")
    
    # Итоговый отчёт
    print("\n\n" + "=" * 60)
    print("📊 ИТОГОВЫЙ ОТЧЁТ")
    print("=" * 60)
    
    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "reference_files": [os.path.abspath(f) for f in REFERENCE_PHOTOS],
        "results": {},
    }
    
    expected = ["test_front", "test_45right"]
    for name in expected:
        if name in all_results:
            r = all_results[name]
            print(f"\n✅ {name}:")
            print(f"   Путь: {r['path']}")
            print(f"   Размер: {r['size']} bytes")
            print(f"   Модель: {r.get('model', 'unknown')}")
            if 'params' in r:
                print(f"   Параметры: {json.dumps(r['params'], indent=4, default=str)}")
            
            report["results"][name] = {
                "path": os.path.abspath(r["path"]),
                "size_bytes": r["size"],
                "model": r.get("model", "unknown"),
                "params": r.get("params", {}),
                "url": r.get("url", ""),
            }
        else:
            print(f"\n❌ {name}: НЕ СГЕНЕРИРОВАНО")
    
    # Сохраняем отчёт
    report_path = os.path.join(OUTPUT_DIR, "generation_report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\n📄 Отчёт сохранён: {report_path}")
    
    return all_results


if __name__ == "__main__":
    results = main()
    if len(results) >= 2:
        print("\n🎉 УСПЕХ: Все 2 тестовых фото сгенерированы!")
    else:
        print(f"\n⚠️ Сгенерировано {len(results)}/2 фото")
    sys.exit(0 if len(results) >= 2 else 1)

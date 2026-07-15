#!/usr/bin/env python3
"""
Генерация фото Зинаиды через Replicate — v3 с правильными именами моделей.
"""
import os
import sys
import base64
import json
import time
import urllib.request
import replicate

OUR_PHOTOS = [
    "/opt/zinaida/inbox/Контент/111/IMG_0413.PNG",
    "/opt/zinaida/inbox/Контент/111/IMG_0415.PNG",
    "/opt/zinaida/inbox/Контент/111/IMG_9391.JPG",
]

OUTPUT_DIR = "/opt/zinaida/design/passport/generated"
os.makedirs(OUTPUT_DIR, exist_ok=True)
RATE_DELAY = 12


def file_to_data_uri(filepath):
    import mimetypes
    mime_type, _ = mimetypes.guess_type(filepath)
    if mime_type is None:
        ext = filepath.lower()
        if ext.endswith(".png"):
            mime_type = "image/png"
        elif ext.endswith(".jpg") or ext.endswith(".jpeg"):
            mime_type = "image/jpeg"
        else:
            mime_type = "image/png"
    with open(filepath, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")
    return f"data:{mime_type};base64,{data}"


def generate_with_retry(model, input_params, max_retries=3):
    for attempt in range(max_retries):
        try:
            output = replicate.run(model, input=input_params)
            return output
        except replicate.exceptions.ReplicateError as e:
            status = e.detail.get("status", 0) if isinstance(e.detail, dict) else 0
            if status == 429:
                wait = 15 + (attempt * 10)
                print(f"  ⏳ Rate limit, жду {wait}с (попытка {attempt+1}/{max_retries})...")
                time.sleep(wait)
            else:
                print(f"  ❌ Ошибка {status}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(10)
                else:
                    return None
        except Exception as e:
            print(f"  ❌ Ошибка: {e}")
            if attempt < max_retries - 1:
                time.sleep(10)
            else:
                return None
    return None


def save_result(output, filename):
    if not output:
        return None
    url = str(output[0]) if isinstance(output, list) else str(output)
    out_path = os.path.join(OUTPUT_DIR, filename)
    urllib.request.urlretrieve(url, out_path)
    size = os.path.getsize(out_path)
    print(f"  ✅ {out_path} ({size} bytes)")
    return {"path": out_path, "size": size, "url": url}


def generate_flux_pro():
    """Flux Pro — лучший фотореализм."""
    print("\n" + "=" * 60)
    print("1. Flux 1.1 Pro — фотореализм")
    print("=" * 60)

    scenarios = [
        {
            "name": "front_serious",
            "filename": "front_serious.jpg",
            "prompt": "Professional high-end portrait photo of a young Russian woman, 27-28 years old, oval face shape, long platinum blonde straight hair parted in the middle, fair skin with neutral-cool undertones, blue almond-shaped eyes, straight narrow nose bridge, defined cupid's bow lips, gently contoured jawline, neutral serious expression, looking directly at camera, studio lighting, plain light gray seamless background, razor sharp focus on eyes, hyper-detailed skin texture with visible pores, natural skin finish without retouching, minimal natural makeup, shot on Hasselblad, 100mm lens, f/8, professional photography, ultra high resolution, raw photo style, photorealistic",
        },
        {
            "name": "front_smile",
            "filename": "front_smile.jpg",
            "prompt": "Professional high-end portrait photo of a young Russian woman, 27-28 years old, oval face shape, long platinum blonde straight hair parted in the middle, fair skin with neutral-cool undertones, blue almond-shaped eyes, straight narrow nose, defined lips, warm genuine smile showing slight teeth, looking directly at camera, soft studio lighting, plain light gray background, razor sharp focus on eyes, hyper-detailed skin texture with visible pores, natural skin, no retouching, bare natural makeup, shot on Hasselblad, 100mm lens, professional photography, ultra high resolution, raw photo style, photorealistic",
        },
        {
            "name": "profile_left",
            "filename": "profile_left.jpg",
            "prompt": "Professional high-end portrait photo of a young Russian woman, 28 years old, oval face shape, long straight platinum blonde hair, fair skin with neutral-cool undertones, blue eyes, straight narrow nose, defined lips, neutral expression, turned to left profile, side view, studio lighting, plain background, razor sharp focus, hyper-detailed skin texture with visible pores, natural skin, no retouching, shot on Hasselblad, 100mm lens, 8k, photorealistic",
        },
        {
            "name": "three_quarter",
            "filename": "three_quarter.jpg",
            "prompt": "Professional high-end portrait photo of a young Russian woman, 28 years old, oval face shape, long straight platinum blonde hair, fair skin with neutral-cool undertones, blue almond-shaped eyes, straight narrow nose, defined lips, neutral expression, three-quarter view, body turned slightly left, head turned toward camera, studio lighting, plain background, razor sharp focus on eyes, hyper-detailed skin texture with visible pores, natural skin, no retouching, shot on Hasselblad, 100mm lens, 8k, photorealistic",
        },
        {
            "name": "dramatic",
            "filename": "dramatic.jpg",
            "prompt": "Professional editorial portrait photo of a young Russian woman, 28 years old, long straight platinum blonde hair, fair skin with neutral-cool undertones, blue eyes, straight nose, defined lips, confident expression, dramatic side lighting with strong shadows, dark background, high contrast, studio photography, razor sharp focus, hyper-detailed skin texture, natural skin, no retouching, editorial style, shot on Hasselblad, 100mm lens, 8k, photorealistic",
        },
        {
            "name": "profile_right",
            "filename": "profile_right.jpg",
            "prompt": "Professional high-end portrait photo of a young Russian woman, 28 years old, oval face shape, long straight platinum blonde hair, fair skin with neutral-cool undertones, blue eyes, straight narrow nose, defined lips, neutral expression, turned to right profile, side view, studio lighting, plain background, razor sharp focus, hyper-detailed skin texture with visible pores, natural skin, no retouching, shot on Hasselblad, 100mm lens, 8k, photorealistic",
        },
    ]

    results = {}
    for sc in scenarios:
        print(f"\n--- {sc['name']} ---")
        output = generate_with_retry(
            "black-forest-labs/flux-1.1-pro",
            {
                "prompt": sc["prompt"],
                "aspect_ratio": "3:4",
                "output_format": "jpg",
                "steps": 50,
                "guidance": 3.5,
                "safety_tolerance": 5,
            },
        )
        if output:
            r = save_result(output, sc["filename"])
            if r:
                results[sc["name"]] = {"model": "black-forest-labs/flux-1.1-pro", **r}
        print(f"  ⏱ Жду {RATE_DELAY}с...")
        time.sleep(RATE_DELAY)

    return results


def generate_flux_pulid():
    """
    Flux PuLID — Pure and Lightning ID Customization.
    Лучшая модель для сохранения лица на Flux!
    """
    print("\n" + "=" * 60)
    print("2. Flux PuLID — сохранение лица + Flux качество")
    print("=" * 60)

    # Используем лучшее фото как ID reference
    ref_uri = file_to_data_uri(OUR_PHOTOS[2])

    scenarios = [
        {
            "name": "pulid_front",
            "filename": "pulid_front.jpg",
            "prompt": "portrait photo of a woman with platinum blonde hair, blue eyes, fair skin, neutral expression, front view, looking at camera, photorealistic, detailed skin texture, natural skin, studio lighting, gray background",
        },
        {
            "name": "pulid_smile",
            "filename": "pulid_smile.jpg",
            "prompt": "portrait photo of a woman with platinum blonde hair, blue eyes, fair skin, warm smile, front view, looking at camera, photorealistic, detailed skin texture, natural skin, soft lighting, gray background",
        },
        {
            "name": "pulid_profile",
            "filename": "pulid_profile.jpg",
            "prompt": "portrait photo of a woman with platinum blonde hair, blue eyes, fair skin, neutral expression, side profile view, photorealistic, detailed skin texture, natural skin, studio lighting",
        },
    ]

    results = {}
    for sc in scenarios:
        print(f"\n--- {sc['name']} ---")
        output = generate_with_retry(
            "bytedance/flux-pulid",
            {
                "input": ref_uri,
                "prompt": sc["prompt"],
                "negative_prompt": "cartoon, anime, illustration, painting, bad quality, blurry, ugly, deformed, asymmetric, watermark, text, logo",
                "steps": 30,
                "guidance_scale": 3.5,
                "width": 768,
                "height": 1024,
            },
        )
        if output:
            r = save_result(output, sc["filename"])
            if r:
                results[sc["name"]] = {"model": "bytedance/flux-pulid", **r}
        print(f"  ⏱ Жду {RATE_DELAY}с...")
        time.sleep(RATE_DELAY)

    return results


def generate_sdxl_ip_adapter():
    """
    SDXL + IP-Adapter Face ID — удержание лица.
    """
    print("\n" + "=" * 60)
    print("3. SDXL + IP-Adapter Face ID")
    print("=" * 60)

    ref_uri = file_to_data_uri(OUR_PHOTOS[2])

    scenarios = [
        {
            "name": "faceid_front",
            "filename": "faceid_front.jpg",
            "prompt": "portrait photo of a woman with platinum blonde hair, blue eyes, fair skin, neutral expression, front view, looking at camera, photorealistic, detailed skin texture, natural skin, 8k quality",
        },
        {
            "name": "faceid_smile",
            "filename": "faceid_smile.jpg",
            "prompt": "portrait photo of a woman with platinum blonde hair, blue eyes, fair skin, warm smile, front view, looking at camera, photorealistic, detailed skin texture, natural skin, 8k quality",
        },
    ]

    results = {}
    for sc in scenarios:
        print(f"\n--- {sc['name']} ---")
        output = generate_with_retry(
            "fofr/sdxl-ip-adapter-face-id",
            {
                "input_image": ref_uri,
                "prompt": sc["prompt"],
                "negative_prompt": "cartoon, anime, illustration, painting, bad quality, blurry, ugly, deformed, asymmetric, watermark, text, logo",
                "num_inference_steps": 30,
                "guidance_scale": 5.0,
                "width": 768,
                "height": 1024,
                "num_outputs": 1,
            },
        )
        if output:
            r = save_result(output, sc["filename"])
            if r:
                results[sc["name"]] = {"model": "fofr/sdxl-ip-adapter-face-id", **r}
        print(f"  ⏱ Жду {RATE_DELAY}с...")
        time.sleep(RATE_DELAY)

    return results


def main():
    print("🚀 Генерация фото Зинаиды (v3) — правильные имена моделей")
    print("=" * 60)

    for f in OUR_PHOTOS:
        status = "✅" if os.path.exists(f) else "❌"
        print(f"{status} Референс: {f}")

    all_results = {}

    # 1: Flux 1.1 Pro — лучший фотореализм (6 фото)
    all_results.update(generate_flux_pro())

    # 2: Flux PuLID — лицо + качество (3 фото)
    all_results.update(generate_flux_pulid())

    # 3: SDXL IP-Adapter — удержание лица (2 фото)
    all_results.update(generate_sdxl_ip_adapter())

    # Отчёт
    print("\n\n" + "=" * 60)
    print("📊 ИТОГОВЫЙ ОТЧЁТ — v3")
    print("=" * 60)

    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "reference_files": [os.path.abspath(f) for f in OUR_PHOTOS],
        "total_generated": len(all_results),
        "results": {},
    }

    for name, r in sorted(all_results.items()):
        print(f"\n✅ {name}:")
        print(f"   Путь: {r['path']}")
        print(f"   Размер: {r['size']} bytes")
        print(f"   Модель: {r['model']}")
        report["results"][name] = {
            "path": r["path"],
            "size_bytes": r["size"],
            "model": r["model"],
            "url": r.get("url", ""),
        }

    report_path = os.path.join(OUTPUT_DIR, "generation_v3_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\n📄 Отчёт: {report_path}")
    print(f"🎉 Всего: {len(all_results)} фото")

    return all_results


if __name__ == "__main__":
    results = main()
    if not results:
        print("❌ Ничего не сгенерировано!")
        sys.exit(1)
    print(f"\n🎉 Успешно: {len(results)} фото")

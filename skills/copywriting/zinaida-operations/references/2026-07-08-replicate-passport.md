# Генерация паспортных фото Зинаиды через Replicate

Дата: 2026-07-08
Модель: `black-forest-labs/flux-1.1-pro` (Replicate)

## Контекст
Для создания визуального контента (посты, обложки, видео) нужен паспорт персонажа Зинаиды — набор сгенерированных фото в разных ракурсах, консистентных по внешности. Источник — 3 оригинальных фото (IMG_0413.PNG, IMG_0415.PNG, IMG_9391.JPG).

## Папки

| Назначение | Путь |
|-----------|------|
| Оригиналы (сервер) | `/opt/zinaida/design/references/zinaida_face/` |
| Оригиналы (OneDrive) | `/opt/zinaida/inbox/Контент/kontent/dizayner/zinaida_passport/original/` |
| Генерации (сервер) | `/opt/zinaida/design/passport/generated/` |
| Генерации (OneDrive) | `/opt/zinaida/inbox/Контент/kontent/dizayner/zinaida_passport/generated/` |
| Паспорт персонажа | `/opt/zinaida/design/passport/ZINAIDA_PASSPORT.md` |

OneDrive смонтирован: `onedrive:Виктория → /opt/zinaida/inbox/`

## Как генерировать через Replicate

### Прямой curl-запрос

```bash
# 1. Запустить генерацию
PREDICTION=$(curl -s -X POST https://api.replicate.com/v1/models/black-forest-labs/flux-1.1-pro/predictions \
  -H "Authorization: Bearer $REPLICATE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "prompt": "A confident elegant woman in her early 30s, dark hair with auburn copper tips, wearing a white oversized shirt, direct gaze at camera, slight knowing smile. Setting: panoramic windows with palm trees and sea view, luxury modern interior. Professional editorial photography style, cinematic lighting, photorealistic, 8K.",
      "width": 1024,
      "height": 1024,
      "num_outputs": 1,
      "num_inference_steps": 50,
      "guidance_scale": 7.5
    }
  }')

# Извлечь ID
ID=$(echo $PREDICTION | python3 -c "import json,sys; print(json.load(sys.stdin)['id'])")

# 2. Подождать 15-20 секунд, проверить результат
curl -s "https://api.replicate.com/v1/predictions/$ID" \
  -H "Authorization: Bearer $REPLICATE_TOKEN"
```

Ответ: `status:succeeded`, `output: https://replicate.delivery/.../file.webp`

### Через Python/скрипты

На сервере есть готовые скрипты:
- `/opt/zinaida/design/passport/generate_passport_photos.py` — полный пайплайн
- `/opt/zinaida/design/passport/generate_zinaida_good_faces.py` — генерация с IP-адаптером
- `/opt/zinaida/design/passport/generate_faces.py` — старая версия
- `/opt/zinaida/design/passport/test_ip_adapter.py` — тест IP-адаптера

### Скачивание результата
```bash
curl -sL "<url_из_output>" -o "/opt/zinaida/design/passport/generated/zinaida_v4_N_RACURS.webp"
```

## Промпт для портрета Зинаиды (из паспорта)

```
A confident elegant woman in her early 30s, dark hair with auburn/copper tips,
wearing a white oversized shirt, black skirt or leather pants, AR glasses on head,
smart watch, name necklace. Direct gaze at camera, slight knowing smile.
Setting: panoramic windows with palm trees and sea view, luxury modern interior.
Vibe: confidence, intelligence, power, sensuality.
Professional editorial photography style.
```

### Варианты ракурсов
1. **front_serious** — анфас, серьёзный взгляд (уверенность)
2. **front_smile** — анфас, лёгкая улыбка (тёплый)
3. **three_quarter** — 3/4 поворот влево
4. **profile_left** — профиль влево
5. **profile_right** — профиль вправо
6. **dramatic** — контровой свет, драматический портрет
7. **looking_up** — взгляд вверх (вдохновение)
8. **laughing** — смех (искренность)
9. **side_looking** — взгляд в сторону (задумчивость)
10. **hands_gesturing** — с жестами (доверие)

Цель: 20-30 ракурсов для полного паспорта (видео + фото).

## Replicate токен
Хранится в `/opt/zinaida/config/secrets.env` как `REPLICATE_API_TOKEN`.
Проверка: `curl -s -X POST https://api.replicate.com/v1/predictions ...` (должен вернуть `status:starting`)

## Лера и генерация
Профиль `lera` имеет навыки:
- `replicate-watch` — мониторинг Replicate
- `study-replicate` — изучение моделей
- `apikey-image-gen` — генерация через API
- `compare-face-models` — сравнение результатов

Лера может генерировать через те же скрипты, вызывая `terminal()` на сервере.

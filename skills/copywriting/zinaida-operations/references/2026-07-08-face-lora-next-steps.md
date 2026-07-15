# Replicate Face LoRA — продолжение (2026-07-08, остановились на создании модели)

## Где остановились

Текущий токен (Zina2, `r8_QZW...`) даёт 403 при создании модели через API.
Нужно создать модель через веб-интерфейс.

## Что нужно сделать Олегу (следующий шаг)

1. Зайти на https://replicate.com/create
2. Залогиниться через Google (почта: toyotaverymany11@gmail.com)
3. Заполнить:
   - **Name:** `zinaida-face-lora`
   - **Visibility:** Private
   - **Hardware:** GPU T4 (самый дешёвый, $0.000725/сек)
4. Нажать **Create model**

## Что сделаю я после этого

1. Загружу `/tmp/zinaida_training.zip` (3 фото: IMG_0413.PNG, IMG_0415.PNG, IMG_9391.JPG)
   - `curl -X POST https://api.replicate.com/v1/files -H "Authorization: Bearer $TOKEN" -F "content=@/tmp/zinaida_training.zip;type=application/zip;filename=data.zip"`
2. Запущу тренировку через `replicate/fast-flux-trainer`:
   - trigger_word: `ZINAIDA`
   - lora_type: `subject`
   - training_steps: 1000
   - destination: созданная модель
3. Через ~2 мин получим готовую LoRA
4. Сгенерируем тестовое фото с триггер-словом
5. Сравним с оригиналом через vision

## Триггер-слово

Использовать `ZINAIDA` (все капсом). В промптах: `"a photo of ZINAIDA, the same person as reference, blonde hair, blue eyes..."`

## Ссылки

- https://replicate.com/blog/fine-tune-flux-with-an-api — полный гайд
- https://replicate.com/replicate/fast-flux-trainer/train — форма тренировки (веб)
- https://replicate.com/create — создание модели
- https://replicate.com/account/api-tokens — токены

## Что понадобится ещё

- Проверить баланс (~$10 хватит на тренировку $2 + сотни генераций)
- Если токен не даст запустить тренинг — создать новый на replicate.com/account/api-tokens

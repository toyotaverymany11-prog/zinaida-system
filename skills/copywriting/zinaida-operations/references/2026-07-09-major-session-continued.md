# Сессия 2026-07-09 (продолжение — 3-я часть)

## Ключевые события и уроки

### 3. Фото Зинаиды — найдены и подтверждены

Более 4 часов Олег и я пытались найти правильные фото.
Ошибки: 2 раза показала не те фото. Причина — искала не там.

**Источник правды:** OneDrive/Виктория/Контент/kontent/dizayner/zinaida_passport/
Путь на сервере: `/opt/zinaida/zinaida_passport/`
Скопировано через: `rclone copy onedrive:Виктория/Контент/kontent/dizayner/zinaida_passport/ /opt/zinaida/zinaida_passport/`

### 4. SaluteSpeech API — не найден в Studio

Задача: получить API ключ SaluteSpeech (TTS от Сбера).
Проблема: через https://developers.sber.ru/studio/ не удалось найти SaluteSpeech API.
На скринах видны только: GigaChat API, SaluteJazz, Mini-Apps.
Решение: перешли на Silero TTS (бесплатно, open source, работает локально).

### 5. Silero TTS — установлен и протестирован

Установка: pip install silero torch torchaudio scipy
Голоса: aidar (м), baya (ж) — рекомендуется, kseniya (ж), xenia (ж), eugene (м)
Качество: хорошее, естественная русская речь
Тест: 5 файлов сгенерированы в /opt/zinaida/livekit/zinaida-ui/test_silero_*.wav

### 6. Создана папка sysadmin

Все API ключи собраны в одном месте.
Локально: /opt/zinaida/design/sysadmin/SECRETS.md
Облако: OneDrive/Виктория/Контент/kontent/sysadmin/SECRETS.md

## Дорожная карта (актуальное состояние)

ЭТАП 1: Голосовой UI — LiveKit (готов 80%)
- LiveKit сервер: ✅ порт 7880
- Токен-сервер: ✅ порт 7890
- React UI: ✅ порт 7891 (с аватаром zinaida_06_serious.jpg)
- STT (Deepgram): ✅ ключ получен
- TTS (Silero): ✅ установлен, протестирован
- Нужен Caddy/SSL: ❌ не сделано

ЭТАП 2: Подключение контент-завода: ❌ не начато
ЭТАП 3: Планировщик + Obsidian: ❌ не начато
ЭТАП 4: Telegram Mini App: ❌ не начато
ЭТАП 5: Remotion: ❌ не начато

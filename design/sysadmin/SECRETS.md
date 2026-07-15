# 💀 СИСАДМИН — ВСЕ КЛЮЧИ И ПАРОЛИ
# Дата: 09.07.2026
# Хранить в: OneDrive/Виктория/Контент/kontent/sysadmin/
# ВНИМАНИЕ: Этот файл содержит чувствительные данные. Не показывать никому.

═══════════════════════════════════════════════
1. AI/LLM ПРОВАЙДЕРЫ
═══════════════════════════════════════════════

🔑 Deepgram (STT - распознавание речи)
   Ключ: 2c917fa7c4a00dfba0e3b91097f0ab8891e0512f
   Проект: 5d540801-1a34-4ad1-97a3-136cf8382e10
   Статус: ✅ Активен (09.07.2026)
   Где используется: /opt/zinaida/livekit/zinaida-ui/ (голосовой UI)

🔑 ElevenLabs (TTS - синтез речи)
   Ключ: ⏳ ЕЩЁ НЕ ПОЛУЧЕН
   Статус: ❌ Нужна регистрация Олега

🔑 Mistral AI (LLM + Vision)
   Ключ 1: ITTNRjD0JrGQVUpTlKum97yoV0yAROAb
   Ключ 2: 4PGuqi4DpRHIn4A0Suw8w73PEom6XV0p
   Ключ 3: 0fb8932f675f09654d4563e2f96c8e82
   Ключ 4 (Greg): 4PGuqi4DpRHIn4A0Suw8w73PEom6XV0p
   Где: /opt/zinaida/config/secrets.env

🔑 OpenAI / GitHub Models (GPT-4o-mini для vision)
   Токен: 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
   Где: /opt/zinaida/config/secrets.env, /root/.hermes/.env

🔑 OpenRouter (универсальный LLM роутер)
   Ключ: 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
   Ключ (Greg): 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
   Где: /opt/zinaida/meta_agent/.env

🔑 Ollama Cloud (LLM, локально)
   Ключ 1: 4cd339f81a8949ca859b74add25644cc.0mpl6iHetsyydTA6vdkXa6jq
   Ключ 2: 29d283bbe11546dd81893e8ac8438d4b._Y7S8JCwwoPN3KDjIco5ZH5M
   Ключ 3: e094248ab5eb4a23915c041ac82d3b10.NzW_KQ85LgfxRqUgKpxQkQsY
   Где: /opt/zinaida/config/secrets.env

🔑 Zhipu AI (GLM-4-Flash, Китай)
   Ключ: 73c9e5414f93b1def516a6c4d509be58.8GGzhn8OJRhfbc7XU
   Где: /opt/zinaida/meta_agent/.env

🔑 GigaChat (Сбер, РФ)
   Client ID: 019d967c-5279-7677-bd29-e4e26eb88431
   Client Secret: MDE5ZDk2N2MtNTI3OS03Njc3LWJkMjktZTRlMjZlYjg4NDMxOmM4Y2RmN2EwLWM0MzMtNDBhOC04Mjk1LTMzMzVkMDM3NjIwOQ==
   Auth Key: MDE5ZDk2N2MtNTI3OS03Njc3LWJkMjktZTRlMjZlYjg4NDMxOmM4Y2RmN2EwLWM0MzMtNDBhOC04Mjk1LTMzMzVkMDM3NjIwOQ==
   Где: /opt/zinaida/meta_agent/.env, /opt/zinaida/config/secrets.env

🔑 Replicate (генерация изображений, LoRA)
   Токен: r8_QZWIGxn9XaMAxfoOh8LwRfCJh3fOLEjv5eXs
   Где: /opt/zinaida/config/secrets.env

🔑 DeepSeek (DeepSeek V3/V4)
   Ключ: ⏳ НЕ НАЙДЕН (обозначен как ***)
   Статус: ⚠️ Надо проверить

═══════════════════════════════════════════════
2. СОЦСЕТИ
═══════════════════════════════════════════════

🔑 Telegram Bot (основной)
   Токен 1: 8247397375:AAEmZP8zHn2k8dLfR1zFElHJnFxn7S7O7Pg
   Токен 2: 8560311602:AAGIsquGY6dpk21dF4HGtMSI5WWxpWz3pIk
   Чат: 6670783611 (Олег)
   Канал: -1004483766379 (утверждение)
   Где: /opt/zinaida/meta_agent/.env, /root/.hermes/.env

🔑 VK
   Токен: VK_GROUP_TOKEN в /opt/zinaida/.env
   Группа: aipsiholog (ID: -237663277)
   Ссылка: https://vk.com/aipsiholog
   Статус: ✅ Активен (10.07.2026)
   Права: wall, photos, stats, docs, groups

═══════════════════════════════════════════════
3. ИНФРАСТРУКТУРА
═══════════════════════════════════════════════

🔑 Tavily Search (веб-поиск для агентов)
   Ключ: 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
   Где: /root/.hermes/.env

🔑 LiveKit (WebRTC транспорт)
   API Key: zinaida-key
   API Secret: zinaida-secret-key
   Где: /opt/zinaida/livekit/

🔑 Hermes API Server
   Ключ: ba58f1bc656c295732d8c9ea15c35775cbad6d1b47517e6aa64e48d722be263f
   Где: /root/.hermes/.env

═══════════════════════════════════════════════
4. СТРУКТУРА ПАПОК (референс)
═══════════════════════════════════════════════

/env файлы:
  /opt/zinaida/config/secrets.env    ← основной файл секретов
  /opt/zinaida/meta_agent/.env       ← роутер и агенты
  /root/.hermes/.env                 ← Hermes (дублирует часть ключей)

Конфиги:
  /root/.hermes/config.yaml          ← Hermes конфигурация
  /opt/zinaida/meta_agent/provider_manager.py  ← провайдеры

Облако (OneDrive) — папка Виктория:
  OneDrive/Файлы/Виктория/Контент/kontent/sysadmin/   ← ЭТА ПАПКА
  OneDrive/Файлы/Виктория/Контент/kontent/dizayner/   ← дизайн

Локальная копия облака:
  /opt/zinaida/design/sysadmin/       ← синхронизируется с OneDrive через rclone

═══════════════════════════════════════════════
5. ПРАВИЛО
═══════════════════════════════════════════════

Любой новый ключ/пароль/токен — сразу в:
  /opt/zinaida/design/sysadmin/SECRETS.md
  (синхронизируется в OneDrive/Виктория/Контент/kontent/sysadmin/SECRETS.md)
| 🔑 FAL.ai | 8e995491-ebb0-4650-8f66-dd0c2dee09ef:... | ✅ Работает | image_gen в Hermes |

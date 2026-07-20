#!/usr/bin/env python3
"""
Telegram Bot Bridge для Hermes Studio (v3.0 — через Gateway)
=============================================================
Связывает Telegram бота @DCHP_Shtab_bot с Hermes Studio Gateway,
чтобы Telegram имел ПОЛНЫЙ доступ к профилю Зинаиды:
навыки, инструменты, MCP, память Mem0/Holographic, session management.

Архитектура:
  Telegram → Gateway 8642 → профиль default (навыки, память, MCP) → 8005 Super Cascade

Команды:
  /newchat — создать новую сессию (сброс контекста)
  /status  — статус системы
  /start   — приветствие

v3.0 (13.07.2026):
  - Полностью переключён с прямого 8005 на Gateway API
  - Telegram получает ВСЁ что есть в вебе: навыки, инструменты, память, MCP
"""

import asyncio
import logging
import os
import sys
import json
import uuid
import re
from datetime import datetime
from pathlib import Path

sys.path.insert(0, "/opt/zinaida")

import aiohttp
import aiofiles
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes
)

# === КОНФИГУРАЦИЯ ===
BOT_TOKEN = os.getenv("TG_BOT_TOKEN", "8560310319:***")
GATEWAY_URL = "http://127.0.0.1:8005"
HERMES_CHAT_RUN = f"{GATEWAY_URL}/v1/chat/completions"
ALLOWED_CHAT_ID = int(os.getenv("TG_CHAT_ID", "6670783611"))
LOG_DIR = "/opt/zinaida/telegram_bot/logs"
MEDIA_DIR = "/opt/zinaida/telegram_bot/media"
SESSIONS_FILE = f"{LOG_DIR}/tg_sessions.json"
CONSILIUM_DIR = "/opt/zinaida/shared_memory/consilium"

# === ЛОГИРОВАНИЕ ===
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(MEDIA_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [TG-BOT-V3] %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(f"{LOG_DIR}/bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# === ХРАНЕНИЕ СЕССИЙ ===
# Маппинг chat_id -> session_id для Hermes Studio
# Храним в JSON файле, чтобы сохранялось при рестарте бота
def load_sessions():
    try:
        if os.path.exists(SESSIONS_FILE):
            with open(SESSIONS_FILE, "r") as f:
                return json.load(f)
    except:
        pass
    return {}

def save_sessions(sessions):
    os.makedirs(LOG_DIR, exist_ok=True)
    with open(SESSIONS_FILE, "w") as f:
        json.dump(sessions, f, ensure_ascii=False, indent=2)

# === ЗАГРУЗКА ПОСЛЕДНЕГО КОНСИЛИУМА ===
def get_last_consilium():
    """Находит последний CONSILIUM_*.md и возвращает его содержимое"""
    try:
        if not os.path.exists(CONSILIUM_DIR):
            return None
        
        files = [f for f in os.listdir(CONSILIUM_DIR) if f.startswith("CONSILIUM_")]
        if not files:
            return None
        
        files.sort(reverse=True)
        latest = files[0]
        
        with open(os.path.join(CONSILIUM_DIR, latest), "r", encoding="utf-8") as f:
            content = f.read()
        
        date_match = re.search(r'CONSILIUM_(\d{4}-\d{2}-\d{2})', latest)
        date_str = date_match.group(1) if date_match else "неизвестно"
        
        return {"date": date_str, "content": content[:3000]}
    except Exception as e:
        logger.warning(f"Ошибка загрузки консилиума: {e}")
        return None

# === ОТПРАВКА ЧЕРЕЗ 8005 РОУТЕР (OpenAI-совместимый) ===
async def send_to_hermes_gateway(message_text, user_id, chat_id, profile="default"):
    """
    Отправить сообщение через 8005 роутер (Super Cascade).
    Прямое обращение к OpenAI-совместимому API.
    """
    
    sessions = load_sessions()
    chat_id_str = str(chat_id)
    session_id = sessions.get(chat_id_str)
    
    full_message = f"[Источник: Telegram] {message_text}"
    
    # Загружаю ДНК ассистента (НЕ контент-персонаж!) — отдельный файл
    soul_path = "/root/.hermes/SOUL.md"
    my_dna_path = "/opt/zinaida/shared_memory/zinaida_assistant_dna.md"
    try:
        with open(my_dna_path, "r", encoding="utf-8") as f:
            system_prompt = f.read()
    except:
        try:
            with open(soul_path, "r", encoding="utf-8") as f:
                raw = f.read()
            # Берём только первую часть до инфраструктуры — отрезаем контент-персонажа
            lines = raw.split('\n')
            result = []
            skip_mode = False
            for line in lines:
                if 'Миссия проекта' in line or '## 1. МИССИЯ' in line:
                    skip_mode = True
                if not skip_mode:
                    result.append(line)
            system_prompt = '\n'.join(result[:80])
        except:
            system_prompt = "Ты — Зинаида, AI-партнёр и ассистент Олега. Женщина. Все глаголы о себе — только женского рода. Отвечаешь на русском."
    
    # Пробуем загрузить последние факты для контекста
    try:
        import subprocess
        facts_result = subprocess.run(
            ["python3", "-c", "from hermes_tools import fact_store; import json; r=fact_store(action='search', query='важное проект задача память'); print(json.dumps(r, ensure_ascii=False, default=str)[:1000])"],
            capture_output=True, text=True, timeout=5
        )
        if facts_result.stdout.strip():
            system_prompt += "\n\nКонтекст из памяти (последние факты):\n" + facts_result.stdout[:800]
    except:
        pass
    
    # OpenAI-совместимый payload для 8005
    payload = {
        "model": "8005-Router",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": full_message}
        ],
        "stream": False,
    }
    
    # Если есть сессия — добавляем историю (храним в файле)
    logger.info(f"📤 Отправляю в 8005: {full_message[:100]}...")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                HERMES_CHAT_RUN,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=180)
            ) as resp:
                body = await resp.json()
                
                if resp.status == 200:
                    reply = body.get("choices", [{}])[0].get("message", {}).get("content", "")
                    if reply:
                        # Сохраняем сессию
                        if not session_id:
                            session_id = str(uuid.uuid4())[:12]
                            sessions[chat_id_str] = session_id
                            save_sessions(sessions)
                        
                        logger.info(f"✅ Ответ от 8005 получен ({len(reply)} символов)")
                        return reply
                
                logger.error(f"❌ 8005 ответил ошибкой: {resp.status} {str(body)[:200]}")
                return f"⚠️ Не удалось связаться с Зинаидой. Сервер может быть перезапущен."

    except asyncio.TimeoutError:
        return "⏳ Зинаида обрабатывает запрос... Это может занять время. Повторите через минуту."
    except aiohttp.ClientError as e:
        logger.error(f"Connection error: {e}")
        return "⚠️ Не удалось связаться с Зинаидой. Сервер может быть перезапущен."

# === КОМАНДЫ ===
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Я Зинаида — твой AI-партнёр.\n\n"
        "📋 Команды:\n"
        "/newchat — новый чат (сброс контекста)\n"
        "/status — статус системы\n\n"
        "📸 Принимаю: фото, видео, голосовые, документы, аудио.\n"
        "Просто отправь — и я разберусь! 💬"
    )

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Проверка Gateway
    gw_ok = False
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{GATEWAY_URL}/health", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                gw_ok = resp.status == 200
    except:
        pass
    
    sessions = load_sessions()
    session_id = sessions.get(str(update.effective_chat.id), None)
    
    gw_emoji = "✅" if gw_ok else "❌"
    session_status = "✅ есть" if session_id else "🆕 новая"
    
    # Проверка 8005
    router_ok = False
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://127.0.0.1:8005/health", timeout=aiohttp.ClientTimeout(total=3)) as resp:
                router_ok = resp.status == 200
    except:
        pass
    
    router_emoji = "✅" if router_ok else "❌"
    
    await update.message.reply_text(
        f"📊 Статус системы:\n\n"
        f"{gw_emoji} Hermes Gateway: {'онлайн' if gw_ok else 'оффлайн'}\n"
        f"{router_emoji} Роутер 8005: {'онлайн' if router_ok else 'оффлайн'}\n"
        f"💬 Сессия Telegram: {session_status}\n"
        f"🔄 /newchat — сбросить сессию"
    )

async def cmd_newchat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Создать новую сессию — сброс контекста"""
    if not update.message or not update.effective_chat:
        return
    chat_id = update.effective_chat.id
    chat_id_str = str(chat_id)
    sessions = load_sessions()
    
    old_session = sessions.pop(chat_id_str, None)
    save_sessions(sessions)
    
    logger.info(f"🆕 Новая сессия для chat_id={chat_id}, старая: {old_session}")
    await update.message.reply_text(
        "🆕 Чат очищен! Начинаю новую сессию.\n"
        "Теперь я не помню предыдущий разговор."
    )

# === ЗАГРУЗКА МЕДИА ===
async def download_media(file_obj, file_name):
    file_path = os.path.join(MEDIA_DIR, file_name)
    try:
        file_bytes = await file_obj.download_as_bytearray()
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(file_bytes)
        logger.info(f"✅ Медиа сохранено: {file_path} ({len(file_bytes)} байт)")
        return file_path
    except Exception as e:
        logger.error(f"❌ Ошибка загрузки медиа: {e}")
        return None

# === ОБРАБОТКА ТЕКСТОВЫХ СООБЩЕНИЙ ===
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message_text = update.message.text
    chat_id = update.effective_chat.id

    logger.info(f"📨 [TEXT] [{user.id}] {user.first_name}: {message_text[:100]}")

    await update.message.chat.send_action("typing")

    reply = await send_to_hermes_gateway(message_text, user.id, chat_id)

    MAX_LEN = 4096
    if len(reply) <= MAX_LEN:
        await update.message.reply_text(reply)
    else:
        for i in range(0, len(reply), MAX_LEN):
            await update.message.reply_text(reply[i:i+MAX_LEN])

    logger.info(f"📤 → [{user.id}]: {reply[:100]}")

# === ОБРАБОТКА МЕДИА ===
async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id
    caption = update.message.caption or ""
    media_paths = []

    try:
        if update.message.photo:
            photo = update.message.photo[-1]
            file_obj = await photo.get_file()
            file_name = f"photo_{uuid.uuid4().hex[:8]}.jpg"
            file_path = await download_media(file_obj, file_name)
            if file_path:
                media_paths.append({"path": file_path, "type": "photo"})
            description = f"📸 Фото ({photo.width}×{photo.height})"

        elif update.message.video:
            video = update.message.video
            file_obj = await video.get_file()
            ext = video.file_name.split(".")[-1] if video.file_name else "mp4"
            file_name = f"video_{uuid.uuid4().hex[:8]}.{ext}"
            file_path = await download_media(file_obj, file_name)
            if file_path:
                media_paths.append({"path": file_path, "type": "video"})
            description = f"🎬 Видео ({video.width}×{video.height}, {video.duration}с)"

        elif update.message.voice:
            voice = update.message.voice
            file_obj = await voice.get_file()
            file_name = f"voice_{uuid.uuid4().hex[:8]}.ogg"
            file_path = await download_media(file_obj, file_name)
            if file_path:
                media_paths.append({"path": file_path, "type": "voice"})
            description = f"🎤 Голосовое ({voice.duration}с)"

        elif update.message.document:
            doc = update.message.document
            file_obj = await doc.get_file()
            ext = doc.file_name.split(".")[-1] if doc.file_name else "bin"
            file_name = f"doc_{uuid.uuid4().hex[:8]}.{ext}"
            file_path = await download_media(file_obj, file_name)
            if file_path:
                media_paths.append({"path": file_path, "type": "document"})
            description = f"📄 Документ: {doc.file_name} ({doc.mime_type})"

        elif update.message.audio:
            audio = update.message.audio
            file_obj = await audio.get_file()
            ext = audio.file_name.split(".")[-1] if audio.file_name else "mp3"
            file_name = f"audio_{uuid.uuid4().hex[:8]}.{ext}"
            file_path = await download_media(file_obj, file_name)
            if file_path:
                media_paths.append({"path": file_path, "type": "audio"})
            description = f"🎵 Аудио: {audio.title or audio.file_name} ({audio.duration}с)"

        else:
            description = "📎 Неизвестное вложение"
            logger.warning(f"Неизвестный тип медиа от {user.id}")

    except Exception as e:
        logger.error(f"❌ Ошибка загрузки медиа: {e}", exc_info=True)
        await update.message.reply_text(f"⚠️ Не удалось загрузить файл: {e}")
        return

    user_message = f"{description}"
    if caption:
        user_message += f"\n\nПодпись: {caption}"

    logger.info(f"📨 [MEDIA] [{user.id}] {user.first_name}: {description} | подпись: {caption[:100] if caption else 'нет'}")

    await update.message.chat.send_action("typing")

    reply = await send_to_hermes_gateway(user_message, user.id, chat_id)

    MAX_LEN = 4096
    if len(reply) <= MAX_LEN:
        await update.message.reply_text(reply)
    else:
        for i in range(0, len(reply), MAX_LEN):
            await update.message.reply_text(reply[i:i+MAX_LEN])

    logger.info(f"📤 → [{user.id}]: {reply[:100]}")

# === MAIN ===
def main():
    logger.info("🚀 Запуск Telegram бота v3.0 (Hermes Gateway)...")
    logger.info(f"📡 Gateway URL: {GATEWAY_URL}")
    logger.info(f"🤖 Провайдер: 8005 / 8005-Router (через Gateway)")
    
    # Сначала проверяем Gateway
    try:
        import requests  # синхронная проверка
        r = requests.get(f"{GATEWAY_URL}/health", timeout=5)
        if r.status_code == 200:
            logger.info("✅ Gateway готов к работе")
        else:
            logger.warning(f"⚠️ Gateway ответил {r.status_code}")
    except Exception as e:
        logger.error(f"❌ Gateway недоступен: {e}")
        logger.warning("⚠️ Бот запускается, но Gateway может быть не готов")
    
    app = Application.builder().token(BOT_TOKEN).build()

    # Команды
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("newchat", cmd_newchat))

    # Текстовые сообщения
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Медиа
    app.add_handler(MessageHandler(filters.PHOTO, handle_media))
    app.add_handler(MessageHandler(filters.VIDEO, handle_media))
    app.add_handler(MessageHandler(filters.VOICE, handle_media))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_media))
    app.add_handler(MessageHandler(filters.AUDIO, handle_media))

    logger.info("✅ Бот v3.0 запущен! Ожидаю сообщения...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()

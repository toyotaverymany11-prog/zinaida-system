#!/usr/bin/env python3
"""
Утилита для отправки уведомлений в Telegram из Зинаиды/Григория.
Использование:
  python3 notify.py "Текст сообщения"
  python3 notify.py --chat_id 123456 "Текст"

v2 — таймаут 15с, повтор 3 раза при ошибке.
"""
import asyncio
import sys
import os

BOT_TOKEN = os.getenv("TG_BOT_TOKEN", "8560310319:AAFFS5ubSS0FQI8xowTl9TCg3UrOw6J3pIk")
DEFAULT_CHAT_ID = int(os.getenv("TG_CHAT_ID", "6670783611"))
MAX_RETRIES = 3
TIMEOUT = 15

async def send(text, chat_id=None):
    from telegram import Bot, request
    target = chat_id or DEFAULT_CHAT_ID

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            req = request.HTTPXRequest(connect_timeout=TIMEOUT, read_timeout=TIMEOUT)
            bot = Bot(token=BOT_TOKEN, request=req)
            await bot.send_message(chat_id=target, text=text)
            print(f"✅ Отправлено в chat_id={target}")
            return True
        except Exception as e:
            print(f"⚠️ Попытка {attempt}/{MAX_RETRIES}: {str(e)[:60]}")
            if attempt < MAX_RETRIES:
                await asyncio.sleep(3)
            else:
                print(f"❌ Не удалось отправить после {MAX_RETRIES} попыток")
                return False

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("message", help="Текст сообщения")
    parser.add_argument("--chat_id", type=int, default=DEFAULT_CHAT_ID)
    args = parser.parse_args()
    exit_code = 0 if asyncio.run(send(args.message, args.chat_id)) else 1
    sys.exit(exit_code)

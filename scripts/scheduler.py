#!/usr/bin/env python3
"""
Планировщик событий для Зинаиды.
Использование (из любого чата):
  "запомни 13 июля в 11:20 прием у хирурга"
  "напомни завтра в 9 утра позвонить"
  "создай событие через 2 часа созвон"

Файл хранилища: /opt/zinaida/shared_memory/events.json
"""
import json, os, sys, subprocess
from datetime import datetime, timedelta

STORAGE = "/opt/zinaida/shared_memory/events.json"
SENT_LOG = "/opt/zinaida/shared_memory/events_sent.json"
TG_BOT = "/opt/zinaida/telegram_bot/notify.py"

def load_events():
    if os.path.exists(STORAGE):
        try:
            with open(STORAGE, 'r') as f:
                return json.load(f)
        except:
            return []
    return []

def save_events(events):
    os.makedirs(os.path.dirname(STORAGE), exist_ok=True)
    with open(STORAGE, 'w') as f:
        json.dump(events, f, ensure_ascii=False, indent=2)

def load_sent():
    if os.path.exists(SENT_LOG):
        try:
            with open(SENT_LOG, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_sent(sent):
    os.makedirs(os.path.dirname(SENT_LOG), exist_ok=True)
    with open(SENT_LOG, 'w') as f:
        json.dump(sent, f, ensure_ascii=False, indent=2)

def parse_datetime(text: str) -> dict:
    """Парсит текст вида 'завтра 11:20 прием у хирурга'"""
    text_lower = text.lower()
    now = datetime.now()

    title = text
    event_time = now

    # "завтра в 11:20"
    if "завтра" in text_lower:
        target = now + timedelta(days=1)
        import re
        time_match = re.search(r'(\d{1,2}):(\d{2})', text)
        if time_match:
            h, m = int(time_match.group(1)), int(time_match.group(2))
            target = target.replace(hour=h, minute=m, second=0, microsecond=0)
            title = re.sub(r'завтра\s*', '', text, flags=re.IGNORECASE)
            title = re.sub(r'\d{1,2}:\d{2}\s*', '', title).strip()
        else:
            target = target.replace(hour=9, minute=0, second=0, microsecond=0)
        event_time = target

    # "через N часа/часов"
    elif "через" in text_lower:
        import re
        hours_match = re.search(r'(\d+)\s*час', text_lower)
        if hours_match:
            h = int(hours_match.group(1))
            target = now + timedelta(hours=h)
            event_time = target.replace(second=0, microsecond=0)
            title = re.sub(r'через\s*\d+\s*часа?\s*', '', text, flags=re.IGNORECASE).strip()

    elif "сегодня" in text_lower:
        import re
        time_match = re.search(r'(\d{1,2}):(\d{2})', text)
        if time_match:
            h, m = int(time_match.group(1)), int(time_match.group(2))
            target = now.replace(hour=h, minute=m, second=0, microsecond=0)
            event_time = target
            title = re.sub(r'сегодня\s*', '', text, flags=re.IGNORECASE)
            title = re.sub(r'\d{1,2}:\d{2}\s*', '', title).strip()

    if not title:
        title = text

    for prefix in ["создай событие ", "запомни ", "напомни "]:
        if title.lower().startswith(prefix):
            title = title[len(prefix):]

    return {
        "time": event_time.strftime("%Y-%m-%d %H:%M"),
        "title": title.strip().capitalize(),
        "created": now.strftime("%Y-%m-%d %H:%M"),
    }

def format_reminder(event: dict) -> str:
    """Красивый формат напоминания с жирным временем"""
    try:
        et = datetime.strptime(event["time"], "%Y-%m-%d %H:%M")
        day_str = "Сегодня" if et.date() == datetime.now().date() else et.strftime("%d.%m")
        time_str = et.strftime("%H:%M")
        return (
            f"⚡️ НАПОМИНАНИЕ\n\n"
            f"📅 *{event['title']}*\n"
            f"⏰ *{day_str} в {time_str}*\n"
            f"🕐 Через 2 часа"
        )
    except:
        return f"⚡️ НАПОМИНАНИЕ\n\n📅 {event['title']}\n⏰ {event['time']}"

def schedule_reminder(event: dict):
    """Создаёт cron задачу для напоминания за 2 часа"""
    event_min = datetime.strptime(event["time"], "%Y-%m-%d %H:%M")
    reminder_time = event_min - timedelta(hours=2)

    minute = reminder_time.minute
    hour = reminder_time.hour
    day = reminder_time.day
    month = reminder_time.month

    msg = format_reminder(event)
    cron_line = f"{minute} {hour} {day} {month} * python3 {TG_BOT} \"{msg}\"\n"

    result = subprocess.run(
        ["bash", "-c", f"(crontab -l 2>/dev/null; echo '{cron_line}') | crontab -"],
        capture_output=True, text=True, timeout=5
    )
    return result.returncode == 0

def todoist_due_string(event_time: str) -> str:
    """Конвертирует '2026-07-13 11:20' в Todoist due_string"""
    try:
        et = datetime.strptime(event_time, "%Y-%m-%d %H:%M")
        now = datetime.now()
        if et.date() == now.date():
            return f"today at {et.strftime('%H:%M')}"
        elif (et.date() - now.date()).days == 1:
            return f"tomorrow at {et.strftime('%H:%M')}"
        else:
            return et.strftime("%Y-%m-%d")
    except:
        return "tomorrow"

def add_event(text: str) -> dict:
    """Добавить событие из текста"""
    event = parse_datetime(text)

    events = load_events()
    # Проверка на дубликат — не добавлять если такое же время и название уже есть
    for e in events:
        if e["time"] == event["time"] and e["title"].lower() == event["title"].lower():
            return {
                "ok": True,
                "todoist": False,
                "event": event,
                "duplicate": True,
                "reminder_at": (datetime.strptime(event["time"], "%Y-%m-%d %H:%M") - timedelta(hours=2)).strftime("%H:%M"),
            }
    events.append(event)
    save_events(events)

    # Только cron (без дублирования через check)
    ok = schedule_reminder(event)

    # Todoist
    todoist_ok = False
    try:
        import sys as _sys
        _sys.path.insert(0, "/opt/zinaida/todoist_integration")
        from todoist_api import TodoistAPI
        api = TodoistAPI()
        r = api.create_reminder(
            content=event["title"],
            when=todoist_due_string(event["time"]),
            project="Встречи"
        )
        if "error" not in r:
            todoist_ok = True
    except Exception as e:
        logger = __import__('logging').getLogger('scheduler')
        logger.warning(f"Todoist error: {e}")

    return {
        "ok": ok,
        "todoist": todoist_ok,
        "event": event,
        "reminder_at": (datetime.strptime(event["time"], "%Y-%m-%d %H:%M") - timedelta(hours=2)).strftime("%H:%M"),
    }

def list_events() -> list:
    events = load_events()
    now = datetime.now()
    upcoming = []
    for e in events:
        try:
            et = datetime.strptime(e["time"], "%Y-%m-%d %H:%M")
            if et > now:
                upcoming.append(e)
        except:
            pass
    return sorted(upcoming, key=lambda x: x["time"])

def check_and_notify():
    """Проверяет и отправляет напоминания (для cron, каждые 15 мин).
    Использует SENT_LOG чтобы не слать дубли одного события."""
    events = load_events()
    sent = load_sent()
    now = datetime.now()

    for e in events:
        try:
            et = datetime.strptime(e["time"], "%Y-%m-%d %H:%M")
            reminder = et - timedelta(hours=2)

            diff = abs((now - reminder).total_seconds())
            event_key = f"{e['time']}_{e['title']}"

            if diff < 300:  # 5 минут до напоминания
                if not sent.get(event_key, False):
                    msg = format_reminder(e)
                    subprocess.run(["python3", TG_BOT, msg], timeout=10, capture_output=True)
                    sent[event_key] = True
                    save_sent(sent)
        except:
            pass

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "add":
            result = add_event(" ".join(sys.argv[2:]))
            print(json.dumps(result, ensure_ascii=False, indent=2))
        elif cmd == "list":
            events = list_events()
            for e in events:
                print(f"  {e['time']} — {e['title']}")
        elif cmd == "check":
            check_and_notify()
        else:
            print("Команды: add, list, check")
    else:
        events = list_events()
        if events:
            for e in events:
                print(f"  {e['time']} — {e['title']}")
        else:
            print("Нет предстоящих событий")

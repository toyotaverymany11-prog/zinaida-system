#!/usr/bin/env python3
"""Утренний консилиум — сбор и отправка в Telegram"""

import json, os, subprocess, sys
from datetime import datetime

def todoist_tasks():
    try:
        import urllib.request
        token = "4f439c11320a5a046dd84e9133cb3b951a7ee9b4"
        req = urllib.request.Request("https://api.todoist.com/api/v1/tasks")
        req.add_header("Authorization", f"Bearer {token}")
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        tasks = data.get('results', data) if isinstance(data, dict) else data
        return tasks
    except Exception as e:
        return f"Ошибка Todoist: {e}"

def build_brief():
    tasks = todoist_tasks()
    if isinstance(tasks, str):
        return tasks
    
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    
    # Сортируем
    p1, p2, p3, p4 = [], [], [], []
    for t in tasks:
        if isinstance(t, dict):
            p = t.get('priority', 4)
            title = t.get('content', '?')
            due = t.get('due')
            due_str = f" [{due['date']}]" if due and due.get('date') else ""
            (p1 if p == 1 else p2 if p == 2 else p3 if p == 3 else p4).append(f"{title}{due_str}")
    
    msg = f"☀️ КОНСИЛИУМ — {now}\n\n"
    
    if p1:
        msg += f"🔥 КРИТИЧЕСКОЕ (p1):\n"
        for t in p1: msg += f"  🔴 {t}\n"
        msg += "\n"
    
    if p2:
        msg += f"🎯 ВАЖНОЕ (p2):\n"
        for t in p2: msg += f"  • {t}\n"
        msg += "\n"
    
    if p3 or p4:
        msg += f"📋 ОСТАЛЬНОЕ:\n"
        for t in p3: msg += f"  • {t}\n"
        for t in p4: msg += f"  · {t}\n"
    
    msg += "\n💡 Напиши что делаем — разгребу."
    
    return msg

if __name__ == "__main__":
    brief = build_brief()
    print(brief)
    # Отправка через hermes send
    result = subprocess.run(
        ["hermes", "send", "--to", "telegram", brief],
        capture_output=True, text=True, timeout=30
    )
    print(f"Send: {result.stdout}")
    if result.stderr:
        print(f"Err: {result.stderr}")

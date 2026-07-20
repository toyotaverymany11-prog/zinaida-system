#!/usr/bin/env python3
"""Добавляет агентов как участников комнаты в правильную БД"""
import sqlite3, time

db = "/root/.hermes-web-ui/hermes-web-ui.db"
room = "mrj9nkx8nln7lx"

conn = sqlite3.connect(db)
cur = conn.cursor()

# Таблицы
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [t[0] for t in cur.fetchall()]
print("Tables:", tables)

# Ищу комнаты
for t in tables:
    if 'room' in t.lower() or 'member' in t.lower() or 'agent' in t.lower() or 'gc' in t.lower():
        cur.execute("PRAGMA table_info({})".format(t))
        cols = [c[1] for c in cur.fetchall()]
        print("\n{}: {}".format(t, cols))
        cur.execute("SELECT * FROM {}".format(t))
        rows = cur.fetchall()
        for r in rows[:10]:
            print("  ", dict(zip(cols, r)))

conn.close()

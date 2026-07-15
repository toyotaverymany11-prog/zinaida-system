import sqlite3
import os
from datetime import datetime

DB_PATH = '/opt/zinaida/memory/unified_memory.db'

def init_db():
    """Инициализирует базу данных и создаёт таблицы при первом запуске."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            channel TEXT NOT NULL,  -- 'telegram', 'webui'
            role TEXT NOT NULL,     -- 'user', 'assistant'
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS knowledge_base (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT,
            content TEXT NOT NULL,
            source TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Включаем WAL режим для конкурентного доступа
    cursor.execute("PRAGMA journal_mode=WAL;")
    conn.commit()
    conn.close()

def write_message(session_id: str, channel: str, role: str, content: str):
    """Записывает сообщение в базу."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO chat_history (session_id, channel, role, content) VALUES (?, ?, ?, ?)",
        (session_id, channel, role, content)
    )
    conn.commit()
    conn.close()

def read_history(session_id: str, limit: int = 20) -> list:
    """Читает последние N сообщений для сессии."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT role, content, timestamp FROM chat_history WHERE session_id = ? ORDER BY timestamp ASC LIMIT ?",
        (session_id, limit)
    )
    rows = cursor.fetchall()
    conn.close()
    return [{"role": r[0], "content": r[1], "timestamp": r[2]} for r in rows]

def search_knowledge(query: str, limit: int = 5) -> list:
    """Поиск по базе знаний (простой LIKE)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT content FROM knowledge_base WHERE content LIKE ? ORDER BY timestamp DESC LIMIT ?",
        (f'%{query}%', limit)
    )
    rows = [r[0] for r in cursor.fetchall()]
    conn.close()
    return rows

if __name__ == "__main__":
    init_db()
    print(f"✅ База данных инициализирована: {DB_PATH}")

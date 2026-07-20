import sqlite3, time, logging
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO, format="%(asctime)s [WATCHDOG] %(message)s")
logger = logging.getLogger(__name__)

DB = "/opt/zinaida/memory/zin_memory.db"

def check_stuck_tasks():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    threshold = (datetime.now() - timedelta(minutes=20)).strftime("%Y-%m-%d %H:%M:%S")
    stuck = conn.execute("SELECT id, title, assignee FROM tasks WHERE status='executing' AND updated_at < ?", (threshold,)).fetchall()

    for task in stuck:
        logger.warning(f"Task {task['id']} '{task['title']}' stuck. Marking as stuck & alerting.")
        conn.execute("UPDATE tasks SET status='stuck', updated_at=CURRENT_TIMESTAMP WHERE id=?", (task['id'],))
        alert_msg = f"🚨 ALERT: Задача '{task['title']}' (ID: {task['id']}, Исполнитель: {task['assignee']}) зависла в статусе executing более 20 минут. Требуется анализ или делегирование."
        conn.execute("INSERT INTO episodes (role, content, summary) VALUES (?, ?, ?)", ("alert", alert_msg, "stuck_task_alert"))
        conn.commit()

    conn.close()

if __name__ == "__main__":
    logger.info("Watchdog started. Checking every 120s.")
    while True:
        try:
            check_stuck_tasks()
        except Exception as e:
            logger.error(f"Watchdog error: {e}")
        time.sleep(120)

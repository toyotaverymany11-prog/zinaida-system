import sys, sqlite3, time, warnings
warnings.filterwarnings("ignore")
DB = "/opt/zinaida/memory/analytics.db"
if len(sys.argv) < 4:
    print("Использование: python3 record_feedback.py <log_id> <rating_1_5> '<notes>'")
    sys.exit(1)
lid, rating, notes = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
conn = sqlite3.connect(DB)
conn.execute("PRAGMA journal_mode=WAL")
conn.execute("PRAGMA busy_timeout=5000")
conn.execute("INSERT OR REPLACE INTO operator_feedback (log_id, timestamp, rating, notes, approved) VALUES (?, ?, ?, ?, 1)",
             (lid, time.strftime("%Y-%m-%d %H:%M:%S"), rating, notes))
conn.commit()
conn.close()
print(f"✅ Фидбек для log_id={lid} записан. Rating={rating}. Куратор учтёт при следующем запуске.")

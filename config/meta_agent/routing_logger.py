import os, json, time, queue, threading

LOG_FILE = "/opt/zinaida/logs/routing_events.jsonl"
MAX_SIZE = 5 * 1024 * 1024
_q = queue.Queue()
_worker_started = False

def _writer():
    while True:
        try:
            event = _q.get(timeout=5)
            if event is None:
                break
            if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > MAX_SIZE:
                os.rename(LOG_FILE, LOG_FILE + ".old")
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")
        except queue.Empty:
            continue
        except Exception:
            pass

def log_routing_event(event):
    global _worker_started
    if not _worker_started:
        t = threading.Thread(target=_writer, daemon=True)
        t.start()
        _worker_started = True
    event["timestamp"] = time.time()
    _q.put(event)

#!/usr/bin/env python3
import os, sys, time, requests, json
import warnings
warnings.filterwarnings("ignore")

ENV_PATH = "/opt/zinaida/.env"
if os.path.exists(ENV_PATH):
    with open(ENV_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if "=" in line and not line.startswith("#"):
                k, _, v = line.strip().partition("=")
                os.environ.setdefault(k, v)

STATE_FILE = "/opt/zinaida/autonomy.state"
TG_TOKEN = os.getenv("TG_BOT_TOKEN", "")
TG_CHAT = os.getenv("TG_CHAT_ID", "")

def load_state():
    data = {}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if "=" in line:
                    k, _, v = line.strip().partition("=")
                    data[k] = v
    except Exception:
        pass
    return data

def send_tg(text):
    if TG_TOKEN and TG_CHAT:
        try:
            requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                          json={"chat_id": TG_CHAT, "text": text}, timeout=5)
        except Exception:
            pass

def main():
    state = load_state()
    success = int(state.get("success_count", "0"))
    rollback = state.get("last_rollback_date", "")
    phase = state.get("phase_current", "0")

    ready = False
    if phase == "3" and success >= 50:
        if not rollback:
            ready = True
        else:
            try:
                last_rb = time.mktime(time.strptime(rollback, "%Y-%m-%d"))
                if (time.time() - last_rb) > (14 * 86400):
                    ready = True
            except Exception:
                pass

    if ready:
        send_tg("AUTOPILOT: Этап 3 завершён. Метрики в норме. Готова к Фазе 4. Жду команду.")
        print("Ready for Phase 4")
    else:
        print(f"Not ready. Success: {success}, Rollback: {rollback}, Phase: {phase}")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
import requests, json, time, os, logging
from datetime import datetime

logging.basicConfig(filename="/opt/zinaida/logs/overnight_autonomy.log", level=logging.INFO, format="%(asctime)s [OVERNIGHT] %(message)s")
logger = logging.getLogger(__name__)

GATEWAY = "http://localhost:8001/v1/chat/completions"
MEMORY = "http://localhost:8505"
MAX_REQ = 80
MAX_ERR = 3
RATE_PAUSE = 300
ERR_PAUSE = 90
STOP_HOUR = 8

tasks = [
    {"role":"Григорий","prompt":"UI v2: создай /opt/zinaida/sandbox/dashboard_v2/index.html с мобильной адаптацией, localStorage+server sync, индикатором статуса, плавной прокруткой. Тестируй curl. Прод 8500 НЕ ТРОГАТЬ."},
    {"role":"Зинаида","prompt":"Аудит безопасности: проверь /opt/zinaida/sandbox/dashboard_v2/ и роутер на утечки ключей, XSS, обработку 429/5xx, таймауты. Фиксируй риски в /opt/zinaida/sandbox/logs/security_audit.md. Ключи в логи НЕ выводить."},
    {"role":"Григорий","prompt":"Стресс-тест роутера: проверь переключение при 429/timeout, работу gemma4:31b/qwen3-80b/deepseek-v4-flash. Отчёт в /opt/zinaida/sandbox/logs/router_stress.json."},
    {"role":"Зинаида","prompt":"Саморефлексия: проанализируй /opt/zinaida/logs/runtime_audit.json и overnight_autonomy.log. Выяви паттерны сбоев, предложи 3 улучшения. Фиксируй в /opt/zinaida/sandbox/knowledge/self_improvement.md."},
    {"role":"Григорий","prompt":"Обнови приоритеты роутера на основе аудита. Протестируй переключение. Логируй результаты."},
    {"role":"Зинаида","prompt":"База знаний: обнови /opt/zinaida/sandbox/knowledge/provider_knowledge_base.md. Удали мёртвые эндпоинты, добавь рабочие таймауты, лимиты, заголовки."}
]

def send(task, attempt=0):
    if attempt >= 2: return False
    try:
        r = requests.post(GATEWAY, json={"messages":[{"role":"system","content":f"Ты {task['role']}. Работай в песочнице /opt/zinaida/sandbox/. Логируй всё. Ключи не выводить. Прод не трогать."},{"role":"user","content":task["prompt"]}]}, timeout=120)
        if r.status_code == 429:
            logger.warning(f"Rate limit. Pause {RATE_PAUSE}s")
            time.sleep(RATE_PAUSE)
            return send(task, attempt+1)
        if r.status_code != 200: return False
        txt = r.json().get("choices",[{}])[0].get("message",{}).get("content","")
        logger.info(f"[{task['role']}] {txt[:200]}")
        try: requests.post(f"{MEMORY}/memory/ingest", json={"role":task["role"].lower(),"content":txt[:1500]}, timeout=4)
        except: pass
        return True
    except Exception as e:
        logger.error(f"Request failed: {e}")
        return False

def main():
    logger.info("🌙 Overnight loop started. MAX_REQ=%d MAX_ERR=%d STOP_HOUR=%d", MAX_REQ, MAX_ERR, STOP_HOUR)
    req=0; err=0; idx=0
    while req < MAX_REQ and err < MAX_ERR and datetime.now().hour != STOP_HOUR:
        t = tasks[idx % len(tasks)]
        logger.info(f"🔄 Cycle {req+1}. {t['role']}")
        ok = send(t)
        req += 1
        err = 0 if ok else err + 1
        if not ok:
            logger.warning(f"⚠️ Error streak: {err}/{MAX_ERR}")
            time.sleep(ERR_PAUSE)
        idx += 1
        time.sleep(60)
    logger.info(f"🏁 Finished. REQ={req} ERR={err} TIME={datetime.now().strftime('%H:%M')}")
    if err >= MAX_ERR: logger.critical("🛑 Circuit breaker triggered")
    elif datetime.now().hour == STOP_HOUR: logger.info("⏰ Morning stop")
    else: logger.info("✅ Limit reached")

if __name__ == "__main__":
    main()

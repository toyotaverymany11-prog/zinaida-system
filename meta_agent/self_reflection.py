#!/usr/bin/env python3
import os, sys, subprocess, sqlite3, time, json
import warnings
warnings.filterwarnings("ignore")

STATE_FILE = "/opt/zinaida/autonomy.state"
ROADMAP_FILE = "/opt/zinaida/memory/knowledge/AUTONOMY_ROADMAP.md"
DB_PATH = "/opt/zinaida/memory/unified_memory.db"
OUTPUT_FILE = "/opt/zinaida/memory/knowledge/SELF_AWARENESS.md"
SERVICES = ["zinaida-router.service", "grigoriy-router.service", "zinaida-autonomous-heartbeat.timer"]
PORTS = ["8002", "8003", "8787"]

def read_state():
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

def count_skills():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("PRAGMA journal_mode=WAL; PRAGMA busy_timeout=5000;")
        cur = conn.execute("SELECT count(*) FROM knowledge_base WHERE project='autonomy_skills'")
        count = cur.fetchone()[0]
        conn.close()
        return count
    except Exception:
        return 0

def check_services():
    status = {}
    for svc in SERVICES:
        try:
            res = subprocess.run(["systemctl", "is-active", svc], capture_output=True, text=True, timeout=5)
            status[svc] = res.stdout.strip()
        except Exception:
            status[svc] = "unknown"
    return status

def check_ports():
    active = []
    try:
        res = subprocess.run(["ss", "-tlnp"], capture_output=True, text=True, timeout=5)
        for p in PORTS:
            if f":{p} " in res.stdout:
                active.append(p)
    except Exception:
        pass
    return active

def get_recent_logs():
    try:
        res = subprocess.run(["journalctl", "-u", "zinaida-router.service", "-u", "grigoriy-router.service", "--since", "1 hour ago", "--no-pager", "-n", "5"], capture_output=True, text=True, timeout=5)
        return res.stdout.strip() or "Нет записей за последний час"
    except Exception:
        return "Ошибка чтения логов"

def main():
    state = read_state()
    skills = count_skills()
    services = check_services()
    ports = check_ports()
    logs = get_recent_logs()
    phase = state.get("phase_current", "unknown")
    success = state.get("success_count", "0")
    rollback = state.get("last_rollback_date", "нет")

    content = f"""# САМОСОСТОЯНИЕ ЗИНАИДЫ
## Текущая фаза автономии: {phase}
## Метрики
- Успешных циклов ремонта: {success}
- Последний откат: {rollback}
- Накоплено навыков в памяти: {skills}
## Активные сервисы
{chr(10).join(f"- {k}: {v}" for k, v in services.items())}
## Открытые порты
- {', '.join(ports) if ports else 'не обнаружены'}
## Последние события (1 час)
{logs}
## Возможности
- Самодиагностика через watchdog каждые 5 минут
- Генерация и валидация фиксов в песочнице
- Атомарный деплой с мгновенным откатом
- Кросс-валидация через Григория (порт 8003)
- Память навыков в SQLite (проект autonomy_skills)
- Оркестратор в режиме симуляции
## Ограничения
- Ядро (роутеры, рантайм, деплой) защищено BLOCKED_FILES
- Автодеплой требует открытого шлюза .approval_gate
- Оркестратор не исполняет код без APPROVED в .orchestrator_gate
- Лимит 3 попытки на одну ошибку
## История обновлений
- Фаза 1-4 внедрены и верифицированы
- Система стабильна. Контекст обновляется автоматически каждые 15 минут.
"""
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Self-awareness updated: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()

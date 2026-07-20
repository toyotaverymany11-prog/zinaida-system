#!/usr/bin/env python3
import os, time, subprocess, json, warnings
warnings.filterwarnings("ignore")

OUT_JSON = "/opt/zinaida/meta_agent/self_diagnostic_data.json"

KNOWLEDGE_REGISTRY = {
    "port_8002": {"name": "Роутер Зинаида", "group": "brain", "function": "Маршрутизация запросов, управление API.", "mechanism": "Принимает JSON. Анализирует интент. Делегирует код на :8003, память на :8505. Fallback на локальную модель при сбое.", "stack": "Python, FastAPI, Uvicorn", "schedule": "Постоянно", "deps": "Григорий, Память"},
    "port_8003": {"name": "Агент Григорий", "group": "brain", "function": "Анализ кода, оптимизация, сложная логика.", "mechanism": "Получает промпт от роутера. Генерирует код. Возвращает результат.", "stack": "Python, LLM API", "schedule": "По запросу", "deps": "Зинаида (:8002)"},
    "port_8004": {"name": "Прокси API", "group": "nerves", "function": "Балансировка нагрузки, проксирование.", "mechanism": "Перенаправляет внешние запросы. Кэширует ответы.", "stack": "Python, HTTP Proxy", "schedule": "Постоянно", "deps": "Зинаида (:8002)"},
    "port_8505": {"name": "Шлюз Памяти", "group": "heart", "function": "Чтение и запись в unified_memory.db, RAG-поиск.", "mechanism": "WAL-режим SQLite. Векторный поиск по embedding. busy_timeout=5000.", "stack": "Python, SQLite, RAG", "schedule": "Постоянно", "deps": "Автопилот, Роутер"},
    "port_8787": {"name": "Hermes WebUI", "group": "hands", "function": "Веб-интерфейс управления, чат.", "mechanism": "Отдает статику. Принимает POST запросы чата. Интеграция с Gateway.", "stack": "Node.js/Python, Caddy", "schedule": "Постоянно", "deps": "Gateway, Caddy"},
    "port_8788": {"name": "Дашборд Статуса", "group": "eyes", "function": "Визуализация состояния системы.", "mechanism": "Читает JSON. Генерирует HTML. Автообновление каждые 10 сек.", "stack": "Python, HTTPServer", "schedule": "Постоянно", "deps": "self_diagnostic.py"},
    "proc_autopilot": {"name": "Автопилот", "group": "nerves", "function": "Управляет циклом самообучения.", "mechanism": "Event loop. Запускает задачи по расписанию. Мониторит логи.", "stack": "Python, systemd", "schedule": "Постоянно", "deps": "Память, Cron"},
    "proc_telegram": {"name": "Telegram Воркер", "group": "hands", "function": "Обработка сообщений, уведомления.", "mechanism": "Long polling. Парсинг команд. Пересылка в inbox.", "stack": "Python, aiogram", "schedule": "Постоянно", "deps": "Hermes Gateway"},
    "proc_vk_bot": {"name": "VK Бот", "group": "hands", "function": "Приём сообщений из ВКонтакте.", "mechanism": "Callback API. Ответы через messages.send.", "stack": "Python, vk_api", "schedule": "Постоянно", "deps": "Роутер"},
    "proc_zinaida_router": {"name": "Процесс Роутера", "group": "brain", "function": "Фоновый воркер маршрутизации.", "mechanism": "Слушает очередь задач. Распределяет по агентам.", "stack": "Python", "schedule": "Постоянно", "deps": "Порт 8002"},
    "proc_grigoriy": {"name": "Процесс Григория", "group": "brain", "function": "Фоновый воркер анализа.", "mechanism": "Обрабатывает очереди кода. Оптимизирует скрипты.", "stack": "Python", "schedule": "Постоянно", "deps": "Порт 8003"},
    "file_night_synthesis.py": {"name": "Ночной Синтез", "group": "subconscious", "function": "Глубокий анализ логов, консолидация знаний.", "mechanism": "Запускается cron в 03:00. Читает логи за день. Пишет в память.", "stack": "Python, Cron", "schedule": "03:00 ежедневно", "deps": "Логи, Память"},
    "file_memory_consolidator.py": {"name": "Консолидатор Памяти", "group": "heart", "function": "Сжатие дублей навыков, очистка БД.", "mechanism": "VACUUM SQLite. Удаление устаревших записей.", "stack": "Python, SQLite", "schedule": "04:00 ежедневно", "deps": "SQLite"},
    "file_self_reflection.py": {"name": "Саморефлексия", "group": "brain", "function": "Анализ успешных фиксов.", "mechanism": "Сравнивает ошибки и решения. Обновляет CORE.md.", "stack": "Python", "schedule": "Каждые 15 мин", "deps": "Логи"}
}

def safe_run(cmd, timeout=2):
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return res.stdout
    except Exception:
        return ""

def scan_system():
    components = {}
    ss_out = safe_run(["ss", "-tlnp"])
    for port in ["8002", "8003", "8004", "8505", "8787", "8788"]:
        if f":{port}" in ss_out:
            components[f"port_{port}"] = {"source": "ss", "status": "active"}
    ps_out = safe_run(["ps", "aux"])
    for pattern in ["autopilot", "telegram", "vk_bot", "zinaida_router", "grigoriy"]:
        if pattern in ps_out:
            components[f"proc_{pattern}"] = {"source": "ps", "status": "active"}
    for dir_path in ["/opt/zinaida/meta_agent"]:
        try:
            for f in os.listdir(dir_path):
                if f in ["night_synthesis.py", "memory_consolidator.py", "self_reflection.py"]:
                    components[f"file_{f}"] = {"source": "ls", "status": "present"}
        except Exception:
            pass
    return components

def analyze_and_describe(components):
    analyzed = {}
    for cid, data in components.items():
        reg = KNOWLEDGE_REGISTRY.get(cid, {})
        analyzed[cid] = {
            "name": reg.get("name", cid),
            "group": reg.get("group", "unknown"),
            "function": reg.get("function", "Нет данных"),
            "mechanism": reg.get("mechanism", "Нет данных"),
            "stack": reg.get("stack", "Нет данных"),
            "schedule": reg.get("schedule", "Нет данных"),
            "deps": reg.get("deps", "Нет данных"),
            "status": data["status"],
            "confidence": 0.95 if reg else 0.30,
            "last_seen": time.time()
        }
    return analyzed

def main():
    new_components = scan_system()
    components = analyze_and_describe(new_components)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(components, f, indent=2, ensure_ascii=False)
    print("Diagnostic complete.")

if __name__ == "__main__":
    main()

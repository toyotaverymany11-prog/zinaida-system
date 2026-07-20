import os, sys, subprocess, datetime, urllib.request
from pathlib import Path

CAPABILITIES_PATH = "/opt/zinaida/inbox/CAPABILITIES.md"
VENV_PIP = "/opt/zinaida/tools/marker_venv/bin/pip"
LOG_PATH = "/opt/zinaida/logs/audit.log"

def log(msg):
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"{datetime.datetime.now().isoformat()} {msg}\n")

def check_service(name):
    try:
        res = subprocess.run(["systemctl", "is-active", name], capture_output=True, text=True, timeout=5)
        return res.stdout.strip() == "active"
    except Exception:
        return False

def check_url(url, timeout=5):
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False

def get_pip_version(pip_path, package):
    try:
        if not os.path.isfile(pip_path):
            return "N/A", "missing"
        res = subprocess.run([pip_path, "show", package], capture_output=True, text=True, timeout=10)
        if res.returncode == 0:
            for line in res.stdout.splitlines():
                if line.startswith("Version:"):
                    return line.split(":", 1)[1].strip(), "installed"
        return "N/A", "missing"
    except Exception:
        return "N/A", "missing"

def run_audit():
    ts = datetime.datetime.now().isoformat()
    core_active = check_service("zinaida-router") and check_service("hermes-gateway")
    router_ok = check_url("http://127.0.0.1:8002/health")
    pdf_ver, pdf_status = get_pip_version("/usr/bin/pip3", "pdfplumber")
    pymupdf_ver, pymupdf_status = get_pip_version("/usr/bin/pip3", "PyMuPDF")
    marker_ver, marker_status = get_pip_version(VENV_PIP, "marker-pdf")
    content = f"""# CAPABILITIES.md - Динамический реестр возможностей Зинаиды
# Обновлено: {ts}

## 1. Ядро системы
- Статус: {"active" if core_active else "degraded"}
- Роутер здоровье: {"ok" if router_ok else "fail"}
- Порт шлюза: 8001
- Порт роутера: 8002
- Архитектура: hybrid. Hermes управляет памятью и задачами. Zinaida Router управляет транспортом.

## 2. Инструменты обработки файлов
- Инструмент: pdfplumber. Версия: {pdf_ver}. Статус: {pdf_status}. Назначение: извлечение текста и таблиц из PDF. Сырой вывод.
- Инструмент: PyMuPDF. Версия: {pymupdf_ver}. Статус: {pymupdf_status}. Назначение: быстрое извлечение сырого текста.
- Инструмент: marker-pdf. Версия: {marker_ver}. Статус: {marker_status}. Назначение: умная очистка PDF от колонтитулов и шума. Вывод чистого Markdown.

## 3. Провайдеры нейросетей
- Провайдер: zhipu. Модель: glm-4-flash. Статус: active. Лимит: free.
- Провайдер: github. Модель: gpt-4.1-mini. Статус: active. Лимит: 150/day.
- Провайдер: mistral. Модель: mistral-small-latest. Статус: active. Лимит: free.
- Провайдер: openrouter. Модель: llama-3.3-70b. Статус: active. Лимит: free.
- Провайдер: gigachat. Модель: GigaChat. Статус: active. Лимит: auth.

## 4. Хранилища и память
- RAG база знаний: /opt/zinaida/inbox/. Инкрементальная индексация. chunk_size 512.
- База памяти state.db: режим WAL включён. Zero-token memory.
- Kanban: база активна. Готова к командам /tasks и /goal.

## 5. Автономные функции
- Curator: enabled. Запускается каждые 12 часов.
- Протокол самодиагностики: активен.
"""
    with open(CAPABILITIES_PATH, "w", encoding="utf-8") as f:
        f.write(content)
    log("Audit completed. Registry updated.")

if __name__ == "__main__":
    run_audit()

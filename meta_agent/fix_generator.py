import sys
import os
import glob
import json
import time
import requests
import warnings
import subprocess
sys.path.insert(0, '/opt/zinaida/meta_agent')
warnings.filterwarnings("ignore")

INBOX_PENDING = "/opt/zinaida/inbox/research_pending"
ROUTER_URL = "http://127.0.0.1:8002/v1/chat/completions"

def _log(message):
    print(message)

def clean_output(text):
    lines = text.splitlines()
    start_idx = -1
    for i, line in enumerate(lines):
        if line.startswith(('import ', '#!/usr/bin/env', 'def ', 'cat <<', 'echo ')):
            start_idx = i
            break
    if start_idx != -1:
        text = "\n".join(lines[start_idx:])
    end_marker = "[END_FIX]"
    if end_marker in text:
        idx = text.find(end_marker)
        text = text[:idx].rstrip()
    return text.strip()

def run_gen():
    try:
        diag_files = sorted(glob.glob(os.path.join(INBOX_PENDING, "diag_*.json")), key=os.path.getmtime, reverse=True)
        if not diag_files:
            _log("Нет новых отчетов диагностики.")
            return
        latest_diag_file = diag_files[0]
        with open(latest_diag_file, "r", encoding="utf-8") as f:
            diag_data = json.load(f)
        issues_desc = "\n".join([f"{issue['type']}: {str(issue['details'])[:100]}" for issue in diag_data.get('issues', [])])
        prompt = f"""--- КОНТЕКСТ ОШИБКИ ---
Сигнатура: {issues_desc}
--- ЗАДАЧА ---
Сгенерируй атомарный bash-скрипт или python-код для устранения причины.
--- ЖЁСТКИЕ ПРАВИЛА ---
- Только полная перезапись файлов через open(..., 'w').
- Heredoc строго << 'PYEOF'.
- Отступы 4 пробела. Импорты в шапке.
- Запрещены: rm -rf, chmod 777, sed, re.sub, os.system, eval.
- Не используй markdown-разметку.
--- ВЫВОД НАЧИНАЕТСЯ СТРОГО С КОДА. ЗАКАНЧИВАЕТСЯ СТРОКОЙ [END_FIX] ---"""
        payload = {"model": "zinaida-router", "messages": [{"role": "user", "content": prompt}], "temperature": 0.2}
        response = requests.post(ROUTER_URL, json=payload, timeout=45)
        response.raise_for_status()
        raw_output = response.json().get("choices", [{}])[0].get("message", {}).get("content", "")
        clean_code = clean_output(raw_output)
        if not clean_code:
            return
        is_bash = clean_code.startswith("#!/bin/bash")
        fix_file = os.path.join(INBOX_PENDING, f"fix_{int(time.time())}.{'sh' if is_bash else 'py'}")
        with open(fix_file, "w", encoding="utf-8") as f:
            f.write(clean_code)
        print(f"ИАР: Предложен фикс. Файл: {fix_file}")
        print(f"Для применения выполни в терминале: bash /opt/zinaida/scripts/apply_fix.sh {os.path.basename(fix_file)}")
    except Exception as e:
        _log(f"FATAL ERROR in generator: {e}")

if __name__ == "__main__":
    run_gen()

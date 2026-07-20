import os
import sys
import json
import shutil
import requests
import re
import warnings
from datetime import datetime
from pathlib import Path

sys.path.insert(0, '/opt/zinaida/meta_agent')
from memory_router import save_fact

warnings.filterwarnings("ignore")

try:
    from pypdf import PdfReader
    PYPDF_OK = True
except Exception:
    PYPDF_OK = False

ROUTER_URL = "http://127.0.0.1:8002/v1/chat/completions"
INBOX = Path("/opt/zinaida/inbox")
PROCESSING = INBOX / "processing"
PROCESSED = INBOX / "processed"
ERRORS = INBOX / "errors"
PROJECTS_DIR = Path("/opt/zinaida/memory/projects")

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def get_projects_context():
    contexts = {}
    for proj_dir in PROJECTS_DIR.iterdir():
        if proj_dir.is_dir():
            brief = proj_dir / "context" / "brief.md"
            if brief.exists():
                contexts[proj_dir.name] = brief.read_text(encoding='utf-8')[:500]
    return contexts

def analyze_with_llm(text, contexts):
    ctx_str = "\n".join([f"- {k}: {v}" for k, v in contexts.items()])
    if not ctx_str:
        ctx_str = "Проекты не заданы, используй 'global'."

    prompt = f"""Ты - аналитик памяти системы Hermes.
Список проектов и их описания (брифы):
{ctx_str}

Входящий текст для анализа:
{text[:4000]}

Задача:
1. Определи, к какому проекту относится текст. Если ни к одному не подходит - используй 'global'.
2. Извлеки ТОЛЬКО ценные факты, идеи, цифры, правила, структуры. Жестко игнорируй воду, лирику, приветствия.

Верни СТРОГО валидный JSON без markdown-разметки и без лишних слов:
{{"project": "имя_папки_проекта", "facts": ["факт 1", "факт 2"]}}"""

    try:
        resp = requests.post(ROUTER_URL, json={
            "messages": [{"role": "user", "content": prompt}],
            "stream": False, "temperature": 0.2
        }, timeout=45)
        resp.raise_for_status()
        content = resp.json()['choices'][0]['message']['content']
        content = re.sub(r'```json\n|```', '', content).strip()
        return json.loads(content)
    except Exception as e:
        log(f"LLM Error: {e}")
        return None

def process_pdf(filepath):
    if not PYPDF_OK:
        log("pypdf недоступен, пропускаю PDF")
        return False
    try:
        reader = PdfReader(str(filepath))
        text = ""
        for page in reader.pages[:20]:
            text += page.extract_text() or ""
        if not text.strip():
            log("PDF пустой")
            return False
        log(f"PDF извлечён: {len(text)} символов")
        return text
    except Exception as e:
        log(f"PDF parse error: {e}")
        return False

def process_file(filepath):
    log(f"Processing: {filepath.name}")
    proc_path = PROCESSING / filepath.name
    success = False
    
    try:
        shutil.move(str(filepath), str(proc_path))
    except Exception as e:
        log(f"Move to processing failed: {e}")
        return False

    try:
        if filepath.suffix.lower() == ".pdf":
            text = process_pdf(proc_path)
            if not text:
                success = False
                return False
        else:
            text = Path(proc_path).read_text(encoding='utf-8', errors='ignore')
            if not text.strip():
                success = False
                return False

        contexts = get_projects_context()
        result = analyze_with_llm(text, contexts)

        if not result or 'project' not in result or 'facts' not in result:
            log("LLM failed to return valid JSON.")
            success = False
            return False

        proj = result['project']
        facts = result['facts']

        if not facts:
            log("No facts extracted (water only).")
            success = True
            return True

        target_proj_dir = PROJECTS_DIR / proj
        if not target_proj_dir.exists():
            log(f"Project {proj} not found, falling back to global.")
            target_proj_dir = PROJECTS_DIR / "global"

        know_dir = target_proj_dir / "knowledge"
        know_dir.mkdir(parents=True, exist_ok=True)

        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        out_file = know_dir / f"extracted_{ts}.md"
        with open(out_file, 'w', encoding='utf-8') as f:
            f.write(f"# Extracted Facts ({ts})\n\n")
            for fact in facts:
                f.write(f"- {fact}\n")
        log(f"Saved to file: {out_file}")

        saved = save_fact("\n".join(facts), filepath.name, proj, ts)
        if saved:
            log("Saved to DB via memory_router.")
        else:
            log("Failed to save to DB.")
            
        success = True
        return True
    except Exception as e:
        log(f"Fatal processing error: {e}")
        success = False
        return False
    finally:
        try:
            if proc_path.exists():
                dest = PROCESSED if success else ERRORS
                dest.mkdir(exist_ok=True)
                new_name = f"{proc_path.stem}_{datetime.now().strftime('%H%M%S')}{proc_path.suffix}"
                shutil.move(str(proc_path), str(dest / new_name))
                log(f"Moved to {dest.name}")
        except Exception as mv_err:
            log(f"Final move error: {mv_err}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(1)
    f_path = Path(sys.argv[1])
    if not f_path.exists():
        sys.exit(1)
    process_file(f_path)

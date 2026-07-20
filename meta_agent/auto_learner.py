import os, sys, sqlite3, json, requests, time, re
import docx
try:
    import fitz # PyMuPDF
except:
    fitz = None

INBOX_DIR = '/opt/zinaida/inbox'
PROCESSED_DIR = '/opt/zinaida/inbox/processed'
KNOWLEDGE_DIR = '/opt/zinaida/memory/knowledge'
DB_PATH = '/opt/zinaida/memory/unified_memory.db'
ROUTER_URL = 'http://127.0.0.1:8002/v1/chat/completions'

os.makedirs(PROCESSED_DIR, exist_ok=True)

def read_file(filepath):
    ext = os.path.splitext(filepath)[1].lower()
    try:
        if ext == '.txt':
            with open(filepath, 'r', encoding='utf-8') as f: return f.read()
        elif ext == '.docx':
            doc = docx.Document(filepath)
            return "\n".join([p.text for p in doc.paragraphs])
        elif ext == '.pdf' and fitz:
            doc = fitz.open(filepath)
            return "\n".join([page.get_text() for page in doc])
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
    return ""

def ask_zinaida(text):
    prompt = "Проанализируй текст. Извлеки ключевые знания, факты и инструкции. Предложи название файла (на английском, без пробелов, .md) и краткое содержание. Ответь ТОЛЬКО в формате JSON: {\"filename\": \"topic.md\", \"content\": \"...\"}"
    payload = {"messages": [{"role": "user", "content": f"{prompt}\n\nТекст:\n{text[:2000]}"}], "stream": False}
    try:
        resp = requests.post(ROUTER_URL, json=payload, timeout=30)
        data = resp.json()
        return data['choices'][0]['message']['content']
    except Exception as e:
        print(f"Router error: {e}")
        return None

def save_to_db(topic, content, source):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO knowledge_base (topic, content, source) VALUES (?, ?, ?)", (topic, content, source))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"DB error: {e}")

def process_inbox():
    for fname in os.listdir(INBOX_DIR):
        fpath = os.path.join(INBOX_DIR, fname)
        if os.path.isfile(fpath) and not fname.startswith('.'):
            text = read_file(fpath)
            if len(text) > 50:
                print(f"Processing {fname}...")
                result = ask_zinaida(text)
                if result:
                    match = re.search(r'\{.*\}', result, re.DOTALL)
                    if match:
                        try:
                            data = json.loads(match.group())
                            filename = data.get('filename', 'unknown.md')
                            content = data.get('content', text)
                            fpath_out = os.path.join(KNOWLEDGE_DIR, filename)
                            with open(fpath_out, 'a', encoding='utf-8') as f:
                                f.write(f"\n\n## Из файла: {fname} ({time.strftime('%Y-%m-%d')})\n{content}\n")
                            save_to_db(filename, content, fname)
                            os.rename(fpath, os.path.join(PROCESSED_DIR, fname))
                            print(f"✅ Processed {fname} -> {filename}")
                        except Exception as e:
                            print(f"JSON parse error: {e}")
                    else:
                        print("No JSON found in response")

if __name__ == "__main__":
    process_inbox()

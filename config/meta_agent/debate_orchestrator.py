import os
import sys
import json
import time
import requests
import warnings

warnings.filterwarnings("ignore")

ROUTER_URL = "http://127.0.0.1:8002/v1/chat/completions"
TIMEOUT = 45

def call_llm(prompt, strategy="filter"):
    try:
        resp = requests.post(ROUTER_URL, json={
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "temperature": 0.3,
            "routing_strategy": strategy
        }, timeout=TIMEOUT)
        resp.raise_for_status()
        return resp.json()['choices'][0]['message']['content']
    except Exception as e:
        print(f"LLM Error: {e}")
        return None

def debate(text, project="global"):
    p1 = f"Ты - Исследователь. Проанализируй текст и задай 5 ключевых вопросов. Текст: {text[:3000]}"
    r1 = call_llm(p1, "filter")
    if not r1:
        return None

    p2 = f"Ты - Аналитик. Ответь на вопросы Исследователя и найди противоречия. Вопросы: {r1}\nТекст: {text[:3000]}"
    r2 = call_llm(p2, "filter")
    if not r2:
        return None

    p3 = f"Ты - Стратег. Синтезируй финальные факты и оцени уверенность (0.0-1.0). Верни СТРОГО валидный JSON без markdown: {{\"facts\": [\"факт 1\"], \"confidence\": 0.9}}. Анализ: {r2}"
    r3 = call_llm(p3, "analyze")
    if not r3:
        return None

    try:
        r3_clean = r3.replace("```json", "").replace("```", "").strip()
        return json.loads(r3_clean)
    except Exception:
        return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(1)
    text = sys.stdin.read() if sys.argv[1] == "-" else open(sys.argv[1], "r", encoding="utf-8", errors="ignore").read()
    result = debate(text)
    print(json.dumps(result, ensure_ascii=False, indent=2))

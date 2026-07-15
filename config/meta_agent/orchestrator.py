#!/usr/bin/env python3
import os, sys, time, json, requests, re
import warnings
warnings.filterwarnings("ignore")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agent_runtime import run_safe

CORE_URL = "http://127.0.0.1:8002/v1/chat/completions"
SANDBOX_DIR = "/opt/zinaida/sandbox"
GATE_FILE = os.path.join(SANDBOX_DIR, ".orchestrator_gate")
MAX_DEPTH = 5
TIMEOUT_SEC = 1800

def load_gate():
    try:
        with open(GATE_FILE, "r", encoding="utf-8") as f:
            return f.read().strip() == "APPROVED"
    except Exception:
        return False

def decompose_task(task_text):
    prompt = f"""ТЫ ОРКЕСТРАТОР. ЗАДАЧА: {task_text[:1500]}
РАЗБЕЙ НА АТОМАРНЫЕ ШАГИ (макс {MAX_DEPTH}).
Верни СТРОГО JSON: {{"steps": ["шаг 1", "шаг 2"]}}
"""
    try:
        r = requests.post(CORE_URL, json={"messages": [{"role": "user", "content": prompt}], "stream": False}, timeout=30)
        if r.status_code == 200:
            txt = r.json().get("choices", [{}])[0].get("message", {}).get("content", "")
            match = re.search(r'\{.*\}', txt, re.DOTALL)
            if match:
                return json.loads(match.group()).get("steps", [])
    except Exception:
        pass
    return []

def main():
    if len(sys.argv) < 2:
        print("Usage: orchestrator.py 'task description'")
        sys.exit(1)
    task = sys.argv[1]
    print(f"Orchestrator started. Task: {task[:50]}...")
    if not load_gate():
        print("Gate closed. Simulation mode only.")
        steps = decompose_task(task)
        plan_file = os.path.join(SANDBOX_DIR, f"orchestrator_plan_{int(time.time())}.txt")
        with open(plan_file, "w", encoding="utf-8") as f:
            f.write(f"TASK: {task}\nSTEPS:\n" + "\n".join(f"- {s}" for s in steps))
        print(f"Plan written to {plan_file}. Waiting for APPROVED in .orchestrator_gate")
        sys.exit(0)
    print("Gate open. Execution not implemented yet. Safety first.")

if __name__ == "__main__":
    main()

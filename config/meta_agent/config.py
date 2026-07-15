from dotenv import load_dotenv


import os
from pathlib import Path
PROJECT_ROOT = Path("/opt/zinaida")
MEMORY_PATH = PROJECT_ROOT / "memory"
KNOWLEDGE_PATH = MEMORY_PATH / "knowledge"
CORE_PATH = KNOWLEDGE_PATH / "CORE.md"
MEMORY_FILES_PATH = KNOWLEDGE_PATH / "MEMORY"
CHAT_LOGS_PATH = MEMORY_PATH / "chat_logs"
PROJECTS_PATH = PROJECT_ROOT / "projects"
LOGS_PATH = PROJECT_ROOT / "logs"
QUOTAS_FILE = PROJECT_ROOT / "quotas.json"
for p in [MEMORY_PATH, KNOWLEDGE_PATH, MEMORY_FILES_PATH, CHAT_LOGS_PATH, PROJECTS_PATH, LOGS_PATH]:
    p.mkdir(parents=True, exist_ok=True)
CRITICAL_FILES = [CORE_PATH, KNOWLEDGE_PATH / "MEMORY" / "tools.md"]

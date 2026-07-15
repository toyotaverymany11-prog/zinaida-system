
import sys, uvicorn, logging
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
sys.path.insert(0, str(Path(__file__).parent))
from config import PROJECTS_PATH

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
app = FastAPI(title="Grigoriy")

class Task(BaseModel): task: str; user_id: int

@app.get("/health")
def health(): return {"status":"ok"}

@app.post("/generate")
def gen(t: Task):
    code = f"# Task: {t.task}\nprint('Grigoriy executed')"
    p = PROJECTS_PATH / f"code_{t.user_id}.py"
    p.write_text(code, encoding="utf-8")
    return {"code": code, "path": str(p)}

if __name__ == "__main__":
    logger.info("Grigoriy starting...")
    uvicorn.run(app, host="0.0.0.0", port=8002)

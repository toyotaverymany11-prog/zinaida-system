import subprocess, tempfile, os, time, json, logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [SKILL-VALIDATOR] %(message)s")
logger = logging.getLogger(__name__)

SANDBOX_TIMEOUT = 10
MAX_MEMORY_MB = 256

def validate_skill(code: str, test_input: str, expected_output: str) -> dict:
    tmp_dir = tempfile.mkdtemp(prefix="skill_sandbox_")
    script_path = os.path.join(tmp_dir, "test_skill.py")
    input_path = os.path.join(tmp_dir, "input.txt")
    
    try:
        with open(script_path, "w") as f:
            f.write(code + "\n")
            f.write("import sys, json\n")
            f.write("try:\n")
            f.write("    data = json.load(open('input.txt'))\n")
            f.write("    result = run(data)\n")
            f.write("    print(json.dumps({'status':'ok','result':result}))\n")
            f.write("except Exception as e:\n")
            f.write("    print(json.dumps({'status':'error','error':str(e)}))\n")
        
        with open(input_path, "w") as f:
            json.dump(test_input, f)

        env = os.environ.copy()
        env.pop("HTTP_PROXY", None)
        env.pop("HTTPS_PROXY", None)
        env.pop("http_proxy", None)
        env.pop("https_proxy", None)
        env["PYTHONPATH"] = ""
        env["HOME"] = tmp_dir

        start = time.time()
        proc = subprocess.run(
            ["python3", script_path],
            cwd=tmp_dir,
            env=env,
            capture_output=True,
            text=True,
            timeout=SANDBOX_TIMEOUT
        )
        elapsed = time.time() - start

        try:
            out = json.loads(proc.stdout.strip())
        except:
            out = {"status": "parse_fail", "error": proc.stderr[:200]}

        score = 0.0
        if out.get("status") == "ok":
            score += 0.5
            if str(out.get("result")) == str(expected_output):
                score += 0.3
            if elapsed < SANDBOX_TIMEOUT * 0.8:
                score += 0.2
        
        logger.info(f"Validation done. Score: {score:.2f}, Time: {elapsed:.2f}s")
        return {"score": score, "elapsed": elapsed, "output": out, "logs": proc.stderr[:300]}

    except subprocess.TimeoutExpired:
        logger.warning("Sandbox timeout")
        return {"score": 0.0, "elapsed": SANDBOX_TIMEOUT, "output": {"status":"timeout"}, "logs":"timeout"}
    except Exception as e:
        logger.error(f"Validator crash: {e}")
        return {"score": 0.0, "elapsed": 0.0, "output": {"status":"crash"}, "logs": str(e)}
    finally:
        import shutil
        shutil.rmtree(tmp_dir, ignore_errors=True)

import os, json, time, uuid, logging, subprocess, tempfile, sys, requests, warnings
warnings.filterwarnings("ignore")
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from contextlib import contextmanager
from typing import List, Dict

sys.path.insert(0, '/opt/zinaida/meta_agent')
from provider_manager import get_provider, request_complexity_score
from routing_logger import log_routing_event

logging.basicConfig(filename='/opt/zinaida/logs/grigoriy_router.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
app = FastAPI()

@contextmanager
def safe_exec(code: str):
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, dir='/tmp') as f:
        f.write("# -*- coding: utf-8 -*-\n" + code)
        f.flush()
        try:
            result = subprocess.run(['python3', f.name], capture_output=True, text=True, timeout=8)
            yield result.stdout, result.stderr, result.returncode
        finally:
            try: os.unlink(f.name)
            except: pass

def call_provider_sync(messages: List[Dict], system_prompt: str, provider: Dict) -> str:
    headers = provider.get('headers', {})
    payload = {
        'model': provider['model'],
        'messages': [{'role': 'system', 'content': system_prompt}] + messages,
        'temperature': 0.7
    }
    try:
        resp = requests.post(provider['url'], json=payload, headers=headers, timeout=25, verify=provider.get('verify', True))
        if resp.status_code == 200:
            data = resp.json()
            content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
            if content:
                print(f"GRIGORIY PROVIDER {provider.get('name', provider['model'])} OK")
                return content
        else:
            print(f"GRIGORIY PROVIDER {provider.get('name', provider['model'])} -> {resp.status_code}: {resp.text[:100]}")
    except Exception as e:
        print(f"GRIGORIY PROVIDER ERROR: {e}")
    return None

@app.get('/health')
def health():
    return {'status': 'ok', 'agent': 'grigoriy_v5.4.1_smart_routing', 'port': 8003}

@app.post('/v1/chat/completions')
async def chat(request: Request):
    try:
        data = await request.json()
        messages = data.get('messages', [])
        execute = data.get('execute', False)

        coder_system = "Ты Григорий, senior Python-разработчик. Пиши только рабочий, безопасный код. Комментируй кратко. Не используй markdown. Если просят выполнить — верни результат выполнения."
        
        text_parts = []
        for msg in messages:
            content = msg.get('content', '')
            if isinstance(content, str):
                text_parts.append(content)
        text = ' '.join(text_parts).strip()
        ctx_size = len(text)
        
        provider = get_provider(strategy="analyze", context_size=ctx_size, text=text + " код скрипт программа")
        start_time = time.time()
        used_provider = "none"
        reply = "Ошибка генерации кода."
        
        if provider:
            try:
                res = call_provider_sync(messages, coder_system, provider)
                if res:
                    reply = res
                    used_provider = provider.get('name', provider.get('model', 'unknown'))
            except Exception as e:
                print(f"GRIGORIY SMART ROUTING ERROR: {e}")
        
        latency = int((time.time() - start_time) * 1000)
        log_routing_event({"strategy": "code", "provider": used_provider, "latency_ms": latency, "status": "ok" if used_provider != "none" else "failed", "context_size": ctx_size, "complexity_score": 1.0})

        if execute and used_provider != "none":
            try:
                with safe_exec(reply) as (out, err, code):
                    if code == 0:
                        reply = f"[EXEC OK]\n{out}"
                    else:
                        reply = f"[EXEC FAIL]\nSTDERR: {err}\nSTDOUT: {out}"
            except subprocess.TimeoutExpired:
                reply = "[EXEC TIMEOUT] Код выполнялся дольше 8 сек."
            except Exception as e:
                reply = f"[EXEC ERROR] {str(e)}"

        return JSONResponse({'choices': [{'message': {'role': 'assistant', 'content': reply}}], 'model': 'grigoriy-router', 'usage': {'total_tokens': 0}})
    except Exception as e:
        logger.error(f'Grigoriy error: {e}')
        return JSONResponse({'error': str(e)}, status_code=500)

if __name__ == '__main__':
    import uvicorn
    logger.info('Starting Grigory Coder v5.4.1 on :8003')
    uvicorn.run(app, host='0.0.0.0', port=8003)

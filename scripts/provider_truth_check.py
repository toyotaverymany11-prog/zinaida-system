#!/usr/bin/env python3
"""
provider_truth_check.py — ЕДИНСТВЕННЫЙ ИСТОЧНИК ПРАВДЫ по провайдерам.
Запускается перед любым утверждением "провайдер не работает".
Выдаёт статус после реального теста.
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SECRETS_DIR = Path("/opt/zinaida")


def _load_key(var_name, *paths):
    """Ищет ключ во всех указанных .env файлах"""
    for path in paths:
        p = Path(path)
        if p.exists():
            with open(p, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith(f"{var_name}="):
                        val = line.split("=", 1)[1].strip().strip("'\"")
                        if val:
                            return val
    return ""


def curl_test(label, url, headers, data, timeout=15):
    """Выполняет curl и возвращает структурированный результат"""
    import json as j

    headers_str = " ".join(f'-H "{k}: {v}"' for k, v in headers.items())
    data_str = j.dumps(data)

    cmd = f'curl -s -w "\\n%{{http_code}}" --max-time {timeout} {headers_str} -d \'{data_str}\' "{url}"'

    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout + 5
        )
        output = result.stdout.strip()
        if not output:
            return {
                "label": label,
                "alive": False,
                "status": "no_output",
                "detail": result.stderr[:200],
            }

        lines = output.rsplit("\n", 1)
        http_code = lines[-1].strip() if len(lines) > 1 else "000"
        body = lines[0] if len(lines) > 1 else output

        if http_code == "200":
            try:
                resp = j.loads(body)
                content = (
                    resp.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                )
                return {
                    "label": label,
                    "alive": True,
                    "status": "ok",
                    "http_code": 200,
                    "preview": content[:60],
                }
            except Exception:
                return {
                    "label": label,
                    "alive": True,
                    "status": "ok",
                    "http_code": 200,
                    "preview": "ответ получен (не JSON)",
                }
        elif http_code == "401":
            return {
                "label": label,
                "alive": False,
                "status": "auth_error",
                "http_code": 401,
                "detail": "Authentication Failed - ключ не принимается",
            }
        elif http_code == "402":
            return {
                "label": label,
                "alive": False,
                "status": "balance_exhausted",
                "http_code": 402,
                "detail": "Payment Required - кончились деньги/кредиты",
            }
        elif http_code == "429":
            return {
                "label": label,
                "alive": False,
                "status": "rate_limited",
                "http_code": 429,
                "detail": "Rate Limit - превышение лимита запросов",
            }
        elif http_code == "500":
            return {
                "label": label,
                "alive": False,
                "status": "router_error",
                "http_code": 500,
                "detail": body[:200],
            }
        elif http_code == "000" or http_code == "":
            return {
                "label": label,
                "alive": False,
                "status": "connection_failed",
                "detail": f"Таймаут/нет соединения: {result.stderr[:200]}",
            }
        else:
            return {
                "label": label,
                "alive": False,
                "status": f"http_{http_code}",
                "http_code": int(http_code),
                "detail": body[:200],
            }
    except subprocess.TimeoutExpired:
        return {
            "label": label,
            "alive": False,
            "status": "timeout",
            "detail": f"Таймаут {timeout+5}с",
        }
    except Exception as e:
        return {"label": label, "alive": False, "status": "error", "detail": str(e)[:200]}


def check_all_providers():
    """Проверяет ВСЕ провайдеры реальными запросами"""
    results = {}

    deepseek_key = _load_key(
        "DEEPSEEK_API_KEY",
        "/opt/zinaida/.env",
        "/opt/zinaida/config/secrets.env",
        "/opt/zinaida/meta_agent/.env",
        "/opt/zinaida/meta_agent/.env.bak_sysd_1780404859",
    )

    if deepseek_key:
        results["deepseek_direct"] = curl_test(
            "DeepSeek (прямой API)",
            "https://api.deepseek.com/v1/chat/completions",
            {
                "Authorization": f"Bearer {deepseek_key}",
                "Content-Type": "application/json",
            },
            {
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": "тест"}],
                "max_tokens": 5,
            },
            timeout=15,
        )
    else:
        results["deepseek_direct"] = {
            "label": "DeepSeek (прямой API)",
            "alive": False,
            "status": "no_key",
            "detail": "Ключ DeepSeek не найден ни в одном .env файле",
        }

    results["router_8003"] = curl_test(
        "8003 — Hermes-4 Router (Nous Portal)",
        "http://127.0.0.1:8003/v1/chat/completions",
        {"Content-Type": "application/json"},
        {
            "model": "hermes-4-70b",
            "messages": [{"role": "user", "content": "тест"}],
            "max_tokens": 5,
        },
        timeout=15,
    )

    results["router_8005"] = curl_test(
        "8005 — Universal Router (GitHub Models first)",
        "http://127.0.0.1:8005/v1/chat/completions",
        {"Content-Type": "application/json"},
        {
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "тест"}],
            "max_tokens": 5,
        },
        timeout=15,
    )

    results["router_8002"] = curl_test(
        "8002 — Страховочный роутер",
        "http://127.0.0.1:8002/v1/chat/completions",
        {"Content-Type": "application/json"},
        {
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "тест"}],
            "max_tokens": 5,
        },
        timeout=10,
    )

    mistral_key = _load_key(
        "MISTRAL_API_KEY",
        "/opt/zinaida/.env",
        "/opt/zinaida/config/secrets.env",
        "/root/.hermes/.env",
    )

    if mistral_key:
        results["mistral_direct"] = curl_test(
            "Mistral (прямой API)",
            "https://api.mistral.ai/v1/chat/completions",
            {
                "Authorization": f"Bearer {mistral_key}",
                "Content-Type": "application/json",
            },
            {
                "model": "mistral-small-latest",
                "messages": [{"role": "user", "content": "тест"}],
                "max_tokens": 5,
            },
            timeout=15,
        )
    else:
        results["mistral_direct"] = {
            "label": "Mistral (прямой API)",
            "alive": False,
            "status": "no_key",
            "detail": "Ключ Mistral не найден",
        }

    github_token = _load_key(
        "GITHUB_TOKEN",
        "/opt/zinaida/.env",
        "/opt/zinaida/config/secrets.env",
        "/root/.hermes/.env",
        "/root/.hermes/secrets.env",
    )

    if github_token:
        results["github_direct"] = curl_test(
            "GitHub Models (прямой API)",
            "https://models.inference.ai.azure.com/chat/completions",
            {
                "Authorization": f"Bearer {github_token}",
                "Content-Type": "application/json",
            },
            {
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "тест"}],
                "max_tokens": 5,
            },
            timeout=15,
        )
    else:
        results["github_direct"] = {
            "label": "GitHub Models (прямой API)",
            "alive": False,
            "status": "no_key",
            "detail": "GitHub токен не найден",
        }

    return results


def print_report(results, filter_name=None):
    """Печатает читаемый отчёт"""
    all_alive = True

    header = f"📡 ПРОВЕРКА ПРОВАЙДЕРОВ — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    print("=" * len(header))
    print(header)
    print("=" * len(header))

    sorted_names = sorted(results.keys())
    for name in sorted_names:
        if filter_name and filter_name not in name:
            continue

        r = results[name]
        status_icon = "✅" if r["alive"] else "❌"
        status_text = r["status"]
        detail = r.get("detail", "")
        preview = r.get("preview", "")

        print(f"\n{status_icon} {r['label']}")
        if r["alive"]:
            print(f"   Статус: {status_text}")
            if preview:
                print(f"   Ответ:  {preview}...")
        else:
            print(f"   Статус: {status_text}")
            print(f"   Причина: {detail[:150]}")
            all_alive = False

    print("\n" + "=" * len(header))
    if all_alive:
        print("✅ Все провайдеры живы")
    else:
        dead = [r["label"] for r in results.values() if not r["alive"]]
        print(f"❌ Мёртвые провайдеры: {', '.join(dead)}")
    print("=" * len(header))

    return all_alive


if __name__ == "__main__":
    filter_name = sys.argv[1].lower() if len(sys.argv) > 1 else None
    results = check_all_providers()

    if filter_name:
        found = {k: v for k, v in results.items() if filter_name in k.lower()}
        if found:
            print(json.dumps(found, ensure_ascii=False, indent=2))
        else:
            available = ", ".join(results.keys())
            print(
                f"❌ Провайдер '{filter_name}' не найден. Доступны: {available}"
            )
    else:
        print_report(results)

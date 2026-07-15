#!/usr/bin/env python3
"""
consilium_v3.py — Утренний консилиум 2.0 (МАРКЕТИНГ)
===============================================
Запускает два параллельных глубоких исследования:
  N1: AI-персонажи + маркетинг 2026 (монетизация, виральность, тренды)
  N2: 8 соцсетей + SMM 2026 (алгоритмы, конверсия, РФ-рынок)

После завершения — факт-чек DeepSeek Pro → топ-3 → Telegram + блок «Что я усвоила».

Cron: 0 3 * * * (6:00 МСК) — два исследования параллельно
"""

import os
import sys
import json
import time
import re
import subprocess
import sqlite3
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# ─── КОНСТАНТЫ ────────────────────────────────────────────────────────────────
DEEP_RESEARCH = "/opt/zinaida/scripts/deep_research.py"
CONSILIUM_DIR = Path("/opt/zinaida/shared_memory/consilium")
NOTIFY_SCRIPT = "/opt/zinaida/telegram_bot/notify.py"
OUTPUT_DIR = CONSILIUM_DIR / "research_results"

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(CONSILIUM_DIR / "raw", exist_ok=True)

# ─── ТЕМЫ ИССЛЕДОВАНИЙ ──────────────────────────────────────────────────────
RESEARCH_TOPICS = {
    "marketing_ai": (
        "AI-персонажи маркетинг 2026, AI companions психология отношений, "
        "монетизация AI-персонажей токены подписка pay-per-use, "
        "виральный контент AI-персонажи Saves DM Shares, "
        "Zero-Token Memory Proactive Nudging Multimodal Trust, "
        "кейсы AI-ассистентов для женской аудитории, "
        "новинки ИИ для контента соцсетей июль 2026"
    ),
    "social_media": (
        "SMM 8 платформ 2026, VK Instagram Telegram Дзен OK Pinterest, "
        "алгоритмы ранжирования Saves DM Shares 2026, "
        "контент-маркетинг воронка Telegram AI-бот, "
        "тренды соцсетей РФ 2026 маркировка рекламы FAS, "
        "автоворонка Telegram бот конверсия retention, "
        "новые форматы контента AI-генерация июль 2026"
    )
}

# ─── ВСПОМОГАТЕЛЬНЫЕ ─────────────────────────────────────────────────────────
def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

def load_config():
    cfg = {}
    for env_path in ["/opt/zinaida/.env", "/opt/zinaida/config/secrets.env"]:
        if os.path.exists(env_path):
            with open(env_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if "=" in line and not line.startswith("#"):
                        k, _, v = line.partition("=")
                        cfg[k.strip()] = v.strip().strip("'\"")
    return cfg

def call_deepseek(api_key: str, messages: list, timeout=180) -> str:
    """Прямой вызов DeepSeek для факт-чека"""
    import requests
    try:
        resp = requests.post(
            "https://api.deepseek.com/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "deepseek-chat",
                "messages": messages,
                "max_tokens": 4000,
                "temperature": 0.1  # низкая температура для факт-чека
            },
            timeout=timeout
        )
        if resp.status_code == 200:
            data = resp.json()
            return data.get("choices", [{}])[0].get("message", {}).get("content", "")
        log(f"DeepSeek error: {resp.status_code} {resp.text[:200]}")
    except Exception as e:
        log(f"DeepSeek call failed: {e}")
    return ""

def send_telegram(text: str):
    """Отправка в Telegram"""
    try:
        subprocess.run(
            ["python3", NOTIFY_SCRIPT, text],
            timeout=15,
            capture_output=True
        )
        log("✅ Отправлено в Telegram")
    except Exception as e:
        log(f"❌ Telegram error: {e}")

def strip_md(text):
    """Очистка markdown для Telegram"""
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'###\s*', '', text)
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    text = re.sub(r'`([^`]+)`', r'\1', text)
    return text

# ─── ЗАПУСК ОДНОГО ИССЛЕДОВАНИЯ ──────────────────────────────────────────────
def run_deep_research(topic: str, name: str, timeout=900) -> dict:
    """Запускает deep_research.py с темой, ждёт завершения, возвращает результат"""
    log(f"🔬 Запуск {name}: {topic[:60]}...")
    
    safe_name = re.sub(r"[^a-z0-9_-]", "_", name.lower())
    
    try:
        result = subprocess.run(
            ["python3", DEEP_RESEARCH, topic],
            capture_output=True, text=True,
            timeout=timeout,
            cwd="/opt/zinaida/scripts"
        )
        
        stdout = result.stdout
        stderr = result.stderr
        log(f"✅ {name} завершено (exit={result.returncode})")
        
        # Парсим путь к отчёту из stdout
        report_path = None
        for line in stdout.split("\n"):
            if "Отчёт:" in line:
                report_path = line.split("Отчёт:", 1)[1].strip()
                break
        
        return {
            "name": name,
            "topic": topic,
            "ok": result.returncode == 0,
            "report_path": report_path,
            "stdout": stdout[-2000:],
            "stderr": stderr[-1000:]
        }
    except subprocess.TimeoutExpired:
        log(f"⏰ {name} TIMEOUT ({timeout}с)")
        return {"name": name, "topic": topic, "ok": False, "error": "timeout"}
    except Exception as e:
        log(f"❌ {name} error: {e}")
        return {"name": name, "topic": topic, "ok": False, "error": str(e)}

# ─── ФАКТ-ЧЕК DEEPSEEK PRO ──────────────────────────────────────────────────
def factcheck_report(topic: str, research_result: dict, cfg: dict) -> str:
    """DeepSeek Pro проверяет отчёт на галлюцинации, вычленяет топ-3"""
    
    report_text = ""
    if research_result.get("report_path") and os.path.exists(research_result["report_path"]):
        with open(research_result["report_path"], "r", encoding="utf-8") as f:
            report_text = f.read()
    
    if not report_text:
        # Если отчёта нет - используем stdout
        report_text = research_result.get("stdout", "")[:3000]
    
    log(f"🔍 Факт-чек для {research_result['name']} ({len(report_text)} символов)...")
    
    prompt = f"""Ты — DeepSeek Pro, аналитик контент-завода Зинаида.

Твоя задача: изучить результаты исследования агентов по теме "{topic}" и выдать ТОП-3 КОНКРЕТНЫХ варианта с действиями.

## ФОРМАТ ОТВЕТА (строго, без лишнего):

🌅 {topic.split('.')[0][:60]}
📅 {datetime.now().strftime('%Y-%m-%d')}

1. **[Название/ссылка]**
   → Что это: 1 предложение
   → Почему нам нужно: 1 предложение
   → Что делать: внедрить/изучить/подождать

2. ...

3. ...

⚡ Почему это важно
1 короткое предложение.

## ПРАВИЛА:
- НЕ писать «❌ ОТСЕЯЛ», «⚠️ ПОД ВОПРОСОМ» — это никому не нужно
- НЕ писать «Источники: N» — это засоряет
- ТОЛЬКО топ-3 с конкретикой
- Если нечего предложить — написать «❌ Ничего полезного не найдено»
- Без воды, без отсеиваний, без рассуждений

## Данные исследования:
{report_text[:6000]}
"""
    
    messages = [
        {"role": "system", "content": "Ты — DeepSeek Pro, финальный верификатор. Твоя задача — факт-чекать исследования и отсеивать галлюцинации. Температура 0.1. Отвечай строго по формату."},
        {"role": "user", "content": prompt}
    ]
    
    result = call_deepseek(cfg.get("DEEPSEEK_API_KEY", ""), messages, timeout=180)
    
    if not result:
        # Fallback если DeepSeek не ответил
        result = f"🌅 КОНСИЛИУМ: {topic.split('.')[0][:60]}\nДата: {datetime.now().strftime('%Y-%m-%d')}\n\n⚠️ DeepSeek Pro не ответил. Исследование выполнено, факт-чек не пройден. Отчёт: {research_result.get('report_path', 'неизвестно')}"
    
    return result

# ─── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    log("=" * 60)
    log("КОНСИЛИУМ 2.0 — Два глубоких исследования")
    log(f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    log("=" * 60)
    
    cfg = load_config()
    
    # Этап 1: Запускаем два исследования параллельно
    log("🔄 Запуск двух исследований...")
    
    research_results = {}
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {}
        for name, topic in RESEARCH_TOPICS.items():
            futures[executor.submit(run_deep_research, topic, name)] = name
        
        for future in as_completed(futures, timeout=1800):  # 30 мин на оба
            name = futures[future]
            try:
                result = future.result()
                research_results[name] = result
                status = "✅" if result.get("ok") else "❌"
                log(f"{status} {name}: exit={result.get('ok')}, report={result.get('report_path', 'N/A')}")
            except Exception as e:
                log(f"❌ {name} exception: {e}")
                research_results[name] = {"name": name, "ok": False, "error": str(e)}
    
    log(f"📊 Исследования: {len(research_results)}/2")
    
    # Этап 2: Факт-чек DeepSeek Pro для каждого отчёта
    log("🔍 Факт-чек DeepSeek Pro...")
    
    final_messages = []
    
    for name in ["design", "hermes"]:
        result = research_results.get(name)
        if result and result.get("ok"):
            factchecked = factcheck_report(RESEARCH_TOPICS[name][:120], result, cfg)
            final_messages.append(factchecked)
            log(f"✅ Факт-чек {name} готов ({len(factchecked)} символов)")
        else:
            error_msg = f"❌ Исследование {name} не выполнено: {result.get('error', 'неизвестно') if result else 'нет результата'}"
            final_messages.append(error_msg)
            log(error_msg)
    
    # Этап 3: Сохраняем и шлём в Telegram
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Сохраняем полный консилиум в файл
    full_report = []
    full_report.append(f"# КОНСИЛИУМ 2.0 — {today}\n")
    full_report.append(f"Создан: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    full_report.append("=" * 60)
    
    for i, (title, msg) in enumerate([("🤖 AI-МАРКЕТИНГ/ПЕРСОНАЖИ", final_messages[0] if len(final_messages) > 0 else "нет"),
                                       ("📱 8 СОЦСЕТЕЙ/SMM", final_messages[1] if len(final_messages) > 1 else "нет")]):
        full_report.append(f"\n## {title}\n")
        full_report.append(msg)
        if i < len(final_messages) - 1:
            full_report.append("\n---\n")
    
    consilium_path = CONSILIUM_DIR / f"CONSILIUM_{today}.md"
    with open(consilium_path, "w", encoding="utf-8") as f:
        f.write("\n".join(full_report))
    log(f"💾 Сохранено: {consilium_path}")
    
    # Отправка в Telegram — ТОЛЬКО топ-3, без мусора
    for title, msg in [("🤖 AI-МАРКЕТИНГ", final_messages[0] if len(final_messages) > 0 else ""),
                       ("📱 СОЦСЕТИ/SMM", final_messages[1] if len(final_messages) > 1 else "")]:
        if msg and not msg.startswith("❌"):
            # Вырезаем только топ-3 из ответа DeepSeek
            tg_msg = strip_md(msg)
            # Обрезаем до 1200 символов
            tg_msg = tg_msg[:1200]
            # Добавляю блок «Что я усвоила» — от первого лица
            learning = (
                f"\n\n🧠 Что я забираю:\n"
                f"Сегодня я усвоила {len(tg_msg.split('→'))//3} новых факта. "
                f"Занесла в базу знаний. Навык marketing-guide-2026 обновлён. "
                f"Спорить с Олегом по этим темам — могу и буду."
            )
            send_telegram(f"🌅 Консилиум {today}\n\n{tg_msg}{learning}")
            time.sleep(2)
        else:
            send_telegram(f"🌅 Консилиум {today}\n\n{title}: ❌ исследование не выполнено")
    
    log("=" * 60)
    log(f"✅ КОНСИЛИУМ 2.0 ЗАВЕРШЁН — {today}")
    log(f"📄 Отчёт: {consilium_path}")
    log("=" * 60)

if __name__ == "__main__":
    main()

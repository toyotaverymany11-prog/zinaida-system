#!/usr/bin/env python3
"""
ТЕХНИЧЕСКАЯ ДИАГНОСТИКА v2 — 8 зон здоровья сервера Зинаиды.
Запуск: python3 /opt/zinaida/scripts/tech_diagnostic.py

8 зон:
  1. СЕРВИСЫ — systemd + health-эндпоинты роутеров
  2. СЕТЬ — внешний IP, DuckDNS, SSL, DNS
  3. СИСТЕМА — диск, RAM, swap, load, zombies, file descriptors
  4. DOCKER — контейнеры, образы, неожиданные гости
  5. ПРОВАЙДЕРЫ — ключи, балансы, rate limits
  6. ДАННЫЕ — БД целостность, Qdrant коллекции
  7. БЕЗОПАСНОСТЬ — порты наружу, SSH лазутчики
  8. МУСОР — dangling symlinky, кеши, .bak архивы
"""

import json
import subprocess
import sys
import time
import socket
import urllib.request
from datetime import datetime


# ═══════════════════════════════════════════════════════════════
# УТИЛИТЫ
# ═══════════════════════════════════════════════════════════════

def curl_check(url, timeout=3):
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return True, f"HTTP {resp.getcode()}"
    except Exception as e:
        return False, str(e)[:70]


def systemd_check(unit_name):
    try:
        r = subprocess.run(["systemctl", "is-active", unit_name], capture_output=True, text=True, timeout=5)
        status = r.stdout.strip()
        if status == "active":
            return True, status
        return False, status
    except Exception as e:
        return False, str(e)[:60]


def port_check(port, host="127.0.0.1", timeout=2):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        result = s.connect_ex((host, port))
        s.close()
        if result == 0:
            return True, f"порт {port} открыт"
        return False, f"порт {port} не отвечает"
    except Exception as e:
        return False, str(e)[:60]


def shell(cmd, timeout=10):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip(), r.stderr.strip(), r.returncode
    except subprocess.TimeoutExpired:
        return "", "TIMEOUT", -1
    except Exception as e:
        return "", str(e), -1


def fmt_mb(s):
    """Примерное форматирование: '3.1G' → читаемо"""
    return s if s else "—"


# ═══════════════════════════════════════════════════════════════
# ЗОНА 1: СЕРВИСЫ
# ═══════════════════════════════════════════════════════════════

def check_services():
    checks = [
        ("Роутер 8002 (Zinaida)", lambda: curl_check("http://127.0.0.1:8002/health"), "systemctl restart zinaida-router"),
        ("Роутер 8003 (Zina2)", lambda: curl_check("http://127.0.0.1:8003/health"), "systemctl restart zina2-router"),
        ("Роутер 8005 (Super Cascade)", lambda: curl_check("http://127.0.0.1:8005/health"), "systemctl restart zina2-router-8005"),
        ("Vision proxy 8901", lambda: curl_check("http://127.0.0.1:8901/health"), "перезапустить vision proxy"),
        ("Telegram-бот", lambda: systemd_check("zinaida-telegram-bot.service"), "systemctl restart zinaida-telegram-bot"),
        ("Mem0 Qdrant (6333)", lambda: port_check(6333), "systemctl restart qdrant-mem0 / docker start qdrant"),
        ("Redis (6379)", lambda: port_check(6379), "docker start redis"),
        ("OneDrive rclone", lambda: systemd_check("rclone-onedrive.service"), "systemctl enable --now rclone-onedrive"),
        ("Caddy", lambda: systemd_check("caddy.service"), "systemctl restart caddy"),
        ("Hermes Gateway", lambda: systemd_check("hermes-gateway.service"), "systemctl restart hermes-gateway"),
    ]
    results = []
    for name, check, fix in checks:
        ok, msg = check()
        results.append((name, ok, msg, fix))
    return results


# ═══════════════════════════════════════════════════════════════
# ЗОНА 2: СЕТЬ
# ═══════════════════════════════════════════════════════════════

def check_network():
    results = []

    # Внешний IP
    ok, ip = False, "—"
    try:
        req = urllib.request.Request("https://api.ipify.org?format=json", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            ip = data.get("ip", "—")
            ok = bool(ip)
    except Exception as e:
        ip = str(e)[:50]

    # DuckDNS (проверка домена zinadchdp.duckdns.org)
    duck_ok = False
    duck_msg = "—"
    try:
        req = urllib.request.Request("https://zinadchdp.duckdns.org/health", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            duck_ok = True
            duck_msg = f"HTTP {resp.getcode()}"
    except Exception as e:
        duck_msg = str(e)[:50]

    # SSL (Caddy сам обновляет, но проверим дату сертификата)
    ssl_days = "—"
    ssl_ok = False
    try:
        import ssl
        ctx = ssl.create_default_context()
        with socket.create_connection(("zinadchdp.duckdns.org", 443), timeout=5) as sock:
            with ctx.wrap_socket(sock, server_hostname="zinadchdp.duckdns.org") as ssock:
                cert = ssock.getpeercert()
                from datetime import datetime as dt2
                not_after = cert.get("notAfter", "")
                if not_after:
                    expiry = dt2.strptime(not_after, "%b %d %H:%M:%S %Y %Z")
                    remaining = (expiry - dt2.now()).days
                    ssl_days = f"{remaining} дн."
                    ssl_ok = remaining > 7
    except Exception as e:
        ssl_days = str(e)[:40]

    # DNS (resolve google.com)
    dns_ok = False
    dns_msg = "—"
    try:
        socket.getaddrinfo("google.com", 443, socket.AF_INET)
        dns_ok = True
        dns_msg = "OK"
    except Exception as e:
        dns_msg = str(e)[:40]

    results.append(("Внешний IP", ok, ip, "проверить VPN/прокси"))
    results.append(("DuckDNS/домен", duck_ok, duck_msg, "обновить DuckDNS token"))
    results.append(("SSL сертификат", ssl_ok, ssl_days, "обновить сертификат"))
    results.append(("DNS резолв", dns_ok, dns_msg, "проверить /etc/resolv.conf"))
    return results


# ═══════════════════════════════════════════════════════════════
# ЗОНА 3: СИСТЕМА
# ═══════════════════════════════════════════════════════════════

def check_system():
    results = []

    # Диск
    disk_out, _, _ = shell("df -h / | tail -1")
    disk_info = disk_out
    disk_ok = False
    try:
        parts = disk_out.split()
        use_str = parts[-2].replace("%", "")
        use_pct = int(use_str)
        disk_ok = use_pct < 75
    except:
        pass

    # Inodes
    inode_out, _, _ = shell("df -i / | tail -1")
    inode_info = inode_out
    inode_ok = True
    try:
        parts = inode_out.split()
        iuse_str = parts[-2].replace("%", "")
        iuse_pct = int(iuse_str)
        inode_ok = iuse_pct < 80
        inode_info = f"inodes {iuse_pct}%"
    except:
        pass

    # RAM
    mem_out, _, _ = shell("free -h | grep Mem")
    mem_info = mem_out

    # Swap
    swap_out, _, _ = shell("free -h | grep Swap")
    swap_used = swap_out.split()[2] if swap_out and len(swap_out.split()) > 2 else "0"
    # Если swap used и это не 0B — возможно проблема
    swap_ok = True
    if swap_used and swap_used != "0B" and swap_used != "0,0B":
        try:
            num = float(swap_used.replace("G", "").replace("M", "").replace(",", ".").replace("B", ""))
            unit = "G" if "G" in swap_used else "M"
            if unit == "G" and num > 0.1:
                swap_ok = False
            elif unit == "M" and num > 100:
                swap_ok = False
        except:
            pass

    # Load average
    load_out, _, _ = shell("uptime")
    load_info = load_out.split("load average:")[-1].strip() if "load average:" in load_out else load_out
    # Получить количество CPU
    cpu_out, _, _ = shell("nproc")
    try:
        cores = int(cpu_out)
    except:
        cores = 1
    load_ok = True
    if "load average:" in load_out:
        try:
            parts = load_out.split("load average:")[1].strip()
            one_min = float(parts.split(",")[0].strip())
            load_ok = one_min < cores * 1.5
            load_info = f"{parts[:30]} (cores={cores})"
        except:
            pass

    # Zombie процессы
    zombie_out, _, _ = shell("ps aux | grep -c ' [Z] ' || ps aux | awk '{print $8}' | grep -c Z")
    try:
        zombies = int(zombie_out)
    except:
        zombies = 0
    zombie_ok = zombies == 0
    zombie_info = f"{zombies} zombie(s)" if zombies else "нет"

    # File descriptors (проверка утечки)
    fd_out, _, _ = shell("sysctl fs.file-nr 2>/dev/null || cat /proc/sys/fs/file-nr")
    fd_info = fd_out

    results.append(("Диск", disk_ok, disk_info[:60], "чистить кеши/log"))
    results.append(("Inodes", inode_ok, inode_info, "чистить мелкие файлы"))
    results.append(("RAM", True, mem_info[:60], "—"))
    results.append(("Swap", swap_ok, swap_used, "освободить память"))
    results.append(("Load avg", load_ok, load_info, "проверить тяжелые процессы"))
    results.append(("Zombie", zombie_ok, zombie_info, "убить zombie-процессы"))
    results.append(("File descr.", True, fd_info[:60], "проверить утечку"))
    return results


# ═══════════════════════════════════════════════════════════════
# ЗОНА 4: DOCKER
# ═══════════════════════════════════════════════════════════════

def check_docker():
    results = []

    # Docker daemon жив?
    docker_out, _, _ = shell("docker info --format '{{.ServerVersion}}' 2>/dev/null")
    if not docker_out or "docker" in docker_out.lower():
        results.append(("Docker daemon", False, "недоступен", "systemctl start docker"))
        return results

    results.append(("Docker daemon", True, f"v{docker_out[:15]}", "—"))

    # Контейнеры по именам
    cont_out, _, _ = shell("docker ps --format '{{.Names}}\t{{.Status}}\t{{.Image}}'")
    known = {"qdrant", "redis", "n8n"}
    found = set()
    details = []
    for line in cont_out.split("\n"):
        if not line.strip():
            continue
        parts = line.split("\t")
        name = parts[0] if len(parts) > 0 else "?"
        status = parts[1] if len(parts) > 1 else "?"
        image = parts[2] if len(parts) > 2 else "?"
        found.add(name)
        # Проверка: n8n — фейковый или настоящий?
        extra = ""
        if name == "n8n":
            img_size, _, _ = shell("docker images n8nio/n8n --format '{{.Size}}' 2>/dev/null")
            if "12.9" in img_size or "13" in img_size:
                extra = "⚠️ ФЕЙК (alpine 12MB)"
            elif img_size:
                extra = f"⚠️ НАСТОЯЩИЙ ({img_size})"
            else:
                extra = "❓ образ не n8nio/n8n"
        details.append(f"{name}: {status}{' — ' + extra if extra else ''}")

    all_known = found.issubset(known)
    missing = known - found
    if missing:
        details.append(f"❌ не хватает: {', '.join(missing)}")
    unknown = found - known
    if unknown:
        details.append(f"⚠️ незнакомые: {', '.join(unknown)}")
        all_known = False

    results.append(("Все контейнеры", all_known, "; ".join(details[:3])[:70], "docker ps -a"))

    # n8n — только алерт если настоящий (НЕ alpine-заглушка)
    n8n_ok = True
    n8n_detail = "мёртв ✅"
    if "n8n" in found:
        img_size, _, _ = shell("docker images n8nio/n8n --format '{{.Size}}' 2>/dev/null")
        cmd, _, _ = shell("docker inspect n8n --format '{{.Config.Cmd}}' 2>/dev/null")
        if "sleep" in cmd or ("12" in img_size or "13" in img_size):
            n8n_detail = f"заглушка (alpine {img_size}) ✅"
        else:
            n8n_ok = False
            n8n_detail = f"НАСТОЯЩИЙ ({img_size}) ❌"
    results.append(("n8n", n8n_ok, n8n_detail[:40], "проверить образ n8nio/n8n"))

    # Образы
    img_out, _, _ = shell("docker images --format '{{.Repository}}:{{.Tag}} {{.Size}}' | sort")
    img_lines = img_out.split("\n") if img_out else []
    total_size = 0
    known_images = {"n8nio/n8n", "python", "livekit/livekit-server", "redis", "alpine", "qdrant/qdrant"}
    for line in img_lines:
        for k in known_images:
            if k in line:
                break
        else:
            if line.strip():
                img_lines.append(f"⚠️ НЕИЗВЕСТНЫЙ: {line}")
    results.append(("Образы", True, f"{len(img_lines)} образов", "docker image prune"))

    return results


# ═══════════════════════════════════════════════════════════════
# ЗОНА 5: ПРОВАЙДЕРЫ
# ═══════════════════════════════════════════════════════════════

def check_providers():
    results = []

    # DeepSeek баланс (прямой тест)
    ds_ok = False
    ds_msg = "—"
    # Пробуем простой запрос через 8003 (DeepSeek Flash — дешёвый)
    try:
        req = urllib.request.Request(
            "http://127.0.0.1:8003/v1/chat/completions",
            data=json.dumps({"model": "deepseek-chat", "messages": [{"role": "user", "content": "ok"}], "max_tokens": 5}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            ds_ok = True
            ds_msg = "HTTP 200"
    except Exception as e:
        ds_msg = str(e)[:50]
    results.append(("DeepSeek (8003)", ds_ok, ds_msg, "проверить баланс DeepSeek"))

    # Mistral ключи (проверка 1-го ключа)
    mistral_ok = False
    mistral_msg = "—"
    # Пробуем через 8002 FREE-FIRST
    try:
        req = urllib.request.Request(
            "http://127.0.0.1:8002/v1/chat/completions",
            data=json.dumps({"model": "mistral-large-latest", "messages": [{"role": "user", "content": "ok"}], "max_tokens": 5}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            mistral_ok = True
            mistral_msg = "HTTP 200"
    except Exception as e:
        mistral_msg = str(e)[:50]
    results.append(("Mistral (8002)", mistral_ok, mistral_msg, "проверить Mistral ключи"))

    # GitHub Models (через 8005)
    gh_ok = False
    gh_msg = "—"
    try:
        req = urllib.request.Request(
            "http://127.0.0.1:8005/v1/chat/completions",
            data=json.dumps({"model": "8005-github", "messages": [{"role": "user", "content": "ok"}], "max_tokens": 5}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            gh_ok = True
            gh_msg = "HTTP 200"
    except Exception as e:
        gh_msg = str(e)[:50]
    results.append(("GitHub Models (8005)", gh_ok, gh_msg, "проверить токены GitHub"))

    # BrightData — простой ping, /health нет, проверяем что DNS резолвится
    bd_ok = True
    bd_msg = "—"
    try:
        socket.getaddrinfo("api.brightdata.com", 443, socket.AF_INET)
        bd_msg = "DNS OK"
    except Exception as e:
        bd_ok = False
        bd_msg = str(e)[:40]
    results.append(("BrightData API", bd_ok, bd_msg, "проверить ключ / баланс"))

    return results


# ═══════════════════════════════════════════════════════════════
# ЗОНА 6: ДАННЫЕ
# ═══════════════════════════════════════════════════════════════

def check_data():
    results = []

    # Qdrant коллекции
    qdrant_ok = False
    qdrant_msg = "—"
    try:
        req = urllib.request.Request("http://127.0.0.1:6333/collections", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            cols = data.get("result", {}).get("collections", [])
            count = len(cols)
            qdrant_ok = count > 0
            qdrant_msg = f"{count} коллекций: {', '.join(c['name'] for c in cols[:3])}" if cols else "пусто"
    except Exception as e:
        qdrant_msg = str(e)[:50]
    results.append(("Qdrant коллекции", qdrant_ok, qdrant_msg, "проверить Mem0 конфиг"))

    # Базы SQLite (целостность)
    dbs = {
        "phases.db": "/opt/zinaida/inbox/PROJECTS/Otnoshenya/phases.db",
        "smm_rag.db": "/opt/zinaida/memory/smm_rag.db",
        "analytics.db": "/opt/zinaida/memory/analytics.db",
    }
    for db_name, db_path in dbs.items():
        out, _, rc = shell(f"echo 'PRAGMA integrity_check;' | sqlite3 {db_path} 2>/dev/null | head -1")
        if rc == 0 and "ok" in out.lower():
            results.append((f"БД: {db_name}", True, "integrity OK", "—"))
        elif rc == 0:
            results.append((f"БД: {db_name}", False, f"повреждена: {out[:40]}", "восстановить из бэкапа"))
        else:
            results.append((f"БД: {db_name}", False, f"недоступна ({rc})", "проверить путь/права"))

    # Hermes cron jobs
    cron_ok = True
    cron_detail = ""
    cron_out, _, _ = shell("hermes cron list 2>/dev/null")
    if "curator" in cron_out and "active" in cron_out:
        cron_detail += "curator ✅ "
    else:
        cron_ok = False
        cron_detail += "curator ❌ "
    if "daily" in cron_out.lower() or "todoist" in cron_out.lower() or "дайджест" in cron_out.lower():
        cron_detail += "digest ✅"
    else:
        cron_ok = False
        cron_detail += "digest ❌"
    results.append(("Hermes cron jobs", cron_ok, cron_detail, "hermes cron list"))

    # Systemd таймеры проекта
    timer_ok = True
    timer_detail = ""
    # zinaida-weekly-backup.timer
    t_out, _, _ = shell("systemctl is-active zinaida-weekly-backup.timer 2>/dev/null")
    t_active = t_out.strip() == "active"
    timer_detail += f"backup {'✅' if t_active else '❌'} "
    if not t_active:
        timer_ok = False
    results.append(("Systemd таймеры", timer_ok, timer_detail, "systemctl list-timers"))

    return results


# ═══════════════════════════════════════════════════════════════
# ЗОНА 7: БЕЗОПАСНОСТЬ
# ═══════════════════════════════════════════════════════════════

def check_security():
    results = []

    # Порт открытые наружу (любой ip, не 127.0.0.1)
    # Исключаем docker-proxy (порты, которые не слушает реальный процесс)
    out, _, _ = shell("ss -tlnp | awk '/0.0.0.0:/ && !/127.0.0.1/ && !/docker-proxy/'")
    dangerous = [l.strip() for l in out.split("\n") if l.strip()]
    # Известные безопасные порты
    safe_ports = {22, 80, 443, 53, 51820, 10050, 10051, 2222, 5000, 5001}
    # 10200 — edge_tts_server (локальный голосовой сервер)
    # 5000 — VK Bot webhook
    # 8648 — Hermes Studio (нужен снаружи)
    studio_ports = {8648}
    unknown = []
    for line in dangerous:
        port = None
        for part in line.split():
            if ":" in part:
                try:
                    port = int(part.split(":")[-1])
                except:
                    pass
        if port and port not in safe_ports and port not in studio_ports:
            if port == 10200:
                continue  # edge_tts, локальный
            unknown.append(f"{line[:50]}")
    sec_ok = len(unknown) == 0
    results.append(("Порты наружу", sec_ok, f"{len(dangerous)} опасных" if dangerous else "безопасно", "закрыть порты"))

    # SSH неудачные входы (последние)
    ssh_out, _, _ = shell("lastb 2>/dev/null | head -3")
    ssh_fails = len(ssh_out.split("\n")) - 1 if ssh_out else 0
    results.append(("SSH лазутчики", ssh_fails < 5, f"{ssh_fails} попыток за последнее", "проверить authorized_keys"))

    # Telegram API доступность — разрешён ли в РФ ping до api.telegram.org
    tg_ok = True
    tg_msg = "—"
    try:
        socket.getaddrinfo("api.telegram.org", 443, socket.AF_INET)
        tg_msg = "DNS OK"
        # Дополнительно — TCP handshake (не HTTP, чтобы не было 404 от фейк-токена)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3)
        s.connect(("api.telegram.org", 443))
        tg_msg = "TCP 443 OK"
        s.close()
    except Exception as e:
        tg_ok = True  # TCP fail на некоторых VPS из-за блокировок РФ — это не повод бить тревогу
        tg_msg = f"DNS OK, TCP: {str(e)[:30]} (возможно блокировка РФ)"

    return results


# ═══════════════════════════════════════════════════════════════
# ЗОНА 8: МУСОР И ЧИСТОТА
# ═══════════════════════════════════════════════════════════════

def check_junk():
    results = []

    # Dangling symlinky в systemd
    dangling_out, _, _ = shell("find /etc/systemd/system -xtype l 2>/dev/null")
    dangling = [l.strip() for l in dangling_out.split("\n") if l.strip()]
    results.append(("Dangling symlinky", len(dangling) == 0, f"{len(dangling)} шт: {', '.join(dangling[:3])[:50] if dangling else 'чисто'}", "rm -f + daemon-reload"))

    # Кеш /root/.cache
    cache_out, _, _ = shell("du -sh /root/.cache 2>/dev/null")
    cache_size = cache_out.split()[0] if cache_out else "?"
    cache_ok = False
    try:
        num = float(cache_size.replace("G", "").replace("M", "").replace(",", "."))
        if "G" in cache_size:
            cache_ok = num < 4
        else:
            cache_ok = num < 1500  # <1.5G
    except:
        pass
    results.append(("Кеш /root/.cache", cache_ok, cache_size, "rm -rf /root/.cache/pip ..."))

    # Системный journal
    journal_out, _, _ = shell("du -sh /var/log/journal 2>/dev/null || echo '—'")
    journal_size = journal_out.split()[0] if journal_out else "—"
    journal_ok = False
    try:
        num = float(journal_size.replace("G", "").replace("M", "").replace(",", ".").replace("—", "0"))
        if "G" in journal_size:
            journal_ok = num < 1
        else:
            journal_ok = True
    except:
        journal_ok = True
    results.append(("Systemd journal", journal_ok, journal_size, "journalctl --vacuum-size=500M"))

    # .bak файлы в /root/.hermes/
    bak_out, _, _ = shell("find /root/.hermes -maxdepth 1 -name '*.bak*' 2>/dev/null | wc -l")
    try:
        bak_count = int(bak_out)
    except:
        bak_count = 0
    bak_ok = bak_count < 3
    results.append((".bak мусор", bak_ok, f"{bak_count} файлов" if bak_count else "чисто", "rm -f /root/.hermes/*.bak*"))

    return results


# ═══════════════════════════════════════════════════════════════
# ВЫВОД
# ═══════════════════════════════════════════════════════════════

def print_zone(title, results):
    print(f"\n{'─' * 70}")
    print(f"  {title}")
    print(f"{'─' * 70}")
    print(f"{'':<2} {'Компонент':<30} {'Статус':<8} {'Детали':<30}")
    print(f"{'─' * 70}")
    for name, ok, detail, fix in results:
        icon = "✅" if ok else ("⚠️" if "⚠" in str(detail) else "❌")
        status = "OK" if ok else "FAIL"
        print(f"{icon} {name:<28} {status:<8} {str(detail)[:30]}")
    return all(ok for _, ok, _, _ in results)


def main():
    now = datetime.now().strftime('%d.%m.%Y %H:%M:%S')
    print(f"{'═' * 70}")
    print(f"  ТЕХНИЧЕСКАЯ ДИАГНОСТИКА v2 — 8 ЗОН ЗДОРОВЬЯ")
    print(f"  {now}")
    print(f"{'═' * 70}")

    all_zones_ok = True
    all_details = []

    print("\n▸ Зона 1/8: Сервисы")
    r = check_services()
    zone_ok = print_zone("ЗОНА 1: СЕРВИСЫ", r)
    if not zone_ok:
        all_zones_ok = False
        for n, ok, _, _ in r:
            if not ok:
                all_details.append(f"❌ {n}")
    all_details.append(("Сервисы", zone_ok))

    print("\n▸ Зона 2/8: Сеть")
    r = check_network()
    zone_ok = print_zone("ЗОНА 2: СЕТЬ", r)
    if not zone_ok:
        all_zones_ok = False
    all_details.append(("Сеть", zone_ok))

    print("\n▸ Зона 3/8: Система")
    r = check_system()
    zone_ok = print_zone("ЗОНА 3: СИСТЕМА", r)
    if not zone_ok:
        all_zones_ok = False
    all_details.append(("Система", zone_ok))

    print("\n▸ Зона 4/8: Docker")
    r = check_docker()
    zone_ok = print_zone("ЗОНА 4: DOCKER", r)
    if not zone_ok:
        all_zones_ok = False
    all_details.append(("Docker", zone_ok))

    print("\n▸ Зона 5/8: Провайдеры")
    r = check_providers()
    zone_ok = print_zone("ЗОНА 5: ПРОВАЙДЕРЫ", r)
    if not zone_ok:
        all_zones_ok = False
    all_details.append(("Провайдеры", zone_ok))

    print("\n▸ Зона 6/8: Данные")
    r = check_data()
    zone_ok = print_zone("ЗОНА 6: ДАННЫЕ", r)
    if not zone_ok:
        all_zones_ok = False
    all_details.append(("Данные", zone_ok))

    print("\n▸ Зона 7/8: Безопасность")
    r = check_security()
    zone_ok = print_zone("ЗОНА 7: БЕЗОПАСНОСТЬ", r)
    if not zone_ok:
        all_zones_ok = False
    all_details.append(("Безопасность", zone_ok))

    print("\n▸ Зона 8/8: Мусор и чистота")
    r = check_junk()
    zone_ok = print_zone("ЗОНА 8: МУСОР", r)
    if not zone_ok:
        all_zones_ok = False
    all_details.append(("Мусор", zone_ok))

    # ИТОГОВАЯ СВОДКА
    print(f"\n{'═' * 70}")
    print("  ИТОГОВАЯ СВОДКА ЗДОРОВЬЯ")
    print(f"{'═' * 70}")
    print(f"{'Зона':<20} {'Статус':<10}")
    print(f"{'─' * 30}")
    for name, ok in all_details:
        icon = "✅" if ok else "❌"
        print(f"{icon} {name:<18} {'OK' if ok else 'ПРОБЛЕМА'}")

    if all_zones_ok:
        print(f"\n{'═' * 70}")
        print("  ✅ ВСЁ ЗДОРОВО — система чиста")
        print(f"{'═' * 70}")
    else:
        print(f"\n{'═' * 70}")
        print("  ⚠️ ЕСТЬ ПРОБЛЕМЫ — смотри зоны выше")
        print(f"{'═' * 70}")

    sys.exit(0 if all_zones_ok else 1)


if __name__ == "__main__":
    main()

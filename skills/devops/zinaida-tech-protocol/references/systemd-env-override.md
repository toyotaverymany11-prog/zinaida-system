# Systemd env override — ключи в .env не работают если есть Environment= в systemd

## Проблема
Systemd-сервисы устанавливают переменные через `Environment=` в `.service` или `.conf` файлах.
Когда Python вызывает `os.environ.setdefault()` — он НЕ перезаписывает эти значения.
В результате роутер использует **мёртвый systemd-ключ** вместо живого из .env.

## Реальный случай (11.07.2026)
- `/opt/zinaida/.env`: `DEEPSEEK_API_KEY=sk-f500991...` (живой, баланс $17.45)
- `/etc/systemd/system/zinaida-core.service.d/env.conf`: `Environment="DEEPSEEK_API_KEY=sk-2805e95...` (мёртвый, 401)
- Роутер через `os.getenv()` получал sk-2805e95... → 402 Insufficient Balance
- Олег показал скриншот DeepSeek Platform с балансом $17.45 — ключ рабочий

## Симптом
`curl /health` роутера показывает префикс ключа, не совпадающий с тем что в .env.

## Фикс
Читать ключи напрямую из .env файла, игнорируя os.getenv():

```python
DEEPSEEK_KEY = ""
for p in ["/opt/zinaida/.env", "/opt/zinaida/meta_agent/.env"]:
    if os.path.exists(p):
        with open(p, "r") as f:
            for line in f:
                if line.startswith("DEEPSEEK_API_KEY") and "=" in line:
                    val = line.split("=", 1)[1].strip()
                    if val and val != "***" and len(val) > 10:
                        DEEPSEEK_KEY = val
                        break
    if DEEPSEEK_KEY:
        break
```

## Затронутые файлы
- `router_8005_v2.py` — ✅ фикс внесён
- `zina2_router.py` — ❌ всё ещё использует os.getenv()

## Связанные навыки
- `devops/provider-audit-reference` — секция «Две проблемы с ключами»
- `devops/production-change-protocol` — протокол безопасных изменений

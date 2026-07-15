# GitHub Tokens Audit (13.07.2026 update)

## Токены (проверены 12.07.2026)

| # | Токен | Аккаунт | Статус | Скорость | Где лежит |
|---|-------|---------|--------|---------|-----------|
| 1 | `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` | toyotaverymany11-prog | ✅ GPT-4o (1.2с), GPT-4o-mini (1.6с) | 🚀 | `secrets.env` → `GITHUB_TOKEN` |
| 2 | `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` | неизвестен | ❌ 401 Bad credentials — **УДАЛЁН** | 💀 | Удалён из всех .env 12.07.2026 |
| 3 | `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` | toyotaverymany11-prog | ✅ GPT-4o (1.3с), GPT-4o-mini (1.4с) | 🚀 | `secrets.env` → `GITHUB_TOKEN_2`, `meta_agent/.env` → `GITHUB_TOKEN` |

## Важно
- Оба живых токена на **один аккаунт** — rate limit ~60 req/min **общий**, не суммируется
- GPT-4o работает за 1.2-1.3с — быстрее DeepSeek Flash (4.5с) в 3-4 раза
- Meta-Llama-3.1-405B-Instruct возвращает HTTP 400 — требует другой формат запроса
- GitHub Copilot (API) — 403, IP заблокирован в РФ

## Где сохранены
- `/opt/zinaida/config/secrets.env` — GITHUB_TOKEN (Токен#1) + GITHUB_TOKEN_2 (Токен#3)
- `/opt/zinaida/meta_agent/.env` — GITHUB_TOKEN (Токен#3) — запасной для 8005 роутера
- Hermes читает из `GITHUB_KEYS` в router_8005_v2.py: грузит оба .env, собирает все строки GITHUB_TOKEN*

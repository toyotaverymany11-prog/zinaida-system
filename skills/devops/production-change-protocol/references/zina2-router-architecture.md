# Zina2-Router Architecture (v1.0)

## Overview
Clean, minimal DeepSeek-only router on port 8003. No bloat, no extra providers.
Created 2026-07-08 as a production-ready alternative to the legacy Zinaida-Router v4.0.

## Key Properties
- **Port:** 8003
- **File:** `/opt/zinaida/meta_agent/zina2_router.py`
- **Service:** `zina2-router.service`
- **API Key:** from `DEEPSEEK_API_KEY` in `/opt/zinaida/.env`
- **Model ID in Hermes:** `Zina2-Router`
- **Provider config key:** `zina2-router`

## Internal Model Selection

### 3 моделей DeepSeek на одном ключе:
| Internal Key | DeepSeek Model ID | When Used |
|---|---|---|
| `flash` | `deepseek-chat` | По умолчанию. Простые/короткие запросы. |
| `pro` | `deepseek-reasoner` | При малейшем намёке на сложность (см. триггеры) |
| `v3` | `deepseek-chat` (alias) | Только через прямой DeepSeek провайдер |

### Pro Trigger Sensitivity (МАКСИМАЛЬНАЯ)
Pro подключается если ЛЮБОЕ из:
- Длина последнего сообщения > 150 символов
- Есть слово-триггер (что, как, почему, анализ, напиши, код, и т.д. — полный список в коде, ~60 слов)
- Есть символы переноса строки или форматирование
- Преобладает латиница (технический запрос)
- НЕ односложное приветствие/подтверждение (привет, да, нет, ок, спасибо)

Flash получает только: привет/пока/да/нет/ок/спасибо/ага/ладно — буквально 1-2 слова.

### Flow:
```
Запрос → _select_model(messages, requested_model)
           ↓
     _should_use_pro(messages)?
      ↓            ↓
    YES           NO
     ↓            ↓
    Pro          Flash
     ↓            ↓
  DeepSeek     DeepSeek
  (reasoner)   (chat)
```

## Deployment
- Systemd service: `zina2-router.service`
- Auto-start: enabled
- Restart: on-failure, 5s delay
- Logs: `journalctl -u zina2-router`

## Testing
```bash
# Quick health
curl -s http://127.0.0.1:8003/health

# Status
curl -s http://127.0.0.1:8003/status

# Sync test
curl -s -X POST http://127.0.0.1:8003/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"Zina2-Router","messages":[{"role":"user","content":"привет"}],"max_tokens":10}'
```

## Version History
- v1.0 (2026-07-08) — Initial. DeepSeek-only, Flash→Pro→V3, max Pro sensitivity.

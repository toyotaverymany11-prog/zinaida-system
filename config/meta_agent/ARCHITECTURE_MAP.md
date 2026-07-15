# 🗺️ КАРТА ПОТОКОВ ДАННЫХ ZINAIDA (MASTER)
# Статус: ОБЯЗАТЕЛЬНО К ЧТЕНИЮ ПЕРЕД ЛЮБОЙ ДИАГНОСТИКОЙ ИЛИ ПРАВКОЙ
# Обновлено: 2026-05-23

## 📍 СЕРВИСЫ И ПОРТЫ
| Сервис | Порт | Файл | Назначение | Статус |
|--------|------|------|------------|--------|
| zinaida-core (proxy) | :8000 | /opt/zinaida/meta_agent/zinaida_openai_proxy.py | Единый прокси с fallback-цепью | 🟢 Работает (Zhipu fallback) |
| zinaida-router | :8002 | /opt/zinaida/meta_agent/zinaida_router.py | Reasoning/Аудит/Стратегия | 🟡 Требует проверки (HTTP:000) |
| grigoriy-router | :8003 | /opt/zinaida/meta_agent/grigoriy_router.py | Код/Исполнение | 🟢 Работает |
| dashboard-api | :8500 | /opt/zinaida/dashboard/dashboard_api.py | UI Песочницы, история, файлы | 🟢 Работает |
| public-api | :8006 | /opt/zinaida/public_api/public_api.py | VK/внешние клиенты (заглушка) | 🟡 Не проброшен в LLM |
| Caddy | :80/:443 | /etc/caddy/Caddyfile | Прокси zinadchdp.duckdns.org → :8500 | 🟢 Работает |

## 🔗 ПОТОКИ ДАННЫХ (DATA FLOW)
1. Браузер (iPad/ноутбук) → HTTPS → Caddy (:443) → :8500 (dashboard_api.py)
2. dashboard_api.py → POST /api/v1/message → :8002 (Зинаида) или :8003 (Григорий)
3. Роутеры → Fallback-цепь: Ollama → GitHub Models → Zhipu → OpenRouter
4. Ответ LLM → JSON → dashboard_api.py → SSE/REST → Браузер
5. Файлы: Браузер → POST /api/v1/upload → /opt/zinaida/sandbox/uploads/ → парсер → knowledge.db (RAG)

## ⛔ ЖЁСТКИЕ ПРАВИЛА ДИАГНОСТИКИ
1. UI-проблема ВСЕГДА начинается с: `grep -rn "fetch\|/api" /opt/zinaida/sandbox/dashboard_v2/modules/*.js`
2. Роутер не отвечает → сначала `ss -tlnp | grep :PORT`, потом `tail -20 /opt/zinaida/logs/...log`, только потом рестарт.
3. Никогда не править YAML/Python через nano/sed. Только полная перезапись файла + `py_compile`.
4. Heredoc только с одинарными кавычками: `cat > file << 'EOF'`
5. Перед любой правкой: бэкап → запись → компиляция → тест → рестарт.
6. Если UI отвечает "Менеджер скоро ответит" → запрос уходит в :8006 (public_api), а не в :8500/:8002. Чинить маршрут, а не код.

## 📦 РЕЗЕРВНЫЕ КОПИИ И ОТКАТ
- Бэкапы роутеров: /opt/zinaida/sandbox/backup_routers_*/
- Бэкапы UI: /opt/zinaida/sandbox/backup_infra_*/
- Откат: `cp backup/file target/file && systemctl restart service`

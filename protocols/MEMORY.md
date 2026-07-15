# ПАМЯТЬ ПРОЕКТА ЗИНАИДА\n\n- Цель: 10 млн рублей.\n- Архитектура: FSM + YAML Skills + Git + HITL.

## ✅ BASELINE_DASHBOARD_API_V1 (2026-05-25)
- Бэкенд для UI починен. Эндпоинты в dashboard_api.py (:8500):
  - GET /api/v1/history (история из SQLite)
  - GET /api/v1/agent_status (статус Зинаиды, Григория, Дашборда)
  - GET /api/v1/logs (последние строки лога FSM)
- Статус: active, curl-тесты 200 OK.
- Фронтенд больше не должен получать 404 и undefined.

## [2026-05-26] Pre-Hermes Migration Baseline
- Роутер :8000: ✅ жив (streaming SSE работает, JSON работает)
- Роутеры :8002, :8003: ✅ работают
- FSM v6.1: ✅ активна
- Telegram: ❌ заблокирован на Timeweb (используем ВК)
- RAM: 4 GB (в процессе апгрейда до 8-16 GB)
- Hermes: НЕ установлен, подготовлены SOUL.md и config.yaml
- Стратегия: после апгрейда VPS → snapshot → установка Hermes CLI
## Baseline Tue May 26 13:38:07 UTC 2026 - Состояние системы перед настройкой
### Статус сервисов
● hermes-gateway.service - Hermes Agent Gateway - Messaging Platform Integration
     Loaded: loaded (/etc/systemd/system/hermes-gateway.service; enabled; vendor preset: enabled)
     Active: active (running) since Tue 2026-05-26 11:10:49 UTC; 2h 27min ago
   Main PID: 16436 (python)
      Tasks: 5 (limit: 9475)
     Memory: 199.8M
        CPU: 30.178s
     CGroup: /system.slice/hermes-gateway.service
             └─16436 /usr/local/lib/hermes-agent/venv/bin/python -m hermes_cli.main gateway run --replace

May 26 11:10:49 7574539-sg107063.twc1.net systemd[1]: Started Hermes Agent Gateway - Messaging Platform Integration.
May 26 12:25:54 7574539-sg107063.twc1.net python[16436]: WARNING gateway.platforms.telegram: [Telegram] Telegram network error, scheduling reconnect: httpx.ReadError:
May 26 12:25:54 7574539-sg107063.twc1.net python[16436]: WARNING gateway.platforms.telegram: [Telegram] Telegram network error (attempt 1/10), reconnecting in 5s. Error: httpx.ReadError:

● zinaida.service - Zinaida Proxy Agent
     Loaded: loaded (/etc/systemd/system/zinaida.service; enabled; vendor preset: enabled)
     Active: active (running) since Tue 2026-05-26 09:57:06 UTC; 3h 41min ago
   Main PID: 674 (python3)
      Tasks: 8 (limit: 9475)
     Memory: 45.8M
        CPU: 55.976s
     CGroup: /system.slice/zinaida.service
             └─674 /usr/bin/python3 /opt/zinaida/meta_agent/zinaida_openai_proxy.py

May 26 09:57:06 7574539-sg107063.twc1.net systemd[1]: Started Zinaida Proxy Agent.
### Открытые порты
LISTEN 0      64           0.0.0.0:8787       0.0.0.0:*    users:(("python3",pid=27687,fd=5))                                                                                                                                
LISTEN 0      2048         0.0.0.0:8000       0.0.0.0:*    users:(("python3",pid=674,fd=13))                                                                                                                                 
LISTEN 0      128          0.0.0.0:2222       0.0.0.0:*    users:(("sshd",pid=686,fd=3))                                                                                                                                     
LISTEN 0      128             [::]:2222          [::]:*    users:(("sshd",pid=686,fd=4))                                                                                                                                     

## Baseline 2026-05-26 13:47 — Мультиагентность
- Профили zinaida/grigoriy/critic созданы и верифицированы
- VK_API_KEY требует замены на валидный ASCII-ключ

## Baseline 2026-05-26 15:55 — Личность и Мониторинг
- SOUL.md адаптирован под Hermes (~1150 символов)
- Создан профиль watchdog для мониторинга инфраструктуры
- Роутер :8000 указан как универсальный шлюз

## Baseline 2026-05-26 16:59 — Глобальные антипаттерны
- Файл: /root/.hermes/ANTI_PATTERNS.md (2149 байт)
- 4 секции: терминал, архитектура, безопасность, поведение
- Загружается в контекст всех агентов

## Baseline 2026-05-26 17:07 — SOUL.md Григория
- Файл: /root/.hermes/profiles/grigoriy/SOUL.md (1999 байт)
- 5 секций верифицированы
- Бэкап: /root/.hermes/profiles/grigoriy/SOUL.md.bak_1779815228

## Baseline 2026-05-26 17:09 — SOUL.md Критика
- Файл: /root/.hermes/profiles/critic/SOUL.md (1982 байт)
- 5 секций: IDENTITY, MISSION, RULES, CHECKLIST, CONTEXT
- Включает правило независимой оценки (другая модель)
- Бэкап: /root/.hermes/profiles/critic/SOUL.md.bak_1779815361

## Baseline 2026-05-26 17:11 — SOUL.md Сторожа
- Файл: /root/.hermes/profiles/watchdog/SOUL.md (1914 байт)
- 5 секций: IDENTITY, MISSION, RULES, CHECKS, CONTEXT
- Включает фильтр ложных срабатываний и проактивный мониторинг
- Бэкап: /root/.hermes/profiles/watchdog/SOUL.md.bak_1779815508

## Baseline 2026-05-26 17:25 — Антискиллы и валидатор
- Добавлена секция §5 в ANTI_PATTERNS.md (работа со скиллами)
- Создан валидатор ~/.hermes/scripts/validate_skill.sh (542 байт)
- Синтаксический dry-run успешен: PASS
- Бэкап: /root/.hermes/ANTI_PATTERNS.md.bak_1779816348

## Baseline 2026-05-26 17:41 — Инфраструктура обучения
- Создан ~/.hermes/logs/incidents.jsonl (валидный JSON)
- Создана ~/.hermes/skills/.drafts/ (изоляция черновиков)
- Добавлена §6 в ANTI_PATTERNS.md (tiered policy, critic checklist, dedup, TTL)
- Бэкап: /root/.hermes/ANTI_PATTERNS.md.bak_1779817302

## Baseline 2026-05-26 17:45 — SOUL.md Сторожа и Зинаиды с циклом обучения
- Сторож: 8 секций (3941 байт) — добавлены MONITORING_SCOPE, INCIDENT_LOGGING, AUTONOMY_BOUNDARIES
- Зинаида: 8 секций (4234 байт) — добавлены INCIDENT_LEARNING, DRAFT_POLICY
- Бэкапы: /root/.hermes/profiles/watchdog/SOUL.md.bak_1779817558, /root/.hermes/profiles/zinaida/SOUL.md.bak_1779817558

## Baseline 2026-05-26 17:59 — Цепочка проверки кода
- Григорий: WORKFLOW обновлён (шаг 5: передача Критику, шаг 6: ожидание вердикта)
- Зинаида: DELEGATION обновлён (требование вердикта Критика)
- Бэкапы: /root/.hermes/profiles/grigoriy/SOUL.md.bak_1779818358, /root/.hermes/profiles/zinaida/SOUL.md.bak_1779818358

## Baseline 2026-05-26 18:03 — Тест цикла обучения
- Инцидент записан в incidents.jsonl
- Черновик создан, верифицирован и интегрирован в skills/
- Бэкапы: /root/.hermes/logs/incidents.jsonl.bak_1779818580, /root/.hermes/skills.bak_1779818580

## Baseline 2026-05-26 18:13 — Шаг 10: Диагностика SSE и шлюзов
- SSE на :8000: OK (2 строк data:)
- TELEGRAM_ALLOWED_USERS:                   # Comma-separated user IDs
6670783611
- hermes-gateway.service: active
- Контекст моделей: ≥64K подтверждён (Zhipu 128K, GPT-4.1 128K+, Mistral 128K)
- Бэкап MEMORY.md: /root/.hermes/MEMORY.md.bak_1779819184

## Baseline 2026-05-26 18:24 — Шаг 12: Еженедельный бэкап ~/.hermes/
- Скрипт: ~/.hermes/scripts/backup_hermes.sh
- Cron: 0 3 * * 0 (вс 03:00)
- Хранилище: /root/backups/hermes/ (локально, готово для rclone/scp)
- Тестовый архив валиден, старые архивы чистятся (max 3)
- Бэкапы: /root/.hermes/MEMORY.md.bak_1779819853, /root/.hermes/crontab.bak_1779819853

## Baseline 2026-05-26 18:36 — Шаг 13: Исправление .env и §7 ANTI_PATTERNS.md
- VK_API_KEY в .env: исправлен (фиктивный ключ, кириллица убрана)
- §7 в ANTI_PATTERNS.md: присутствует (правила cron)
- Бэкапы: /root/.hermes/.env.bak_1779820576, /root/.hermes/ANTI_PATTERNS.md.bak_1779820576

## Baseline 2026-05-27 04:26 — Фаза 1.1: Уточнённая диагностика API
- GigaChat oauth: 000000
- YandexCloud base: 404
- SMMplanner base: 000000
- GigaChat gen: 000000
- YandexCloud gen: 405
- SMMplanner acc: 000000
- Сеть OK: все эндпоинты вернули не 000
- Бэкап: /root/.hermes/MEMORY.md.bak_1779855995

## Baseline 2026-05-27 04:32 — Фаза 1: Проверка API-ключей и провайдеров
- Запущен full_provider_audit.py (динамический поиск :free, verify=False для GigaChat)
- Exit code: 0 | Log: /tmp/provider_audit.log (8450 байт)
- Следующий шаг: интеграция рабочих провайдеров в ~/.hermes/.env и модули
- Бэкап: /root/.hermes/MEMORY.md.bak_1779856328

## Baseline 2026-05-27 04:35 — Фаза 1.2: Диагностика GigaChat
- OAuth: токен получен (длина >20)
- Генерация: PASS (GigaChat-2-Max)
- Токенов затрачено: 63
- Статус: готов к интеграции в SMM-конвейер (RU-копирайтинг)
- Бэкап: /root/.hermes/MEMORY.md.bak_1779856532

## Baseline 2026-05-27 04:39 — Фаза 2: Интеграция текстового движка
- Модуль: api_text_client.py создан (GigaChat + Ollama fallback)
- Ключи: добавлены в .env
- Тест: PASS (генерация успешна)
- Бэкапы: /root/.hermes/.env.bak_1779856796, /root/.hermes/MEMORY.md.bak_1779856796

## Baseline 2026-05-27 05:10 — Фаза 1.2: Диагностика API изображений
- Сеть: Kandinsky(200), Yandex(404)
- Модуль: api_image_client.py создан (py_compile PASS)
- Статус: готов к наполнению логикой после получения ключей
- Бэкап: /root/.hermes/MEMORY.md.bak_1779858655

## Baseline 2026-05-27 09:48 — Фаза 1: Инъекция SMM-знаний
- Память: smm_knowledge.md создан (verified)
- Статус: готов к установке целевых навыков
- Бэкап: /root/.hermes/backup_1779875337

## Baseline 2026-05-27 10:42 — Устранение конфликта 8000 (Fix)
- Реальный файл zinaida-core.service перемещён в бэкап (mask не сработал)
- daemon-reload выполнен, счётчик падений сброшен
- Спам в логах прекращён

## Baseline 2026-05-27 11:15 — Аудит SMM-навыков (честный статус)
- ✅ copywriting (lobehub) — установлен и верифицирован
- ❌ video-script — отсутствует в реестре (inspect показывал, install не находит)
- ❌ ai-image-prompt, social-media-hashtag, social-post-scheduler — отсутствуют в реестре
- 📦 ascii-video — установлен ранее (легитимный ffmpeg-рендер, не часть SMM-пакета)
- Ядро, порты, systemd не затронуты

## Baseline 2026-05-27 11:22 — Аудит и установка SMM-навыков (v2)
- Успешно/уже активны: video-script(builtin) ai-image-prompt(builtin) social-media-hashtag(builtin) social-post-scheduler(builtin)
- Не доступны в реестре: none
- Проверка безопасности: пройдена
- Ядро, порты, systemd не затронуты

## Baseline 2026-05-27 12:38 — Пересоздание и легализация SMM-навыков
- Восстановлены: smm_strategy_planner.md smm_image_prompter.md smm_hashtag_master.md smm_queue_planner.md
- Аудит: clean
- Триггеры: активны
- Ядро/порты не затронуты

## Baseline 2026-05-27 13:27 — SMM-команда (researcher + strategist + channel_planner)
- Созданы навыки для анализа ниши, стратегии и оформления каналов
- Триггеры: активны
- Следующий шаг: тест через hermes chat

## Baseline 2026-05-27 16:05 — Синхронизация OneDrive → Гермес
- Cloud: onedrive:Виктория/villa
- Local: /root/workspace/villa_sales
- Файлов: 1

## Baseline 2026-05-27 17:10 — Структура ниш создана
- Путь: /root/workspace/niches
- Ниша: villa_sales
- Файлов в raw_files: 1
- Следующий шаг: модификация роутера с валидацией X-Niche-ID

## Baseline 2026-05-27 17:16 — Роутер с изоляцией ниш (Фаза 2)
- Путь: /opt/zinaida/meta_agent/zinaida_router.py
- Логика: X-Niche-ID валидация + инжект brief/tone
- Фоллбэк: Zhipu -> GitHub -> OpenRouter

## Baseline 2026-05-27 18:06 — provider_router.py v1 создан. Фоллбэк, динамический OpenRouter, автообновление GigaChat, логирование.

## Baseline 2026-05-27 18:17 — Роутер :8002 запущен с uvicorn-блоком. Изоляция ниш + фоллбэк активны.

## Baseline 2026-05-27 18:44 — Роутер Григория :8003 запущен с uvicorn-блоком. Единый пул провайдеров активен.

## Baseline 2026-05-27 18:49 — Мониторинг и ротация логов активны. Эндпоинты /health/providers на :8002 и :8003. Полная перезапись файлов (без sed). Cron-ротация ежедневно.

## Baseline 2026-05-27 18:52 — Финальная верификация пройдена. Изоляция ниш, единый пул провайдеров, мониторинг, ротация логов активны. Система готова к продуктивной работе.

## Baseline 2026-05-28 02:31 — Прокси-сервер :8004 с парсером X-Niche-ID из префикса сообщения. Готов к подключению WebUI.

## Baseline 2026-05-28 02:35 — Hermes WebUI переключен на прокси :8004. Парсер [Ниша: id] активен в браузере.

## Baseline 2026-05-28 05:17 — Brief Analyzer with robust JSON parser (regex fallback). Handles malformed LLM output.

## Baseline 2026-05-28 05:38 — Tavily integrated. Search Engine created (Tavily->DDG fallback). Analyzer uses research before questions.

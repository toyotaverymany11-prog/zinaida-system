# Hermes Studio Integration with Zinaida-Router

При настройке Hermes Studio для работы с Zinaida-Router — как решать типовые проблемы.

## Типовая проблема: дубликаты моделей в Hermes Studio

Hermes Studio показывает несколько экземпляров одной и той же модели (Zinaida-Router, DeepSeek, Mistral, etc. повторяются N раз в списке).

### Причина
Hermes Studio **сканирует конфиг провайдеров построчно** и регистрирует каждое совпадение как отдельную модель. Если в `~/.hermes/config.yaml` один и тот же провайдер (например, Zinaida-Router) указан в нескольких профилях или повторяется в разных секциях — Studio создаёт дубли.

Дополнительная причина: **роутер сам отдаёт `/v1/models` все модели**, а Hermes Studio также читает модели из config.yaml — наложение двух источников даёт дубли.

### Решение (через UI Studio)

1. **Открой Hermes Studio** (браузер → http://localhost:8080 или на удалённом сервере)
2. Перейди в **Settings → Providers** (или **Admin → Providers**)
3. Найди дублирующихся провайдеров (Zinaida-Router, DeepSeek, etc.)
4. **Удали дубли** — оставь только один экземпляр каждого провайдера
5. **Перезагрузи Hermes Studio:**
   - Нажми кнопку "Reload" / "Refresh" в UI
   - Или перезапусти сервис: `systemctl restart hermes-studio` (если доступно)
6. **Проверь модельный листинг** — дубли должны исчезнуть

### Решение (через CLI)

Если нужно почистить дубли без UI:

```bash
# 1. Найти секцию providers в конфиге Hermes
cat ~/.hermes/config.yaml | grep -A2 -E "provider:|name:.*Zinaida" | head -20

# 2. Проверить, сколько раз Zinaida-Router указан в разных профилях
grep -c "Zinaida-Router" ~/.hermes/config.yaml

# 3. Оставить уникальный провайдер, удалить дубли через patch
# (смотри references/hermes-config-quirks.md — как безопасно редактировать YAML)
```

### Профилактика

При добавлении нового профиля в `~/.hermes/config.yaml`:

1. Не копируй провайдеров из другого профиля — используй `hermes provider set` или добавляй только через файл провайдера
2. Если используешь `inherit` в профиле — провайдеры родителя не дублируются
3. Провайдер Zinaida-Router должен быть указан **ровно один раз** в конфиге, через него работают все модели

## Проверка модельного листинга

После настройки — убедись, что всё работает корректно:

```bash
# 1. Что отдаёт роутер
curl -s http://127.0.0.1:8002/v1/models | python3 -m json.tool | grep '"id"'

# 2. Что видит Hermes Studio (через браузер или API)
curl -s http://localhost:8080/api/models 2>/dev/null | python3 -m json.tool | grep '"id"'

# 3. Сравни списки — не должно быть дублей
```

## Типовая проблема: модель есть в роутере, но не видна в Hermes Studio

### Причины:

1. **Роутер не прописан в конфиге Hermes** — проверь `~/.hermes/config.yaml`:
   ```yaml
   providers:
     - name: Zinaida-Router
       type: openai
       api_base: http://127.0.0.1:8002/v1
       api_key: any # роутер не проверяет ключ
       models:
         - "Zinaida-Router"
         - "deepseek-chat"
         - "mistral"
         # ... остальные модели из роутера
   ```

2. **Модели не добавлены в список models провайдера** — роутер отдаёт `Zinaida-Router` как единую модель, но Hermes Studio может не сканировать `/v1/models` автоматически. Явно перечисли нужные model ID в секции провайдера:
   ```yaml
   models:
     - "Zinaida-Router"
     - "deepseek-chat"
     - "mistral"
     - "gigachat"
     - "zhipu"
     - "github-models"
   ```

3. **Кэш Hermes Studio** — Studio кэширует список моделей. После изменений нужна перезагрузка.

4. **Провайдер в неактивном профиле** — если Zinaida-Router указан в профиле, который не активен, Studio его не видит. Убедись, что нужный профиль выбран:
   ```bash
   hermes profile current  # показать активный профиль
   hermes profile list     # показать все профили
   ```

## Диагностика одним скриптом

```bash
#!/bin/bash
echo "=== Роутер ==="
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://127.0.0.1:8002/v1/models
curl -s http://127.0.0.1:8002/v1/models | python3 -m json.tool 2>/dev/null | grep '"id"' | head -10

echo "=== Hermes Studio ==="
curl -s http://localhost:8080/api/health 2>/dev/null | head -1 || echo "Studio не отвечает на localhost:8080"

echo "=== Config ==="
grep -n "Zinaida" ~/.hermes/config.yaml 2>/dev/null || echo "Zinaida не найдена в конфиге Hermes"
echo "---"
grep -c "Zinaida" ~/.hermes/config.yaml 2>/dev/null
```

## Связанные файлы

- `references/hermes-config-quirks.md` — безопасное редактирование YAML
- `references/pre-flight-diagnostics.md` — диагностика роутера и провайдеров

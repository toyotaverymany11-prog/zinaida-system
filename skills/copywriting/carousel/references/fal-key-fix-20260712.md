# FAL_KEY FIX: image_generate через Hermes
## 12.07.2026 — починено ✅

### Проблема
`image_generate` tool возвращал «FAL_KEY not set» даже при наличии ключа в `/root/.hermes/.env`.

**Причина:** Gateway/воркер Hermes не экспортирует переменные из `.env` в свой процесс.

### Фикс
1. Добавить `export FAL_KEY=...` в `~/.bashrc` и `~/.profile`
2. Экспортировать в текущую сессию: `export FAL_KEY=8e995491-ebb0-4650-8f66-dd0c2dee09ef:4fb8fc63694193ad8463f04ad9b25c1f`
3. Перезапустить Gateway: `npx hermes gateway start --daemon` (в background)
4. Проверить: `image_generate(aspect_ratio="square", prompt="test")`

### Текущий статус
✅ FAL_KEY экспортирован в bashrc/profile, Gateway перезапущен, `image_generate` работает штатно.

### Если сломается снова
Проверить что FAL_KEY есть в окружении процесса:
```bash
echo $FAL_KEY | head -c 10
```
Если пусто — экспортировать заново и перезапустить Gateway.

**Fallback:** прямой curl к queue.fal.run (см. PRODUCTION_PIPELINE.md → ШАГ 4)

### Конфиг модели
```yaml
image_gen:
  provider: fal
  model: fal-ai/gpt-image-2  # для кириллицы
  use_gateway: false
```

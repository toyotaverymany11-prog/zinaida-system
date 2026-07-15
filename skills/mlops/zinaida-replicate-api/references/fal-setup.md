# FAL.ai setup для Hermes (10.07.2026)

## Что сделано
- FAL_KEY сохранён в `/opt/zinaida/.env` и `/opt/zinaida/config/secrets.env`
- SECRETS.md обновлён
- `~/.hermes/config.yaml`: `image_gen.provider: fal`, модель `fal-ai/ideogram/v3`

## Проблема
Аккаунт заблокирован: `User is locked. Reason: Exhausted balance.`
Решение: пополнить баланс на https://fal.ai/dashboard/billing

## Модели для кириллицы
1. `fal-ai/ideogram/v3` — best typography, $0.03-0.09/image, ~5 сек
2. `fal-ai/gpt-image-2` — SOTA text rendering + CJK, $0.04-0.06, ~20 сек
3. `fal-ai/nano-banana-pro` — typography, $0.15, ~8 сек

## Как проверить
После пополнения баланса: `/reset` в чате → `сгенерируй обложку VK 1590×400 с текстом МЕГАМОЗГ`

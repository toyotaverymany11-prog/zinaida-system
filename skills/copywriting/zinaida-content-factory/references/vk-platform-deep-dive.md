# VK (ВКонтакте) — Platform Deep Dive

## 1. Group & Page

| Item | URL | Status |
|------|-----|--------|
| Group | https://vk.com/aipsiholog | ✅ open, 5 subscribers |
| Personal | https://vk.com/zinadchdp | ✅ open |
| Group tokens | `VK_GROUP_TOKEN` in `.env`, `VK_GROUP_ID=aipsiholog` | ✅ saved |

## 2. Formats & Limits

| Parameter | Value |
|-----------|-------|
| Image (post) | 1080×1080 | 
| Image (story) | 1080×1920 |
| Cover (desktop) | 1590×400 |
| Cover (mobile) | 1080×1920 |
| Avatar | 200×200 (circle) |
| Text | up to 15,000 chars |
| Optimal length | 2000-5000 chars |
| Hashtags | 3-5 max |
| Best time | weekdays 19:00-23:00, weekends daytime |

## 3. Shadowban Causes (from VK docs)

### 3.1 Nemezida & Duplicate Content
- If "Описание" text matches "Закреп" (pinned post) by >60% → VK cuts both reach
- **Fix:** Описание sells methodology; Закреп sells instant value. Make them orthogonal.

### 3.2 Stop Words & Clickbait
- ❌ Direct calls to action: "Поставьте лайк", "Поделитесь в комментариях", "Сделайте репост"
- ❌ "Если вам было полезно", "А как это у вас?"
- ❌ Direct "подписывайся" → replace with indirect: "Хочешь разобраться?"
- **Fix:** Transform direct calls into indirect ones. CTA must not use banned phrasing.

### 3.3 Low-Quality Content
- Bad text structure
- No analytical depth
- Emotional/evaluative tone instead of analytical

## 4. Safe Automation (API)

- **App type:** Standalone
- **Token scopes:** groups, photos, wall, offline
- **Posting:** community token with `wall` scope
- **Messaging:** community token with `messages` scope
- **Do NOT use:** SMM Planner, third-party auto-posting services (shadowban risk)
- **Only use:** official VK API via script running on server

## 5. Algospeak for VK

| Original | Algospeak |
|----------|-----------|
| измена / изменяет | смотрит налево |
| секс | близость |
| любовник | другой |
| абьюз | т6ксичное поведение |
| насилие | насил1е |
| суицид | су1цид |
| депрессия | д3прессия |

Source: `/opt/zinaida/inbox/algospeak_dict.json`

## 6. VK Bots on Server

| Bot | Location | Type | Status |
|-----|----------|------|--------|
| vk_bot | `/opt/zinaida/vk_bot/vk_bot.py` | Flask, port 5000, webhooks→n8n | ✅ systemd vkbot.service, running |
| vk_bot_longpoll | `/opt/zinaida/vk_bot/vk_bot_longpoll.py` | Longpoll alt | present |
| vk_public | `/opt/zinaida/vk_public/vk_public_bot.py` | Longpoll, port 8006, vk_api lib | present, uses .env from /opt/zinaida/vk_public/ |
| vk_app | `/opt/zinaida/vk_app/` | Old web chat UI | legacy, not used |

## 7. Post Verifier for VK

Each VK post must pass:
- [ ] No direct calls: "лайкни", "репостни", "подпишись" (use indirect CTA)
- [ ] No stop words from section 3.2 above
- [ ] Image 1080×1080
- [ ] 3-5 hashtags
- [ ] Algospeak checked (source: algospeak_dict.json)
- [ ] Group description ≠ pinned post text (>60% difference needed)
- [ ] Analytical tone, not emotional
- [ ] Шквальный style (16 rules)
- [ ] Blacklist (18 blocks)
- [ ] Tool CTA mapped (1 of 5 tools)
- [ ] Gender: feminine for Zinaida, masculine for Oleg

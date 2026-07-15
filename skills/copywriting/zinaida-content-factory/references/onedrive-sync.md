# OneDrive Sync — Zinaida Content Factory

## CRITICAL: FUSE Mount (Inbox = Live OneDrive)

`/opt/zinaida/inbox` is a **live FUSE mount** of `onedrive:Виктория`.

**You do NOT need to `rclone copy` to OneDrive for anything under /opt/zinaida/inbox/**
Any file written directly to a path like `/opt/zinaida/inbox/Контент/kontent/dizayner/zinaida_passport/generated/dramatic_lighting.png` is **immediately visible on the user's OneDrive** — no rclone sync, no background job, nothing.

### CORRECT workflow for generated assets:
1. Generate images → write directly to `/opt/zinaida/inbox/Контент/kontent/dizayner/zinaida_passport/generated/`
2. The user checks OneDrive on his tablet → files are already there

### WRONG workflow (DO NOT do):
- Save generated images to `/opt/zinaida/design/passport/generated/` — user cannot see them there
- Save to any path outside `/opt/zinaida/inbox/` — user will ask "where are the images?"

### When to actually use rclone copy
Only for files that live outside the inbox mount hierarchy (e.g. `/opt/zinaida/SmmFabrika/assets/` → need explicit copy).

## Mounted Remote

```
rclone config name: onedrive (type: personal OneDrive)
Mount service: rclone-onedrive.service (systemd, active)
FUSE mount target: /opt/zinaida/inbox  (remote: onedrive:/Виктория/)#!/bin/bash

## Key Paths

| Path | Content |
|------|---------|
| `onedrive:/` | Root — contains `Виктория/`, `ИИ/`, `Документы/`, etc. |
| `onedrive:/Виктория/Контент/kontent/` | Main content folder |
| `onedrive:/Виктория/Контент/kontent/dizayner/` | Design assets for Zinaida |
| `onedrive:/Виктория/Контент/kontent/dizayner/zinaida_passport/` | Паспорт лица Зинаиды |
| `zinaida_passport/original/` | Original photos (IMG_0413.PNG, IMG_0415.PNG, IMG_9391.JPG) |
| `zinaida_passport/generated/` | AI-generated rakurse images (push here, not locally) |
| `zinaida_passport/passport.json` | Config for face generation |
| `dizayner/templates/` | Design templates (variant_1_zhurnal.txt, variant_2_tsitata.txt, variant_3_kino.txt) |
| `dizayner/approved/` | Approved final designs |
| `dizayner/oblozhki/` | Cover images |
| `dizayner/test/` | Test variants |
| `dizayner/arkhiv/` | Archive |

## Rclone Config

Config file: `/root/.config/rclone/rclone.conf`
Remote name: `onedrive`
Drive type: personal

> ⚠️ **IMPORTANT**: Files under `/opt/zinaida/inbox/` are already on OneDrive via FUSE mount. Do NOT use `rclone copy` for them — just `cp` or `mv` to the inbox path directly. Only use `rclone copy` for files outside the mount (e.g. `/opt/zinaida/SmmFabrika/assets/`).

## Useful Commands

```bash
# List top-level dirs
rclone lsd onedrive:

# List subdirectory
rclone lsd onedrive:/Виктория/Контент/kontent/

# Tree view
rclone tree onedrive:/Виктория/Контент/kontent/dizayner/

# Copy generated images to sync directory
rclone copy /local/path onedrive:/Виктория/Контент/kontent/dizayner/zinaida_passport/generated/

# Check sync state
systemctl status rclone-onedrive
```

## Rule
Generated AI images for Zinaida's passport should be WRITTEN DIRECTLY to `onedrive:/Виктория/Контент/kontent/dizayner/zinaida_passport/generated/` via rclone, not saved only on the local server. The user checks OneDrive, not the server filesystem.

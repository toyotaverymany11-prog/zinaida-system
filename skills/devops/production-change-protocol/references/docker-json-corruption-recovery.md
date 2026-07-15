# Docker JSON Corruption Recovery (13.07.2026 — Техник 13)

## Context
During n8n cleanup, modified JSON files inside `/var/lib/docker/` to remove n8n references from `repositories.json` and container `config.v2.json`. This broke Docker entirely.

## Symptoms
```log
panic: runtime error: invalid memory address or nil pointer dereference
github.com/moby/moby/v2/daemon.(*Daemon).register(0x...).container.go:92
```
Docker service enters restart loop: `systemctl start docker.service` fails with `exit-code`.

## Root cause
Two independent issues:
1. **repositories.json deleted entirely** — `find /var/lib/docker -name "*n8n*" -exec rm -rf {} +` caught the repositories.json file (which is named `repositories.json`, no "n8n" in name — the rm found nothing, but a subsequent python overwrite that wrote `{}` instead of `{'Repositories': {}}` left it in an invalid state)
2. **Container config.v2.json lost its Name field** — the generic `find /var/lib/docker -type f -name "*.json" | while read f; do python3 -c ... ` script iterated ALL JSON files including container configs. It deleted the `Name` field from a container's config because 'n8n' appeared in the `Image` field (sha256 hash digest that contained "d9296..." — not even 'n8n' text, but the clean-sweep was too broad)

## Resolution

### Step 1: Find the broken container
```bash
for dir in /var/lib/docker/containers/*/; do
  python3 -c "
import json
with open('$dir/config.v2.json') as f:
    d = json.load(f)
if not d.get('Name', ''):
    print(f'BITIY: $dir  ID: {d.get(\"ID\",\"?\")}  Image: {d.get(\"Image\",\"?\")}')
" 2>/dev/null
done
```

### Step 2: Remove the broken container directory
```bash
rm -rf /var/lib/docker/containers/НАЙДЕННЫЙ_ХЕШ/
```

### Step 3: Rebuild repositories.json if missing/corrupt
```bash
python3 -c "
import json
with open('/var/lib/docker/image/overlay2/repositories.json', 'w') as f:
    json.dump({'Repositories': {}}, f)
"
```

### Step 4: Restart Docker
```bash
systemctl reset-failed docker.service
systemctl start docker.service
```

If Docker still fails to start (after these fixes), run `timeout 15 dockerd 2>&1 | grep -E "panic|SIGSEGV"` to identify the exact crash point.

## Prevention
- NEVER `find /var/lib/docker -type f -name "*.json" -exec <modify>` — this is too broad
- Docker internal JSON files have strict schemas — modifying them breaks daemon
- Only legitimate Docker JSON modification: `repositories.json` with correct `{'Repositories': {}}` structure
- Always test Docker restart after any manual /var/lib/docker/ operation
- Keep Redis/Qdrant container run commands ready for recovery: `docker start redis qdrant` / `docker run -d --name redis ...`

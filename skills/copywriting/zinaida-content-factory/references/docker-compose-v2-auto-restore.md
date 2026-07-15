# Docker Compose V2 Auto-Restore (Container Won't Stay Dead)

## Problem
A Docker container with `restart: always` keeps reappearing seconds after `docker stop + docker rm`. No systemd service, no cron job, no watchdog process — yet it resurrects itself.

## Root Cause
**Docker Compose V2** (built into modern Docker CLI) watches docker-compose.yml files. When a container defined in a compose file is deleted, Compose V2 automatically recreates it from the compose definition. This is NOT `restart: always` behavior — `restart: always` only restarts existing containers that crash, it does not recreate destroyed ones.

## Detection
```bash
# 1. Check if container has compose labels
docker inspect <name> --format '{{json .Config.Labels}}' | grep compose

# 2. If NO compose labels — the compose project is not running but the FILE still exists.
#    Search all docker-compose files on the system:
grep -rl "<name>" /opt/ /root/ --include="docker-compose*" --include="compose.*" 2>/dev/null

# 3. Check what services a compose file defines:
docker compose -f /path/to/docker-compose.yml config --services 2>/dev/null

# 4. Check docker events to confirm recreation speed:
docker events --since 1m --format '{{.Time}} {{.Type}} {{.Action}} {{.Actor.Attributes.name}}'
```

## Fix (Order Matters!)
1. **Delete the docker-compose.yml FIRST** — remove the definition so nothing can recreate the container
2. Then stop and remove the container
3. Remove volume and image
4. Clean up stale env vars

```bash
# CORRECT ORDER:
rm -f /path/to/docker-compose.yml                       # 1. Remove definition
docker stop <name> && docker rm <name>                   # 2. Kill container
docker volume rm <name>_data                             # 3. Kill volume
docker rmi <image_name>                                  # 4. Remove image
sed -i '/N8N_API_KEY/d; /N8N_URL/d' ~/.bashrc           # 5. Clean env vars (if applicable)
```

## Verification
```bash
docker ps -a --format "{{.Names}}" | grep <name>  # Should be empty
ss -tlnp | grep <port>                              # Port should be free
# Wait 2+ minutes and re-check — if still gone, it's permanent
sleep 120 && docker ps -a | grep <name>
```

## Real-World Example
The n8n container at `/opt/openclaw/docker-compose.yml` defined service `n8n` with `restart: always`. Every time it was deleted via `docker rm`, Docker Compose V2 recreated it within 9 seconds. Fix: removed the compose file, then stopped+removed the container, volume, and image. Gone permanently.

## Key Lesson
**Don't just `docker rm` — check what OWNS the container definition first.** If there's a docker-compose.yml anywhere, that's the source of truth, not Docker's runtime state. Delete the compose file to kill the container permanently.

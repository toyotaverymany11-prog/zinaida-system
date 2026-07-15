# GitHub Tokens Audit (12.07.2026)

## Live tokens

Both stored in `/opt/zinaida/config/secrets.env`:

```
GITHUB_TOKEN=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
GITHUB_TOKEN_2=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
```

- **Account:** toyotaverymany11-prog (same account, tokens are redundant)
- **Tested (12.07.2026):** gpt-4o ✅ (1.2s), gpt-4o-mini ✅ (1.4s)
- **Base URL:** `https://models.inference.ai.azure.com/chat/completions?api-version=2024-10-21`
- **Rate limit:** ~60 req/min

## Dead tokens (removed)

```
GREG_GITHUB_TOKEN=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  → 401 Bad credentials
```

Removed from `/opt/zinaida/meta_agent/.env` on 12.07.2026. Replaced with comment `# GREG_GITHUB_TOKEN=... (dead 401)`.

## Storage locations (for code)

Router 8005 reads GitHub keys from:
1. `/opt/zinaida/config/secrets.env` (main)
2. `/opt/zinaida/meta_agent/.env` (fallback, only GITHUB_TOKEN remains)

```python
GITHUB_KEYS = []
for env_path in [Path("/opt/zinaida/config/secrets.env"), Path("/opt/zinaida/meta_agent/.env")]:
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("GITHUB_TOKEN") and "=" in line:
                    val = line.split("=", 1)[1].strip().strip("'\"")
                    if val and val not in ("***", "") and len(val) > 10:
                        GITHUB_KEYS.append(val)
```

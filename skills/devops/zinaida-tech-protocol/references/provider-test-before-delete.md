# Provider Test-Before-Delete Workflow

## Lesson (11.07.2026)
Олег: «а ты уверена блядь что ты правильно там всё делаешь там же у всех свои хитрости»

## Protocol: How to safely verify a provider before deleting

### Step 1: Check config entry
```bash
grep -B2 -A10 'provider_name' /root/.hermes/config.yaml
```
Note whether it's a built-in provider (no custom: prefix) or custom (has custom: prefix + base_url).

### Step 2: Make a real test call via Hermes Studio
Don't just check the config — actually send a request:
```python
from hermes_tools import call Hermes Studio MCP tools
# Use hermes_studio_use_chat_run with that specific model
result = mcp_hermes_studio_use_chat_run(
    input="Ответь одним словом: тест",
    model="model-id",
    provider="provider-key",
    timeout_ms=30000
)
```

If result has `error` key — provider is broken (missing key, 403, 401).
If result succeeds — provider works, keep it.

### Step 3: Determine why it's broken
| Error | Meaning | Action |
|-------|---------|--------|
| `no API key was found. Set the ... environment variable` | Key not configured | Delete from Hermes, or configure key |
| `403` / `IP blocked` | Region-locked (GitHub Copilot in РФ) | Delete from Hermes |
| `401` / `402` | Key expired / out of credits | Delete from Hermes (get new key later) |
| Timeout > 30s | Service unreachable | Check region/network, then delete if confirmed dead |

### Step 4: Safe deletion
Always use MCP API, NOT config.yaml editing:
```python
mcp_hermes_studio_use_provider_delete(
    pool_key="provider-name",  # or custom:provider-name
    profile="default"
)
```

### Copilot specific (discovered 11.07.2026)
- Provider name in Hermes: `copilot`
- Requires: `COPILOT_GITHUB_TOKEN` environment variable
- Token: GitHub Personal Access Token with Copilot permissions
- Without token: `Provider 'copilot' is set in config.yaml but no API key was found`
- In РФ: may also get 403 if GitHub Copilot is blocked
- Removed from Hermes Studio via MCP API: ✅ success

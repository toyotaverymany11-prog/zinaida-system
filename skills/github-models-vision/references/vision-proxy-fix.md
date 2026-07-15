# Vision proxy architecture (expanded)
## Overview
Ollama Cloud Fallback Proxy — automatic 401 retry across 3 keys + auto-resize for large images.

## Components
- Proxy: `/opt/zinaida/scripts/ollama_fallback_proxy.py` (port 8900)
- Service: `ollama-proxy.service` (systemd)
- Keys: 3 in `/opt/zinaida/config/secrets.env` (OLLAMA_API_KEY_1/2/3)
- Model: gemma3:27b via Ollama Cloud

## Key fix: auto-resize
The proxy now resizes images >1024px to 1024px and converts PNG→JPEG (quality 80) when base64 exceeds 512KB. This fixes "invalid JSON" 400 errors from Ollama when sending large PNG screenshots.

Also increased aiohttp `client_max_size` to 50MB to prevent "Request Entity Too Large" on large requests.

## Config in Hermes
```yaml
vision:
  provider: ollama
  model: gemma3:27b
  base_url: http://127.0.0.1:8900
  api_key: proxy
  timeout: 120
```

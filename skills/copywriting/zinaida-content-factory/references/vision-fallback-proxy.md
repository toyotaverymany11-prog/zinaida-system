# Vision Fallback Proxy (GitHub → Ollama)

Прокси на порту 8901. Установлен как systemd-сервис `vision-proxy.service`.

```
GitHub Models (gpt-4o-mini) → Ollama Cloud (gemma3:27b, 3 ключа)
```

При ошибке GitHub → автоматический fallback на Ollama с перебором ключей.
Старый прокси (8900, только Ollama) — резервный, работает.

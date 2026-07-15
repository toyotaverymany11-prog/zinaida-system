# Быстрые команды: роутер 8005

## Управление systemd
```bash
systemctl status|start|stop|restart zina2-router-8005.service
journalctl -u zina2-router-8005.service --no-pager -n 50
```

## Статус
```bash
curl -s http://127.0.0.1:8005/health | python3 -m json.tool
```

## Модели
```bash
curl -s http://127.0.0.1:8005/v1/models | python3 -m json.tool
```

## Запустить
```bash
cd /opt/zinaida/meta_agent && python3 router_8005_v2.py 2>/tmp/router_8005.log
```

## Логи
```bash
cat /tmp/router_8005.log | grep -E "CLASSIFY|DEEPSEEK|OLLAMA|VERIFY|POLISH|FALLBACK|OK|ERROR" | tail -20
```

## Тест
```bash
curl -s -X POST http://127.0.0.1:8005/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"8005-Router","messages":[{"role":"user","content":"привет"}],"max_tokens":10}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['model'], d['choices'][0]['message']['content'][:50])"
```

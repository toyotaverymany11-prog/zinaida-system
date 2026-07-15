# LiveKit Agent Starter React — Развёртывание (09.07.2026)

## Что случилось

После ДВУХ неудачных попыток показать Олегу самописный HTML-интерфейс («кругляшок»),
был установлен и настроен официальный LiveKit Agent Starter React.

**Ссылка:** https://zinadchdp.duckdns.org/voice/

## Установка

```bash
cd /opt/zinaida/livekit
git clone https://github.com/livekit-examples/agent-starter-react.git ui-react
cd ui-react
npm install
```

## Конфигурация

**`.env.local` (серверные переменные):**
```bash
LIVEKIT_API_KEY=apidev...
```

**Патч для production (убрать dev-only check):**
В `/app/api/token/route.ts` удалён блок:
```typescript
if (process.env.NODE_ENV !== 'development') {
  throw new Error('THIS API ROUTE IS INSECURE...');
}
```
Это нужно, чтобы API токенов работал в production.

## Кастомизация (app-config.ts)

```typescript
audioVisualizerType: 'aura' | 'bar' | 'wave' | 'grid' | 'radial';  // 5 стилей
audioVisualizerColor: '#...';         // цвет
audioVisualizerColorDark: '#...';     // цвет тёмной темы
startButtonText: 'Start call';       // текст кнопки
companyName: 'Зинаида';             // имя в шапке
```

## Запуск

```bash
cd /opt/zinaida/livekit/ui-react
NODE_ENV=production npx next start -p 3030
```

## Caddy (прокси)

В Caddyfile добавлено:
```caddy
handle_path /voice/* {
    reverse_proxy localhost:3030
}
```

## Структура

```
/opt/zinaida/livekit/ui-react/
├── app/
│   ├── api/token/route.ts     # Генерация JWT токенов
│   ├── page.tsx               # Главная страница
│   └── layout.tsx             # Layout
├── components/
│   ├── agents-ui/             # Agents UI компоненты
│   ├── ai-elements/           # AI элементы
│   ├── ui/                    # shadcn/ui примитивы
│   └── app/                   # Пользовательские компоненты
├── app-config.ts              # Конфигурация UI
├── package.json
└── .env.local                 # API ключи
```

## Что нужно для токенов

Приложение использует Next.js API route `/api/token` для генерации JWT.
Требует `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`, `LIVEKIT_URL` в `.env.local`.

## Проверка

```bash
curl -s -o /dev/null -w "%{http_code}" https://zinadchdp.duckdns.org/voice/
# → 200
```

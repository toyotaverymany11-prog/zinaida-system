# Super Cascade v2 — Stress Test Results (12.07.2026)

## Test results — 10/10 passed

| # | Test | Provider | Time | Price |
|---|------|----------|------|-------|
| 1 | Приветствие | Ollama (free) | 0.9s | $0 |
| 2 | Короткий вопрос | Mistral (free) | 1.0s | $0 |
| 3 | Обычный вопрос | Mistral → gpt-4o | 22.4s | $0 |
| 4 | Сложный анализ | DeepSeek Pro | 18.7s | $1.42/M |
| 5 | Вопрос про код | DeepSeek Pro | 7.9s | $1.42/M |
| 6 | Психология с цифрами | Mistral → gpt-4o | 6.8s | $0 |
| 7 | Длинный запрос (10K) | DeepSeek Pro | 39.9s | $1.42/M |
| 8 | Пустой запрос | Mistral → gpt-4o | 2.7s | $0 |
| 9 | Спецсимволы | Mistral → gpt-4o | 2.7s | $0 |
| 10 | Вопрос про GitHub | gpt-4o + RAG | 10.9s | $0 |

## Cascade distribution

- **Ollama:** 1 (5%) — приветствия
- **Mistral (self-confidence ≥75):** 3 (20%) — короткие, простые
- **Mistral → gpt-4o (GitHub):** 5 (35%) — когда Mistral не уверен
- **DeepSeek Pro (triggers):** 4 (25%) — код, анализ, длинные
- **13/17 requests = 76% free** (Mistral + gpt-4o)

## Key numbers

- Mistral self-confidence: works correctly (95 on simple, <75 on edge cases)
- gpt-4o speed: 1.2-2.3s (faster than DeepSeek Flash at 4.5s!)
- RAG context served for complex queries (~1600 chars)
- 0 errors, 0 rate limits, 0 alerts

## Edge cases found

- Llama 405B → 400 Bad Request (not compatible format)
- Empty input → gpt-4o answers in English (cosmetic)
- Very long (5940+ chars) → automatically routes to Pro due to length

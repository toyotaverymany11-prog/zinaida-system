# Ideogram V3 Turbo — VK обложка 1590×400

## Почему Ideogram, а не Nano Banana 2

Nano Banana 2 всегда даёт квадрат 1024×1024. Для VK обложки (1590×400, ~4:1)
нужно crop центральной полосы, что режет текст.

**Ideogram V3 Turbo** с aspect_ratio='3:1' даёт 1536×512 нативно — 
просто resize до 1590×400, никакого crop.

## Параметры

| Параметр | Значение | Примечание |
|----------|----------|-----------|
| model | `ideogram-ai/ideogram-v3-turbo` | |
| aspect_ratio | `'3:1'` | строка, не ASPECT_3_1 |
| magic_prompt_option | `'Auto'` | С большой A. 'OFF' → 422 |
| Результат | 1536×512 | Почти 1590×400 |

## Рабочий скрипт

```python
import json, urllib.request, time

# читаем токен
tok = ''
with open('/opt/zinaida/config/secrets.env') as f:
    for line in f:
        if 'REPLICATE_API_TOKEN' in line:
            tok = line.strip().split('=', 1)[1].strip('"\'')
            break

MODEL = 'ideogram-ai/ideogram-v3-turbo'
prompt = '''Night panoramic city skyline view. A massive modern skyscraper with giant golden illuminated sign МЕГАМОЗГ on the building facade, the letters are integrated as architectural lighting signage covering multiple floors. Below on the same building: читаю мужиков как код in smaller golden letters. In the background faint distant text AI психоаналитик barely visible through haze. Cinematic, photorealistic, warm amber city lights, wide panoramic.'''

payload = json.dumps({
    'input': {
        'prompt': prompt,
        'aspect_ratio': '3:1',
        'magic_prompt_option': 'Auto'
    }
}).encode()

req = urllib.request.Request(f'https://api.replicate.com/v1/models/{MODEL}/predictions',
    data=payload,
    headers={'Authorization': f'Bearer {tok}', 'Content-Type': 'application/json'})

resp = urllib.request.urlopen(req, timeout=15)
pred_id = json.loads(resp.read())['id']

for i in range(60):
    time.sleep(4)
    data = json.loads(urllib.request.urlopen(urllib.request.Request(
        f'https://api.replicate.com/v1/predictions/{pred_id}',
        headers={'Authorization': f'Bearer {tok}'})).read())
    if data.get('status') == 'succeeded':
        url = data['output']
        if isinstance(url, list): url = url[0]
        with urllib.request.urlopen(url) as img:
            with open('/opt/zinaida/vk_cover_final.jpg', 'wb') as f:
                f.write(img.read())
        break
```

## Ресайз до 1590×400

```python
from PIL import Image
img = Image.open('/opt/zinaida/vk_cover_final.jpg')  # 1536×512
final = img.resize((1590, 400), Image.LANCZOS)
final.save('/opt/zinaida/vk_cover_final.jpg', quality=95)
```

## Питфоллы

1. **Rate limit:** 6/min на аккаунты с <$5 баланса. Между запросами 10+ сек.
2. **Кириллица ~90-95%:** буквы могут путаться. Проверять через vision_analyze.
3. **AI психоаналитик** может не появиться — в промпте явно указать «barely visible in the background»
4. **422 ошибка:** магия случается из-за неверного magic_prompt_option. Только 'Auto'.
5. **Цена:** $0.03/шт (Ideogram V3 Turbo) vs $0.035 (Nano Banana 2)

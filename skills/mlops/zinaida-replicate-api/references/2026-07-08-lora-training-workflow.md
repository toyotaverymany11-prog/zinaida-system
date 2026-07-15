# LoRA Training Workflow на Replicate — проверено 2026-07-08

## Процесс

### 1. Подготовка фото
- 7+ фото в одинаковом формате (JPEG, 1024px по большей стороне)
- Переименовать в zinaida_01.jpg ... zinaida_N.jpg
- **Важно:** фото должны быть в одном формате! PNG+JPG в одном zip = проблемы.
- Упаковать в zip: `cd /tmp/photos && zip -r /tmp/training.zip .`

### 2. Загрузить zip на Replicate через Files API
```python
import urllib.request, json

with open('/opt/zinaida/config/secrets.env') as f:
    for line in f:
        if 'REPLICATE_API_TOKEN' in line:
            token = line.strip().split('=', 1)[1]
            break

boundary = '----Boundary'
with open('/tmp/training.zip', 'rb') as f:
    file_data = f.read()

body = []
body.append(f'--{boundary}'.encode())
body.append(b'Content-Disposition: form-data; name="content"; filename="photos.zip"')
body.append(b'Content-Type: application/zip')
body.append(b'')
body.append(file_data)
body.append(f'--{boundary}--'.encode())
body_bytes = b'\r\n'.join(body)

req = urllib.request.Request(
    'https://api.replicate.com/v1/files',
    data=body_bytes,
    headers={
        'Authorization': f'Bearer {token}',
        'Content-Type': f'multipart/form-data; boundary={boundary}'
    }
)
resp = urllib.request.urlopen(req, timeout=30)
d = json.loads(resp.read())
url = d.get('urls', {}).get('get', '').strip()
print(url)  # Чистая ссылка, без переносов!
```

### 3. Дать ссылку пользователю
Ссылку давать ОТДЕЛЬНОЙ СТРОКОЙ, без пробелов и переносов в конце.
Иначе при копировании из чата добавляется `%0A` (newline) → 404 Not Found.

Пример: `https://api.replicate.com/v1/files/XXX.zip`

### 4. Обучение через fast-flux-trainer
- Страница: https://replicate.com/replicate/fast-flux-trainer/train
- destination: создать новую модель, например `zinaida/zinaida-face-lora`
- input_images: вставить ссылку из шага 3
- trigger_word: **ZINAIDA** (латиница, капсом, никаких русских букв и пробелов!)
- lora_type: subject
- training_steps: 1000 (нормально, ~$1.46)
- Стоимость: ~$1.46

### 5. Использование обученной модели
```python
import replicate
output = replicate.run(
    "owner/model:version_hash",
    input={"prompt": "ZINAIDA, ...", "guidance_scale": 2.5}
)
```

### Проблемы

#### Проблема: %0A в URL
Ссылка с Replicate Files API заканчивается на `.zip`. При копировании из чата может добавиться `\n` → URL становится `XXX.zip%0A` → 404.
**Решение:** давать ссылку отдельной строкой в отдельном сообщении.

#### Проблема: FileOutput
replicate Python библиотека возвращает FileOutput, не строку. Нельзя обращаться как к списку.
**Решение:** прямые HTTP запросы (см. zinaida-replicate-api skill)

#### Проблема: 429 Rate Limit
После быстрой серии генераций Replicate возвращает 429.
**Решение:** пауза 10+ секунд между запросами, при 429 ждать 60 секунд.

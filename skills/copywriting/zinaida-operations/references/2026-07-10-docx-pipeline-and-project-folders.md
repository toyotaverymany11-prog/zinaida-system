# Пакетная обработка docx-файлов от Олега — pipeline

## Когда использовать
- Олег присылает 3+ .docx/.txt файлов и говорит «разбери, добавь в проект, распредели по папкам»

## Протокол (3 шага)

### Шаг 1: Извлечение текста

```bash
pip install python-docx -q

python3 << 'PYEOF'
from docx import Document
import os

outdir = "/tmp/docx_extracted"
os.makedirs(outdir, exist_ok=True)

files = [...]  # список путей

for fpath in files:
    fname = os.path.basename(fpath)
    try:
        doc = Document(fpath)
        text = "\n".join(p.text for p in doc.paragraphs)
        outpath = os.path.join(outdir, fname.replace(".docx", ".txt"))
        with open(outpath, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"✅ {fname}: {len(text)} символов")
    except Exception as e:
        print(f"❌ {fname}: {e}")
PYEOF
```

### Шаг 2: Делегировать анализ subagent-у

Subagent читает каждый файл (большие — по частям через offset/limit) и возвращает:
1. Что нового в файле (чего нет в папке назначения)
2. Что дублируется
3. Что добавить и куда

### Шаг 3: Распределить

- Новое → patch/update существующих файлов в папке проекта
- Дубли → пропустить
- Шелуха → не добавлять

**Типовые ошибки:**
- Не читать файлы целиком в основном контексте — делегировать subagent-у
- Большие файлы (100K+) читать частями (offset+limit по 200 строк)
- После распределения проверить итог: wc -l и du -sh

---

## Формат папки проекта (шаблон)

```
/opt/zinaida/projects/{Project}/{Theme}/
├── 00_README.md    — выжимка, правила, ссылки
├── 01_*.md         — специфичные файлы темы
├── ...
├── 04_approved/    — утверждённые файлы
└── 05_notes/       — журнал изменений (опционально)
```

**Правило:** файлы нумеруются 00, 01, 02... для детерминированного порядка загрузки.
При старте чата читается вся папка целиком.

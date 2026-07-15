# Процедура: перенос задания от AI-агента (Abacus) на сервер

**Дата:** 2026-07-11
**Источник:** Abacus AI Agent (веб-интерфейс) → Задание Гермесу на сервер

## Контекст

В этой сессии Abacus AI Agent (другой LLM в веб-интерфейсе) написал задание для Гермеса. Задача была: проанализировать две системы на сервере и написать план объединения.

Abacus сгенерировал Python-код, который:
1. Подключается по SSH к серверу
2. Создаёт файл `/opt/zinaida/TASK_FOR_HERMES.md` с заданием
3. Проверяет что файл создан

## Как это работает

```python
import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(host, port=port, username=user, password=password, timeout=30)

# Создать файл с заданием
chan = client.get_transport().open_session()
chan.exec_command("cat > /opt/zinaida/TASK_FOR_HERMES.md")
chan.sendall(task.encode())
chan.shutdown_write()
chan.recv_exit_status()

# Проверить
stdin, stdout, stderr = client.exec_command("wc -l /opt/zinaida/TASK_FOR_HERMES.md")
print(stdout.read().decode())

client.close()
```

## Структура задания

Задание оформляется как Markdown-файл:

```markdown
# ЗАДАНИЕ ДЛЯ ГЕРМЕСА — [НАЗВАНИЕ]
> Автор: [кто] | Дата: [дата]
> Приоритет: ВЫСОКИЙ
> Выход: один файл `/opt/zinaida/OUTPUT_FILE.md`

## ЗАДАЧА
[описание проблемы]

## ЧТО НУЖНО СДЕЛАТЬ
### 1. ПРОЧИТАЙ
[список файлов]

### 2. НАЙДИ
[что искать]

### 3. НАПИШИ файл `/opt/zinaida/OUTPUT_FILE.md`
[структура выходного файла]

## ОГРАНИЧЕНИЯ
- [что НЕ трогать]
```

## Требования к заданию

- Чёткие ограничения (что нельзя трогать)
- Конкретный выходной файл (один)
- Список файлов для чтения
- Структура выходного файла
- Приоритет

## Когда этот подход уместен

- Когда задача слишком большая для одного чата
- Когда нужно чтобы Гермес работал автономно, без контроля
- Когда задание пришло от внешнего AI-агента и его нужно перенести на сервер

#!/usr/bin/env python3
"""
ШАБЛОН: чтение API-ключей из .env (доказано работает)
Проблема: os.environ.setdefault() не перезаписывает systemd-переменные.
os.getenv() может вернуть мёртвый ключ из systemd вместо живого из .env.

Фикс: читать напрямую из файла, игнорируя os.environ.
"""
import os
from pathlib import Path

def read_key_from_env(key_name: str, env_paths: list = None) -> str:
    """
    Читает API-ключ напрямую из .env файлов.
    Игнорирует systemd Environment= и os.environ.
    
    Args:
        key_name: Имя переменной (DEEPSEEK_API_KEY, MISTRAL_API_KEY и т.д.)
        env_paths: Список путей к .env файлам
    
    Returns:
        Значение ключа или пустую строку
    """
    if env_paths is None:
        env_paths = [
            Path("/opt/zinaida/.env"),
            Path("/opt/zinaida/meta_agent/.env"),
        ]
    
    for p in env_paths:
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith(key_name) and "=" in line:
                        val = line.split("=", 1)[1].strip()
                        if val and val != "***" and len(val) > 10:
                            return val
    return ""

# Пример использования:
# DEEPSEEK_KEY = read_key_from_env("DEEPSEEK_API_KEY")
# MISTRAL_KEYS = [
#     read_key_from_env("MISTRAL_API_KEY"),
#     read_key_from_env("MISTRAL_API_KEY_2"),
# ]
# OLLAMA_KEYS = [
#     read_key_from_env("OLLAMA_API_KEY"),
#     read_key_from_env("OLLAMA_API_KEY_2"),
#     read_key_from_env("GREG_OLLAMA_KEY"),
# ]
# GIGA_KEY = read_key_from_env("GIGA_AUTH_KEY") or read_key_from_env("GIGACHAT_AUTH_KEY")

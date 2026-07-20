import os
import openai
from pathlib import Path

# Инициализация клиента LiteLLM Proxy
llm_client = openai.OpenAI(
    base_url="http://localhost:4000",
    api_key="sk-zinaida-2026"  # master_key из конфига
)

# Загрузка переменных окружения (на всякий случай)
ENV_PATH = Path("/opt/zinaida/.env")
if ENV_PATH.exists():
    with open(ENV_PATH, "r") as f:
        for line in f:
            if "=" in line and not line.startswith("#"):
                key, value = line.strip().split("=", 1)
                os.environ.setdefault(key, value)

# Код-триггеры для определения типа задачи
CODE_TRIGGERS = ["код", "скрипт", "функция", "класс", "алгоритм", "python", "исправь", "напиши скрипт", "создай файл"]

def is_code_request(text: str) -> bool:
    """Определяет, требует ли запрос генерации кода"""
    return any(t in text.lower() for t in CODE_TRIGGERS)

def call_llm(prompt: str, system_prompt: str = "", task_type: str = "chat", timeout: int = 30) -> str:
    """
    Вызывает LLM через LiteLLM Proxy с автоматическим fallback
    
    Args:
        prompt: Текст запроса
        system_prompt: Системный промпт (личность)
        task_type: "chat" | "code" | "analysis"
        timeout: Таймаут в секундах
    
    Returns:
        Ответ модели
    """
    try:
        # Выбираем модель по типу задачи
        if task_type == "code":
            model_name = "grigoriy-primary"
        elif task_type == "analysis":
            model_name = "zinaida-backup"  # GPT-4 лучше для анализа
        else:
            model_name = "zinaida-primary"
        
        # Формируем сообщения
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        # Вызываем через LiteLLM (автоматический fallback!)
        response = llm_client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=0.7,
            max_tokens=1500,
            timeout=timeout
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Ошибка LLM ({model_name}): {error_msg[:100]}")
        
        # Пробуем fallback вручную если основная упала
        if "zinaida-primary" in model_name:
            try:
                print("🔄 Fallback на zinaida-backup...")
                messages = [{"role": "user", "content": prompt}]
                if system_prompt:
                    messages.insert(0, {"role": "system", "content": system_prompt})
                
                response = llm_client.chat.completions.create(
                    model="zinaida-backup",
                    messages=messages,
                    temperature=0.7,
                    max_tokens=1500,
                    timeout=40
                )
                return response.choices[0].message.content
            except Exception as fallback_error:
                print(f"❌ Fallback тоже упал: {str(fallback_error)[:100]}")
        
        return f"❌ Ошибка модели: {error_msg[:200]}"

# Тест при запуске
if __name__ == "__main__":
    print("--- Тест LiteLLM Proxy ---")
    resp = call_llm("Скажи коротко: Тест пройден.", system_prompt="Ты помощник.")
    print(f"Ответ: {resp}")

import os
from openai import OpenAI

# Инициализация клиента LiteLLM Proxy (порт 4000)
# Используем локальный URL, так как LiteLLM запущен рядом
LITELLM_URL = "http://localhost:4000"
LITELLM_KEY = "sk-zinaida-2026"

client = OpenAI(base_url=LITELLM_URL, api_key=LITELLM_KEY)

# --- Ключевые слова для определения типа задачи ---
CODE_TRIGGERS = ["код", "скрипт", "функция", "напиши", "исправь", "ошибка", "python", "bash", "js", "json", "html", "sql", "debug", "рефакторинг", "алгоритм"]
ANALYSIS_TRIGGERS = ["анализ", "почему", "объясни", "сравни", "продумай", "план", "стратегия", "список", "идея"]

def analyze_complexity(query: str) -> str:
    """
    Определяет маршрут запроса.
    Возвращает имя модели из LiteLLM конфига.
    """
    query_lower = query.lower()
    
    # 1. Проверка на код (отдаем Григорию или мощной кодер-модели)
    if any(t in query_lower for t in CODE_TRIGGERS):
        return "grigoriy-primary"  # Отдаем специализированной модели/агенту
        
    # 2. Проверка на сложность/анализ
    if any(t in query_lower for t in ANALYSIS_TRIGGERS):
        # Если запрос длинный, это тоже признак сложности
        if len(query) > 150:
            return "zinaida-primary" # Мощная модель для длинных мыслей
        return "zinaida-primary" # Аналитика требует ума

    # 3. Если ничего не подошло — это "болтовня" или простой запрос
    return "zinaida-backup" # Дешевая и быстрая модель

def get_smart_reply(prompt: str, system_prompt: str = "") -> str:
    """
    Главная функция.
    1. Анализирует запрос.
    2. Выбирает модель.
    3. Вызывает LiteLLM.
    """
    # Определяем, куда летит запрос
    target_model = analyze_complexity(prompt)
    
    # Формируем сообщения
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    print(f"🧠 SmartRouter -> Выбираю маршрут: {target_model} для запроса: '{prompt[:50]}...'")
    
    try:
        # Вызываем через LiteLLM Proxy
        # LiteLLM сам разберется, какую реальную модель (Zhipu/GitHub) использовать 
        # на основе настройки model_name в конфиге
        response = client.chat.completions.create(
            model=target_model,
            messages=messages,
            temperature=0.7,
            max_tokens=2000
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"❌ Ошибка SmartRouter: {e}")
        return f"❌ Ошибка при обработке запроса: {e}"

# Тест при запуске напрямую
if __name__ == "__main__":
    print("--- Тест SmartRouter ---")
    print(get_smart_reply("Напиши скрипт на Python для парсинга", system_prompt="Ты помощник."))
    print(get_smart_reply("Почему небо синее?"))
    print(get_smart_reply("Привет, как дела?"))

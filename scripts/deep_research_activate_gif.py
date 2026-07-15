#!/usr/bin/env python3
"""Анимированный GIF для глубокого исследования"""
from PIL import Image, ImageDraw, ImageFont
import os

W, H = 800, 500
frames = []

try:
    font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 44)
    font_med = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 26)
    font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
    font_tiny = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
except:
    font_large = font_med = font_small = font_tiny = ImageFont.load_default()

# Агенты
agents = [
    ("🔍 Mistral", "Поиск в интернет"),
    ("⚡ GitHub", "Анализ кода"),
    ("🤖 Ollama", "Локальный поиск"),
    ("🧠 DeepSeek", "Синтез отчёта"),
]

# Цветовая схема - фиолетово-розовая (научная)
for frame_i in range(12):
    img = Image.new('RGB', (W, H), (15, 10, 35))
    draw = ImageDraw.Draw(img)
    
    # Пульсирующий цвет
    phase = frame_i / 12
    r = int(150 + 80 * (0.5 + 0.5 * (phase * 3.14159 * 2)))
    g = int(50 + 30 * (0.5 + 0.5 * ((phase + 0.33) * 3.14159 * 2)))
    b = int(200 + 55 * (0.5 + 0.5 * ((phase + 0.66) * 3.14159 * 2)))
    accent = (min(r,255), min(g,255), min(b,255))
    
    # Фоновые "звёзды" - данные
    for i in range(20):
        sx = int(50 + (i * 37 + frame_i * 13) % (W - 100))
        sy = int(50 + (i * 53 + frame_i * 7) % (H - 100))
        size = ((i % 3) + 1)
        draw.ellipse([(sx, sy), (sx + size, sy + size)], fill=(accent[0]//3, accent[1]//3, accent[2]//3))
    
    # Верхняя полоса
    draw.rectangle([(0, 0), (W, 4)], fill=accent)
    
    # Заголовок
    draw.text((W//2, 55), "🔬 ГЛУБОКОЕ ИССЛЕДОВАНИЕ", fill=(255, 255, 255), font=font_large, anchor="mt")
    
    # Подзаголовок
    draw.text((W//2, 95), "Deep Research - мультиагентный анализ", fill=accent, font=font_small, anchor="mt")
    
    # Линия
    draw.line([(100, 115), (W-100, 115)], fill=accent, width=1)
    
    # Блок с агентами
    box_y = 145
    draw.rounded_rectangle([(100, box_y), (W-100, box_y+210)], radius=10, fill=(20, 15, 45), outline=accent, width=2)
    
    # Агенты с прогрессом
    for i, (name, desc) in enumerate(agents):
        y = box_y + 20 + i * 48
        
        # Имя агента
        draw.text((130, y), name, fill=(255, 255, 255), font=font_med, anchor="lt")
        draw.text((130, y + 28), desc, fill=(180, 180, 200), font=font_tiny, anchor="lt")
        
        # Анимация статуса (каждый агент активируется по очереди)
        active_idx = frame_i % 8
        if active_idx < 4:
            is_active = (i == active_idx)
        else:
            is_active = (i == active_idx - 4)
        
        if is_active:
            # Пульсирующий кружок
            radius = 8 + int(4 * (0.5 + 0.5 * (phase * 3.14159 * 2)))
            cx = W - 150
            cy = y + 18
            draw.ellipse([(cx-radius, cy-radius), (cx+radius, cy+radius)], fill=accent)
            draw.ellipse([(cx-3, cy-3), (cx+3, cy+3)], fill=(255, 255, 255))
        else:
            # Серый кружок
            draw.ellipse([(W-158, y+10), (W-142, y+26)], fill=(60, 60, 80))
    
    # Прогресс-бар
    bar_y = 385
    draw.rounded_rectangle([(120, bar_y), (W-120, bar_y+16)], radius=8, fill=(30, 25, 55))
    
    progress = (frame_i + 1) / 12
    bar_w = int((W - 240) * progress)
    if bar_w > 0:
        draw.rounded_rectangle([(120, bar_y), (120 + bar_w, bar_y+16)], radius=8, fill=accent)
    
    pct = f"{int(progress * 100)}%"
    draw.text((W//2, bar_y + 8), pct, fill=(255, 255, 255), font=font_tiny, anchor="mt")
    
    # Сбор команды
    status_texts = [
        "🔍 Поиск источников...",
        "⚡ Анализ данных...",
        "🤖 Локальная проверка...",
        "🧠 Синтез отчёта...",
        "📊 Формирование выводов...",
        "✅ Исследование завершено"
    ]
    status_idx = min(frame_i, 5)
    draw.text((W//2, H-40), status_texts[status_idx], fill=accent, font=font_small, anchor="mt")
    
    # Нижняя полоса
    draw.rectangle([(0, H-4), (W, H)], fill=accent)
    
    frames.append(img)

# Сохраняем
path = "/opt/zinaida/design/deep_research_activate.gif"
os.makedirs(os.path.dirname(path), exist_ok=True)
frames[0].save(path, save_all=True, append_images=frames[1:], duration=400, loop=0)
print(f"Сохранено: {path}")
print(f"Кадров: {len(frames)}")

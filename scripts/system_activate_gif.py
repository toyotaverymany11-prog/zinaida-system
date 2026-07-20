#!/usr/bin/env python3
"""Анимированный GIF активации системы - пульсирующий эффект"""
from PIL import Image, ImageDraw, ImageFont
import os

W, H = 800, 500
frames = []
colors = [
    (0, 150, 255),   # синий
    (0, 200, 255),   # голубой  
    (255, 200, 50),  # золотой
    (50, 255, 100),  # зелёный
    (255, 100, 50),  # оранжевый
]

try:
    font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
    font_med = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
    font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
except:
    font_large = font_med = font_small = ImageFont.load_default()

for frame_i in range(10):
    img = Image.new('RGB', (W, H), (10, 10, 30))
    draw = ImageDraw.Draw(img)
    
    # Пульсирующий цвет
    accent = colors[frame_i % len(colors)]
    glow = max(50, 255 - frame_i * 20)
    
    # Верхняя полоса с пульсацией
    draw.rectangle([(0, 0), (W, 4)], fill=accent)
    
    # Заголовок
    draw.text((W//2, 60), "⚡ SYSTEM ⚡", fill=accent, font=font_large, anchor="mt")
    
    # Линия
    draw.line([(W//4, 95), (3*W//4, 95)], fill=accent, width=2)
    
    # Статус
    draw.text((W//2, 140), "СИСТЕМНЫЙ ПРОТОКОЛ АКТИВИРОВАН", fill=(255, 255, 255), font=font_med, anchor="mt")
    
    # Блок
    box_y = 190
    draw.rounded_rectangle([(100, box_y), (W-100, box_y+180)], radius=10, fill=(20, 20, 60), outline=accent, width=2)
    
    points = [
        "✓ MEMORY.md          ✓ USER.md              ✓ Mem0",
        "✓ SOUL.md               ✓ AGENTS.md          ✓ Telegram bot",
        "✓ Router 8002           ✓ Router 8003          ✓ Router 8005",
        "✓ Skills                     ✓ fact_store         ✓ Shared memory",
        "✓ BrightData              ✓ Context Engine  ✓ MOA везде",
    ]
    
    for i, pt in enumerate(points):
        y = box_y + 20 + i * 32
        c = (50, 255, 100) if frame_i % 2 == 0 else (100, 255, 150)
        draw.text((W//2, y), pt, fill=c, font=font_small, anchor="mt")
    
    # Гарантия
    guar = "13 точек • Полная верификация • Гарантия сохранности"
    guar_color = accent if frame_i % 2 == 0 else (255, 255, 255)
    draw.text((W//2, H-60), guar, fill=guar_color, font=font_small, anchor="mt")
    
    # Нижняя полоса
    draw.rectangle([(0, H-4), (W, H)], fill=accent)
    
    frames.append(img)

# Сохраняем GIF
path = "/opt/zinaida/design/system_activate.gif"
os.makedirs(os.path.dirname(path), exist_ok=True)
frames[0].save(path, save_all=True, append_images=frames[1:], duration=300, loop=0)
print(f"Сохранено: {path}")
print(f"Кадров: {len(frames)}")

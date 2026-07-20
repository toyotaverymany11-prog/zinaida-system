#!/usr/bin/env python3
"""Генерация PNG-изображения активации системы"""
from PIL import Image, ImageDraw, ImageFont
import os

W, H = 800, 500
img = Image.new('RGB', (W, H), (10, 10, 30))
draw = ImageDraw.Draw(img)

# Цвета
GOLD = (255, 200, 50)
CYAN = (0, 200, 255)
WHITE = (200, 200, 220)
DARK = (20, 20, 60)
GREEN = (50, 255, 100)

# Верхняя полоса
draw.rectangle([(0, 0), (W, 4)], fill=(0, 150, 255))

# Заголовок
try:
    font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
    font_med = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
    font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
except:
    font_large = ImageFont.load_default()
    font_med = font_large
    font_small = font_large

# SYSTEM заголовок
draw.text((W//2, 60), "⚡ SYSTEM ⚡", fill=GOLD, font=font_large, anchor="mt")

# Линия под заголовком
draw.line([(W//4, 95), (3*W//4, 95)], fill=CYAN, width=2)

# Статус активации  
draw.text((W//2, 140), "СИСТЕМНЫЙ ПРОТОКОЛ АКТИВИРОВАН", fill=CYAN, font=font_med, anchor="mt")

# Блок с точками
box_y = 190
draw.rounded_rectangle([(100, box_y), (W-100, box_y+180)], radius=10, fill=DARK, outline=CYAN, width=1)

points = [
    "✓ MEMORY.md          ✓ USER.md              ✓ Mem0",
    "✓ SOUL.md               ✓ AGENTS.md          ✓ Telegram bot",
    "✓ Router 8002           ✓ Router 8003          ✓ Router 8005",
    "✓ Skills                     ✓ fact_store         ✓ Shared memory",
    "✓ BrightData              ✓ Context Engine  ✓ MOA везде",
]

for i, pt in enumerate(points):
    y = box_y + 20 + i * 32
    draw.text((W//2, y), pt, fill=GREEN if "✓" in pt else WHITE, font=font_small, anchor="mt")

# Нижняя полоса
draw.rectangle([(0, H-4), (W, H)], fill=(0, 150, 255))

# Путь сохранения
path = "/opt/zinaida/design/system_activate.png"
os.makedirs(os.path.dirname(path), exist_ok=True)
img.save(path)
print(f"Сохранено: {path}")
print(f"Размер: {W}x{H}")

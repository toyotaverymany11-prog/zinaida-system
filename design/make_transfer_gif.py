#!/usr/bin/env python3
"""Генерирует анимацию активации ПЕРЕНОС — 1920×120, 3 сек, 15 FPS"""

from PIL import Image, ImageDraw, ImageFont
import os, math

OUTPUT = "/opt/zinaida/design/transfer_activate.gif"
FPS = 15
DURATION = 3
FRAMES = FPS * DURATION
W, H = 1920, 120

# Цвета
BG = (10, 10, 10)
ACCENT = (0, 200, 255)
ACCENT2 = (100, 255, 200)
TEXT_COLOR = (220, 220, 220)

# Создаём кадры
frames = []
font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
font_large = ImageFont.truetype(font_path, 52) if os.path.exists(font_path) else None
font_small = ImageFont.truetype(font_path, 28) if os.path.exists(font_path) else None

for i in range(FRAMES):
    img = Image.new("RGBA", (W, H), BG)
    draw = ImageDraw.Draw(img)
    
    t = i / FRAMES  # 0..1
    progress = min(1.0, t * 3)  # первая треть
    
    # Бегущая строка слева направо
    bar_x = int(W * (t * 1.5 % 1.0))
    bar_w = 30
    draw.rectangle([bar_x, 0, bar_x + bar_w, H], fill=ACCENT)
    
    # Вторая волна
    bar_x2 = int(W * ((t * 1.5 + 0.3) % 1.0))
    draw.rectangle([bar_x2, 0, bar_x2 + bar_w, H], fill=ACCENT2)
    
    # Текст
    if font_large and font_small:
        # Заголовок
        alpha = int(255 * progress)
        draw.text((60, 15), "⚡ ПЕРЕНОС СИСТЕМЫ", font=font_large, fill=(*TEXT_COLOR, alpha))
        
        # Подзаголовок с пульсацией
        pulse = 0.5 + 0.5 * math.sin(t * 4 * math.pi)
        alpha2 = int(200 + 55 * pulse)
        draw.text((60, 70), "Сбор дампа → Передача новому агенту → GitHub", 
                  font=font_small, fill=(*ACCENT, alpha2))
        
        # Индикатор прогресса справа
        pct = min(100, int(t * 100))
        draw.text((W - 200, 30), f"{pct}%", font=font_large, fill=(*ACCENT, alpha))
        draw.rectangle([W - 200, 90, W - 200 + int(150 * t), 110], fill=ACCENT)
    
    frames.append(img)

# Сохраняем
frames[0].save(
    OUTPUT,
    save_all=True,
    append_images=frames[1:],
    duration=1000 // FPS,
    loop=0,
    optimize=False
)

print(f"✅ GIF создан: {OUTPUT}")
print(f"   {len(frames)} кадров, {DURATION} сек, {os.path.getsize(OUTPUT)/1024:.0f} KB")

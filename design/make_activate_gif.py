#!/usr/bin/env python3
"""Генерирует анимацию активации — узкая полоса 1920×120, 3 секунды, 15 FPS"""

from PIL import Image, ImageDraw, ImageFont
import os, math

W, H = 1920, 120
FPS = 15
DURATION = 3.0
TOTAL_FRAMES = int(FPS * DURATION)

FRAMES_DIR = '/tmp/activate_frames_v2'
os.makedirs(FRAMES_DIR, exist_ok=True)

BG = (10, 10, 10)
ACCENT = (0, 200, 255)
ACCENT2 = (255, 100, 200)
WHITE = (220, 220, 220)

try:
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 26)
except:
    font = ImageFont.load_default()

def make_frame(i):
    t = i / TOTAL_FRAMES
    img = Image.new('RGB', (W, H), BG)
    draw = ImageDraw.Draw(img)
    
    # 1. Матричные полоски (все кадры)
    for x in range(0, W, 14):
        if hash(f'v2_bar_{i}_{x}') % 4 == 0:
            bh = 1 + (hash(f'h2_{x}') % 5)
            by = hash(f'y2_{x}_{i//3}') % H
            val = 30 + 25 * (1 - abs(t - 0.5) * 0.6)
            draw.rectangle([x, by, x+3, by+bh], fill=(0, int(val), int(val//2)))
    
    # 2. Бегущая линия
    scan_x = int(W * t)
    # свечение
    for dx in range(0, 100, 3):
        alpha = max(0, int(80 * (1 - dx/100)))
        draw.rectangle([scan_x - dx, 0, scan_x - dx + 2, H], fill=(0, 180, 255, alpha))
    # ядро
    draw.rectangle([scan_x, 0, scan_x + 5, H], fill=ACCENT)
    
    # 3. Дополнительная линия-эхо (отстаёт на 20%)
    if t > 0.2:
        echo_x = int(W * (t - 0.2))
        draw.rectangle([echo_x, 0, echo_x + 2, H], fill=(0, 100, 180, 80))
    
    # 4. Пульс по краям
    pulse = int(50 + 50 * (1 + math.sin(t * math.pi * 4)) / 2)
    draw.rectangle([0, 0, W, 3], fill=(0, pulse, pulse))
    draw.rectangle([0, H-3, W, H], fill=(0, pulse, pulse))
    
    # 5. Текст (появляется на 30%, мерцает)
    if t > 0.3:
        text = "СИСТЕМА АКТИВИРОВАНА"
        # мерцание
        flicker = 1.0
        if 0.5 < t < 0.55:
            flicker = 0.3 + 0.7 * (1 - (t - 0.5) / 0.05 % 1)
        
        alpha = min(255, int(255 * (t - 0.3) / 0.2 * flicker))
        bbox = draw.textbbox((0,0), text, font=font)
        tw = bbox[2] - bbox[0]
        tx = (W - tw) // 2
        ty = (H - 26) // 2 - 2
        draw.text((tx, ty), text, fill=(*ACCENT, alpha), font=font)
        
        # подтекст
        sub = "▸ ЗАПУСК МАРКЕТИНГ-МОДУЛЯ ◂"
        bbox2 = draw.textbbox((0,0), sub, font=ImageFont.load_default())
        sw = bbox2[2] - bbox2[0]
        sx = (W - sw) // 2
        sy = ty + 30
        draw.text((sx, sy), sub, fill=(*ACCENT2, int(alpha * 0.6)), font=ImageFont.load_default())
    
    path = os.path.join(FRAMES_DIR, f'frame_{i:04d}.png')
    img.save(path, 'PNG')
    return path

print(f"Генерирую {TOTAL_FRAMES} кадров ({W}×{H})...")
for i in range(TOTAL_FRAMES):
    make_frame(i)
    if i % 15 == 0:
        print(f"  {i}/{TOTAL_FRAMES}")

print("Собираю GIF...")
frames = [Image.open(os.path.join(FRAMES_DIR, fn)) for fn in sorted(os.listdir(FRAMES_DIR))]
first = frames[0]
rest = frames[1:]

out_path = '/opt/zinaida/design/system_activate.gif'
first.save(out_path, save_all=True, append_images=rest,
           duration=int(1000 / FPS), loop=0,
           disposal=2, optimize=True)

print(f"Готово: {out_path}")
size_kb = os.path.getsize(out_path) / 1024
print(f"Размер: {size_kb:.0f} KB")
print(f"Кадры: {len(frames)}")

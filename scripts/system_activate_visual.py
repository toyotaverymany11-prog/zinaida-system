#!/usr/bin/env python3
"""Активационный визуал системы «РЕШИ ВОПРОС СИСТЕМНО»"""
import pyfiglet, shutil, os

cols = min(shutil.get_terminal_size().columns, 80)

def center(text):
    pad = max(0, (cols - len(text)) // 2)
    return ' ' * pad + text

print()
# Верхняя рамка
print('╔' + '═' * (cols - 2) + '╗')

# Пустая строка
print('║' + ' ' * (cols - 2) + '║')

# Большой заголовок pyfiglet
title = pyfiglet.figlet_format('SYSTEM', font='big')
for line in title.split('\n'):
    if line.strip():
        padding = max(0, (cols - len(line.rstrip())) // 2)
        display = line.rstrip()
        print('║' + ' ' * padding + display + ' ' * max(0, cols - padding - len(display) - 1) + '║')

# Пустая строка
print('║' + ' ' * (cols - 2) + '║')

# Декоративный разделитель
sep = '█' * (cols - 4)
print('║ ' + sep + ' ║')

print('║' + ' ' * (cols - 2) + '║')

# Основной статус - крупно
status = '⚡ СИСТЕМНЫЙ ПРОТОКОЛ АКТИВИРОВАН ⚡'
print('║' + center('▄' * len(status)) + '║')
print('║' + center(status) + '║')
print('║' + center('▀' * len(status)) + '║')

print('║' + ' ' * (cols - 2) + '║')

# Детали
details = [
    '→ 13 точек внедрения',
    '→ Полная верификация',
    '→ Гарантия сохранности',
]
for d in details:
    print('║' + center(d) + '║')

print('║' + ' ' * (cols - 2) + '║')

# Нижняя рамка
print('╚' + '═' * (cols - 2) + '╝')
print()

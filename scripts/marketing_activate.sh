#!/bin/bash
# МАРКЕТИНГ-ТРИГГЕР v3.0
# Запускается когда первое слово в чате = "маркетинг"
# Живая сборка: ищет маркетинговые файлы по всему проекту, не только в marketing/
# Дата: 13.07.2026

echo "═══════════════════════════════════════════"
echo "  ЗИНАИДА: СБОР МАРКЕТИНГА v3.0"
echo "═══════════════════════════════════════════"
echo ""

echo "[1/8] Маркетинговые файлы (все источники)..."

# Основная папка marketing/
MKTG="/opt/zinaida/projects/Otnoshenya/marketing"
if [ -d "$MKTG" ]; then
    COUNT_MKTG=$(find "$MKTG" -type f | wc -l)
    echo "   📁 marketing/ — $COUNT_MKTG файлов"
    find "$MKTG" -type f -name "*.md" | sort | head -30 | sed 's/^/      /'
fi
echo ""

# Гайд маркетинга 2026
GUIDE="/opt/zinaida/inbox/MARKETING_GUIDE_2026.md"
if [ -f "$GUIDE" ]; then
    GUIDE_SIZE=$(numfmt --to=iec $(stat --printf="%s" "$GUIDE" 2>/dev/null) 2>/dev/null || echo "$(wc -c < "$GUIDE") байт")
    echo "   📋 $GUIDE — $GUIDE_SIZE ($(wc -l < "$GUIDE") строк)"
fi

# Скрипты маркетинга
SCRIPTS="/opt/zinaida/scripts/marketing_activate.sh"
if [ -f "$SCRIPTS" ]; then
    echo "   🛠  $SCRIPTS — триггер-скрипт (v3.0)"
fi

# Файлы поддержки в shared_memory
SHARED="/opt/zinaida/shared_memory/updates_log.md"
if [ -f "$SHARED" ]; then
    echo "   📝 $SHARED — лог изменений"
fi
echo ""

# Вариант Ц и связка канал+бот
VC="/opt/zinaida/projects/Otnoshenya/marketing/variant_C_hybrid.md"
if [ -f "$VC" ]; then
    echo "   ✅ Вариант Ц: канал + бот ($(wc -l < "$VC") строк)"
fi
TG_BOT="/opt/zinaida/projects/Otnoshenya/marketing/telegram_kanal_bot_swyazka.md"
if [ -f "$TG_BOT" ]; then
    echo "   ✅ Связка Telegram: канал + бот ($(wc -l < "$TG_BOT") строк)"
fi
echo ""

# product/ — файлы по продукту
PROD="/opt/zinaida/projects/Otnoshenya/product"
if [ -d "$PROD" ]; then
    COUNT_PROD=$(find "$PROD" -type f | wc -l)
    echo "   📦 product/ — $COUNT_PROD файлов"
fi
echo ""

# legal/ — юридические
LEGAL="/opt/zinaida/projects/Otnoshenya/legal"
if [ -d "$LEGAL" ]; then
    COUNT_LEGAL=$(find "$LEGAL" -type f | wc -l)
    echo "   ⚖️  legal/ — $COUNT_LEGAL файл"
fi
echo ""

echo "[2/8] Резюме текущего состояния воронки..."
echo "   ┌────────────────────────────────────────────────────────┐"
echo "   │ Вариант Ц: канал (контент) → бот (продукт)            │"
echo "   │ Канал: Otnoshenya (2 подписчика)                      │"
echo "   │ Бот: @DCHP_Shtab_bot (через Hermes, 8005)             │"
echo "   │ Инструментов: 6 (12-18 токенов)                       │"
echo "   │ Автоворонка: 3-4 часа (день 1) → paywall              │"
echo "   │ Подписка: 900-990₽/мес (уточняется)                   │"
echo "   └────────────────────────────────────────────────────────┘"
echo ""

echo "[3/8] updates_log — последние изменения..."
grep -i "маркетинг\|воронка\|вариант ц\|AI-инструмент\|СПРАВОЧНИК\|консилиум" /opt/zinaida/shared_memory/updates_log.md 2>/dev/null | tail -5 | sed 's/^/   /'
echo ""

echo "[4/8] Задачи Todoist по маркетингу..."
python3 /opt/zinaida/todoist_integration/todoist_api.py today 2>/dev/null | grep -i "МАРКЕТИНГ\|ВОРОНКА\|ПРОДУКТ\|ИНСТРУМЕНТ\|ЗАПУСК\|БОТ\|КАНАЛ\|TELEGRAM\|ВСТРЕЧИ" | sed 's/^/   /'
echo ""

echo "[5/8] Консилиум — исследования маркетинга..."
ls -lt /opt/zinaida/shared_memory/consilium/CONSILIUM_*.md 2>/dev/null | head -3 | sed 's/^/   /'
echo ""

echo "[6/8] Навык marketing-guide-2026..."
if [ -f "/root/.hermes/skills/zinaida/marketing-guide-2026/SKILL.md" ]; then
    VER=$(grep "version:" /root/.hermes/skills/zinaida/marketing-guide-2026/SKILL.md 2>/dev/null | head -1 | sed 's/version: //')
    echo "   ✅ Навык версии $VER — готов к загрузке"
fi
echo ""

echo "[7/8] SOUL.md — режим спора..."
grep -c "ЗИНАИДА-МАРКЕТОЛОГ" /root/.hermes/SOUL.md 2>/dev/null | xargs -I{} echo "   ✅ Режим \"Спорь\" активен: {} блок"
echo ""

echo "[8/8] Пробелы (не закрыто):"
echo "   ⚠ Автоворонка Telegram — не написана (скрипты/промпты)"
echo "   ⚠ Бот-прослойка VK/Instagram — не реализован"
echo "   ⚠ Контент-план публикаций — нет"
echo "   ⚠ Токеновая экономика — не настроена"
echo "   ⚠ 1-й тестовый пост не написан"
echo ""

echo "═══════════════════════════════════════════"
echo "  ✅ СБОР ЗАВЕРШЁН. $COUNT_MKTG+ файлов, гайд, навык, воронка."
echo "  Я в режиме спора. О чём думаем?"
echo "═══════════════════════════════════════════"

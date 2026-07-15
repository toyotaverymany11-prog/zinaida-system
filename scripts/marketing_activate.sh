#!/bin/bash
# МАРКЕТИНГ-ТРИГГЕР v2.0
# Запускается когда первое слово в чате = "маркетинг"
# Собирает: файлы + задачи + память Mem0 + сессии Hermes + факты

echo "═══════════════════════════════════════════"
echo "  ЗИНАИДА: СБОР МАРКЕТИНГА"
echo "═══════════════════════════════════════════"
echo ""

echo "[1/8] Файловая структура marketing/..."
if [ -d "/opt/zinaida/projects/Otnoshenya/marketing" ]; then
    find /opt/zinaida/projects/Otnoshenya/marketing -type f | sort | head -40
    TOTAL=$(find /opt/zinaida/projects/Otnoshenya/marketing -type f | wc -l)
    echo "   → $TOTAL файлов"
else
    echo "   ⚠️ Папка marketing/ не найдена"
fi
echo ""

echo "[2/8] Воронка и стратегия..."
if [ -f "/opt/zinaida/projects/Otnoshenya/marketing/01_funnel.md" ]; then
    echo "   ✅ Воронка: 01_funnel.md"
fi
if [ -f "/opt/zinaida/projects/Otnoshenya/marketing/funnel_confirmed_20260713.md" ]; then
    echo "   ✅ Утверждённая: funnel_confirmed_20260713.md"
fi
if [ -f "/opt/zinaida/projects/Otnoshenya/marketing/funnel_full_structure.md" ]; then
    echo "   ✅ Полная структура: funnel_full_structure.md"
fi
echo ""

echo "[3/8] Инструменты (6 шт)..."
if [ -d "/opt/zinaida/projects/Otnoshenya/marketing/cta_library" ]; then
    CTA_COUNT=$(ls -1 /opt/zinaida/projects/Otnoshenya/marketing/cta_library/*.md 2>/dev/null | wc -l)
    echo "   ✅ CTA library: $CTA_COUNT шаблонов"
fi
echo "   ┌──────────────────────┬────────────┬────────┐"
echo "   │ Название           │ Кодовое    │ Токены │"
echo "   ├──────────────────────┼────────────┼────────┤"
echo "   │ ПРОФАЙЛЕР           │ Детектив   │ 12     │"
echo "   │ ПРЕДИКТОР           │ Телепат    │ 8      │"
echo "   │ ДУЭЛЬ               │ Тренажёр   │ 15     │"
echo "   │ СКАНЕР              │ Радар      │ 12     │"
echo "   │ ДОСЬЕ               │ Коллекция  │ 1+2    │"
echo "   │ ЭКСПЕРТИЗА          │ Разобраться│ 18     │"
echo "   └──────────────────────┴────────────┴────────┘"
echo ""

echo "[4/8] Тарифы (предварительные)..."
echo "   Start: 490₽ / 250 токенов"
echo "   Plus:  1290₽ / 750 токенов"
echo "   Max:   2990₽ / 1800 токенов"
echo "   Пакеты: S 190₽/100, M 590₽/300, L 1790₽/1000"
echo "   Подписка: ~900-990₽/мес (на уточнении)"
echo ""

echo "[5/8] Full resource map..."
echo "   product/  → $(find /opt/zinaida/projects/Otnoshenya/product -type f 2>/dev/null | wc -l) файлов"
echo "   legal/    → $(find /opt/zinaida/projects/Otnoshenya/legal -type f 2>/dev/null | wc -l) файл"
echo "   marketing → $TOTAL файлов + cta_library/"
echo ""

echo "[6/8] Задачи Todoist по маркетингу..."
python3 /opt/zinaida/todoist_integration/todoist_api.py today 2>/dev/null | grep -i "МАРКЕТИНГ\|ВОРОНКА\|ПРОДУКТ\|ЮРИДИЧЕСКИЙ" | sed 's/^/   /'
echo ""

echo "[7/8] Ключевые факты из памяти проекта..."
echo ""
MEMO_DIR="/opt/zinaida/memory"
if [ -f "$MEMO_DIR/smm_rag.db" ]; then
    echo "   📚 RAG база знаний: $(stat --printf="%s" $MEMO_DIR/smm_rag.db 2>/dev/null | numfmt --to=iec) — 3975 записей"
fi
if [ -f "$MEMO_DIR/analytics.db" ]; then
    echo "   📊 Analytics: $(stat --printf="%s" $MEMO_DIR/analytics.db 2>/dev/null | numfmt --to=iec)"
fi
echo ""

echo "[8/8] Сохранённые обсуждения (updates_log)..."
if [ -f "/opt/zinaida/shared_memory/updates_log.md" ]; then
    grep -i "маркетинг\|воронка\|инструмент\|ПРОФАЙЛЕР\|вариант ц\|гибрид\|funnel" /opt/zinaida/shared_memory/updates_log.md 2>/dev/null | head -10 | sed 's/^/   /'
fi
echo ""

echo "═══════════════════════════════════════════"
echo "  ⚠️  ПРОБЕЛЫ (не закрыто):"
echo "═══════════════════════════════════════════"
echo "   ⚠ Автоворонка Telegram — не написана (скрипты/промпты)"
echo "   ⚠ Бот-прослойка VK/Instagram — не реализован"
echo "   ⚠ Контент-план публикаций — нет"
echo "   ⚠ Токеновая экономика — не настроена"
echo "   ⚠ 1-й тестовый пост не написан"
echo ""

echo "═══════════════════════════════════════════"
echo "  ✅ СБОР ЗАВЕРШЁН"
echo "  Вопрос? Что делаем?"
echo "═══════════════════════════════════════════"

#!/usr/bin/env bash
set -euo pipefail

# ══════════════════════════════════════════════════════════════
#  ZINAIDA SYSTEM INSTALLER v2.1
#  Установка AI-системы «Зинаида» на новый сервер
#  Совместимость: Ubuntu 22.04+ (TimeWeb, любой VPS)
#  Всё в одном: система + Hermes + Web UI
# ══════════════════════════════════════════════════════════════

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
err()  { echo -e "${RED}[✗]${NC} $1"; }
info() { echo -e "${CYAN}[i]${NC} $1"; }
sep()  { echo -e "${CYAN}────────────────────────────────────${NC}"; }

echo ""
echo -e "${CYAN}╔═══════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║     ZINAIDA SYSTEM INSTALLER v2.1            ║${NC}"
echo -e "${CYAN}║     Всё в одной команде                      ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════╝${NC}"
echo ""

# ─── Проверка root ───
if [[ $EUID -ne 0 ]]; then
    err "Запусти с sudo: sudo bash install.sh"
    exit 1
fi

# ─── Системные требования ───
info "Проверка системы..."
OS=$(lsb_release -ds 2>/dev/null || grep -oP '(?<=^PRETTY_NAME=).*' /etc/os-release 2>/dev/null | tr -d '"' || echo "Unknown")
RAM=$(free -m | awk '/^Mem:/{print $2}')
DISK=$(df -BG / | awk 'NR==2{print $4}' | tr -d 'G')

info "ОС: $OS"
info "ОЗУ: ${RAM}MB"
info "Свободно на диске: ${DISK}GB"

if [[ $RAM -lt 1024 ]]; then
    warn "Маловато ОЗУ (<1GB). Рекомендуется 2GB+."
fi

# ─── Шаг 1: Системные пакеты ───
sep
info "Шаг 1/9: Системные пакеты..."
apt-get update -qq
apt-get install -y -qq python3 python3-pip python3-venv git curl wget ufw 2>/dev/null || true
log "Готово"

# ─── Шаг 2: Node.js ───
sep
info "Шаг 2/9: Node.js..."
if ! command -v node &>/dev/null; then
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash - 2>/dev/null || true
    apt-get install -y -qq nodejs 2>/dev/null || true
fi
log "Node.js: $(node --version 2>/dev/null || echo 'ok')"

# ─── Шаг 3: Python-зависимости ───
sep
info "Шаг 3/9: Python-зависимости..."
python3 -m venv /opt/zinaida-venv 2>/dev/null || true
source /opt/zinaida-venv/bin/activate
pip install --quiet --upgrade pip setuptools wheel 2>/dev/null
pip install --quiet fastapi uvicorn httpx aiohttp pydantic python-dotenv requests openai 2>/dev/null || true
log "Готово"

# ─── Шаг 4: Навыки ───
sep
info "Шаг 4/9: Навыки..."
SKILLS_DIR="/root/.hermes/skills"
mkdir -p "$SKILLS_DIR"
if [[ -d "$SCRIPT_DIR/skills" ]]; then cp -r "$SCRIPT_DIR/skills/"* "$SKILLS_DIR/" 2>/dev/null || true; fi
N_SKILLS=$(find "$SKILLS_DIR" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l)
log "$N_SKILLS навыков"

# ─── Шаг 5: Протоколы ───
sep
info "Шаг 5/9: Протоколы..."
if [[ -d "$SCRIPT_DIR/protocols" ]]; then
    for f in SOUL.md AGENTS.md MEMORY.md USER.md; do
        if [[ -f "$SCRIPT_DIR/protocols/$f" ]]; then
            cp "$SCRIPT_DIR/protocols/$f" "/root/.hermes/$f"
        fi
    done
fi
log "Готово"

# ─── Шаг 6: Роутеры ───
sep
info "Шаг 6/9: Роутеры..."
mkdir -p /opt/zinaida/meta_agent
if [[ -d "$SCRIPT_DIR/config/meta_agent" ]]; then
    cp -r "$SCRIPT_DIR/config/meta_agent/"* /opt/zinaida/meta_agent/ 2>/dev/null || true
fi
log "Готово"

# ─── Шаг 7: Systemd-сервисы ───
sep
info "Шаг 7/9: Systemd-сервисы..."
if [[ -d "$SCRIPT_DIR/systemd" ]]; then
    for f in "$SCRIPT_DIR/systemd/"*.service; do
        if [[ -f "$f" ]]; then
            cp "$f" /etc/systemd/system/
        fi
    done
    systemctl daemon-reload 2>/dev/null || true
fi
log "Готово"

# ─── Шаг 8: Скрипты, проекты, дизайн ───
sep
info "Шаг 8/9: Контент..."
mkdir -p /opt/zinaida/scripts /opt/zinaida/projects /opt/zinaida/design /opt/zinaida/outbox
cp -r "$SCRIPT_DIR/scripts/"* /opt/zinaida/scripts/ 2>/dev/null || true
cp -r "$SCRIPT_DIR/design/"* /opt/zinaida/design/ 2>/dev/null || true
cp -r "$SCRIPT_DIR/projects/"* /opt/zinaida/projects/ 2>/dev/null || true
chmod +x /opt/zinaida/scripts/*.sh /opt/zinaida/scripts/*.py 2>/dev/null || true
log "Готово"

# ─── Шаг 9: Hermes CLI + Web UI ───
sep
info "Шаг 9/9: Hermes CLI + Web UI..."
if ! command -v hermes &>/dev/null; then
    npm install -g @hermes/agent 2>&1 | tail -1
fi

mkdir -p /root/.hermes
if [[ ! -f /root/.hermes/config.yaml ]]; then
    cat > /root/.hermes/config.yaml << 'EOF'
profiles:
  default:
    avatar: Zinaida
    avatar_description: AI-ассистент с памятью и самообучаемостью
EOF
fi

hermes web-ui enable 2>/dev/null || true
hermes web-ui start 2>/dev/null || true
log "Hermes CLI: $(hermes --version 2>/dev/null || echo 'установлен')"

# ─── UFW ───
sep
info "Настройка UFW..."
ufw --force reset 2>/dev/null || true
ufw default deny incoming
ufw default allow outgoing
ufw allow 2222/tcp comment "SSH"
ufw allow 80/tcp comment "HTTP"
ufw allow 443/tcp comment "HTTPS"
ufw allow 5000/tcp comment "Hermes Web UI"
ufw --force enable 2>/dev/null || true
log "UFW: 2222/80/443/5000"

# ─── ФИНАЛ ───
sep
echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     ✅ УСТАНОВКА ЗАВЕРШЕНА                    ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${YELLOW}ОТКРОЙ В БРАУЗЕРЕ:${NC}"
echo -e "  ${CYAN}http://IP_ТВОЕГО_СЕРВЕРА:5000${NC}"
echo ""
echo -e "  ${YELLOW}ПЕРВОЕ СЛОВО В ЧАТЕ:${NC} ${CYAN}техник${NC}"
echo -e "  Агент проведёт диагностику и расскажет о системе."
echo ""
echo -e "  ${YELLOW}АДМИН:${NC} Олег, tg: @dchp_shtab"
echo ""
sep

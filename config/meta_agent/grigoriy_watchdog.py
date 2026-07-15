import time
from pathlib import Path
from datetime import datetime

class GrigoriyWatchdog:
    def __init__(self):
        self.log_file = Path("/opt/zinaida/logs/app.log")
        self.repair_log = Path("/opt/zinaida/logs/grigoriy_repairs.log")
        self.last_check = None
        
    def scan_errors(self):
        """Сканирует логи на ошибки"""
        if not self.log_file.exists():
            return []
        
        errors = []
        with open(self.log_file) as f:
            for line in f:
                if "[ERROR]" in line:
                    errors.append(line.strip())
        return errors[-10:]  # Последние 10 ошибок
    
    def analyze_and_repair(self, errors):
        """Анализирует и пытается починить"""
        for error in errors:
            if "syntax error" in error.lower() or "import" in error:
                self.log_repair(f"Auto-repair: {error}")
    
    def log_repair(self, message):
        """Логирует ремонт"""
        with open(self.repair_log, "a") as f:
            f.write(f"{datetime.now()} - {message}\n")
    
    def run(self):
        """Основной цикл"""
        print("🔧 Grigoriy Watchdog started...")
        while True:
            errors = self.scan_errors()
            if errors:
                self.analyze_and_repair(errors)
            time.sleep(300)  # Каждые 5 минут

if __name__ == "__main__":
    GrigoriyWatchdog().run()

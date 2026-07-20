import os, sys, requests, base64, logging, telebot, json, asyncio, edge_tts
from faster_whisper import WhisperModel
from pydub import AudioSegment
import db_manager

# Lockfile с PID-check для предотвращения 409 Conflict
LOCK_FILE = "/tmp/tg_worker.lock"
if os.path.exists(LOCK_FILE):
    try:
        with open(LOCK_FILE, "r") as f:
            old_pid = int(f.read().strip())
        os.kill(old_pid, 0)
        print(f"⚠️ Воркер уже запущен (PID {old_pid}). Выход.")
        sys.exit(0)
    except (ProcessLookupError, ValueError, PermissionError):
        print(f"🔓 Удалён мёртвый lockfile")
        try: os.remove(LOCK_FILE)
        except: pass

with open(LOCK_FILE, "w") as f:
    f.write(str(os.getpid()))

logging.basicConfig(filename='/opt/zinaida/logs/telegram_worker.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

TOKEN = os.getenv('TELEGRAM_TOKEN', '8560310319:AAFFS5ubSS0FQI8xowTl9TCg3UrOw6J3pIk')
ZINAIDA_URL = "http://127.0.0.1:8002/v1/chat/completions"
VOICE_STATE_FILE = "/opt/zinaida/meta_agent/voice_state.json"

logger.info("Загрузка Whisper модели (base/int8)...")
whisper_model = None
try:
    whisper_model = WhisperModel("base", device="cpu", compute_type="int8", local_files_only=False)
    logger.info("✅ Whisper OK.")
except Exception as e:
    logger.error(f"❌ Whisper error: {e}")

bot = telebot.TeleBot(TOKEN)

def get_voice_state():
    try:
        with open(VOICE_STATE_FILE, "r") as f: return json.load(f).get("enabled", False)
    except: return False

def set_voice_state(enabled: bool):
    with open(VOICE_STATE_FILE, "w") as f: json.dump({"enabled": enabled}, f)

async def text_to_speech(text: str, out_path: str):
    communicate = edge_tts.Communicate(text[:1000], "ru-RU-SvetlanaNeural", rate="-15%")
    await communicate.save(out_path)

def send_reply_with_voice(message, text_reply):
    bot.reply_to(message, text_reply)
    if get_voice_state():
        try:
            tmp_audio = f"/tmp/zv_{message.chat.id}.mp3"
            asyncio.run(text_to_speech(text_reply, tmp_audio))
            if os.path.exists(tmp_audio):
                with open(tmp_audio, "rb") as audio: bot.send_voice(message.chat.id, audio)
                os.remove(tmp_audio)
        except Exception as e: logger.error(f"TTS Error: {e}")

def transcribe_audio(file_path):
    if not whisper_model: return "Ошибка: Whisper не загружен."
    try:
        audio = AudioSegment.from_file(file_path, format="ogg")
        wav_path = file_path.replace(".ogg", ".wav")
        audio.export(wav_path, format="wav")
        segments, _ = whisper_model.transcribe(wav_path, beam_size=5, language="ru")
        text = " ".join([s.text for s in segments])
        os.remove(file_path); os.remove(wav_path)
        return text.strip()
    except Exception as e:
        logger.error(f"STT Error: {e}")
        if os.path.exists(file_path): os.remove(file_path)
        return "Не удалось расшифровать."

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, 'Привет! Я Зинаида. Используй /voice. Можешь слать голосовые.')

@bot.message_handler(commands=['voice'])
def voice_cmd(message):
    state = not get_voice_state()
    set_voice_state(state)
    bot.reply_to(message, "🔊 Голос включен" if state else "🔇 Голос выключен")

@bot.message_handler(content_types=['text'])
def handle_text(message):
    chat_id = str(message.chat.id)
    try: db_manager.write_message(chat_id, 'telegram', 'user', message.text)
    except Exception as e: logger.warning(f"DB write user err: {e}")
    
    payload = {"messages": [{"role": "user", "content": message.text}], "stream": False, "session_id": chat_id}
    try:
        resp = requests.post(ZINAIDA_URL, json=payload, timeout=60)
        resp.raise_for_status()
        reply = resp.json().get('choices', [{}])[0].get('message', {}).get('content', 'Нет ответа')
        try: db_manager.write_message(chat_id, 'telegram', 'assistant', reply)
        except Exception as e: logger.warning(f"DB write assist err: {e}")
        send_reply_with_voice(message, reply)
    except Exception as e:
        logger.error(f"Zinaida error: {e}")
        bot.reply_to(message, 'Ошибка связи с Зинаидой.')

@bot.message_handler(content_types=['voice', 'audio'])
def handle_voice(message):
    chat_id = str(message.chat.id)
    try:
        file_info = bot.get_file(message.voice.file_id if message.voice else message.audio.file_id)
        downloaded = bot.download_file(file_info.file_path)
        tmp_ogg = f"/tmp/vin_{chat_id}.ogg"
        with open(tmp_ogg, 'wb') as f: f.write(downloaded)
        bot.send_chat_action(message.chat.id, 'typing')
        text = transcribe_audio(tmp_ogg)
        
        try: db_manager.write_message(chat_id, 'telegram', 'user', f"[Голос] {text}")
        except Exception as e: logger.warning(f"DB write voice err: {e}")
        
        payload = {"messages": [{"role": "user", "content": text}], "stream": False, "session_id": chat_id}
        resp = requests.post(ZINAIDA_URL, json=payload, timeout=60)
        resp.raise_for_status()
        reply = resp.json().get('choices', [{}])[0].get('message', {}).get('content', 'Нет ответа')
        
        try: db_manager.write_message(chat_id, 'telegram', 'assistant', reply)
        except Exception as e: logger.warning(f"DB write voice reply err: {e}")
        
        send_reply_with_voice(message, f"🎤 {text}\n\n💬 {reply}")
    except Exception as e:
        logger.error(f"Voice err: {e}")
        bot.reply_to(message, 'Ошибка голоса.')

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    chat_id = str(message.chat.id)
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded = bot.download_file(file_info.file_path)
        b64 = base64.b64encode(downloaded).decode('utf-8')
        text = message.caption or "Что на фото?"
        
        try: db_manager.write_message(chat_id, 'telegram', 'user', f"[Фото] {text}")
        except Exception as e: logger.warning(f"DB write photo err: {e}")
        
        payload = {
            "messages": [{"role": "user", "content": [{"type": "text", "text": text}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}]}],
            "stream": False, "session_id": chat_id
        }
        resp = requests.post(ZINAIDA_URL, json=payload, timeout=60)
        resp.raise_for_status()
        reply = resp.json().get('choices', [{}])[0].get('message', {}).get('content', 'Нет ответа')
        
        try: db_manager.write_message(chat_id, 'telegram', 'assistant', reply)
        except Exception as e: logger.warning(f"DB write photo reply err: {e}")
        
        send_reply_with_voice(message, reply)
    except Exception as e:
        logger.error(f"Photo err: {e}")
        bot.reply_to(message, 'Ошибка фото.')

if __name__ == '__main__':
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=30)
    finally:
        if os.path.exists(LOCK_FILE):
            try: os.remove(LOCK_FILE)
            except: pass
            print("🔓 Lockfile удалён при выходе")

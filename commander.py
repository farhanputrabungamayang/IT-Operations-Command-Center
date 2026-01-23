import os
import time
import psutil
import pyautogui
import telebot
from dotenv import load_dotenv
from datetime import datetime

# --- LOAD KONFIGURASI DARI .ENV ---
load_dotenv()

# Ambil data rahasia
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
try:
    MY_CHAT_ID = int(os.getenv('TELEGRAM_CHAT_ID'))
except:
    print("⚠️ ERROR: TELEGRAM_CHAT_ID di file .env belum diisi atau salah format!")
    MY_CHAT_ID = 0

# Cek apakah token ada isinya
if not TELEGRAM_TOKEN:
    print("❌ ERROR FATAL: TELEGRAM_TOKEN tidak ditemukan di file .env!")
    print("👉 Pastikan file .env sudah dibuat dan diisi token.")
    exit()

# Inisialisasi Bot dengan Token dari .env
bot = telebot.TeleBot(TELEGRAM_TOKEN)

print("🤖 IT-OPS COMMANDER: ONLINE & LISTENING...")

# --- KEAMANAN: HANYA MERESPON MASBRO ---
def is_authorized(message):
    if message.chat.id != MY_CHAT_ID:
        bot.reply_to(message, f"⛔ AKSES DITOLAK! ID Anda: {message.chat.id} tidak terdaftar.")
        print(f"⚠️ Unauthorized access attempt from ID: {message.chat.id}")
        return False
    return True

# --- COMMANDS ---

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    # Bypass otorisasi khusus untuk /start biar kita tau ID kita berapa
    if message.chat.id != MY_CHAT_ID:
        bot.reply_to(message, f"👋 Hai! Bot ini privat.\nID Telegram Anda: `{message.chat.id}`\n(Salin ID ini ke file .env bagian TELEGRAM_CHAT_ID)", parse_mode="Markdown")
        return

    help_text = """
🛡️ **COMMAND CENTER CONTROLS** 🛡️

/status - Cek CPU, RAM, & Uptime
/screen - Intip Layar Laptop (Screenshot)
/clean - Jalankan Pembersihan Sampah
/lock - Kunci Laptop (Lock Screen)
/shutdown - Matikan Laptop (Hati-hati!)
    """
    bot.reply_to(message, help_text, parse_mode="Markdown")

@bot.message_handler(commands=['status'])
def check_status(message):
    if not is_authorized(message): return
    
    bot.send_message(message.chat.id, "⏳ Mengambil data telemetri...")
    
    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory().percent
    
    # Hitung Uptime
    boot_time = psutil.boot_time()
    uptime_sec = time.time() - boot_time
    uptime_h = int(uptime_sec // 3600)
    uptime_m = int((uptime_sec % 3600) // 60)
    
    msg = f"""
📊 **SYSTEM STATUS REPORT**
━━━━━━━━━━━━━━━━━━━
🔥 **CPU Load:** {cpu}%
💾 **RAM Usage:** {ram}%
⏱️ **Uptime:** {uptime_h} Jam {uptime_m} Menit
━━━━━━━━━━━━━━━━━━━
_System is running stable._
    """
    bot.reply_to(message, msg, parse_mode="Markdown")

@bot.message_handler(commands=['screen'])
def take_screenshot(message):
    if not is_authorized(message): return
    
    bot.send_chat_action(message.chat.id, 'upload_photo')
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"capture_{timestamp}.png"
    
    try:
        # Ambil Screenshot
        screenshot = pyautogui.screenshot()
        screenshot.save(filename)
        
        # Kirim ke Telegram
        with open(filename, 'rb') as photo:
            bot.send_photo(message.chat.id, photo, caption=f"📸 **Desktop Capture**\n🕒 {timestamp}", parse_mode="Markdown")
        
        # Hapus file setelah dikirim
        os.remove(filename)
    except Exception as e:
        bot.reply_to(message, f"❌ Gagal screenshot: {e}")

@bot.message_handler(commands=['clean'])
def run_cleaner(message):
    if not is_authorized(message): return
    
    bot.reply_to(message, "🧹 Menjalankan Protokol Kebersihan...")
    temp_folders = [
        os.path.join(os.environ['TEMP']),
        os.path.join(os.environ['WINDIR'], 'Temp')
    ]
    deleted_count = 0
    
    for folder in temp_folders:
        try:
            for root, dirs, files in os.walk(folder):
                for file in files:
                    try:
                        os.remove(os.path.join(root, file))
                        deleted_count += 1
                    except: pass
        except: pass
        
    bot.reply_to(message, f"✅ **CLEANUP COMPLETE!**\n🗑️ Berhasil menghapus {deleted_count} file sampah.")

@bot.message_handler(commands=['lock'])
def lock_pc(message):
    if not is_authorized(message): return
    bot.reply_to(message, "🔒 Mengunci Workstation...")
    os.system("rundll32.exe user32.dll,LockWorkStation")

@bot.message_handler(commands=['shutdown'])
def shutdown_pc(message):
    if not is_authorized(message): return
    
    # Fitur konfirmasi
    markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True)
    markup.add('YES SHUTDOWN', 'CANCEL')
    msg = bot.reply_to(message, "⚠️ **WARNING!**\nAnda yakin ingin mematikan Laptop?", reply_markup=markup, parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_shutdown_step)

def process_shutdown_step(message):
    if message.text == 'YES SHUTDOWN':
        bot.send_message(message.chat.id, "🔌 **SHUTTING DOWN SYSTEM...**\nBye bye! 👋")
        os.system("shutdown /s /t 5")
    else:
        bot.send_message(message.chat.id, "✅ Shutdown dibatalkan.", reply_markup=telebot.types.ReplyKeyboardRemove())

# --- JALANKAN BOT ---
if __name__ == "__main__":
    try:
        bot.infinity_polling()
    except Exception as e:
        print(f"❌ Bot Error: {e}")
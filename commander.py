import json
import requests
import os
import time
import psutil
import pyautogui
import telebot
import cv2
import webbrowser
import threading
import tkinter as tk
import numpy as np            
from tkinter import font as tkfont
from dotenv import load_dotenv
from datetime import datetime
from gtts import gTTS         
import pygame                 
import cleaner                
import google.generativeai as genai
import PIL.Image  

# --- IMPORT FITUR REPORT ---
try:
    from reporter import generate_pdf
except ImportError:
    generate_pdf = None

# --- LOAD KONFIGURASI ---
load_dotenv()

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

try:
    MY_CHAT_ID = int(os.getenv('TELEGRAM_CHAT_ID'))
except:
    MY_CHAT_ID = 0

if not TELEGRAM_TOKEN:
    print("❌ ERROR FATAL: Token Telegram tidak ditemukan di .env!")
    exit()

# --- [PENTING] INISIALISASI BOT DISINI ---
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# --- GLOBAL VARIABLES ---
SENTRY_ACTIVE = False
SENTRY_THREAD = None

# --- SETUP GEMINI AI ---
AI_ACTIVE = False
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-2.5-flash')
        AI_ACTIVE = True
        print("🧠 AI CORE: ONLINE (Gemini 2.5 Flash - VISION READY)")
    except Exception as e:
        print(f"⚠️ AI CORE ERROR: {e}")
else:
    print("⚠️ AI CORE: OFFLINE")

# --- SETUP FOLDER ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCREENSHOT_DIR = os.path.join(BASE_DIR, "storage", "screenshots")
WEBCAM_DIR = os.path.join(BASE_DIR, "storage", "webcam")
VIDEO_DIR = os.path.join(BASE_DIR, "storage", "videos") 
TEMP_IMG_DIR = os.path.join(BASE_DIR, "storage", "temp_images")

os.makedirs(SCREENSHOT_DIR, exist_ok=True)
os.makedirs(WEBCAM_DIR, exist_ok=True)
os.makedirs(VIDEO_DIR, exist_ok=True)
os.makedirs(TEMP_IMG_DIR, exist_ok=True)

print("🤖 IT-OPS COMMANDER: ONLINE & READY...")

# --- KEAMANAN ---
def is_authorized(message):
    if message.chat.id != MY_CHAT_ID:
        bot.reply_to(message, "⛔ AKSES DITOLAK! Anda bukan Komandan saya.")
        return False
    return True

# ==========================================
# 🛡️ FUNGSI SENTRY MODE (SATPAM AI)
# ==========================================
def sentry_mode_task():
    global SENTRY_ACTIVE
    print("🛡️ SENTRY MODE: ACTIVATED")
    cap = cv2.VideoCapture(0)
    ret, frame1 = cap.read()
    ret, frame2 = cap.read()
    
    while SENTRY_ACTIVE and cap.isOpened():
        diff = cv2.absdiff(frame1, frame2)
        gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5,5), 0)
        _, thresh = cv2.threshold(blur, 20, 255, cv2.THRESH_BINARY)
        dilated = cv2.dilate(thresh, None, iterations=3)
        contours, _ = cv2.findContours(dilated, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        
        motion_detected = False
        for contour in contours:
            if cv2.contourArea(contour) < 5000: continue
            motion_detected = True
        
        if motion_detected:
            print("🚨 GERAKAN TERDETEKSI!")
            file_ts = datetime.now().strftime("%H%M%S")
            filepath = os.path.join(WEBCAM_DIR, f"INTRUDER_{file_ts}.jpg")
            cv2.imwrite(filepath, frame1)
            try:
                with open(filepath, 'rb') as photo:
                    bot.send_photo(MY_CHAT_ID, photo, caption="🚨 <b>SENTRY ALERT!</b>", parse_mode="HTML")
            except: pass
            time.sleep(5)
            ret, frame1 = cap.read()
            ret, frame2 = cap.read()
        else:
            frame1 = frame2
            ret, frame2 = cap.read()
        time.sleep(0.1)
    cap.release()
    print("🛡️ SENTRY MODE: DEACTIVATED")

# ==========================================
# 📡 FUNGSI PELAPOR (SYS GAZE REPORTER)
# ==========================================
def task_report_to_dashboard():
    time.sleep(3) 
    while True:
        try:
            cpu = psutil.cpu_percent()
            ram = psutil.virtual_memory().percent
            payload = {'name': 'COMMANDER-LAPTOP', 'cpu': cpu, 'ram': ram}
            requests.post("http://127.0.0.1:5000/api/agent/report", json=payload, timeout=1)
        except: pass 
        time.sleep(2)

# ==========================================
# FUNGSI AI (TEXT & VISION)
# ==========================================
def ask_ai_text(text):
    if not AI_ACTIVE: return "⚠️ Fitur AI mati."
    try:
        prompt = "Kamu Jarvis, asisten IT. Jawab ringkas:\n" + text
        response = model.generate_content(prompt)
        return response.text
    except Exception as e: return f"❌ Error AI: {e}"

def ask_ai_vision(image_path, caption="Jelaskan gambar ini"):
    if not AI_ACTIVE: return "⚠️ Fitur AI mati."
    try:
        img = PIL.Image.open(image_path)
        prompt = "Analisa gambar ini. " + (caption if caption else "")
        response = model.generate_content([prompt, img])
        return response.text
    except Exception as e: return f"❌ Error Vision: {e}"

# ==========================================
# FUNGSI PENDUKUNG
# ==========================================
def speak_text(text):
    def run_speech():
        try:
            tts = gTTS(text=text, lang='id') 
            filename = f"voice_{int(time.time())}.mp3"
            tts.save(filename)
            pygame.mixer.init()
            pygame.mixer.music.load(filename)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy(): pygame.time.Clock().tick(10)
            pygame.mixer.quit()
            os.remove(filename)
        except: pass
    t = threading.Thread(target=run_speech)
    t.start()

def show_hacker_alert_ui(message_text):
    speak_text(f"Peringatan! {message_text}")
    root = tk.Tk()
    root.attributes('-fullscreen', True)
    root.attributes('-topmost', True)
    root.configure(bg='black')
    root.overrideredirect(True)
    header_font = tkfont.Font(family="Courier New", size=40, weight="bold")
    msg_font = tkfont.Font(family="Courier New", size=28)
    btn_font = tkfont.Font(family="Courier New", size=14, weight="bold")
    frame = tk.Frame(root, bg='black')
    frame.pack(expand=True)
    tk.Label(frame, text="⚠️ SYSTEM ALERT ⚠️", font=header_font, fg="#ff0000", bg="black").pack(pady=(0, 60))
    tk.Label(frame, text=message_text, font=msg_font, fg="#00ff00", bg="black", wraplength=900, justify="center").pack(pady=(0, 120))
    def close_alert(): root.destroy()
    tk.Button(frame, text="[ ACKNOWLEDGE ]", font=btn_font, command=close_alert,
              fg="white", bg="#222222", activebackground="#444444", activeforeground="white",
              bd=2, relief="ridge", padx=30, pady=15, cursor="hand2").pack()
    root.mainloop()

def record_screen_task(chat_id, duration=5):
    try:
        screen_size = pyautogui.size()
        file_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"rec_{file_ts}.avi"
        filepath = os.path.join(VIDEO_DIR, filename)
        fourcc = cv2.VideoWriter_fourcc(*"XVID")
        fps = 10.0 
        out = cv2.VideoWriter(filepath, fourcc, fps, screen_size)
        start_time = time.time()
        while (time.time() - start_time) < duration:
            img = pyautogui.screenshot()
            frame = np.array(img)
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            out.write(frame)
        out.release()
        with open(filepath, 'rb') as video:
            bot.send_video(chat_id, video, caption=f"🎬 **Rec** ({duration}s)", parse_mode="Markdown")
    except Exception as e:
        bot.send_message(chat_id, f"❌ Gagal merekam: {e}")

# --- COMMAND HANDLERS ---

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    if not is_authorized(message): return
    speak_text("Halo Komandan. Sistem Full Akses Siap.") 
    help_text = """
🔥 **COMMAND CENTER V4.0 (ENTERTAINMENT)**

🎮 **MEDIA & CONTROL (BARU)**
/vol [0-100] - Atur Volume (Cth: /vol 50)
/mute - Matikan Suara
/play - Play / Pause Media
/next - Lagu Selanjutnya
/prev - Lagu Sebelumnya
/type [teks] - Ngetik di Laptop

🛡️ **SECURITY & SENTRY**
/guard - ON Sentry Mode
/relax - OFF Sentry Mode

⚡ **POWER & UTILITY**
/shutdown, /restart, /lock
/cam, /screen, /record
/say, /msg, /open
/report - Download PDF
    """
    bot.reply_to(message, help_text, parse_mode="Markdown")

# --- GROUP: MEDIA & VOLUME (BARU!) ---
@bot.message_handler(commands=['vol'])
def set_volume(message):
    if not is_authorized(message): return
    args = message.text.split()
    if len(args) > 1:
        try:
            level = int(args[1])
            # Konversi 0-100 ke jumlah ketukan tombol (windows volume step biasanya 2)
            # Ini simulasi kasar, 50 kali tekan volumeup/down
            # Cara lebih akurat pakai library pycaw, tapi kita pakai pyautogui biar ga perlu install library baru
            bot.reply_to(message, f"🔊 Mengatur volume ke sekitar {level}%...")
            
            # Reset ke 0 dulu
            for _ in range(50): pyautogui.press('volumedown')
            # Naikkan sesuai level (dibagi 2 karena 1 tekan = 2%)
            for _ in range(int(level / 2)): pyautogui.press('volumeup')
        except: bot.reply_to(message, "❌ Format salah. Cth: /vol 50")
    else:
        bot.reply_to(message, "ℹ️ Masukkan angka 0-100. Cth: /vol 50")

@bot.message_handler(commands=['mute'])
def toggle_mute(message):
    if not is_authorized(message): return
    pyautogui.press('volumemute')
    bot.reply_to(message, "🔇 Mute Toggled.")

@bot.message_handler(commands=['play', 'pause'])
def toggle_play(message):
    if not is_authorized(message): return
    pyautogui.press('playpause')
    bot.reply_to(message, "⏯️ Play/Pause.")

@bot.message_handler(commands=['next'])
def next_track(message):
    if not is_authorized(message): return
    pyautogui.press('nexttrack')
    bot.reply_to(message, "⏭️ Next Song.")

@bot.message_handler(commands=['prev'])
def prev_track(message):
    if not is_authorized(message): return
    pyautogui.press('prevtrack')
    bot.reply_to(message, "⏮️ Prev Song.")

@bot.message_handler(commands=['type'])
def remote_type(message):
    if not is_authorized(message): return
    text = message.text.replace("/type", "").strip()
    if not text: return
    bot.reply_to(message, f"⌨️ Mengetik: '{text}'")
    pyautogui.write(text, interval=0.1)

# --- GROUP: SENTRY MODE ---
@bot.message_handler(commands=['guard'])
def activate_sentry(message):
    global SENTRY_ACTIVE, SENTRY_THREAD
    if not is_authorized(message): return
    if SENTRY_ACTIVE:
        bot.reply_to(message, "🛡️ Sentry Mode SUDAH AKTIF.")
        return
    SENTRY_ACTIVE = True
    SENTRY_THREAD = threading.Thread(target=sentry_mode_task)
    SENTRY_THREAD.daemon = True
    SENTRY_THREAD.start()
    bot.reply_to(message, "🛡️ **SENTRY MODE: ON**", parse_mode="Markdown")
    speak_text("Mode Satpam Aktif.")

@bot.message_handler(commands=['relax'])
def deactivate_sentry(message):
    global SENTRY_ACTIVE
    if not is_authorized(message): return
    if not SENTRY_ACTIVE:
        bot.reply_to(message, "☕ Sudah santai kok.")
        return
    SENTRY_ACTIVE = False
    bot.reply_to(message, "🛡️ **SENTRY MODE: OFF**", parse_mode="Markdown")
    speak_text("Mode Satpam Nonaktif.")

# --- GROUP: SURVEILLANCE & MEDIA ---
@bot.message_handler(commands=['cam'])
def snap_webcam(message):
    if not is_authorized(message): return
    if SENTRY_ACTIVE:
        bot.reply_to(message, "⚠️ Matikan /relax dulu!", parse_mode="Markdown")
        return
    bot.send_chat_action(message.chat.id, 'upload_photo')
    filepath = os.path.join(WEBCAM_DIR, f"cam_{int(time.time())}.jpg")
    try:
        cap = cv2.VideoCapture(0)
        ret, frame = cap.read()
        cap.release()
        if ret:
            cv2.imwrite(filepath, frame)
            with open(filepath, 'rb') as photo: bot.send_photo(message.chat.id, photo)
        else: bot.reply_to(message, "❌ Kamera error")
    except: bot.reply_to(message, "❌ Gagal akses kamera")

@bot.message_handler(commands=['screen'])
def take_screenshot(message):
    if not is_authorized(message): return
    bot.send_chat_action(message.chat.id, 'upload_photo')
    filepath = os.path.join(SCREENSHOT_DIR, f"cap_{int(time.time())}.png")
    try:
        pyautogui.screenshot().save(filepath)
        with open(filepath, 'rb') as photo: bot.send_photo(message.chat.id, photo)
    except: bot.reply_to(message, "❌ Gagal screenshot")

@bot.message_handler(commands=['record'])
def command_record(message):
    if not is_authorized(message): return
    args = message.text.split()
    duration = 5 
    if len(args) > 1:
        try: duration = int(args[1])
        except: pass
    bot.reply_to(message, f"🎥 Merekam {duration}s...")
    threading.Thread(target=record_screen_task, args=(message.chat.id, duration)).start()

@bot.message_handler(commands=['report'])
def send_report_pdf(message):
    if not is_authorized(message): return
    if generate_pdf:
        bot.reply_to(message, "📄 Generating PDF Report...")
        try:
            pdf_path = generate_pdf()
            with open(pdf_path, 'rb') as doc: bot.send_document(message.chat.id, doc)
        except Exception as e: bot.reply_to(message, f"❌ Gagal: {e}")
    else: bot.reply_to(message, "❌ File reporter.py hilang!")

@bot.message_handler(commands=['status'])
def check_status(message):
    if not is_authorized(message): return
    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory().percent
    bot.reply_to(message, f"📊 **STATUS:**\n🔥 CPU: {cpu}%\n💾 RAM: {ram}%")

@bot.message_handler(commands=['public'])
def get_public_url(message):
    if not is_authorized(message): return
    try:
        response = requests.get("http://127.0.0.1:4040/api/tunnels")
        data = json.loads(response.text)
        public_url = data['tunnels'][0]['public_url']
        bot.reply_to(message, f"🌐 Link: {public_url}")
    except: bot.reply_to(message, "❌ Ngrok Offline")

# --- GROUP: UTILITY & POWER ---
@bot.message_handler(commands=['say'])
def command_say(message):
    if not is_authorized(message): return
    text = message.text.replace("/say", "").strip()
    if not text: return
    bot.reply_to(message, f"🗣️ Mengucapkan...")
    speak_text(text)

@bot.message_handler(commands=['msg'])
def send_hacker_message(message):
    if not is_authorized(message): return
    text = message.text.replace("/msg", "").strip()
    threading.Thread(target=show_hacker_alert_ui, args=(text,)).start()
    bot.reply_to(message, "☠️ Alert Sent.")

@bot.message_handler(commands=['open'])
def open_website(message):
    if not is_authorized(message): return
    url = message.text.replace("/open", "").strip()
    if not url: return
    if not url.startswith("http"): url = "https://" + url
    bot.reply_to(message, f"🌐 Opening: {url}")
    webbrowser.open(url)
    speak_text("Membuka website.")

@bot.message_handler(commands=['clean'])
def run_cleaner_command(message):
    if not is_authorized(message): return
    try:
        cleaner.sweep_root_folder()
        cleaner.clean_old_archives()
        bot.reply_to(message, "✅ System Cleaned.")
        speak_text("File sampah dibersihkan.")
    except: bot.reply_to(message, "❌ Gagal")

@bot.message_handler(commands=['lock'])
def lock_pc(message):
    if not is_authorized(message): return
    os.system("rundll32.exe user32.dll,LockWorkStation")
    bot.reply_to(message, "🔒 Locked.")

@bot.message_handler(commands=['restart'])
def restart_pc(message):
    if not is_authorized(message): return
    speak_text("Restarting System.")
    os.system("shutdown /r /t 5")
    bot.reply_to(message, "🔄 Restarting (5s)...")

@bot.message_handler(commands=['shutdown'])
def shutdown_pc(message):
    if not is_authorized(message): return
    speak_text("Shutting Down.")
    os.system("shutdown /s /t 5")
    bot.reply_to(message, "🔌 Shutdown (5s)...")

# --- AI HANDLERS ---
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    if not is_authorized(message): return
    bot.send_chat_action(message.chat.id, 'typing')
    bot.reply_to(message, "👀 Melihat gambar...")
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        temp_path = os.path.join(TEMP_IMG_DIR, f"vision_{int(time.time())}.jpg")
        with open(temp_path, 'wb') as new_file: new_file.write(downloaded_file)
        caption = message.caption if message.caption else "Apa ini?"
        ai_reply = ask_ai_vision(temp_path, caption)
        os.remove(temp_path)
        bot.reply_to(message, ai_reply) 
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

@bot.message_handler(func=lambda message: True)
def handle_text_message(message):
    if not is_authorized(message): return
    bot.send_chat_action(message.chat.id, 'typing')
    ai_reply = ask_ai_text(message.text)
    bot.reply_to(message, ai_reply) 

# --- MAIN LOOP ---
if __name__ == "__main__":
    t_report = threading.Thread(target=task_report_to_dashboard)
    t_report.daemon = True 
    t_report.start()
    
    print("🔄 Menghubungkan ke Server Telegram...")
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60, skip_pending=True)
        except requests.exceptions.ReadTimeout:
            print("⚠️ Timeout. Retry...")
            time.sleep(1)
        except Exception as e:
            print(f"❌ Error: {e}")
            time.sleep(5)
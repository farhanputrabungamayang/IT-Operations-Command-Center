import os
import threading
import time

# --- THIRD-PARTY IMPORTS ---
import psutil
import requests
from dotenv import load_dotenv
from flask import Flask, render_template
from flask_socketio import SocketIO

# Load Environment Variables (.env)
load_dotenv()

app = Flask(__name__)
# Ambil SECRET_KEY dari .env (Fallback ke default kalau gagal)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'sysgaze-default-secret')

# Port 5001 (Beda dengan NetWatch yang 5000)
# Gunakan async_mode='threading' agar kompatibel di Windows
socketio = SocketIO(app, cors_allowed_origins='*', async_mode='threading')

# --- KONFIGURASI TELEGRAM (Aman dari .env) ---
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# --- KONFIGURASI ALARM ---
CPU_THRESHOLD = 85   # Persen
RAM_THRESHOLD = 90   # Persen
DISK_THRESHOLD = 90  # Persen (Storage Penuh)
ALERT_COOLDOWN = 60  # Jeda antar notif (detik)

last_alert_time = 0 

@app.route('/')
def index():
    # Render file templates/index.html
    return render_template('index.html')

def send_telegram_alert(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID: return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
        requests.post(url, data=data)
        print(f"⚠️ Telegram Alert Sent: {message}")
    except Exception as e:
        print(f"❌ Failed to send alert: {e}")

def get_system_stats():
    # 1. CPU
    cpu = psutil.cpu_percent(interval=1)
    
    # 2. RAM
    ram = psutil.virtual_memory()
    ram_percent = ram.percent
    ram_used = round(ram.used / (1024**3), 2)
    ram_total = round(ram.total / (1024**3), 2)
    
    # 3. MULTI-DISK MONITORING (Cerdas!)
    disks = []
    try:
        partitions = psutil.disk_partitions()
        for p in partitions:
            # Filter: Abaikan CD-ROM atau drive kosong
            if 'cdrom' in p.opts or p.fstype == '':
                continue
            try:
                usage = psutil.disk_usage(p.mountpoint)
                disks.append({
                    'letter': p.device.replace('\\', ''), # Contoh: "C:" atau "D:"
                    'percent': usage.percent,
                    'free': f"{round(usage.free / (1024**3), 1)} GB Free"
                })
            except:
                continue
    except:
        pass # Fallback kalau gagal baca disk

    # 4. Uptime
    boot_time = psutil.boot_time()
    uptime_seconds = time.time() - boot_time
    uptime_hours = round(uptime_seconds / 3600, 1)

    return {
        'cpu': cpu,
        'ram_percent': ram_percent,
        'ram_text': f"{ram_used}/{ram_total} GB",
        'disks': disks, # Kirim list semua drive
        'uptime': f"{uptime_hours} Hours"
    }

def monitor_task():
    global last_alert_time
    print("🚀 SysGaze ULTIMATE Multi-Drive Started (Port 5001)...")
    
    while True:
        try:
            stats = get_system_stats()
            
            # --- LOGIKA KECERDASAN BUATAN (TELEGRAM ALERT) ---
            current_time = time.time()
            
            # Cek apakah sudah lewat masa cooldown
            if (current_time - last_alert_time) > ALERT_COOLDOWN:
                alert_msg = ""
                
                # Cek Bahaya CPU
                if stats['cpu'] > CPU_THRESHOLD:
                    alert_msg += f"🔥 CPU CRITICAL: {stats['cpu']}%\n"
                
                # Cek Bahaya RAM
                if stats['ram_percent'] > RAM_THRESHOLD:
                    alert_msg += f"💾 RAM FULL: {stats['ram_percent']}%\n"
                
                # Cek Bahaya SEMUA DISK
                for d in stats['disks']:
                    if d['percent'] > DISK_THRESHOLD:
                        alert_msg += f"💿 {d['letter']} FULL: {d['percent']}%\n"
                
                # Kalau ada bahaya, kirim Telegram
                if alert_msg:
                    full_msg = f"🚨 [SYSGAZE ALERT] 🚨\n\n{alert_msg}\nCheck Dashboard Immediately!"
                    send_telegram_alert(full_msg)
                    last_alert_time = current_time # Reset waktu cooldown

            socketio.emit('update_stats', stats)
            
        except Exception as e:
            print(f"Error Monitor: {e}")

        # Delay dikit biar gak makan resource
        time.sleep(1)

if __name__ == '__main__':
    socketio.start_background_task(monitor_task)
    # Debug False WAJIB biar monitoring jalan lancar dan gak double run
    # Allow unsafe werkzeug biar bisa jalan di environment windows tertentu
    socketio.run(app, host='0.0.0.0', port=5001, debug=False, allow_unsafe_werkzeug=True)
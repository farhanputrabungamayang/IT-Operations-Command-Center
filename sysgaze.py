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
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'sysgaze-default-secret')

# SETUP SOCKET IO
# cors_allowed_origins='*' PENTING biar HTML bisa akses dari mana aja
# async_mode='threading' PENTING buat Windows
socketio = SocketIO(app, cors_allowed_origins='*', async_mode='threading')

# --- KONFIGURASI TELEGRAM ---
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# --- KONFIGURASI ALARM ---
CPU_THRESHOLD = 85   
RAM_THRESHOLD = 90   
DISK_THRESHOLD = 90  
ALERT_COOLDOWN = 60  

last_alert_time = 0 

@app.route('/')
def index():
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
    
    # 3. DISK
    disks = []
    try:
        partitions = psutil.disk_partitions()
        for p in partitions:
            if 'cdrom' in p.opts or p.fstype == '': continue
            try:
                usage = psutil.disk_usage(p.mountpoint)
                disks.append({
                    'letter': p.device.replace('\\', ''),
                    'percent': usage.percent,
                    'free': f"{round(usage.free / (1024**3), 1)} GB Free"
                })
            except: continue
    except: pass

    # 4. Uptime
    boot_time = psutil.boot_time()
    uptime_seconds = time.time() - boot_time
    uptime_hours = round(uptime_seconds / 3600, 1)

    return {
        'cpu': cpu,
        'ram_percent': ram_percent,
        'ram_text': f"{ram_used}/{ram_total} GB",
        'disks': disks,
        'uptime': f"{uptime_hours} Hours"
    }

def monitor_task():
    global last_alert_time
    print("🚀 SysGaze ULTIMATE Multi-Drive Started (Port 5001)...")
    
    while True:
        try:
            # DEBUGGING: Print ini akan muncul tiap detik kalau Python SEHAT
            print("💓 Denyut Nadi: Mengirim Data ke Dashboard...") 
            
            stats = get_system_stats()
            
            # --- LOGIKA TELEGRAM ALERT ---
            current_time = time.time()
            if (current_time - last_alert_time) > ALERT_COOLDOWN:
                alert_msg = ""
                if stats['cpu'] > CPU_THRESHOLD: alert_msg += f"🔥 CPU CRITICAL: {stats['cpu']}%\n"
                if stats['ram_percent'] > RAM_THRESHOLD: alert_msg += f"💾 RAM FULL: {stats['ram_percent']}%\n"
                for d in stats['disks']:
                    if d['percent'] > DISK_THRESHOLD: alert_msg += f"💿 {d['letter']} FULL: {d['percent']}%\n"
                
                if alert_msg:
                    send_telegram_alert(f"🚨 [SYSGAZE ALERT] 🚨\n\n{alert_msg}")
                    last_alert_time = current_time

            socketio.emit('update_stats', stats)
            
        except Exception as e:
            print(f"Error Monitor: {e}")

        time.sleep(1)

if __name__ == '__main__':
    socketio.start_background_task(monitor_task)
    # Debug=False dan allow_unsafe_werkzeug WAJIB
    socketio.run(app, host='0.0.0.0', port=5001, debug=False, allow_unsafe_werkzeug=True)
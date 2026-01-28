import time
import psutil
import requests
import socket

# --- KONFIGURASI ---
# IP Server NetWatch Masbro. 
# Kalau ngetes di laptop sendiri pake 'http://127.0.0.1:5000'
# Kalau dipasang di laptop adik/teman, ganti jadi IP Laptop Masbro (misal 'http://192.168.1.10:5000')
SERVER_URL = 'http://127.0.0.1:5000/api/agent/report'

# Nama Identitas Agent ini
AGENT_NAME = f"Laptop-{socket.gethostname()}"

print(f"🕵️‍♂️ AGENT '{AGENT_NAME}' STARTED...")
print(f"📡 Target Server: {SERVER_URL}")

while True:
    try:
        # 1. Ambil Data Diri Sendiri
        cpu = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory().percent
        
        payload = {
            "name": AGENT_NAME,
            "cpu": cpu,
            "ram": ram
        }
        
        # 2. Kirim Laporan ke Bos (Server NetWatch)
        response = requests.post(SERVER_URL, json=payload, timeout=2)
        
        if response.status_code == 200:
            print(f"✅ Laporan Terkirim: CPU {cpu}% | RAM {ram}%")
        else:
            print(f"⚠️ Server Menolak: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Gagal Lapor: {e}")
        print("Mencoba lagi dalam 5 detik...")
    
    # Lapor setiap 3 detik
    time.sleep(3)
import subprocess
import time
import sys
import os
import signal

# --- KONFIGURASI ---
scripts = [
    {"name": "NetWatch Security", "file": "netwatch.py",  "port": 5000},
    {"name": "SysGaze Monitor",   "file": "sysgaze.py",   "port": 5001},
    {"name": "IT-Ops Commander",  "file": "commander.py", "port": None},
    {"name": "The Cleaner",       "file": "cleaner.py",   "port": None}
]

processes = []

def start_services():
    print("🚀 INITIALIZING IT-OPS SILENT PROTOCOL...")
    print("==========================================")
    
    for item in scripts:
        if not os.path.exists(item['file']):
            print(f"❌ File hilang: {item['file']}")
            continue

        print(f"✅ Starting {item['name']}...", end=" ")
        
        # --- TEKNIK RAHASIA: MATIKAN POPUP WINDOW ---
        # creationflags=0x08000000 (CREATE_NO_WINDOW) -> Khusus Windows biar gak muncul CMD baru
        # stdout=subprocess.DEVNULL -> Biar log-nya gak nyampur di sini (jadi bersih)
        
        if sys.platform == "win32":
            CREATE_NO_WINDOW = 0x08000000
            p = subprocess.Popen(
                ["python", item['file']],
                creationflags=CREATE_NO_WINDOW,
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.DEVNULL
            )
        else:
            # Buat Linux/Mac
            p = subprocess.Popen(
                ["python", item['file']],
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.DEVNULL
            )
            
        processes.append(p)
        print("OK! [Background Mode]")
        time.sleep(1)

    print("==========================================")
    print("💻 STATUS: ALL SYSTEMS RUNNING.")
    print("ℹ️  Web Dashboard: http://127.0.0.1:5000")
    print("🛑 Tekan CTRL + C di sini untuk mematikan SEMUA bot.")

def stop_services():
    print("\n\n🛑 Shutting down all services...")
    for p in processes:
        try:
            p.terminate() # Bunuh proses secara halus
        except:
            pass
    print("✅ All services stopped. Bye!")

# --- JALANKAN ---
if __name__ == '__main__':
    try:
        start_services()
        # Loop biar script induk gak mati (Keep Alive)
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        # Kalau user tekan Ctrl+C, matikan semua anak buahnya
        stop_services()
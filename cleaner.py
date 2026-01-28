import os
import time
import shutil
import sys
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# --- KONFIGURASI PATH ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOADS_DIR = os.path.join(os.path.expanduser("~"), "Downloads")

# Folder Tujuan Arsip
SCREENSHOT_DIR = os.path.join(BASE_DIR, "storage", "screenshots")
REPORT_DIR = os.path.join(BASE_DIR, "storage", "reports")

# Pastikan folder tujuan ada
os.makedirs(SCREENSHOT_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)

# Folder yang akan dipantau umurnya (untuk dihapus)
FOLDERS_TO_CLEAN = [SCREENSHOT_DIR, REPORT_DIR]
MAX_AGE_DAYS = 7 

# Konfigurasi Sortir Downloads
DEST_DIRS = {
    "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp"],
    "Documents": [".pdf", ".docx", ".doc", ".txt", ".ppt", ".pptx", ".xlsx", ".csv"],
    "Installers": [".exe", ".msi", ".bat", ".apk", ".iso"],
    "Archives": [".zip", ".rar", ".7z", ".tar", ".gz"],
    "Videos": [".mp4", ".mkv", ".avi", ".mov"],
    "Music": [".mp3", ".wav"],
    "Code": [".py", ".html", ".css", ".js", ".json"]
}

# ==========================================
# BAGIAN 1: SAPU JAGAT (ROOT SWEEPER) - BARU!
# ==========================================
def sweep_root_folder():
    print("🧹 [ROOT SWEEPER] Merapikan file yang berceceran di folder utama...")
    moved_count = 0
    
    # Scan semua file di folder utama project
    for filename in os.listdir(BASE_DIR):
        filepath = os.path.join(BASE_DIR, filename)
        
        # Skip kalau itu folder
        if not os.path.isfile(filepath):
            continue
            
        # 1. Pindahkan Screenshot Nyasar
        if filename.startswith("capture_") and filename.endswith(".png"):
            shutil.move(filepath, os.path.join(SCREENSHOT_DIR, filename))
            print(f"   📦 Mengamankan Screenshot: {filename}")
            moved_count += 1
            
        # 2. Pindahkan Report Nyasar
        elif filename.startswith("Report_") and filename.endswith(".pdf"):
            shutil.move(filepath, os.path.join(REPORT_DIR, filename))
            print(f"   📦 Mengamankan Laporan: {filename}")
            moved_count += 1
            
    if moved_count > 0:
        print(f"✅ {moved_count} file berhasil dipindahkan ke folder 'storage'.")
    else:
        print("✅ Folder utama sudah bersih/rapi.")

# ==========================================
# BAGIAN 2: PENGHAPUS ARSIP TUA (> 7 HARI)
# ==========================================
def clean_old_archives():
    print("\n🗑️ [ARCHIVE CLEANER] Mencari file kadaluarsa (> 7 hari)...")
    deleted_count = 0
    now = time.time()
    max_age_seconds = MAX_AGE_DAYS * 24 * 60 * 60

    for folder in FOLDERS_TO_CLEAN:
        if not os.path.exists(folder): continue
            
        print(f"   📂 Scanning isi: {folder}...")
        for filename in os.listdir(folder):
            filepath = os.path.join(folder, filename)
            
            if not os.path.isfile(filepath): continue
                
            # Cek Umur File
            file_age = now - os.path.getmtime(filepath)
            
            if file_age > max_age_seconds:
                try:
                    os.remove(filepath)
                    print(f"      ❌ Dihapus (Expired): {filename}")
                    deleted_count += 1
                except Exception as e:
                    print(f"      ⚠️ Gagal hapus {filename}: {e}")

    print(f"✅ Selesai. Total sampah dihapus: {deleted_count}")

# ==========================================
# BAGIAN 3: SATPAM DOWNLOADS (WATCHDOG)
# ==========================================
class MoverHandler(FileSystemEventHandler):
    def on_modified(self, event):
        with os.scandir(DOWNLOADS_DIR) as entries:
            for entry in entries:
                self.move_file(entry)

    def move_file(self, entry):
        if entry.is_file():
            name = entry.name
            ext = os.path.splitext(name)[1].lower()
            if ext in ['.tmp', '.crdownload', '.part', '.ini']: return 

            for category, extensions in DEST_DIRS.items():
                if ext in extensions:
                    target_folder = os.path.join(DOWNLOADS_DIR, category)
                    os.makedirs(target_folder, exist_ok=True)
                    destination = os.path.join(target_folder, name)
                    
                    if os.path.exists(destination):
                        timestamp = int(time.time())
                        new_name = f"{os.path.splitext(name)[0]}_{timestamp}{ext}"
                        destination = os.path.join(target_folder, new_name)

                    try:
                        time.sleep(0.5)
                        shutil.move(entry.path, destination)
                        print(f"📦 [DOWNLOADS] Moved: {name} -> {category}")
                    except: pass
                    break

def start_watchdog():
    print(f"\n👀 [CLEANER BOT] STANDBY Memantau Folder Downloads...")
    event_handler = MoverHandler()
    observer = Observer()
    observer.schedule(event_handler, DOWNLOADS_DIR, recursive=False)
    observer.start()
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

# ==========================================
# MAIN EXECUTION
# ==========================================
if __name__ == "__main__":
    # 1. Jalankan Sapu Jagat (Rapikan folder utama)
    sweep_root_folder()
    
    # 2. Jalankan Penghapus File Tua
    clean_old_archives()

    # 3. Cek Mode (Bot atau Manual)
    if len(sys.argv) > 1 and sys.argv[1] == "once":
        print("\n🤖 Mode Bot: Tugas Selesai. Exiting...")
    else:
        start_watchdog()
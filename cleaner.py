import os
import time
import shutil
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# --- KONFIGURASI FOLDER TARGET (AUTO DETECT) ---
# os.path.expanduser("~") itu otomatis ngambil "C:\Users\NamaMasbro"
source_dir = os.path.join(os.path.expanduser("~"), "Downloads")

# Kategori File & Tujuannya
dest_dirs = {
    "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp"],
    "Documents": [".pdf", ".docx", ".doc", ".txt", ".ppt", ".pptx", ".xlsx", ".csv"],
    "Installers": [".exe", ".msi", ".bat", ".apk", ".iso"],
    "Archives": [".zip", ".rar", ".7z", ".tar", ".gz"],
    "Videos": [".mp4", ".mkv", ".avi", ".mov"],
    "Music": [".mp3", ".wav"]
}

class MoverHandler(FileSystemEventHandler):
    def on_modified(self, event):
        # Scan folder setiap ada perubahan
        with os.scandir(source_dir) as entries:
            for entry in entries:
                self.move_file(entry)

    def move_file(self, entry):
        # 1. Cek apakah ini file beneran (bukan folder)
        if entry.is_file():
            name = entry.name
            ext = os.path.splitext(name)[1].lower()

            # 2. LOGIKA ANTI-CORRUPT (PENTING!)
            # Jangan pindahin kalau masih download (.tmp / .crdownload)
            if ext in ['.tmp', '.crdownload', '.part', '.ini']:
                return 

            # 3. Cek Kategori & Pindahkan
            for category, extensions in dest_dirs.items():
                if ext in extensions:
                    # Buat path folder tujuan (Misal: Downloads/Images)
                    target_folder = os.path.join(source_dir, category)
                    os.makedirs(target_folder, exist_ok=True)
                    
                    # Cek kalau file udah ada, ganti nama biar gak ketimpa
                    destination = os.path.join(target_folder, name)
                    if os.path.exists(destination):
                        timestamp = int(time.time())
                        new_name = f"{os.path.splitext(name)[0]}_{timestamp}{ext}"
                        destination = os.path.join(target_folder, new_name)

                    # Eksekusi Pindah
                    try:
                        shutil.move(entry.path, destination)
                        print(f"🧹 Moved: {name} -> {category}")
                    except Exception as e:
                        print(f"❌ Error moving {name}: {e}")
                    break

if __name__ == "__main__":
    print(f"👀 CLEANER BOT STANDBY di: {source_dir}")
    print("Tekan Ctrl + C untuk stop.")
    
    event_handler = MoverHandler()
    observer = Observer()
    observer.schedule(event_handler, source_dir, recursive=False)
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
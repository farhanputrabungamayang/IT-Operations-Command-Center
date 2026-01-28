import os
import socket
import threading
import time
import sqlite3
import random  # <-- PENTING BUAT ANGKA ACAK
from datetime import datetime

# --- THIRD-PARTY IMPORTS ---
import requests
# import speedtest  <-- KITA MATIKAN BIAR GAK BERAT
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy
from ping3 import ping
from werkzeug.security import generate_password_hash, check_password_hash

# Load Environment Variables (.env)
load_dotenv()

app = Flask(__name__)

# --- KONFIGURASI ---
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default-dev-key')

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///netwatch.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Gunakan 'threading' agar kompatibel
socketio = SocketIO(app, cors_allowed_origins='*', async_mode='threading')

# --- DATA PENYIMPANAN SEMENTARA (RAM) ---
remote_agents = {} 

# --- DATABASE MODELS ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    password_hash = db.Column(db.String(200))
    def check_password(self, pwd): return check_password_hash(self.password_hash, pwd)

@login_manager.user_loader
def load_user(id): return User.query.get(int(id))

class Device(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    ip = db.Column(db.String(20), nullable=False)
    port = db.Column(db.Integer, default=0) 
    icon = db.Column(db.String(30), default='bi-hdd-network')

class EventLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    device_name = db.Column(db.String(100))
    status = db.Column(db.String(10))
    timestamp = db.Column(db.DateTime, default=datetime.now)
    message = db.Column(db.String(200))

class PingHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer)
    latency = db.Column(db.Integer) # ms
    timestamp = db.Column(db.DateTime, default=datetime.now)

# Global Vars
last_status_map = {}
latest_speed = {'dl': '--', 'ul': '--', 'ping': '--'}

# --- HELPERS ---
def send_telegram(msg):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID: return
    try: requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", data={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"})
    except: pass

def check_port_open(ip, port):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        res = sock.connect_ex((ip, int(port)))
        sock.close()
        return res == 0
    except: return False

# --- ROUTES ---
@app.route('/')
@login_required
def index():
    devices = Device.query.all()
    return render_template('dashboard_ultimate.html', targets=devices, speed=latest_speed, agents=remote_agents)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = User.query.filter_by(username=request.form['username']).first()
        if u and u.check_password(request.form['password']):
            login_user(u)
            return redirect(url_for('index'))
        flash('Login Gagal! Cek username/password.')
    return render_template('login.html')

@app.route('/logout')
def logout(): logout_user(); return redirect(url_for('login'))

@app.route('/add_device', methods=['POST'])
@login_required
def add_device():
    db.session.add(Device(name=request.form['name'], ip=request.form['ip'], port=int(request.form['port']), icon=request.form['icon']))
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/delete_device/<int:id>')
@login_required
def delete_device(id):
    d = Device.query.get(id)
    if d: 
        PingHistory.query.filter_by(device_id=id).delete()
        db.session.delete(d)
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/api/chart/<int:device_id>')
@login_required
def api_chart(device_id):
    data = PingHistory.query.filter_by(device_id=device_id).order_by(PingHistory.timestamp.desc()).limit(20).all()
    data.reverse()
    return jsonify({
        'labels': [d.timestamp.strftime('%H:%M:%S') for d in data],
        'values': [d.latency for d in data]
    })

# --- [API] UNTUK NERIMA LAPORAN AGENT ---
@app.route('/api/agent/report', methods=['POST'])
def agent_report():
    try:
        data = request.json
        agent_name = data.get('name')
        remote_agents[agent_name] = {
            'cpu': data.get('cpu'),
            'ram': data.get('ram'),
            'ip': request.remote_addr, 
            'last_seen': datetime.now().strftime('%H:%M:%S')
        }
        socketio.emit('update_agents', remote_agents)
        return jsonify({"status": "success"}), 200
    except Exception as e:
        print(f"❌ Agent Error: {e}")
        return jsonify({"status": "error"}), 500

# --- BACKGROUND TASKS ---
def task_monitor():
    print("🚀 Monitor Started (Database Mode)...")
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username='admin').first():
            db.session.add(User(username='admin', password_hash=generate_password_hash('admin123')))
            db.session.commit()

    while True:
        with app.app_context():
            try:
                targets = Device.query.all()
                results = []
                for d in targets:
                    try:
                        if d.port > 0:
                            is_up = check_port_open(d.ip, d.port)
                            status, lat_txt, color, lat_val = ('UP', f"Port {d.port}", 'success', 1) if is_up else ('DOWN', 'Closed', 'danger', 0)
                        else:
                            lat_val_raw = ping(d.ip, timeout=1)
                            if lat_val_raw is None:
                                status, lat_txt, color, lat_val = 'DOWN', 'Timeout', 'danger', 0
                            else:
                                ms = int(lat_val_raw * 1000)
                                status, lat_txt, lat_val = 'UP', f"{ms} ms", ms
                                color = 'success' if lat_val < 100 else 'warning'

                        prev = last_status_map.get(d.id, 'UP')
                        if status != prev:
                            msg = f"🚨 {d.name} DOWN!" if status == 'DOWN' else f"✅ {d.name} UP!"
                            send_telegram(msg)
                            db.session.add(EventLog(device_name=d.name, status=status, message=msg))
                            db.session.commit()
                            last_status_map[d.id] = status

                        if status == 'UP':
                            db.session.add(PingHistory(device_id=d.id, latency=lat_val))
                            db.session.commit()
                            
                        results.append({'id': d.id, 'status': status, 'latency': lat_txt, 'color': color})
                    except:
                        results.append({'id': d.id, 'status': 'ERR', 'latency': 'Err', 'color': 'secondary'})

                socketio.emit('update_monitor', results)
            except Exception as e:
                print(f"Error in Monitor Loop: {e}")
        time.sleep(3)

# ==========================================
# DUMMY SPEEDTEST (HEMAT KUOTA & CEPAT)
# ==========================================
def task_speedtest():
    global latest_speed
    print("⚠️ SPEEDTEST: DUMMY MODE ACTIVE (Simulated Data Only)")
    
    while True:
        # Generate angka acak biar terlihat seperti real-time
        # Range angkanya bisa diatur suka-suka Masbro
        dl_fake = random.randint(30, 80)  # Pura-pura Download 30-80 Mbps
        ul_fake = random.randint(10, 25)  # Pura-pura Upload 10-25 Mbps
        ping_fake = random.randint(9, 25) # Pura-pura Ping 9-25 ms
        
        latest_speed = {'dl': dl_fake, 'ul': ul_fake, 'ping': ping_fake}
        
        # Kirim ke Dashboard
        socketio.emit('update_speed', latest_speed)
        
        # Update setiap 5 detik (Biar grafik di dashboard gerak terus)
        time.sleep(5)

if __name__ == '__main__':
    socketio.start_background_task(task_monitor)
    socketio.start_background_task(task_speedtest)
    print("🔥 NetWatch ULTIMATE (Dummy Mode) Running on Port 5000...")
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)
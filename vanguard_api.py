from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import datetime
import os  # 📌 เพิ่มบรรทัดนี้เข้ามา
app = Flask(__name__)
CORS(app) # อนุญาตให้แอปมือถือยิงข้อมูลเข้ามาได้

DB_NAME = "aurora_saas_v2.db"

# 🛠️ 1. สร้างตารางเก็บพิกัดรถสดๆ (ถ้ายังไม่มี)
def init_fleet_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS live_fleet 
                 (fleet_id TEXT PRIMARY KEY, lat REAL, lon REAL, speed REAL, last_update DATETIME)''')
    # ตารางใหม่: เก็บพิกัดทุกจุดเพื่อทำ Trail
    c.execute('''CREATE TABLE IF NOT EXISTS fleet_history 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, fleet_id TEXT, lat REAL, lon REAL, timestamp DATETIME)''')
    conn.commit()
    conn.close()
    

init_fleet_db()

# 📡 2. Endpoint สำหรับเช็คว่าเซิร์ฟเวอร์เปิดอยู่ไหม
@app.route('/ping', methods=['GET'])
def ping():
    return jsonify({"status": "AuRORA API is Online 🟢"})

# 🚀 3. Endpoint หลัก: คอยรับพิกัดจากแอป Flutter
@app.route('/update_location', methods=['POST'])
def update_location():
    data = request.json
    fleet_id = data.get('fleet_id', 'UNKNOWN')
    lat = data.get('lat', 0.0)
    lon = data.get('lon', 0.0)
    speed = data.get('speed', 0.0)
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # บันทึกพิกัดใหม่ทับของเดิม (อัปเดตแบบ Real-time)
    c.execute('''INSERT INTO live_fleet (fleet_id, lat, lon, speed, last_update) 
                 VALUES (?, ?, ?, ?, ?)
                 ON CONFLICT(fleet_id) DO UPDATE SET 
                 lat=excluded.lat, lon=excluded.lon, speed=excluded.speed, last_update=excluded.last_update''',
              (fleet_id, lat, lon, speed, datetime.datetime.now()))
    c.execute("INSERT INTO fleet_history (fleet_id, lat, lon, timestamp) VALUES (?, ?, ?, ?)",
          (fleet_id, lat, lon, datetime.datetime.now()))
    conn.commit()
    conn.close()
    
    # ปริ้นท์โชว์ใน Terminal ให้พี่เอสเห็นว่ามีรถส่งพิกัดเข้ามา
    print(f"📡 สัญญาณเข้าจาก {fleet_id}: พิกัด [{lat:.4f}, {lon:.4f}] ความเร็ว {speed:.1f} km/h")
    
    return jsonify({"status": "success", "message": "พิกัดอัปเดตเรียบร้อย"})

if __name__ == '__main__':
    print("=========================================")
    print("🚀 VANGUARD CLOUD API GATEWAY 🟢 ONLINE")
    print("=========================================")
    # 📌 ให้คลาวด์สุ่ม Port ให้ ถ้าไม่มีให้ใช้ 5000
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
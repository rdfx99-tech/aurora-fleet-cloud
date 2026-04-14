from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
import datetime

app = Flask(__name__)
CORS(app)

# 🔐 นำลิงก์ Supabase ของพี่เอสมาใส่ตรงนี้ (อย่าลืมเปลี่ยน [YOUR-PASSWORD] เป็นรหัสผ่านจริง)
DB_URL = "postgresql://postgres.yzzsjmiziylmlqougaat:edED65565656@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres"

# 📥 ฟังก์ชันเชื่อมต่อ Database
def get_db_connection():
    return psycopg2.connect(DB_URL)

# 🛠️ 1. สร้างตารางแบบ PostgreSQL (ถ้ายังไม่มี)
def init_fleet_db():
    conn = get_db_connection()
    c = conn.cursor()
    # ตารางรถปัจจุบัน
    c.execute('''CREATE TABLE IF NOT EXISTS live_fleet 
                 (fleet_id TEXT PRIMARY KEY, lat REAL, lon REAL, speed REAL, last_update TIMESTAMP)''')
    # ตารางประวัติ (PostgreSQL ใช้ SERIAL แทน AUTOINCREMENT)
    c.execute('''CREATE TABLE IF NOT EXISTS fleet_history 
                 (id SERIAL PRIMARY KEY, fleet_id TEXT, lat REAL, lon REAL, timestamp TIMESTAMP)''')
    conn.commit()
    c.close()
    conn.close()

init_fleet_db()

@app.route('/ping', methods=['GET'])
def ping():
    return jsonify({"status": "AuRORA API is Online 🟢 (Connected to Supabase)"})

# 🚀 2. Endpoint รับพิกัด
@app.route('/update_location', methods=['POST'])
def update_location():
    data = request.json
    fleet_id = data.get('fleet_id', 'UNKNOWN')
    lat = data.get('lat', 0.0)
    lon = data.get('lon', 0.0)
    speed = data.get('speed', 0.0)
    
    conn = get_db_connection()
    c = conn.cursor()
    
    now = datetime.datetime.now()
    
    # 📌 บันทึกพิกัดล่าสุด (PostgreSQL ใช้ %s แทน ?)
    c.execute('''INSERT INTO live_fleet (fleet_id, lat, lon, speed, last_update) 
                 VALUES (%s, %s, %s, %s, %s)
                 ON CONFLICT(fleet_id) DO UPDATE SET 
                 lat=EXCLUDED.lat, lon=EXCLUDED.lon, speed=EXCLUDED.speed, last_update=EXCLUDED.last_update''',
              (fleet_id, lat, lon, speed, now))
              
    # 📌 บันทึกประวัติเพื่อทำ Trail
    c.execute("INSERT INTO fleet_history (fleet_id, lat, lon, timestamp) VALUES (%s, %s, %s, %s)",
              (fleet_id, lat, lon, now))
              
    conn.commit()
    c.close()
    conn.close()
    
    print(f"📡 ☁️ [CLOUD] สัญญาณเข้าจาก {fleet_id}: พิกัด [{lat:.4f}, {lon:.4f}]")
    
    return jsonify({"status": "success"})

if __name__ == '__main__':
    print("=========================================")
    print("🚀 VANGUARD CLOUD API GATEWAY 🟢 ONLINE")
    print("=========================================")
    app.run(host='0.0.0.0', port=5000)
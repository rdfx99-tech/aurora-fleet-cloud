import streamlit as st
import pandas as pd
import sqlite3
import pydeck as pdk
import time
from datetime import datetime, timedelta

# ⚙️ ตั้งค่าหน้าจอเป็นแบบเต็มจอ Dark Mode
st.set_page_config(page_title="VANGUARD Command Center", layout="wide")

DB_NAME = "aurora_saas_v2.db"

# 📥 1. ฟังก์ชันดึงข้อมูลรถปัจจุบัน (Live)
def load_live_data():
    try:
        conn = sqlite3.connect(DB_NAME)
        df = pd.read_sql_query("SELECT * FROM live_fleet", conn)
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()

# 📥 2. ฟังก์ชันดึงประวัติเส้นทาง (แบบระบุวันที่)
def load_history_by_date(fleet_id, target_date):
    try:
        conn = sqlite3.connect(DB_NAME)
        # ดึงข้อมูลเฉพาะวันที่เลือก (ตัดเวลาออก เอาแค่วันที่ไปเทียบ)
        query = f"""
            SELECT lat, lon 
            FROM fleet_history 
            WHERE fleet_id='{fleet_id}' 
            AND DATE(timestamp) = '{target_date}'
            ORDER BY timestamp ASC
        """
        df_hist = pd.read_sql_query(query, conn)
        conn.close()
        return df_hist[['lon', 'lat']].values.tolist()
    except Exception:
        return []

# ==========================================
# 🖥️ หน้าจอแสดงผล UI
# ==========================================
st.markdown("<h2 style='text-align: center; color: #00F0FF;'>🛰️ VANGUARD OMNIVERSE: LIVE RADAR</h2>", unsafe_allow_html=True)

# 🗓️ ส่วนควบคุม: ปฏิทินเลือกวัน (Time Machine)
st.sidebar.markdown("### 🕰️ TIME MACHINE")
st.sidebar.markdown("เลือกดูประวัติการเดินทางย้อนหลัง (สูงสุด 30 วัน)")

# สร้างตัวเลือกวันที่ย้อนหลัง 30 วัน
today = datetime.now().date()
date_options = [today - timedelta(days=i) for i in range(30)]
date_labels = ["วันนี้ (Live)"] + [str(d) for d in date_options[1:]]

# Dropdown สำหรับเลือกวัน
selected_label = st.sidebar.selectbox("เลือกวันที่ต้องการดูประวัติ:", date_labels)
# แปลง Label กลับมาเป็นวันที่จริงๆ
if selected_label == "วันนี้ (Live)":
    selected_date = str(today)
else:
    selected_date = selected_label

st.sidebar.markdown(f"**แสดงผลเส้นทางของวันที่:** `{selected_date}`")

# ดึงข้อมูลสดๆ
df = load_live_data()

if not df.empty:
    st.success(f"🟢 เชื่อมต่อสัญญาณแล้ว! พบเป้าหมาย {len(df)} คันในระบบ")
    
    # 🗺️ Layer 1: จุดสีฟ้าของรถปัจจุบัน (Live Marker)
    # *ซ่อนจุดรถปัจจุบัน ถ้าผู้ใช้กำลังดูประวัติย้อนหลัง*
    scatter_layer = None
    if selected_date == str(today):
        scatter_layer = pdk.Layer(
            'ScatterplotLayer',
            data=df,
            get_position='[lon, lat]',
            get_color='[0, 240, 255, 255]', 
            get_radius=200, 
            pickable=True
        )

    # 🗺️ Layer 2: เส้นทางแสง (Trail Path)
    path_data = []
    # วนลูปวาดเส้นให้รถทุกคัน ตาม 'วันที่เลือก'
    for fleet_id in df['fleet_id']:
        history_coords = load_history_by_date(fleet_id, selected_date)
        if len(history_coords) > 1: 
            path_data.append({"path": history_coords, "color": [0, 240, 255, 120]})

    path_layer = pdk.Layer(
        'PathLayer',
        data=path_data,
        get_path='path',
        get_color='color',
        width_min_pixels=4
    )

    # 🎥 ตั้งกล้อง: ถ้ามีเส้นทางให้ซูมไปที่เส้นทาง ถ้าไม่มีให้ซูมไปที่รถล่าสุด
    view_state_lat = df['lat'].mean()
    view_state_lon = df['lon'].mean()
    
    if len(path_data) > 0 and len(path_data[0]['path']) > 0:
        # ดึงพิกัดจุดแรกของเส้นทางในวันนั้นมาตั้งเป็นจุดศูนย์กลางกล้อง
        view_state_lon = path_data[0]['path'][0][0]
        view_state_lat = path_data[0]['path'][0][1]

    view_state = pdk.ViewState(
        latitude=view_state_lat,
        longitude=view_state_lon,
        zoom=14,
        pitch=45 
    )

    # 🛠️ ประกอบร่างแผนที่
    layers_to_render = [path_layer]
    if scatter_layer: # ถ้าเป็นวันนี้ ให้ใส่จุดรถเข้าไปด้วย
        layers_to_render.append(scatter_layer)

    r = pdk.Deck(
        layers=layers_to_render, 
        initial_view_state=view_state, 
        map_style='mapbox://styles/mapbox/dark-v10',
        tooltip={"text": "Fleet ID: {fleet_id}\nความเร็ว: {speed} km/h\nอัปเดตล่าสุด: {last_update}"}
    )
    
    st.pydeck_chart(r)

    # 📊 ตารางสรุป
    if selected_date == str(today):
        st.markdown("### 📊 ข้อมูลเป้าหมาย (Live Telemetry)")
        st.dataframe(df, use_container_width=True)
    else:
        st.markdown(f"### 📊 ประวัติของวันที่ {selected_date}")
        st.info("กำลังดูโหมดย้อนหลัง (Time Machine Mode) ระบบจะไม่แสดงตาราง Live Status")

else:
    st.warning("⏳ สแตนด์บาย... กำลังรอสัญญาณแรกจากเครือข่าย AuRORA Fleet")

# 🔄 Auto-Refresh: รีเฟรชเฉพาะตอนที่ดูโหมด "วันนี้" เท่านั้น (ดูอดีตไม่ต้องรีเฟรช)
if selected_date == str(today):
    time.sleep(5)
    st.rerun()
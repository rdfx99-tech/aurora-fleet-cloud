import streamlit as st
import pandas as pd
import pydeck as pdk
import time
from datetime import datetime, timedelta
from sqlalchemy import create_engine

# ⚙️ ตั้งค่าหน้าจอเป็นแบบเต็มจอ Dark Mode
st.set_page_config(page_title="VANGUARD Command Center", layout="wide")

# 🔐 Cloud Database: ลิงก์ Supabase (อย่าลืมเปลี่ยน [YOUR-PASSWORD] เป็นรหัสผ่านจริงนะครับ)
# 🔐 แผน B: ใช้ท่อ Pooler ผ่านพอร์ต 5432 (เสถียรกว่าสำหรับ Render)
# 🔐 Patch สำหรับโปรเจกต์: yzzsjmiziylmlqougaat
# 🔐 ลิงก์เชื่อมต่อเวอร์ชัน "ท่อด่วนพิเศษ" (Port 6543)
# 🔐 ลิงก์ของแท้จากเซิร์ฟเวอร์โตเกียว (Port 6543)
DB_URL = "postgresql://postgres.yzzsjmiziylmlqougaat:edED65565656@aws-1-ap-northeast-1.pooler.supabase.com:6543/postgres"
engine = create_engine(DB_URL)

# 📥 1. ฟังก์ชันดึงข้อมูลรถปัจจุบัน (Live)
def load_live_data():
    try:
        # เปลี่ยนจาก sqlite3 เป็นการดึงผ่าน engine ของ SQLAlchemy
        df = pd.read_sql_query("SELECT * FROM live_fleet", engine)
        return df
    except Exception:
        return pd.DataFrame()

# 📥 2. ฟังก์ชันดึงประวัติเส้นทาง (แบบระบุวันที่)
def load_history_by_date(fleet_id, target_date):
    try:
        # ปรับ Query ให้ใช้ PostgreSQL Syntax (timestamp::date) เพื่อความแม่นยำบน Cloud
        query = f"""
            SELECT lat, lon 
            FROM fleet_history 
            WHERE fleet_id='{fleet_id}' 
            AND timestamp::date = '{target_date}'
            ORDER BY timestamp ASC
        """
        df_hist = pd.read_sql_query(query, engine)
        return df_hist[['lon', 'lat']].values.tolist()
    except Exception:
        return []

# ==========================================
# 🖥️ หน้าจอแสดงผล UI
# ==========================================
st.markdown("<h2 style='text-align: center; color: #00F0FF;'>🛰️ VANGUARD OMNIVERSE: CLOUD RADAR</h2>", unsafe_allow_html=True)

# 🗓️ ส่วนควบคุม: ปฏิทินเลือกวัน (Time Machine)
st.sidebar.markdown("### 🕰️ TIME MACHINE")
st.sidebar.markdown("เลือกดูประวัติการเดินทางย้อนหลัง (สูงสุด 30 วัน)")

today = datetime.now().date()
date_options = [today - timedelta(days=i) for i in range(30)]
date_labels = ["วันนี้ (Live)"] + [str(d) for d in date_options[1:]]

selected_label = st.sidebar.selectbox("เลือกวันที่ต้องการดูประวัติ:", date_labels)
selected_date = str(today) if selected_label == "วันนี้ (Live)" else selected_label

st.sidebar.markdown(f"**แสดงผลเส้นทางของวันที่:** `{selected_date}`")

# ดึงข้อมูลจาก Cloud
df = load_live_data()

if not df.empty:
    st.success(f"🟢 เชื่อมต่อ Cloud สำเร็จ! พบเป้าหมาย {len(df)} คันในระบบ")
    
    # 🗺️ Layer 1: จุดสีฟ้าของรถปัจจุบัน (Live Marker)
    scatter_layer = None
    if selected_label == "วันนี้ (Live)":
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

    # 🎥 ตั้งกล้องอัตโนมัติ
    view_state_lat = df['lat'].mean()
    view_state_lon = df['lon'].mean()
    
    if len(path_data) > 0 and len(path_data[0]['path']) > 0:
        view_state_lon, view_state_lat = path_data[0]['path'][0]

    view_state = pdk.ViewState(
        latitude=view_state_lat,
        longitude=view_state_lon,
        zoom=14,
        pitch=45 
    )

    # 🛠️ ประกอบร่างแผนที่
    layers_to_render = [path_layer]
    if scatter_layer:
        layers_to_render.append(scatter_layer)

    r = pdk.Deck(
        layers=layers_to_render, 
        initial_view_state=view_state, 
        map_style='mapbox://styles/mapbox/dark-v10',
        tooltip={"text": "Fleet ID: {fleet_id}\nความเร็ว: {speed} km/h\nอัปเดตล่าสุด: {last_update}"}
    )
    
    st.pydeck_chart(r)

    # 📊 ตารางสรุปข้อมูล
    if selected_label == "วันนี้ (Live)":
        st.markdown("### 📊 ข้อมูลเป้าหมาย (Live Telemetry)")
        st.dataframe(df, use_container_width=True)
    else:
        st.markdown(f"### 📊 ประวัติของวันที่ {selected_date}")
        st.info("โหมด Time Machine: กำลังแสดงข้อมูลประวัติจากฐานข้อมูล Cloud")

else:
    st.warning("⏳ สแตนด์บาย... กำลังรอสัญญาณแรกจากเครือข่าย AuRORA Fleet (Cloud)")

# 🔄 Auto-Refresh เฉพาะโหมดวันนี้
if selected_label == "วันนี้ (Live)":
    time.sleep(5)
    st.rerun()
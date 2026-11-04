import streamlit as st
import pandas as pd
from datetime import datetime
import os

st.set_page_config(page_title="Audit Forklift Realtime", layout="centered")

st.title("🚜 Sistem Audit K3 Forklift")
st.markdown("Aplikasi pencatatan waktu dan kecepatan otomatis untuk evaluasi K3.")

# ==========================================
# DATABASE RUTE PABRIK
# ==========================================
db_rute = {
    "Gedung A -> Gedung B": {"jarak_m": 120.0, "area": "Outdoor"},
    "Gedung B -> Gedung C": {"jarak_m": 85.5, "area": "Outdoor"},
    "Area Mixing A -> Area Mixing F": {"jarak_m": 45.0, "area": "Indoor"},
    "Plant 3 (Indoor) -> Plant 3 (Outdoor)": {"jarak_m": 35.0, "area": "Indoor"},
    "Plant 3 (Outdoor) -> Plant 4 (Outdoor)": {"jarak_m": 145.0, "area": "Outdoor"}
    # Anda dapat menambahkan rute lainnya di sini
}

CSV_FILENAME = "Audit_Kecepatan_Cloud.csv"

# ==========================================
# FORMULIR INPUT TRACKER
# ==========================================
with st.form("form_tracker"):
    col1, col2 = st.columns(2)
    with col1:
        seri = st.selectbox("Seri Forklift", [f"Seri {i}" for i in range(1158, 1165)])
        beban = st.selectbox("Status Beban", ["Kosong (Tanpa Palet)", "Isi (Bawa Barang)"])
    with col2:
        rute = st.selectbox("Rute Pergerakan", list(db_rute.keys()))
        jarak_info = db_rute[rute]['jarak_m']
        st.info(f"Jarak Rute: {jarak_info} meter ({db_rute[rute]['area']})")

    st.markdown("---")
    waktu_aktif = st.number_input("Waktu Tempuh Kendaraan (Detik)", min_value=1.0, value=10.0, step=1.0)
    delay = st.number_input("Waktu Terhalang / Antre (Detik) - Opsional", min_value=0.0, value=0.0, step=1.0)

    submit = st.form_submit_button("Simpan & Hitung Kecepatan", type="primary")

# ==========================================
# LOGIKA PEMROSESAN & PENYIMPANAN
# ==========================================
if submit:
    jarak_m = db_rute[rute]['jarak_m']
    area = db_rute[rute]['area']
    
    # Hitung kecepatan Aktual
    kecepatan_kmh = round((jarak_m / waktu_aktif) * 3.6, 2)
    
    # Audit K3 Kecepatan
    batas = 5.0 if area == "Indoor" else 10.0
    if kecepatan_kmh > batas:
        status_audit = f"⚠️ OVERSPEED ({batas} km/h)"
        st.error(f"PELANGGARAN K3! Kecepatan tercatat: {kecepatan_kmh} km/jam.")
    else:
        status_audit = "✅ Aman"
        st.success(f"Aman. Kecepatan tercatat: {kecepatan_kmh} km/jam.")

    # Simpan ke CSV
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    baris_baru = pd.DataFrame([{
        "Waktu": timestamp, "Seri": seri, "Rute": rute, "Area": area, 
        "Jarak (m)": jarak_m, "Beban": beban, "Waktu Aktif (s)": waktu_aktif, 
        "Delay (s)": delay, "Kecepatan (km/h)": kecepatan_kmh, "Audit": status_audit
    }])

    if os.path.exists(CSV_FILENAME):
        df_lama = pd.read_csv(CSV_FILENAME)
        df_baru = pd.concat([baris_baru, df_lama], ignore_index=True)
    else:
        df_baru = baris_baru

    df_baru.to_csv(CSV_FILENAME, index=False)

# ==========================================
# MENAMPILKAN DATA & TOMBOL UNDUH
# ==========================================
st.markdown("### 📊 Log Hasil Audit")
if os.path.exists(CSV_FILENAME):
    df_tampil = pd.read_csv(CSV_FILENAME)
    st.dataframe(df_tampil, use_container_width=True)
    
    # Konversi ke CSV untuk tombol unduh
    csv_data = df_tampil.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="⬇️ Unduh File Excel (CSV)",
        data=csv_data,
        file_name="Laporan_Audit_Forklift.csv",
        mime="text/csv",
    )
else:
    st.info("Belum ada data yang tersimpan hari ini.")

import streamlit as st
import pandas as pd
from datetime import datetime
import os
import math
import streamlit.components.v1 as components

# ==========================================
# KONFIGURASI HALAMAN
# ==========================================
st.set_page_config(page_title="Audit Forklift PT S.R.I.", layout="wide")

st.title("Sistem Audit Forklift PT S.R.I.")
st.markdown("Aplikasi pelacakan rute distribusi real-time, evaluasi hambatan, dan efisiensi biaya operasional.")

CSV_FILENAME = "Audit_Kecepatan_Cloud.csv"

# ==========================================
# KOMPONEN PETA LIVE GPS & TRACKING (HTML/JS)
# ==========================================
leaflet_component = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        body { margin: 0; padding: 0; font-family: sans-serif; }
        #map { height: 400px; width: 100%; border-radius: 8px; margin-bottom: 15px; border: 2px solid #e2e8f0; }
        .button-container { display: flex; gap: 10px; margin-bottom: 15px; }
        button { flex: 1; padding: 14px; font-size: 15px; font-weight: bold; border: none; border-radius: 6px; cursor: pointer; color: white; transition: 0.3s; }
        #btn-start { background-color: #16a34a; }
        #btn-start:hover { background-color: #15803d; }
        #btn-stop { background-color: #dc2626; }
        #btn-stop:hover { background-color: #b91c1c; }
        button:disabled { background-color: #cbd5e1; cursor: not-allowed; }
        #info-panel { display: flex; justify-content: space-between; background: #f8fafc; padding: 15px; border-radius: 8px; border: 1px solid #e2e8f0; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
        .info-box { text-align: center; }
        .info-box span { display: block; font-size: 20px; font-weight: bold; color: #0f172a; margin-top: 5px; }
    </style>
</head>
<body>
    <div id="map"></div>
    <div class="button-container">
        <button id="btn-start" onclick="mulaiTracking()">MULAI PERJALANAN</button>
        <button id="btn-stop" onclick="selesaiTracking()" disabled>SAMPAI TUJUAN</button>
    </div>
    <div id="info-panel">
        <div class="info-box"><b>Status</b> <span id="status-text" style="color: #64748b;">Standby</span></div>
        <div class="info-box"><b>Jarak Tempuh</b> <span id="jarak-text">0.00 m</span></div>
        <div class="info-box"><b>Waktu Aktif</b> <span id="waktu-text">0 s</span></div>
    </div>

    <script>
        let map, marker, polyline;
        let watchId = null;
        let latLngs = [];
        let totalJarak = 0;
        let startTime = null;
        let timerInterval = null;
        let activeSeconds = 0;

        function initMap(lat = -6.480, lon = 106.840) {
            map = L.map('map').setView([lat, lon], 17);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                maxZoom: 19,
                attribution: '© OpenStreetMap'
            }).addTo(map);
            polyline = L.polyline([], {color: '#2563eb', weight: 5}).addTo(map);
        }

        function hitungJarakMeter(lat1, lon1, lat2, lon2) {
            let R = 6371e3; 
            let dLat = (lat2 - lat1) * Math.PI / 180;
            let dLon = (lon2 - lon1) * Math.PI / 180;
            let a = Math.sin(dLat/2) * Math.sin(dLat/2) +
                    Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
                    Math.sin(dLon/2) * Math.sin(dLon/2);
            let c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
            return R * c;
        }

        function mulaiTracking() {
            if (!navigator.geolocation) {
                alert("GPS tidak didukung oleh browser Anda.");
                return;
            }
            latLngs = []; totalJarak = 0; activeSeconds = 0;
            document.getElementById("btn-start").disabled = true;
            document.getElementById("btn-stop").disabled = false;
            document.getElementById("status-text").innerText = "Melacak GPS...";
            document.getElementById("status-text").style.color = "#16a34a";

            startTime = Date.now();
            timerInterval = setInterval(() => {
                activeSeconds = Math.floor((Date.now() - startTime) / 1000);
                document.getElementById("waktu-text").innerText = activeSeconds + " s";
            }, 1000);

            watchId = navigator.geolocation.watchPosition(
                (position) => {
                    let lat = position.coords.latitude;
                    let lon = position.coords.longitude;
                    let newPoint = [lat, lon];

                    if (latLngs.length > 0) {
                        let lastPoint = latLngs[latLngs.length - 1];
                        let dist = hitungJarakMeter(lastPoint[0], lastPoint[1], lat, lon);
                        if (dist > 1.0) {
                            totalJarak += dist;
                            latLngs.push(newPoint);
                            polyline.setLatLngs(latLngs);
                        }
                    } else {
                        latLngs.push(newPoint);
                    }

                    if (!marker) {
                        marker = L.marker(newPoint).addTo(map);
                    } else {
                        marker.setLatLng(newPoint);
                    }
                    map.setView(newPoint, map.getZoom());
                    document.getElementById("jarak-text").innerText = totalJarak.toFixed(2) + " m";
                },
                (error) => { console.warn("GPS error: " + error.message); },
                { enableHighAccuracy: true, maximumAge: 0, timeout: 5000 }
            );
        }

        function selesaiTracking() {
            if (watchId !== null) navigator.geolocation.clearWatch(watchId);
            clearInterval(timerInterval);

            document.getElementById("btn-start").disabled = false;
            document.getElementById("btn-stop").disabled = true;
            document.getElementById("status-text").innerText = "Selesai";
            document.getElementById("status-text").style.color = "#2563eb";

            const dataHasil = {
                jarak_m: totalJarak > 0 ? totalJarak : 1.0,
                waktu_aktif: activeSeconds > 0 ? activeSeconds : 1
            };
            window.parent.postMessage({type: 'streamlit:setComponentValue', value: dataHasil}, '*');
        }

        window.onload = function() {
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(
                    (pos) => initMap(pos.coords.latitude, pos.coords.longitude),
                    () => initMap(-6.480, 106.840)
                );
            } else {
                initMap(-6.480, 106.840);
            }
        };
    </script>
</body>
</html>
"""

# ==========================================
# BAGIAN 1: DATA OPERASIONAL & KENDARAAN
# ==========================================
st.markdown("### 1. Data Operasional & Kendaraan")
with st.container():
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Spesifikasi Kendaraan**")
        seri = st.selectbox("Seri Forklift", [f"Seri {i}" for i in range(1158, 1165)])
        beban = st.selectbox("Status Beban", ["Kosong (Tanpa Palet)", "Isi (Bawa Barang)"])
        area = st.selectbox("Area Operasional", ["Indoor", "Outdoor"])
        
    with col2:
        st.markdown("**Kendala Lapangan**")
        hambatan = st.text_area("Hambatan di Rute (Opsional)", placeholder="Misal: Jalan berlubang, area loading ramai...")
        allowance_waktu = st.number_input("Allowance Waktu (Menit)", min_value=0, value=0, help="Tambahan waktu kelonggaran akibat hambatan")

st.markdown("---")

# ==========================================
# BAGIAN 2: PETA PELACAKAN RUTE
# ==========================================
st.markdown("### 2. Peta Pelacakan Rute Real-Time")
# Render Komponen Peta Live GPS
result_data = components.html(leaflet_component, height=550)

st.markdown("---")

# ==========================================
# BAGIAN 3: KALKULASI & SIMPAN HASIL AUDIT
# ==========================================
st.markdown("### 3. Kalkulasi & Simpan Hasil Audit")
st.info("Salin angka Jarak dan Waktu dari layar peta di atas, lalu pastikan parameter BBM sudah sesuai untuk menghitung total efisiensi biaya.")

with st.form("form_simpan"):
    f_col1, f_col2 = st.columns(2)
    
    with f_col1:
        st.markdown("**Data dari GPS**")
        input_jarak = st.number_input("Jarak Tempuh Tercatat (Meter)", min_value=0.0, value=0.0, step=1.0)
        input_waktu = st.number_input("Waktu Tempuh Tercatat (Detik)", min_value=0, value=0, step=1)
        
    with f_col2:
        st.markdown("**Parameter Biaya**")
        konsumsi_bbm = st.number_input("Penggunaan Bensin (Liter/Km)", min_value=0.0, value=1.5, step=0.1)
        harga_bbm = st.number_input("Harga BBM per Liter (Rp)", min_value=0, value=10000, step=500)
        
    st.markdown("<br>", unsafe_allow_html=True)
    btn_simpan = st.form_submit_button("Kalkulasi & Simpan Data", use_container_width=True)

if btn_simpan:
    if input_jarak > 0:
        # Kalkulasi
        jarak_km = input_jarak / 1000
        total_liter = jarak_km * konsumsi_bbm
        total_biaya = total_liter * harga_bbm
        efisiensi_per_m = total_biaya / input_jarak if input_jarak > 0 else 0
        
        # Tampilkan Metrik Biaya 
        st.success("Data berhasil dihitung dan disimpan!")
        m1, m2, m3 = st.columns(3)
        m1.metric(label="Total Bensin Digunakan", value=f"{total_liter:.2f} Liter")
        m2.metric(label="Total Biaya Operasional", value=f"Rp {total_biaya:,.0f}")
        m3.metric(label="Efisiensi Rupiah / Meter", value=f"Rp {efisiensi_per_m:,.2f}")
        
        # Simpan ke DataFrame/CSV
        data_baru = pd.DataFrame([{
            "Tanggal": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Seri Forklift": seri,
            "Beban": beban,
            "Area": area,
            "Jarak (Meter)": input_jarak,
            "Waktu (Detik)": input_waktu,
            "Hambatan": hambatan if hambatan else "Tidak Ada",
            "Allowance (Menit)": allowance_waktu,
            "Liter/Km": konsumsi_bbm,
            "Total Biaya (Rp)": total_biaya
        }])
        
        if os.path.exists(CSV_FILENAME):
            df_existing = pd.read_csv(CSV_FILENAME)
            df_updated = pd.concat([df_existing, data_baru], ignore_index=True)
        else:
            df_updated = data_baru
            
        df_updated.to_csv(CSV_FILENAME, index=False)
    else:
        st.error("Jarak tempuh masih 0. Pastikan Anda sudah menjalankan tracking dan memasukkan angkanya ke dalam formulir.")

st.markdown("---")

# ==========================================
# BAGIAN 4: LOG LAPORAN
# ==========================================
st.markdown("### 4. Log Laporan Audit PT S.R.I.")
if os.path.exists(CSV_FILENAME):
    df_tampil = pd.read_csv(CSV_FILENAME)
    st.dataframe(df_tampil, use_container_width=True)
    
    csv_data = df_tampil.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Unduh File Laporan (CSV)",
        data=csv_data,
        file_name="Laporan_Audit_Forklift_PT_SRI.csv",
        mime="text/csv",
        use_container_width=True
    )
else:
    st.info("Belum ada data perjalanan yang tersimpan di server.")

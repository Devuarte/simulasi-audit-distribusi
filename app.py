import streamlit as st
import pandas as pd
from datetime import datetime
import os
import math

st.set_page_config(page_title="Audit Forklift Live GPS", layout="centered")

st.title("🚜 Sistem Audit K3 Forklift (Live GPS)")
st.markdown("Aplikasi pelacakan rute distribusi real-time menggunakan koordinat GPS.")

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
        #map { height: 350px; width: 100%; border-radius: 8px; margin-bottom: 10px; }
        .button-container { display: flex; gap: 10px; margin-bottom: 10px; }
        button { flex: 1; padding: 12px; font-size: 15px; font-weight: bold; border: none; border-radius: 6px; cursor: pointer; color: white; }
        #btn-start { background-color: #16a34a; }
        #btn-stop { background-color: #dc2626; }
        button:disabled { background-color: #cbd5e1; cursor: not-allowed; }
        #info-panel { font-family: sans-serif; font-size: 14px; background: #f8fafc; padding: 10px; border-radius: 6px; border: 1px solid #e2e8f0; }
    </style>
</head>
<body>
    <div id="map"></div>
    <div class="button-container">
        <button id="btn-start" onclick="mulaiTracking()">▶ MULAI PERJALANAN</button>
        <button id="btn-stop" onclick="selesaiTracking()" disabled>⏹ SAMPAI TUJUAN</button>
    </div>
    <div id="info-panel">
        <div><b>Status:</b> <span id="status-text" style="color: gray;">Standby</span></div>
        <div><b>Jarak Tempuh GPS:</b> <span id="jarak-text">0.00</span> meter</div>
        <div><b>Waktu Aktif:</b> <span id="waktu-text">0</span> detik</div>
    </div>

    <script>
        let map, marker, polyline;
        let watchId = null;
        let latLngs = [];
        let totalJarak = 0;
        let startTime = null;
        let timerInterval = null;
        let activeSeconds = 0;

        // Inisialisasi Peta
        function initMap(lat = -6.480, lon = 106.840) {
            map = L.map('map').setView([lat, lon], 17);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                maxZoom: 19,
                attribution: '© OpenStreetMap'
            }).addTo(map);

            polyline = L.polyline([], {color: 'blue', weight: 4}).addTo(map);
        }

        // Hitung jarak Haversine antar 2 titik koordinat GPS (dalam meter)
        function hitungJarakMeter(lat1, lon1, lat2, lon2) {
            let R = 6371e3; // Radius bumi dalam meter
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

            latLngs = [];
            totalJarak = 0;
            activeSeconds = 0;
            document.getElementById("btn-start").disabled = true;
            document.getElementById("btn-stop").disabled = false;
            document.getElementById("status-text").innerText = "Berjalan (Melacak GPS...)";
            document.getElementById("status-text").style.color = "green";

            startTime = Date.now();
            timerInterval = setInterval(() => {
                activeSeconds = Math.floor((Date.now() - startTime) / 1000);
                document.getElementById("waktu-text").innerText = activeSeconds;
            }, 1000);

            watchId = navigator.geolocation.watchPosition(
                (position) => {
                    let lat = position.coords.latitude;
                    let lon = position.coords.longitude;
                    let newPoint = [lat, lon];

                    if (latLngs.length > 0) {
                        let lastPoint = latLngs[latLngs.length - 1];
                        let dist = hitungJarakMeter(lastPoint[0], lastPoint[1], lat, lon);
                        // Hanya catat jika perpindahan > 1 meter untuk menghindarinoise GPS
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

                    document.getElementById("jarak-text").innerText = totalJarak.toFixed(2);
                },
                (error) => {
                    alert("Gagal mendeteksi GPS: " + error.message);
                },
                { enableHighAccuracy: true, maximumAge: 0, timeout: 5000 }
            );
        }

        function selesaiTracking() {
            if (watchId !== null) {
                navigator.geolocation.clearWatch(watchId);
            }
            clearInterval(timerInterval);

            document.getElementById("btn-start").disabled = false;
            document.getElementById("btn-stop").disabled = true;
            document.getElementById("status-text").innerText = "Selesai";
            document.getElementById("status-text").style.color = "blue";

            // Kirim data otomatis ke Streamlit menggunakan window.parent postMessage
            const dataHasil = {
                jarak_m: totalJarak > 0 ? totalJarak : 1.0,
                waktu_aktif: activeSeconds > 0 ? activeSeconds : 1
            };
            
            // Simpan ke localStorage agar bisa dibaca Streamlit python component
            window.parent.postMessage({type: 'streamlit:setComponentValue', value: dataHasil}, '*');
        }

        // Panggil inisialisasi peta awal
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
# FORMULIR & TAMPILAN UTAMA STREAMLIT
# ==========================================
col1, col2 = st.columns(2)
with col1:
    seri = st.selectbox("Seri Forklift", [f"Seri {i}" for i in range(1158, 1165)])
    beban = st.selectbox("Status Beban", ["Kosong (Tanpa Palet)", "Isi (Bawa Barang)"])
with col2:
    area = st.selectbox("Area Operasional", ["Indoor", "Outdoor"])

st.markdown("### 📍 Peta Pelacakan Rute Real-Time")

# Render Komponen Peta Live GPS
import streamlit.components.v1 as components
result_data = components.html(leaflet_component, height=480)

st.markdown("---")
st.markdown("### 📊 Log Hasil Audit")
if os.path.exists(CSV_FILENAME):
    df_tampil = pd.read_csv(CSV_FILENAME)
    st.dataframe(df_tampil, use_container_width=True)
    
    csv_data = df_tampil.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="⬇️ Unduh File Excel (CSV)",
        data=csv_data,
        file_name="Laporan_Audit_Forklift.csv",
        mime="text/csv",
    )
else:
    st.info("Belum ada data perjalanan yang tersimpan.")

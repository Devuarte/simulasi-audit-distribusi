import streamlit as st
import pandas as pd
from datetime import datetime
import os
import base64
from io import BytesIO
import streamlit.components.v1 as components
import xlsxwriter
import json  # <-- Modul baru untuk menyimpan opsi yang bisa diedit

# ==========================================
# KONFIGURASI HALAMAN & DIREKTORI
# ==========================================
st.set_page_config(page_title="Audit Forklift PT S.R.I.", layout="wide")

st.title("Sistem Audit Forklift PT S.R.I.")
st.markdown("Aplikasi pelacakan rute distribusi real-time, evaluasi hambatan, dan efisiensi biaya operasional.")

CSV_FILENAME = "Audit_Kecepatan_Cloud.csv"
IMAGE_DIR = "map_snapshots"
CONFIG_OPTIONS_FILE = "config_options.json" # File untuk menyimpan opsi manual

os.makedirs(IMAGE_DIR, exist_ok=True) # Buat folder untuk simpan foto rute sementara

# FUNGSI UNTUK MEMUAT & MENYIMPAN OPSI MANUAL
def load_options():
    if os.path.exists(CONFIG_OPTIONS_FILE):
        try:
            with open(CONFIG_OPTIONS_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    # Default Opsi jika file belum ada
    return {
        "Seri Forklift": [f"Seri {i}" for i in range(1158, 1165)],
        "Status Beban": ["Kosong (Tanpa Palet)", "Isi (Bawa Barang)"],
        "Area Operasional": ["Indoor", "Outdoor"]
    }

def save_options(opts):
    with open(CONFIG_OPTIONS_FILE, 'w') as f:
        json.dump(opts, f)

options_data = load_options()

# ==========================================
# KOMPONEN PETA LIVE GPS & TRACKING (HTML/JS)
# ==========================================
leaflet_component = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
    <style>
        body { margin: 0; padding: 0; font-family: sans-serif; }
        #map { height: 50vh; min-height: 320px; width: 100%; border-radius: 8px; margin-bottom: 15px; border: 2px solid #e2e8f0; }
        .button-container { display: flex; gap: 10px; margin-bottom: 15px; flex-wrap: wrap; }
        button { flex: 1; min-width: 140px; padding: 14px; font-size: 15px; font-weight: bold; border: none; border-radius: 6px; cursor: pointer; color: white; transition: 0.3s; }
        #btn-start { background-color: #16a34a; }
        #btn-start:hover { background-color: #15803d; }
        #btn-stop { background-color: #dc2626; }
        #btn-stop:hover { background-color: #b91c1c; }
        button:disabled { background-color: #cbd5e1; cursor: not-allowed; }
        #info-panel { display: flex; justify-content: space-between; flex-wrap: wrap; gap: 10px; background: #f8fafc; padding: 15px; border-radius: 8px; border: 1px solid #e2e8f0; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
        .info-box { flex: 1; min-width: 30%; text-align: center; }
        .info-box span { display: block; font-size: 18px; font-weight: bold; color: #0f172a; margin-top: 5px; }
        .watermark-overlay { position: absolute; top: 10px; right: 10px; z-index: 1000; background: rgba(255, 255, 255, 0.85); padding: 5px 10px; border-radius: 5px; font-size: 11px; font-weight: bold; border: 1px solid #ccc; color: #333; pointer-events: none; }
        .map-icon { font-size: 20px; line-height: 20px; text-align: center; text-shadow: 0px 0px 5px white; }
    </style>
</head>
<body>
    <div style="position: relative;" id="map-container">
        <div id="map"></div>
        <div class="watermark-overlay">© System by Mikha Febrian</div>
    </div>
    
    <div class="button-container">
        <button id="btn-start" onclick="mulaiTracking()">MULAI PERJALANAN</button>
        <button id="btn-stop" onclick="selesaiTracking()" disabled>SAMPAI TUJUAN</button>
    </div>
    <div id="info-panel">
        <div class="info-box"><b style="font-size: 12px;">Status</b> <span id="status-text" style="color: #64748b;">Standby</span></div>
        <div class="info-box"><b style="font-size: 12px;">Jarak Tempuh</b> <span id="jarak-text">0.00 m</span></div>
        <div class="info-box"><b style="font-size: 12px;">Waktu Aktif</b> <span id="waktu-text">0 s</span></div>
    </div>

    <script>
        let map, startMarker, currentMarker, polyline;
        let watchId = null;
        let latLngs = [];
        let totalJarak = 0;
        let startTime = null;
        let timerInterval = null;
        let activeSeconds = 0;

        // Custom Icons
        const startIcon = L.divIcon({ html: '🟢', className: 'map-icon', iconSize: [20, 20] });
        const truckIcon = L.divIcon({ html: '🚜', className: 'map-icon', iconSize: [28, 28] });

        function initMap(lat = -6.480, lon = 106.840) {
            map = L.map('map', {preferCanvas: true}).setView([lat, lon], 17);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                maxZoom: 19,
                attribution: '© OpenStreetMap | <b>Hak Cipta © Mikha Febrian</b>',
                crossOrigin: true
            }).addTo(map);
            polyline = L.polyline([], {color: '#2563eb', weight: 6, opacity: 0.8}).addTo(map);
        }

        function hitungJarakMeter(lat1, lon1, lat2, lon2) {
            let R = 6371e3; 
            let dLat = (lat2 - lat1) * Math.PI / 180;
            let dLon = (lon2 - lon1) * Math.PI / 180;
            let a = Math.sin(dLat/2) * Math.sin(dLat/2) + Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * Math.sin(dLon/2) * Math.sin(dLon/2);
            let c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
            return R * c;
        }

        function mulaiTracking() {
            if (!navigator.geolocation) {
                alert("GPS tidak didukung oleh browser Anda.");
                return;
            }
            latLngs = []; totalJarak = 0; activeSeconds = 0;
            if(startMarker) map.removeLayer(startMarker);
            if(currentMarker) map.removeLayer(currentMarker);
            startMarker = null; currentMarker = null;
            polyline.setLatLngs([]);

            document.getElementById("btn-start").disabled = true;
            document.getElementById("btn-stop").disabled = false;
            document.getElementById("status-text").innerText = "Melacak GPS";
            document.getElementById("status-text").style.color = "#16a34a";

            startTime = Date.now();
            timerInterval = setInterval(() => {
                activeSeconds = Math.floor((Date.now() - startTime) / 1000);
                document.getElementById("waktu-text").innerText = activeSeconds + " s";
            }, 1000);

            watchId = navigator.geolocation.watchPosition(
                (position) => {
                    if(position.coords.accuracy > 20) return; 

                    let lat = position.coords.latitude;
                    let lon = position.coords.longitude;
                    let newPoint = [lat, lon];

                    if (latLngs.length > 0) {
                        let lastPoint = latLngs[latLngs.length - 1];
                        let dist = hitungJarakMeter(lastPoint[0], lastPoint[1], lat, lon);
                        if (dist > 2.0) {
                            totalJarak += dist;
                            latLngs.push(newPoint);
                            polyline.setLatLngs(latLngs);
                        }
                    } else {
                        latLngs.push(newPoint);
                        startMarker = L.marker(newPoint, {icon: startIcon}).addTo(map);
                    }

                    if (!currentMarker

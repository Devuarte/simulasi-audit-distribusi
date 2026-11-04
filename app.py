import streamlit as st
import pandas as pd
from datetime import datetime
import os
import math
import streamlit.components.v1 as components

# ==========================================
# KONFIGURASI HALAMAN
# ==========================================
st.set_page_config(page_title="Audit Forklift PT S.R.I.", layout="wide", page_icon="🚜")

st.title("🚜 Sistem Audit Forklift PT S.R.I.")
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
        <button id="btn-start" onclick="mulaiTracking()">▶ MULAI PERJALANAN</button>
        <button id="btn-stop" onclick="selesaiTracking()" disabled>⏹ SAMPAI TUJUAN</button>
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
            document

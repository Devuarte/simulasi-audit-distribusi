import streamlit as st
import pandas as pd
from datetime import datetime
import os
import base64
from io import BytesIO
import streamlit.components.v1 as components
import xlsxwriter
import json  


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

                    if (!currentMarker) {
                        currentMarker = L.marker(newPoint, {icon: truckIcon}).addTo(map);
                    } else {
                        currentMarker.setLatLng(newPoint); 
                    }
                    map.setView(newPoint, map.getZoom());
                    document.getElementById("jarak-text").innerText = totalJarak.toFixed(2) + " m";
                },
                (error) => { console.warn("GPS error: " + error.message); },
                { enableHighAccuracy: true, maximumAge: 0, timeout: 5000 }
            );
        }

        function setStreamlitInput(labelFragment, value) {
            let parentDoc = window.parent.document;
            let inputs = parentDoc.querySelectorAll('input');
            for (let i = 0; i < inputs.length; i++) {
                let ariaLabel = inputs[i].getAttribute('aria-label');
                if (ariaLabel && ariaLabel.includes(labelFragment)) {
                    let nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
                    nativeSetter.call(inputs[i], value);
                    inputs[i].dispatchEvent(new Event('input', { bubbles: true }));
                    break;
                }
            }
        }

        function selesaiTracking() {
            if (watchId !== null) navigator.geolocation.clearWatch(watchId);
            clearInterval(timerInterval);

            document.getElementById("btn-start").disabled = false;
            document.getElementById("btn-stop").disabled = true;
            document.getElementById("status-text").innerText = "Menyimpan Data...";
            document.getElementById("status-text").style.color = "#eab308";

            setTimeout(() => {
                html2canvas(document.querySelector("#map-container"), {useCORS: true}).then(canvas => {
                    let imgData = canvas.toDataURL("image/png");
                    
                    setStreamlitInput("Jarak Tempuh Tercatat", totalJarak.toFixed(2));
                    setStreamlitInput("Waktu Tempuh Tercatat", activeSeconds.toString());
                    setStreamlitInput("Base64 Peta Rahasia", imgData);
                    
                    document.getElementById("status-text").innerText = "Selesai";
                    document.getElementById("status-text").style.color = "#2563eb";
                }).catch(err => {
                    setStreamlitInput("Jarak Tempuh Tercatat", totalJarak.toFixed(2));
                    setStreamlitInput("Waktu Tempuh Tercatat", activeSeconds.toString());
                    document.getElementById("status-text").innerText = "Selesai (Map Gagal)";
                });
            }, 1000); 
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

# --- FITUR BARU: PENGATURAN OPSI MANUAL ---
with st.expander("⚙️ Pengaturan Manual (Tambah/Edit Seri, Beban & Area)"):
    st.caption("Jika ada alat/area baru, edit daftar di bawah ini (pisahkan dengan baris baru / Enter) lalu klik Simpan untuk memperbarui pilihan formulir.")
    opt_col1, opt_col2, opt_col3 = st.columns(3)
    with opt_col1:
        edit_seri = st.text_area("Daftar Seri Forklift", "\n".join(options_data["Seri Forklift"]), height=150)
    with opt_col2:
        edit_beban = st.text_area("Daftar Status Beban", "\n".join(options_data["Status Beban"]), height=150)
    with opt_col3:
        edit_area = st.text_area("Daftar Area Operasional", "\n".join(options_data["Area Operasional"]), height=150)
        
    if st.button("Simpan Perubahan Opsi", type="secondary"):
        # Menyimpan data yang dipisahkan baris baru ke dalam List
        options_data["Seri Forklift"] = [x.strip() for x in edit_seri.split("\n") if x.strip()]
        options_data["Status Beban"] = [x.strip() for x in edit_beban.split("\n") if x.strip()]
        options_data["Area Operasional"] = [x.strip() for x in edit_area.split("\n") if x.strip()]
        
        save_options(options_data)
        st.success("Pilihan formulir berhasil diperbarui secara permanen!")
        st.rerun() # Refresh halaman agar daftar dropdown ikut ter-update
# -------------------------------------------

with st.container():
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Spesifikasi Kendaraan**")
        # Dropdown kini diisi dengan data fleksibel dari konfigurasi JSON
        seri = st.selectbox("Seri Forklift", options_data["Seri Forklift"])
        beban = st.selectbox("Status Beban", options_data["Status Beban"])
        area = st.selectbox("Area Operasional", options_data["Area Operasional"])
        
    with col2:
        st.markdown("**Kendala Lapangan**")
        hambatan = st.text_area("Hambatan di Rute (Opsional)", placeholder="Misal: Jalan berlubang, area loading ramai...")
        allowance_waktu = st.number_input("Allowance Waktu (Menit)", min_value=0, value=0, help="Tambahan waktu kelonggaran akibat hambatan")

st.markdown("---")

# ==========================================
# BAGIAN 2: PETA PELACAKAN RUTE
# ==========================================
st.markdown("### 2. Peta Pelacakan Rute Real-Time")
result_data = components.html(leaflet_component, height=600)

st.markdown("---")

# ==========================================
# BAGIAN 3: KALKULASI & SIMPAN HASIL AUDIT
# ==========================================
st.markdown("### 3. Kalkulasi & Simpan Hasil Audit")
st.info("💡 Angka GPS dan Foto Peta kini akan terisi **OTOMATIS** saat Anda menekan tombol 'SAMPAI TUJUAN' di layar Peta atas.")

with st.form("form_simpan"):
    f_col1, f_col2 = st.columns(2)
    
    with f_col1:
        st.markdown("**Data dari GPS (Terisi Otomatis)**")
        input_jarak_str = st.text_input("Jarak Tempuh Tercatat (Meter)", value="0.0")
        input_waktu_str = st.text_input("Waktu Tempuh Tercatat (Detik)", value="0")
        
        # Hidden input untuk base64 image
        input_img_b64 = st.text_input("Base64 Peta Rahasia", value="", label_visibility="collapsed")
        
    with f_col2:
        st.markdown("**Parameter Biaya**")
        konsumsi_bbm = st.number_input("Penggunaan Bensin (Liter/Km)", min_value=0.0, value=1.5, step=0.1)
        harga_bbm = st.number_input("Harga BBM per Liter (Rp)", min_value=0, value=10000, step=500)
        
    st.markdown("<br>", unsafe_allow_html=True)
    btn_simpan = st.form_submit_button("Kalkulasi & Simpan Data", use_container_width=True)

# Trik CSS untuk menyembunyikan kotak input Base64 Peta
st.markdown("""<style>div[data-testid="stTextInput"]:has(input[aria-label="Base64 Peta Rahasia"]) { display: none; }</style>""", unsafe_allow_html=True)

if btn_simpan:
    try:
        input_jarak = float(input_jarak_str)
        input_waktu = int(input_waktu_str)
    except:
        input_jarak = 0.0
        input_waktu = 0

    if input_jarak > 0:
        jarak_km = input_jarak / 1000
        total_liter = jarak_km * konsumsi_bbm
        total_biaya = total_liter * harga_bbm
        efisiensi_per_m = total_biaya / input_jarak if input_jarak > 0 else 0
        
        st.success("Data & Foto Rute berhasil dihitung dan disimpan!")
        m1, m2, m3 = st.columns(3)
        m1.metric(label="Total Bensin Digunakan", value=f"{total_liter:.2f} Liter")
        m2.metric(label="Total Biaya Operasional", value=f"Rp {total_biaya:,.0f}")
        m3.metric(label="Efisiensi Rupiah / Meter", value=f"Rp {efisiensi_per_m:,.2f}")
        
        # Simpan Foto Peta secara lokal
        map_filepath = "Tidak Ada"
        if input_img_b64.startswith("data:image"):
            try:
                img_data = base64.b64decode(input_img_b64.split(",")[1])
                filename = f"Map_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                map_filepath = os.path.join(IMAGE_DIR, filename)
                with open(map_filepath, "wb") as f:
                    f.write(img_data)
            except:
                pass
        
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
            "Total Biaya (Rp)": total_biaya,
            "Otorisasi Sistem": "© Mikha Febrian",
            "File Peta": map_filepath 
        }])
        
        if os.path.exists(CSV_FILENAME):
            df_existing = pd.read_csv(CSV_FILENAME)
            df_updated = pd.concat([df_existing, data_baru], ignore_index=True)
        else:
            df_updated = data_baru
            
        df_updated.to_csv(CSV_FILENAME, index=False)
    else:
        st.error("Jarak tempuh masih 0. Pastikan GPS sudah mendeteksi perjalanan sebelum klik Simpan.")

st.markdown("---")

# ==========================================
# BAGIAN 4: LOG LAPORAN & MANAJEMEN DATA
# ==========================================
st.markdown("### 4. Log Laporan Audit PT S.R.I.")
if os.path.exists(CSV_FILENAME):
    df_tampil = pd.read_csv(CSV_FILENAME)
    st.dataframe(df_tampil, use_container_width=True)
    
    # Fungsi Generate File Excel (.xlsx) dengan Foto Peta tertempel otomatis
    def generate_excel_with_images(df):
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet("Laporan Audit")
        
        bold_format = workbook.add_format({'bold': True, 'bg_color': '#f3f4f6', 'border': 1})
        border_format = workbook.add_format({'border': 1, 'valign': 'vcenter'})
        
        headers = df.columns
        for col_num, data in enumerate(headers):
            worksheet.write(0, col_num, data, bold_format)
            worksheet.set_column(col_num, col_num, 15)
        
        for row_num, row_data in df.iterrows():
            for col_num, cell_data in enumerate(row_data):
                if headers[col_num] == "File Peta" and str(cell_data).endswith('.png'):
                    worksheet.write(row_num + 1, col_num, "Terlampir", border_format)
                    if os.path.exists(cell_data):
                        worksheet.insert_image(row_num + 1, col_num, cell_data, {'x_scale': 0.15, 'y_scale': 0.15, 'x_offset': 5, 'y_offset': 5})
                        worksheet.set_row(row_num + 1, 60) 
                else:
                    worksheet.write(row_num + 1, col_num, cell_data, border_format)
                    
        workbook.close()
        return output.getvalue()

    col_dl, col_blank = st.columns([1, 2])
    with col_dl:
        excel_data = generate_excel_with_images(df_tampil)
        st.download_button(
            label="Unduh File Laporan EXCEL (Dengan Foto Rute)",
            data=excel_data,
            file_name="Laporan_Audit_Forklift_PT_SRI.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    
    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("Manajemen Data (Hapus Kesalahan Input)"):
        if not df_tampil.empty:
            
            opsi_hapus = df_tampil.apply(
                lambda row: f"{row.name} | {row.get('Tanggal', 'N/A')} - {row.get('Seri Forklift', 'N/A')} - Rp {row.get('Total Biaya (Rp)', 0)}", 
                axis=1
            )
            
            baris_dihapus = st.selectbox(
                "Pilih data yang salah input untuk dihapus:", 
                df_tampil.index, 
                format_func=lambda x: opsi_hapus[x]
            )
            
            if st.button("Hapus Data Terpilih", type="primary"):
                path_foto = df_tampil.get("File Peta", pd.Series()).get(baris_dihapus)
                
                if pd.notna(path_foto) and str(path_foto).endswith('.png') and os.path.exists(str(path_foto)):
                    try:
                        os.remove(path_foto) 
                    except:
                        pass
                
                df_tampil = df_tampil.drop(index=baris_dihapus)
                df_tampil.to_csv(CSV_FILENAME, index=False)
                st.success("Data beserta foto rutenya berhasil dihapus dari sistem!")
                st.rerun() 
        else:
            st.info("Data masih kosong.")
else:
    st.info("Belum ada data perjalanan yang tersimpan di server.")

# ==========================================
# WATERMARK SISTEM (HAK CIPTA)
# ==========================================
st.markdown("""
    <br><br>
    <div style="text-align: center; font-size: 12px; color: #888; border-top: 1px solid #eaeaea; padding-top: 15px;">
        <b>Sistem Audit Forklift PT S.R.I.</b><br>
        Hak Cipta © 2026 Dirancang dan Dikembangkan oleh <b>Mikha Febrian</b>.<br>
        <i>Sistem dan file basis data ini dilindungi. Tidak untuk diakui, diduplikasi, atau didistribusikan tanpa izin.</i>
    </div>
""", unsafe_allow_html=True)

import streamlit as st
import pandas as pd
from PIL import Image
import imagehash
import os
import google.generativeai as genai

# --- KONFIGURASI AI (GEMINI) ---
# Dapatkan API Key gratis di: https://aistudio.google.com/
API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=API_KEY)
model_ai = genai.GenerativeModel('gemini-1.5-flash')

# --- KONFIGURASI FOLDER ---
FOLDER_GAMBAR = "screenshot_mahasiswa"
FILE_CSV = "data_nilai.csv"

if not os.path.exists(FOLDER_GAMBAR):
    os.makedirs(FOLDER_GAMBAR)

if not os.path.exists(FILE_CSV):
    df_awal = pd.DataFrame(columns=["Nama", "NIM", "Total_Skor", "Plagiasi", "Keputusan_AI", "File_Gambar"])
    df_awal.to_csv(FILE_CSV, index=False)

st.set_page_config(page_title="Penilaian Web Angkatan 26", layout="wide")
st.title("Sistem Penilaian Web (AI Decision & Plagiarism Check)")

# Fungsi Cek Plagiasi
def cek_plagiasi(gambar_baru):
    hash_baru = imagehash.phash(Image.open(gambar_baru))
    batas_mirip = 5 
    for file in os.listdir(FOLDER_GAMBAR):
        hash_lama = imagehash.phash(Image.open(os.path.join(FOLDER_GAMBAR, file)))
        if hash_baru - hash_lama <= batas_mirip:
            return True, file
    return False, None

# Opsi Bobot Nilai
opsi_poin = {"Sempurna (1.0)": 1.0, "Sebagian (0.5)": 0.5, "Sedikit (0.25)": 0.25, "Tidak Ada (0.0)": 0.0}

with st.form("form_nilai"):
    st.subheader("1. Identitas Mahasiswa")
    col1, col2 = st.columns(2)
    with col1:
        nama = st.text_input("Nama Mahasiswa")
        nim = st.text_input("NIM")
    with col2:
        kelas = st.selectbox("Kelas", ["A", "B", "C", "D"])
        paham_kode = st.radio("Pemahaman Wawancara:", ["Sangat Paham", "Kurang Paham", "Tidak Paham/Nyontek"])

    st.subheader("2. Penilaian Fitur")
    col_wajib, col_opsional = st.columns(2)
    with col_wajib:
        st.markdown("**Fitur Wajib**")
        f_login = st.selectbox("Login", list(opsi_poin.keys()), key="f1")
        f_crud = st.selectbox("CRUD", list(opsi_poin.keys()), key="f2")
        f_edit = st.selectbox("Bisa Edit Elemen", list(opsi_poin.keys()), key="f3")
    
    with col_opsional:
        st.markdown("**Fitur Opsional**")
        f_welcome = st.selectbox("Welcome/Landing Page", list(opsi_poin.keys()), key="f4")
        f_register = st.selectbox("Register", list(opsi_poin.keys()), key="f5")

    st.subheader("3. Catatan Asdos & File")
    notes_asdos = st.text_area("Catatan/Notes Tambahan (Opsional, tapi penting untuk AI):", 
                               placeholder="Contoh: Tampilan webnya rapi, tapi saat ditanya alur CRUD dia bingung di bagian database...")
    gambar_upload = st.file_uploader("Upload Screenshot Web", type=['png', 'jpg', 'jpeg'])
    
    submit = st.form_submit_button("Generate AI Decision & Simpan")

# --- PROSES SCORING & AI ---
if submit:
    if not (nama and nim and gambar_upload):
        st.error("Nama, NIM, dan Screenshot wajib diisi!")
    else:
        with st.spinner("Sedang memproses gambar dan generate AI Decision..."):
            # Hitung Skor
            skor_wajib = opsi_poin[f_login] + opsi_poin[f_crud] + opsi_poin[f_edit]
            skor_opsional = opsi_poin[f_welcome] + opsi_poin[f_register]
            total_skor = skor_wajib + skor_opsional
            
            # Cek Plagiasi
            terindikasi, file_mirip = cek_plagiasi(gambar_upload)
            status_plagiasi = f"TERDETEKSI (Mirip dgn {file_mirip})" if terindikasi else "AMAN"

            # Buat Prompt untuk AI
            prompt = f"""
            Kamu adalah asisten dosen. Berikan keputusan singkat (1-2 paragraf) apakah mahasiswa ini Lulus, Lulus dengan Syarat, atau Diskualifikasi dari tugas Web.
            Data Mahasiswa:
            - Skor Fitur Wajib (Max 3): {skor_wajib}
            - Skor Fitur Opsional (Max 2): {skor_opsional}
            - Pemahaman Wawancara: {paham_kode}
            - Indikasi Plagiasi UI: {status_plagiasi}
            - Catatan Asdos saat Wawancara: {notes_asdos}
            
            Aturan: Jika terdeteksi plagiasi ATAU tidak paham saat wawancara, wajib berikan sanksi tegas/diskualifikasi. Jelaskan alasannya berdasarkan data di atas.
            """
            
            # Panggil Gemini AI
            try:
                respon_ai = model_ai.generate_content(prompt)
                keputusan_ai = respon_ai.text
            except Exception as e:
                keputusan_ai = "Gagal memuat AI Decision. Periksa API Key."

            # Tampilkan Hasil AI
            st.write("### 🤖 Hasil Keputusan AI")
            if terindikasi:
                st.error(f"⚠️ PLAGIASI UI TERDETEKSI: Tampilan mirip dengan {file_mirip}")
            st.info(keputusan_ai)

            # Simpan File Gambar & Database
            nama_file_baru = f"{nim}_{nama}.jpg"
            with open(os.path.join(FOLDER_GAMBAR, nama_file_baru), "wb") as f:
                f.write(gambar_upload.getbuffer())
                
            df = pd.read_csv(FILE_CSV)
            data_baru = pd.DataFrame([{
                "Nama": nama, "NIM": nim, "Total_Skor": total_skor, 
                "Plagiasi": status_plagiasi, "Keputusan_AI": keputusan_ai, "File_Gambar": nama_file_baru
            }])
            df = pd.concat([df, data_baru], ignore_index=True)
            df.to_csv(FILE_CSV, index=False)

st.write("### Rekap Nilai Sementara")
st.dataframe(pd.read_csv(FILE_CSV)[["Nama", "NIM", "Total_Skor", "Plagiasi"]])

# --- TOMBOL DOWNLOAD DATA ---
st.write("### Backup Data")
with open(FILE_CSV, "rb") as file:
    st.download_button(
        label="📥 Download Data Nilai (CSV)",
        data=file,
        file_name="Rekap_Nilai_Web_Angkatan_26.csv",
        mime="text/csv"
    )
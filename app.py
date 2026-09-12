import streamlit as st
import pandas as pd
from PIL import Image
import imagehash
import os
import google.generativeai as genai

# --- KONFIGURASI AI (GEMINI) ---
API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=API_KEY)
model_ai = genai.GenerativeModel('gemini-1.5-flash')

# --- KONFIGURASI FOLDER ---
FOLDER_GAMBAR = "screenshot_mahasiswa"
FILE_CSV = "data_nilai.csv"

if not os.path.exists(FOLDER_GAMBAR):
    os.makedirs(FOLDER_GAMBAR)

if not os.path.exists(FILE_CSV):
    df_awal = pd.DataFrame(columns=["Nama", "NIM", "Kelas", "Total_Skor", "Plagiasi", "Keputusan_AI", "File_Gambar"])
    df_awal.to_csv(FILE_CSV, index=False)

st.set_page_config(page_title="Penilaian Web Angkatan 26", layout="wide")
st.title("Sistem Penilaian Web (AI Decision & Plagiarism Check)")

# Fungsi Cek Plagiasi untuk Multi-Gambar
def cek_plagiasi(daftar_gambar_upload):
    batas_mirip = 5 
    for img_upload in daftar_gambar_upload:
        hash_baru = imagehash.phash(Image.open(img_upload))
        for file in os.listdir(FOLDER_GAMBAR):
            hash_lama = imagehash.phash(Image.open(os.path.join(FOLDER_GAMBAR, file)))
            if hash_baru - hash_lama <= batas_mirip:
                return True, file 
    return False, None

# --- OPSI BOBOT NILAI BARU ---
opsi_mutlak = {"Ya (1.0)": 1.0, "Tidak (0.0)": 0.0} # Khusus Fitur Wajib
opsi_poin = {"Sempurna (1.0)": 1.0, "Sebagian (0.5)": 0.5, "Sedikit (0.25)": 0.25, "Tidak Ada (0.0)": 0.0} # Khusus Fitur Opsional

with st.form("form_nilai"):
    st.subheader("1. Identitas Mahasiswa")
    col1, col2 = st.columns(2)
    with col1:
        nama = st.text_input("Nama Mahasiswa")
        nim = st.text_input("NIM")
    with col2:
        kelas = st.selectbox("Kelas", ["A Layo", "B Layo", "A Bukit", "B Bukit"])

    st.subheader("2. Penilaian Fitur")
    col_wajib, col_opsional = st.columns(2)
    with col_wajib:
        st.markdown("**Fitur Wajib (Mutlak)**")
        f_login = st.selectbox("Login", list(opsi_mutlak.keys()), key="f1")
        f_crud = st.selectbox("CRUD", list(opsi_mutlak.keys()), key="f2")
        f_edit = st.selectbox("Bisa Edit Elemen", list(opsi_mutlak.keys()), key="f3")
    
    with col_opsional:
        st.markdown("**Fitur Opsional (Bisa Parsial)**")
        f_welcome = st.selectbox("Welcome/Landing Page", list(opsi_poin.keys()), key="f4")
        f_register = st.selectbox("Register", list(opsi_poin.keys()), key="f5")

    st.subheader("3. Catatan Asdos & File")
    notes_asdos = st.text_area("Catatan/Notes Tambahan (Opsional, tapi penting untuk AI):", 
                               placeholder="Contoh: Logika CRUD sudah jalan, tapi tampilan berantakan...")
    
    gambar_uploads = st.file_uploader("Upload Screenshot Web (Bisa pilih/blok banyak gambar sekaligus)", 
                                      type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)
    
    submit = st.form_submit_button("Generate AI Decision & Simpan")

# --- PROSES SCORING & AI ---
if submit:
    if not (nama and nim and len(gambar_uploads) > 0):
        st.error("Nama, NIM, dan minimal 1 Screenshot wajib diisi!")
    else:
        with st.spinner("Sedang memproses gambar dan generate AI Decision..."):
            # Hitung Skor dengan pemisah dictionary
            skor_wajib = opsi_mutlak[f_login] + opsi_mutlak[f_crud] + opsi_mutlak[f_edit]
            skor_opsional = opsi_poin[f_welcome] + opsi_poin[f_register]
            total_skor = skor_wajib + skor_opsional
            
            # Cek Plagiasi
            terindikasi, file_mirip = cek_plagiasi(gambar_uploads)
            status_plagiasi = f"TERDETEKSI (Mirip dgn {file_mirip})" if terindikasi else "AMAN"

            # Buat Prompt untuk AI (Instruksi Diperketat)
            prompt = f"""
            Kamu adalah asisten dosen. Berikan keputusan singkat (1-2 paragraf) apakah mahasiswa ini Lulus, Lulus dengan Syarat, atau Diskualifikasi dari tugas Web.
            Data Mahasiswa:
            - Skor Fitur Wajib (Max 3): {skor_wajib}
            - Skor Fitur Opsional (Max 2): {skor_opsional}
            - Indikasi Plagiasi UI: {status_plagiasi}
            - Catatan Asdos: {notes_asdos}
            
            Aturan: 
            - Jika terdeteksi plagiasi, wajib berikan sanksi tegas/diskualifikasi. 
            - Jika Skor Fitur Wajib kurang dari 3, berikan kritik keras karena fitur mutlak tidak lengkap, dan jangan berikan kelulusan sempurna.
            Jelaskan alasannya berdasarkan data di atas dan pertimbangkan catatan asdos.
            """
            
            try:
                respon_ai = model_ai.generate_content(prompt)
                keputusan_ai = respon_ai.text
            except Exception as e:
                keputusan_ai = "Gagal memuat AI Decision."

            # Tampilkan Hasil AI
            st.write("### 🤖 Hasil Keputusan AI")
            if terindikasi:
                st.error(f"⚠️ PLAGIASI UI TERDETEKSI: Terdapat screenshot yang mirip dengan tugas {file_mirip}")
            st.info(keputusan_ai)

            # Simpan File Gambar & Database
            nama_file_tersimpan = []
            for i, img in enumerate(gambar_uploads):
                nama_file_baru = f"{nim}_{nama}_pic{i+1}.jpg"
                with open(os.path.join(FOLDER_GAMBAR, nama_file_baru), "wb") as f:
                    f.write(img.getbuffer())
                nama_file_tersimpan.append(nama_file_baru)
            
            file_gambar_str = ", ".join(nama_file_tersimpan)
                
            df = pd.read_csv(FILE_CSV)
            data_baru = pd.DataFrame([{
                "Nama": nama, "NIM": nim, "Kelas": kelas, "Total_Skor": total_skor, 
                "Plagiasi": status_plagiasi, "Keputusan_AI": keputusan_ai, "File_Gambar": file_gambar_str
            }])
            df = pd.concat([df, data_baru], ignore_index=True)
            df.to_csv(FILE_CSV, index=False)

st.write("### Rekap Nilai Sementara")
st.dataframe(pd.read_csv(FILE_CSV)[["Nama", "NIM", "Kelas", "Total_Skor", "Plagiasi"]])

# --- TOMBOL DOWNLOAD DATA ---
st.write("### Backup Data")
with open(FILE_CSV, "rb") as file:
    st.download_button(
        label="📥 Download Data Nilai (CSV)",
        data=file,
        file_name="Rekap_Nilai_Web_Angkatan_26.csv",
        mime="text/csv"
    )

import streamlit as st
import pandas as pd
from PIL import Image
import imagehash
import os
import google.generativeai as genai

# --- KONFIGURASI AI ---
API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=API_KEY)
model_ai = genai.GenerativeModel('gemini-1.5-flash')

# --- KONFIGURASI FOLDER & DATABASE ---
FOLDER_GAMBAR = "screenshot_mahasiswa"
FILE_CSV = "data_nilai.csv"

if not os.path.exists(FOLDER_GAMBAR):
    os.makedirs(FOLDER_GAMBAR)

COLUMNS = [
    "NIM", "Nama", "Kelas", "F_Login", "F_CRUD", "F_Edit", "F_Welcome", "F_Register", 
    "Skor_Wajib", "Skor_Opsional", "Total_Skor", "Notes", "File_Gambar", 
    "Plagiasi", "Keputusan_AI", "Status"
]

if not os.path.exists(FILE_CSV):
    pd.DataFrame(columns=COLUMNS).to_csv(FILE_CSV, index=False)

# --- FUNGSI PERBAIKAN NIM (AUTO-HEALING) ---
def perbaiki_nim(nim_val):
    n = str(nim_val).strip()
    # Jika terbaca sebagai desimal (float), hilangkan .0 di belakangnya
    if n.endswith('.0'): 
        n = n[:-2]
    # Jika angka 0 di depan hilang (khas NIM UNSRI 0304 terbaca 304)
    if n.startswith('304'): 
        n = '0' + n
    return n

# Baca Database dan Bersihkan Duplikat
df = pd.read_csv(FILE_CSV)
df['NIM'] = df['NIM'].apply(perbaiki_nim) # Paksa format NIM jadi teks utuh
df = df.drop_duplicates(subset=['NIM'], keep='last') # AUTO-CLEAN: Hapus duplikat yang telanjur masuk

st.set_page_config(page_title="Penilaian Web Angkatan 26", layout="wide")
st.title("Sistem Penilaian Web (Mode Kolaborasi)")

# --- OPSI BOBOT NILAI ---
opsi_mutlak = {"Ya (1.0)": 1.0, "Tidak (0.0)": 0.0} 
opsi_poin = {"Sempurna (1.0)": 1.0, "Sebagian (0.5)": 0.5, "Sedikit (0.25)": 0.25, "Tidak Ada (0.0)": 0.0}

# --- TABS UI ---
tab1, tab2, tab3 = st.tabs(["📝 1. Input & Update Data", "🎯 2. Final Scoring AI", "🗄️ 3. Database"])

# ==========================================
# TAB 1: INPUT & UPDATE (Simpan Sementara)
# ==========================================
with tab1:
    st.header("Tambah Data Baru / Update Screenshot")
    nim_input = st.text_input("🔍 Masukkan NIM Mahasiswa (Tekan Enter):")
    
    if nim_input:
        nim_input_str = perbaiki_nim(nim_input)
        
        existing_data = df[df['NIM'] == nim_input_str]
        is_exist = not existing_data.empty
        
        if is_exist:
            st.info(f"✅ Data ditemukan! Anda sedang mengupdate data NIM: {nim_input_str}")
            row = existing_data.iloc[0]
            def_nama = str(row['Nama']) if pd.notna(row['Nama']) else ""
            def_kelas = str(row['Kelas'])
            def_notes = str(row['Notes']) if pd.notna(row['Notes']) else ""
        else:
            st.info(f"✨ Data belum ada. Mendaftarkan NIM baru: {nim_input_str}")
            def_nama = ""
            def_kelas = "A Layo"
            def_notes = ""
            
        with st.form("form_input", clear_on_submit=False):
            st.subheader("Identitas")
            nama = st.text_input("Nama Mahasiswa", value=def_nama)
            
            idx_kelas = ["A Layo", "B Layo", "A Bukit", "B Bukit"].index(def_kelas) if is_exist and def_kelas in ["A Layo", "B Layo", "A Bukit", "B Bukit"] else 0
            kelas = st.selectbox("Kelas", ["A Layo", "B Layo", "A Bukit", "B Bukit"], index=idx_kelas)
            
            st.subheader("Penilaian Fitur")
            col_wajib, col_opsional = st.columns(2)
            with col_wajib:
                st.markdown("**Fitur Wajib (Mutlak)**")
                f_login = st.selectbox("Login", list(opsi_mutlak.keys()))
                f_crud = st.selectbox("CRUD", list(opsi_mutlak.keys()))
                f_edit = st.selectbox("Bisa Edit Elemen", list(opsi_mutlak.keys()))
            
            with col_opsional:
                st.markdown("**Fitur Opsional (Parsial)**")
                f_welcome = st.selectbox("Welcome/Landing Page", list(opsi_poin.keys()))
                f_register = st.selectbox("Register", list(opsi_poin.keys()))

            st.subheader("Catatan & Screenshot")
            notes_asdos = st.text_area("Catatan/Notes Asdos:", value=def_notes)
            gambar_uploads = st.file_uploader("Upload Screenshot Baru (Bisa pilih banyak sekaligus)", 
                                              type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)
            
            submit_draft = st.form_submit_button("Simpan Data (Draft)")
            
            if submit_draft:
                if not nama:
                    st.error("Nama wajib diisi!")
                else:
                    saved_files = []
                    # Ambil gambar lama jika ada supaya tidak hilang
                    if is_exist and pd.notna(row['File_Gambar']) and str(row['File_Gambar']).strip() != "":
                        saved_files = [x.strip() for x in str(row['File_Gambar']).split(',')]
                        
                    # Simpan gambar baru
                    for img in gambar_uploads:
                        img_name = f"{nim_input_str}_{len(saved_files)+1}.jpg"
                        with open(os.path.join(FOLDER_GAMBAR, img_name), "wb") as f:
                            f.write(img.getbuffer())
                        saved_files.append(img_name)
                        
                    file_gambar_str = ", ".join(saved_files)
                    
                    skor_wajib = opsi_mutlak[f_login] + opsi_mutlak[f_crud] + opsi_mutlak[f_edit]
                    skor_opsional = opsi_poin[f_welcome] + opsi_poin[f_register]
                    total_skor = skor_wajib + skor_opsional
                    
                    new_data = {
                        "NIM": nim_input_str, "Nama": nama, "Kelas": kelas,
                        "F_Login": f_login, "F_CRUD": f_crud, "F_Edit": f_edit,
                        "F_Welcome": f_welcome, "F_Register": f_register,
                        "Skor_Wajib": skor_wajib, "Skor_Opsional": skor_opsional, "Total_Skor": total_skor,
                        "Notes": notes_asdos, "File_Gambar": file_gambar_str,
                        "Plagiasi": "-", "Keputusan_AI": "-", "Status": "Draft"
                    }
                    
                    if is_exist:
                        for key, val in new_data.items():
                            df.loc[df['NIM'] == nim_input_str, key] = val
                    else:
                        df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
                        
                    df.to_csv(FILE_CSV, index=False)
                    st.success(f"✅ Data {nama} ({nim_input_str}) berhasil disimpan! Silakan cek Tab 3.")

# ==========================================
# TAB 2: FINAL SCORING & AI
# ==========================================
with tab2:
    st.header("Jalankan Final Scoring & Pengecekan AI")
    df_draft = df[df['Status'] == 'Draft']
    
    if df_draft.empty:
        st.info("Belum ada mahasiswa berstatus Draft yang datanya siap difinalisasi.")
    else:
        nim_final = st.selectbox("Pilih Mahasiswa:", df_draft['NIM'] + " - " + df_draft['Nama'])
        nim_target = nim_final.split(" - ")[0].strip()
        
        target_data = df_draft[df_draft['NIM'] == nim_target].iloc[0]
        
        file_gbr = target_data['File_Gambar']
        student_imgs = [x.strip() for x in str(file_gbr).split(',')] if pd.notna(file_gbr) and str(file_gbr).strip() != '' else []
        
        st.write(f"**Nama:** {target_data['Nama']}")
        st.write(f"**Total Screenshot Tersimpan:** {len(student_imgs)} gambar")
        
        if st.button("Jalankan Final Scoring & Cek Plagiasi", type="primary"):
            if not student_imgs:
                st.error("Mahasiswa ini belum memiliki screenshot sama sekali! Tambahkan lewat Tab 1.")
            else:
                with st.spinner("Menganalisis kemiripan gambar dan memanggil AI..."):
                    terindikasi = False
                    file_mirip = ""
                    batas_mirip = 5
                    
                    for img_name in student_imgs:
                        target_path = os.path.join(FOLDER_GAMBAR, img_name)
                        if os.path.exists(target_path):
                            hash_baru = imagehash.phash(Image.open(target_path))
                            
                            for all_files in os.listdir(FOLDER_GAMBAR):
                                if all_files not in student_imgs: 
                                    file_lama_path = os.path.join(FOLDER_GAMBAR, all_files)
                                    if os.path.exists(file_lama_path):
                                        hash_lama = imagehash.phash(Image.open(file_lama_path))
                                        if hash_baru - hash_lama <= batas_mirip:
                                            terindikasi = True
                                            file_mirip = all_files
                                            break
                        if terindikasi: break
                        
                    status_plagiasi = f"TERDETEKSI (Mirip dgn {file_mirip})" if terindikasi else "AMAN"
                    
                    prompt = f"""
                    Kamu adalah asisten dosen. Berikan keputusan singkat (1-2 paragraf) apakah mahasiswa ini Lulus, Lulus dengan Syarat, atau Diskualifikasi dari tugas Web.
                    - Skor Fitur Wajib (Max 3): {target_data['Skor_Wajib']}
                    - Skor Fitur Opsional (Max 2): {target_data['Skor_Opsional']}
                    - Indikasi Plagiasi UI: {status_plagiasi}
                    - Catatan Asdos: {target_data['Notes']}
                    
                    Aturan mutlak: 
                    1. Jika terdeteksi plagiasi, wajib diskualifikasi.
                    2. Jika Skor Fitur Wajib kurang dari 3, berikan kritik keras dan jangan berikan kelulusan sempurna.
                    """
                    
                    try:
                        respon_ai = model_ai.generate_content(prompt)
                        keputusan_ai = respon_ai.text
                    except Exception as e:
                        keputusan_ai = "Gagal memuat AI Decision."
                        
                    df.loc[df['NIM'] == nim_target, 'Plagiasi'] = status_plagiasi
                    df.loc[df['NIM'] == nim_target, 'Keputusan_AI'] = keputusan_ai
                    df.loc[df['NIM'] == nim_target, 'Status'] = "Final"
                    df.to_csv(FILE_CSV, index=False)
                    
                    st.success("Final Scoring Selesai!")
                    if terindikasi:
                        st.error(f"⚠️ PLAGIASI UI TERDETEKSI dengan file {file_mirip}")
                    st.info(keputusan_ai)

# ==========================================
# TAB 3: DATABASE & BACKUP
# ==========================================
with tab3:
    st.header("Database Rekap Nilai")
    # Menampilkan tabel tanpa index bawaan Pandas supaya lebih rapi
    st.dataframe(df[["NIM", "Nama", "Kelas", "Skor_Wajib", "Skor_Opsional", "Total_Skor", "Plagiasi", "Status"]].reset_index(drop=True))
    
    with open(FILE_CSV, "rb") as file:
        st.download_button(
            label="📥 Download Data Lengkap (CSV)",
            data=file,
            file_name="Rekap_Nilai_Web_Angkatan_26.csv",
            mime="text/csv"
        )

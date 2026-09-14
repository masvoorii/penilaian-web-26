import streamlit as st
import pandas as pd
from PIL import Image
import imagehash
import os
import time
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
    "Skor_Wajib", "Skor_Opsional", "Total_Skor", "Notes", 
    "Img_Login", "Img_CRUD", "Img_Edit", "Img_Welcome", "Img_Register", 
    "Plagiasi", "Keputusan_AI", "Status"
]

if not os.path.exists(FILE_CSV):
    pd.DataFrame(columns=COLUMNS).to_csv(FILE_CSV, index=False)

# --- FUNGSI AUTO-NIM & CLEANING ---
def perbaiki_nim(nim_val):
    n = str(nim_val).strip()
    if n.endswith('.0'): 
        n = n[:-2]
        
    if n.isdigit() and len(n) <= 3:
        n = n.zfill(3) 
        num = int(n)
        if 1 <= num <= 35:
            n = f"03041182631{n}"
        elif 36 <= num <= 102:
            n = f"03041282631{n}"
        elif 103 <= num <= 173:
            n = f"03041382631{n}"
            
    elif n.startswith('304'): 
        n = '0' + n
        
    return n

# Membaca & Menyiapkan Database Awal
df = pd.read_csv(FILE_CSV)

for col in COLUMNS:
    if col not in df.columns:
        df[col] = ""

kolom_teks = ["NIM", "Nama", "Kelas", "F_Login", "F_CRUD", "F_Edit", "F_Welcome", "F_Register", 
              "Notes", "Img_Login", "Img_CRUD", "Img_Edit", "Img_Welcome", "Img_Register", 
              "Plagiasi", "Keputusan_AI", "Status"]

for col in kolom_teks:
    df[col] = df[col].astype(str).replace('nan', '')

df['NIM'] = df['NIM'].apply(perbaiki_nim)
df = df.drop_duplicates(subset=['NIM'], keep='last')
df = df.sort_values(by='NIM')

st.set_page_config(page_title="Penilaian Web Angkatan 26", layout="wide")

st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

st.title("Sistem Penilaian Web (Mode Kolaborasi)")

opsi_mutlak = {"Ya (1.0)": 1.0, "Tidak (0.0)": 0.0} 
opsi_poin = {
    "Sempurna (1.0)": 1.0, 
    "Hampir Sempurna (0.75)": 0.75, 
    "Sebagian (0.5)": 0.5, 
    "Sedikit (0.25)": 0.25, 
    "Tidak Ada (0.0)": 0.0
}

tab1, tab2, tab3, tab4 = st.tabs(["📝 1. Input & Update", "🎯 2. Final Scoring AI", "🗄️ 3. Database", "🖼️ 4. Galeri Screenshot"])

# ==========================================
# TAB 1: INPUT & UPDATE DATA
# ==========================================
with tab1:
    st.header("Tambah Data Baru / Update Screenshot")
    nim_input = st.text_input("🔍 Masukkan NIM (Bisa full atau cukup 3 digit terakhir lalu Enter):")
    
    if nim_input:
        nim_input_str = perbaiki_nim(nim_input)
        existing_data = df[df['NIM'] == nim_input_str]
        is_exist = not existing_data.empty
        
        if is_exist:
            st.info(f"✅ Data ditemukan! Anda sedang mengupdate data NIM: **{nim_input_str}**")
            row = existing_data.iloc[0]
            def_nama = str(row['Nama']).title() if pd.notna(row['Nama']) and str(row['Nama']) != "" else ""
            def_kelas = str(row['Kelas'])
            def_notes = str(row['Notes']) if pd.notna(row['Notes']) else ""
            
            idx_login = list(opsi_mutlak.keys()).index(row['F_Login']) if row['F_Login'] in opsi_mutlak else 0
            idx_crud = list(opsi_mutlak.keys()).index(row['F_CRUD']) if row['F_CRUD'] in opsi_mutlak else 0
            idx_edit = list(opsi_mutlak.keys()).index(row['F_Edit']) if row['F_Edit'] in opsi_mutlak else 0
            idx_welcome = list(opsi_poin.keys()).index(row['F_Welcome']) if row['F_Welcome'] in opsi_poin else 0
            idx_register = list(opsi_poin.keys()).index(row['F_Register']) if row['F_Register'] in opsi_poin else 0
        else:
            st.info(f"✨ Data belum ada. Mendaftarkan NIM baru: **{nim_input_str}**")
            def_nama, def_kelas, def_notes = "", "A Layo", ""
            idx_login = idx_crud = idx_edit = idx_welcome = idx_register = 0
            
        with st.form("form_input", clear_on_submit=False):
            st.subheader("Identitas")
            nama = st.text_input("Nama Mahasiswa", value=def_nama)
            
            # --- LOGIKA FILTER KELAS GANJIL/GENAP ---
            if nim_input_str and nim_input_str[-1].isdigit():
                digit_terakhir = int(nim_input_str[-1])
                if digit_terakhir % 2 != 0: 
                    opsi_kelas = ["A Layo", "A Bukit"] # Ganjil
                else: 
                    opsi_kelas = ["B Layo", "B Bukit"] # Genap
            else:
                opsi_kelas = ["A Layo", "B Layo", "A Bukit", "B Bukit"]
                
            # Cegah error jika def_kelas dari database lama tidak ada di opsi_kelas yang baru terfilter
            if is_exist and def_kelas in opsi_kelas:
                idx_kelas = opsi_kelas.index(def_kelas)
            else:
                idx_kelas = 0
                
            kelas = st.selectbox("Kelas", opsi_kelas, index=idx_kelas)
            # ----------------------------------------
            
            st.subheader("Rubrik Penilaian Fitur")
            
            st.markdown("**Fitur Wajib (Mutlak)**")
            f_login = st.radio("1. Fitur Login", list(opsi_mutlak.keys()), index=idx_login, horizontal=True)
            f_crud = st.radio("2. Fitur CRUD", list(opsi_mutlak.keys()), index=idx_crud, horizontal=True)
            f_edit = st.radio("3. Bisa Edit Elemen", list(opsi_mutlak.keys()), index=idx_edit, horizontal=True)
            
            st.markdown("---")
            st.markdown("**Fitur Opsional (Bisa Parsial)**")
            f_welcome = st.radio("4. Welcome/Landing Page", list(opsi_poin.keys()), index=idx_welcome, horizontal=True)
            f_register = st.radio("5. Fitur Register", list(opsi_poin.keys()), index=idx_register, horizontal=True)
            st.markdown("---")

            st.subheader("Catatan & Screenshot")
            notes_asdos = st.text_area("Catatan/Notes Asdos:", value=def_notes)
            
            st.write("Jika ingin mengganti, langsung upload gambar baru. Jika ingin menghapus total, centang '🗑️ Hapus foto lama'.")
            
            def render_uploader(col, label, img_type):
                with col:
                    up_file = st.file_uploader(label, type=['png', 'jpg', 'jpeg'])
                    del_flag = False
                    if is_exist and f'Img_{img_type}' in row and pd.notna(row[f'Img_{img_type}']) and row[f'Img_{img_type}'] != "":
                        del_flag = st.checkbox(f"🗑️ Hapus foto lama", key=f"del_{img_type}")
                    return up_file, del_flag

            c1, c2, c3, c4, c5 = st.columns(5)
            up_login, del_login = render_uploader(c1, "Login", "Login")
            up_crud, del_crud = render_uploader(c2, "CRUD", "CRUD")
            up_edit, del_edit = render_uploader(c3, "Edit Elemen", "Edit")
            up_welcome, del_welcome = render_uploader(c4, "Welcome Pg", "Welcome")
            up_register, del_register = render_uploader(c5, "Register", "Register")
            
            submit_draft = st.form_submit_button("Simpan Data (Draft)")
            
            if submit_draft:
                if not nama:
                    st.error("Nama wajib diisi!")
                else:
                    nama_kapital = nama.strip().title()

                    def save_img(uploader_file, img_type, del_flag):
                        if uploader_file:
                            filename = f"{nim_input_str}_{img_type}.jpg"
                            with open(os.path.join(FOLDER_GAMBAR, filename), "wb") as f:
                                f.write(uploader_file.getbuffer())
                            return filename
                        elif del_flag:
                            old_file = os.path.join(FOLDER_GAMBAR, f"{nim_input_str}_{img_type}.jpg")
                            if os.path.exists(old_file):
                                os.remove(old_file)
                            return ""
                        elif is_exist and f'Img_{img_type}' in row and pd.notna(row[f'Img_{img_type}']) and row[f'Img_{img_type}'] != "":
                            return str(row[f'Img_{img_type}'])
                        return ""

                    img_log = save_img(up_login, "Login", del_login)
                    img_crd = save_img(up_crud, "CRUD", del_crud)
                    img_edt = save_img(up_edit, "Edit", del_edit)
                    img_wel = save_img(up_welcome, "Welcome", del_welcome)
                    img_reg = save_img(up_register, "Register", del_register)
                    
                    skor_wajib = opsi_mutlak[f_login] + opsi_mutlak[f_crud] + opsi_mutlak[f_edit]
                    skor_opsional = opsi_poin[f_welcome] + opsi_poin[f_register]
                    
                    new_data = {
                        "NIM": nim_input_str, "Nama": nama_kapital, "Kelas": kelas,
                        "F_Login": f_login, "F_CRUD": f_crud, "F_Edit": f_edit, "F_Welcome": f_welcome, "F_Register": f_register,
                        "Skor_Wajib": skor_wajib, "Skor_Opsional": skor_opsional, "Total_Skor": skor_wajib + skor_opsional,
                        "Notes": notes_asdos, 
                        "Img_Login": img_log, "Img_CRUD": img_crd, "Img_Edit": img_edt, "Img_Welcome": img_wel, "Img_Register": img_reg,
                        "Plagiasi": "-", "Keputusan_AI": "-", "Status": "Draft"
                    }
                    
                    if is_exist:
                        for key, val in new_data.items(): df.loc[df['NIM'] == nim_input_str, key] = val
                    else:
                        df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
                        
                    df = df.sort_values(by='NIM')
                    df.to_csv(FILE_CSV, index=False)
                    st.success(f"✅ Data {nama_kapital} berhasil disimpan!")
                    time.sleep(1)
                    st.rerun()

# ==========================================
# TAB 2: FINAL SCORING & AI
# ==========================================
with tab2:
    st.header("Jalankan Final Scoring & Pengecekan AI")
    df_draft = df[df['Status'] == 'Draft']
    
    if df_draft.empty:
        st.info("Belum ada mahasiswa berstatus Draft.")
    else:
        nim_final = st.selectbox("Pilih Mahasiswa:", df_draft['NIM'] + " - " + df_draft['Nama'])
        nim_target = nim_final.split(" - ")[0].strip()
        target_data = df_draft[df_draft['NIM'] == nim_target].iloc[0]
        
        student_imgs = [str(target_data[k]) for k in ["Img_Login", "Img_CRUD", "Img_Edit", "Img_Welcome", "Img_Register"] 
                        if pd.notna(target_data[k]) and str(target_data[k]).strip() != ""]
        
        st.write(f"**Nama:** {target_data['Nama']} | **Total Screenshot:** {len(student_imgs)}")
        
        if st.button("Jalankan Final Scoring & Cek Plagiasi", type="primary"):
            if not student_imgs:
                st.error("Mahasiswa ini belum memiliki screenshot yang valid di server!")
            else:
                with st.spinner("Menganalisis kemiripan gambar dan memanggil AI..."):
                    terindikasi, file_mirip = False, ""
                    for img_name in student_imgs:
                        target_path = os.path.join(FOLDER_GAMBAR, img_name)
                        if os.path.exists(target_path):
                            hash_baru = imagehash.phash(Image.open(target_path))
                            for all_files in os.listdir(FOLDER_GAMBAR):
                                if all_files not in student_imgs: 
                                    file_lama_path = os.path.join(FOLDER_GAMBAR, all_files)
                                    if os.path.exists(file_lama_path):
                                        if hash_baru - imagehash.phash(Image.open(file_lama_path)) <= 5:
                                            terindikasi, file_mirip = True, all_files
                                            break
                        if terindikasi: break
                        
                    status_plagiasi = f"TERDETEKSI (Mirip dgn {file_mirip})" if terindikasi else "AMAN"
                    
                    prompt = f"""
                    Kamu adalah asisten dosen. Berikan keputusan singkat (1-2 paragraf) apakah mahasiswa Lulus, Lulus dengan Syarat, atau Diskualifikasi dari tugas Web.
                    - Skor Fitur Wajib (Max 3): {target_data['Skor_Wajib']}
                    - Skor Fitur Opsional (Max 2): {target_data['Skor_Opsional']}
                    - Indikasi Plagiasi UI: {status_plagiasi}
                    - Catatan Asdos: {target_data['Notes']}
                    Aturan mutlak: 1. Jika terdeteksi plagiasi, wajib diskualifikasi. 2. Jika Fitur Wajib < 3, kritik keras dan jangan beri kelulusan sempurna.
                    """
                    try:
                        keputusan_ai = model_ai.generate_content(prompt).text
                    except:
                        keputusan_ai = "Gagal memuat AI Decision."
                        
                    df.loc[df['NIM'] == nim_target, 'Plagiasi'] = status_plagiasi
                    df.loc[df['NIM'] == nim_target, 'Keputusan_AI'] = keputusan_ai
                    df.loc[df['NIM'] == nim_target, 'Status'] = "Final"
                    
                    df = df.sort_values(by='NIM')
                    df.to_csv(FILE_CSV, index=False)
                    
                    st.success("Final Scoring Selesai!")
                    if terindikasi: st.error(f"⚠️ PLAGIASI UI TERDETEKSI dengan file {file_mirip}")
                    st.info(keputusan_ai)

# ==========================================
# TAB 3: DATABASE & IMPORT/EXPORT
# ==========================================
with tab3:
    st.header("Database Rekap Nilai")
    
    kolom_ditampilkan = [
        "NIM", "Nama", "Kelas", 
        "F_Login", "F_CRUD", "F_Edit", "F_Welcome", "F_Register", 
        "Total_Skor", "Plagiasi", "Notes", "Status"
    ]
    st.dataframe(df[kolom_ditampilkan].reset_index(drop=True))
    
    col_dl, col_up = st.columns(2)
    with col_dl:
        with open(FILE_CSV, "rb") as file:
            st.download_button("📥 Download Data Lengkap (CSV)", data=file, file_name="Rekap_Nilai.csv", mime="text/csv")
            
    with col_up:
        uploaded_csv = st.file_uploader("📤 Import/Restore File CSV Lama", type=['csv'])
        if uploaded_csv is not None:
            if st.button("Restore Database"):
                try:
                    df_import = pd.read_csv(uploaded_csv)
                    for col in kolom_teks:
                        if col in df_import.columns:
                            df_import[col] = df_import[col].astype(str).replace('nan', '')
                    df_import['NIM'] = df_import['NIM'].apply(perbaiki_nim)
                    
                    df_import = df_import.sort_values(by='NIM')
                    df_import.to_csv(FILE_CSV, index=False)
                    
                    st.success("✅ Database berhasil di-restore! Halaman akan dimuat ulang...")
                    time.sleep(2)
                    st.rerun()
                except Exception as e:
                    st.error(f"Gagal Import: {e}")
        
    st.markdown("---")
    st.subheader("🗑️ Hapus Data Mahasiswa")
    if not df.empty:
        hapus_nim = st.selectbox("Pilih data yang ingin dihapus permanen:", df['NIM'] + " - " + df['Nama'])
        nim_to_delete = hapus_nim.split(" - ")[0].strip()
        
        if st.button("Hapus Data", type="primary"):
            row_to_delete = df[df['NIM'] == nim_to_delete].iloc[0]
            for img_col in ["Img_Login", "Img_CRUD", "Img_Edit", "Img_Welcome", "Img_Register"]:
                img_file = str(row_to_delete[img_col])
                if pd.notna(img_file) and img_file.strip() != "":
                    img_path = os.path.join(FOLDER_GAMBAR, img_file)
                    if os.path.exists(img_path):
                        os.remove(img_path)
            
            df = df[df['NIM'] != nim_to_delete]
            df.to_csv(FILE_CSV, index=False)
            
            st.success(f"Data {hapus_nim} berhasil dihapus beserta fotonya!")
            time.sleep(1)
            st.rerun()
    else:
        st.info("Database masih kosong.")

# ==========================================
# TAB 4: GALERI SCREENSHOT
# ==========================================
with tab4:
    st.header("Galeri Screenshot Mahasiswa")
    kategori = {"Login": "Img_Login", "CRUD": "Img_CRUD", "Edit Elemen": "Img_Edit", 
                "Welcome Page": "Img_Welcome", "Register": "Img_Register"}
    
    pilihan_kat = st.multiselect("Tampilkan kolom:", list(kategori.keys()), default=list(kategori.keys()))
    
    if not df.empty and pilihan_kat:
        for index, row in df.iterrows():
            with st.expander(f"👨‍💻 {row['Nama']} - {row['NIM']} ({row['Kelas']})", expanded=True):
                cols = st.columns(len(pilihan_kat))
                for i, nama_kat in enumerate(pilihan_kat):
                    kolom_db = kategori[nama_kat]
                    with cols[i]:
                        st.markdown(f"**{nama_kat}**")
                        nama_file = str(row[kolom_db])
                        
                        if pd.notna(row[kolom_db]) and nama_file.strip() != "":
                            path_gbr = os.path.join(FOLDER_GAMBAR, nama_file)
                            if os.path.exists(path_gbr):
                                st.image(Image.open(path_gbr), use_container_width=True)
                            else:
                                st.warning("File foto belum di-reupload")
                        else:
                            st.info("Kosong")
    elif not pilihan_kat:
        st.info("Pilih kategori filter.")
    else:
        st.info("Belum ada data.")

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

def perbaiki_nim(nim_val):
    n = str(nim_val).strip()
    if n.endswith('.0'): n = n[:-2]
    if n.startswith('304'): n = '0' + n
    return n

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

st.set_page_config(page_title="Penilaian Web Angkatan 26", layout="wide")

# Sembunyikan menu bawaan yang tidak perlu
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

st.title("Sistem Penilaian Web (Mode Kolaborasi)")

opsi_mutlak = {"Ya (1.0)": 1.0, "Tidak (0.0)": 0.0} 
opsi_poin = {"Sempurna (1.0)": 1.0, "Sebagian (0.5)": 0.5, "Sedikit (0.25)": 0.25, "Tidak Ada (0.0)": 0.0}

tab1, tab2, tab3, tab4 = st.tabs(["📝 1. Input & Update", "🎯 2. Final Scoring AI", "🗄️ 3. Database", "🖼️ 4. Galeri Screenshot"])

# ==========================================
# TAB 1: INPUT & UPDATE DATA
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
            def_nama = str(row['Nama']) if pd.notna(row['Nama']) and str(row['Nama']) != "" else ""
            def_kelas = str(row['Kelas'])
            def_notes = str(row['Notes']) if pd.notna(row['Notes']) else ""
        else:
            st.info(f"✨ Data belum ada. Mendaftarkan NIM baru: {nim_input_str}")
            def_nama, def_kelas, def_notes = "", "A Layo", ""
            
        with st.form("form_input", clear_on_submit=False):
            st.subheader("Identitas")
            nama = st.text_input("Nama Mahasiswa", value=def_nama)
            idx_kelas = ["A Layo", "B Layo", "A Bukit", "B Bukit"].index(def_kelas) if is_exist and def_kelas in ["A Layo", "B Layo", "A Bukit", "B Bukit"] else 0
            kelas = st.selectbox("Kelas", ["A Layo", "B Layo", "A Bukit", "B Bukit"], index=idx_kelas)
            
            st.subheader("Penilaian Fitur")
            col_wajib, col_opsional = st.columns(2)
            with col_wajib:
                f_login = st.selectbox("Login", list(opsi_mutlak.keys()))
                f_crud = st.selectbox("CRUD", list(opsi_mutlak.keys()))
                f_edit = st.selectbox("Bisa Edit Elemen", list(opsi_mutlak.keys()))
            with col_opsional:
                f_welcome = st.selectbox("Welcome/Landing Page", list(opsi_poin.keys()))
                f_register = st.selectbox("Register", list(opsi_poin.keys()))

            st.subheader("Catatan & Screenshot (Upload sesuai tipe)")
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
                        "NIM": nim_input_str, "Nama": nama, "Kelas": kelas,
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
                        
                    df.to_csv(FILE_CSV, index=False)
                    st.success(f"✅ Data {nama} berhasil disimpan!")
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
                st.error("Mahasiswa ini belum memiliki screenshot!")
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
                    df.to_csv(FILE_CSV, index=False)
                    
                    st.success("Final Scoring Selesai!")
                    if terindikasi: st.error(f"⚠️ PLAGIASI UI TERDETEKSI dengan file {file_mirip}")
                    st.info(keputusan_ai)

# ==========================================
# TAB 3: DATABASE & DELETE
# ==========================================
with tab3:
    st.header("Database Rekap Nilai")
    st.dataframe(df[["NIM", "Nama", "Kelas", "Skor_Wajib", "Total_Skor", "Plagiasi", "Status"]].reset_index(drop=True))
    with open(FILE_CSV, "rb") as file:
        st.download_button("📥 Download Data Lengkap (CSV)", data=file, file_name="Rekap_Nilai.csv", mime="text/csv")
        
    st.markdown("---")
    st.subheader("🗑️ Hapus Data Mahasiswa")
    if not df.empty:
        hapus_nim = st.selectbox("Pilih data yang ingin dihapus permanen:", df['NIM'] + " - " + df['Nama'])
        nim_to_delete = hapus_nim.split(" - ")[0].strip()
        
        if st.button("Hapus Data", type="primary"):
            row_to_delete = df[df['NIM'] == nim_to_delete].iloc[0]
            
            # Hapus foto-fotonya dari folder server dulu
            for img_col in ["Img_Login", "Img_CRUD", "Img_Edit", "Img_Welcome", "Img_Register"]:
                img_file = str(row_to_delete[img_col])
                if pd.notna(img_file) and img_file.strip() != "":
                    img_path = os.path.join(FOLDER_GAMBAR, img_file)
                    if os.path.exists(img_path):
                        os.remove(img_path)
            
            # Hapus data dari file CSV
            df = df[df['NIM'] != nim_to_delete]
            df.to_csv(FILE_CSV, index=False)
            
            st.success(f"Data {hapus_nim} berhasil dihapus beserta fotonya!")
            time.sleep(1) # Jeda sedikit biar pesan suksesnya sempat terbaca
            st.rerun()    # Refresh halaman
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
                                st.warning("File hilang")
                        else:
                            st.info("Kosong")
    elif not pilihan_kat:
        st.info("Pilih kategori filter.")
    else:
        st.info("Belum ada data.")

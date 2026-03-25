import streamlit as st
from supabase import create_client, Client
import pandas as pd
import re

# --- CONFIGURASI HALAMAN ---
st.set_page_config(page_title="Agenda Harian", layout="wide", page_icon="🚀")

# --- 1. KONEKSI SUPABASE ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- 2. LOGIN SESSION ---
if 'user_email' not in st.session_state:
    st.title("🔐 Agenda Harian")
    email_input = st.text_input("Masukkan Email Anda:", placeholder="contoh: namamu@email.com")
    if st.button("Masuk"):
        if email_input and re.match(r"[^@]+@[^@]+\.[^@]+", email_input):
            st.session_state.user_email = email_input.strip().lower()
            st.rerun()
        else:
            st.error("⚠️ Masukkan format email yang valid.")
    st.stop()

current_user = st.session_state.user_email

# --- 3. FUNGSI HELPER DATABASE ---
def add_task(content, category):
    if content:
        supabase.table("tasks").insert({
            "content": content, "category": category, "author": current_user
        }).execute()
        st.rerun()

def add_jurnal(ket, jenis, jumlah):
    supabase.table("finance_jurnal").insert({
        "keterangan": ket, "jenis": jenis, "jumlah": jumlah, "author": current_user
    }).execute()
    st.rerun()

def delete_item(table, item_id):
    supabase.table(table).delete().eq("id", item_id).execute()
    st.rerun()

# --- 4. SIDEBAR ---
st.sidebar.title("👤 Profil")
st.sidebar.write(f"Login: **{current_user}**")
if st.sidebar.button("Keluar (Logout)"):
    del st.session_state.user_email
    st.rerun()

# --- 5. TAMPILAN UTAMA ---
st.title("🚀 Agenda Harian")
tabs = st.tabs(["🔥 Important", "⏰ Urgent", "🤝 Delegate", "🔄 Swip", "💰 Jurnal", "📜 Riwayat Semua"])

# --- TAB 1-4: TO-DO SYSTEM ---
categories = ["important", "urgent", "delegate", "swip"]
for i in range(4):
    with tabs[i]:
        cat = categories[i]
        with st.form(key=f"form_{cat}", clear_on_submit=True):
            content = st.text_area(
                f"Tambah {cat.capitalize()}:", 
                placeholder="Tulis detail tugas... (Maks 500 kata / 30 baris)",
                height=200
            )
            
            if st.form_submit_button("Simpan Permanen", use_container_width=True):
                # --- LOGIKA VALIDASI SPAM ---
                word_count = len(content.split())
                line_count = content.count('\n') + 1
                
                if not content.strip():
                    st.error("⚠️ Konten tidak boleh kosong.")
                elif word_count > 500:
                    st.error(f"⚠️ Terlalu panjang! Maksimal 500 kata (Input kamu: {word_count} kata).")
                elif line_count > 30:
                    st.error(f"⚠️ Terlalu banyak baris! Maksimal 30 baris (Input kamu: {line_count} baris).")
                else:
                    # Jika lolos validasi, baru simpan
                    add_task(content, cat)
                    st.toast("✅ Tugas berhasil disimpan!", icon="🚀")
        
        st.write("---")
        # Menampilkan list dengan gaya Expander agar teks panjang tidak memenuhi layar
        res = supabase.table("tasks").select("*").eq("author", current_user).eq("category", cat).order("created_at", desc=True).execute()
        for item in res.data:
            # Menggunakan expander agar jika teksnya 30 baris, tetap rapi di HP
            with st.expander(f"📌 {item['content'][:40]}..."):
                st.write(item['content'])
                if st.button("🗑️ Hapus", key=f"del_t_{item['id']}", use_container_width=True):
                    delete_item("tasks", item['id'])
                    
# --- TAB 5: JURNAL & LABA RUGI ---
with tabs[4]:
    st.subheader("💰 Keuangan")
    res_fin = supabase.table("finance_jurnal").select("*").eq("author", current_user).order("created_at", desc=True).execute()
    
    if res_fin.data:
        df = pd.DataFrame(res_fin.data)
        df['created_at'] = pd.to_datetime(df['created_at']).dt.date
        d_val = df[df['jenis'] == 'debit']['jumlah'].sum()
        k_val = df[df['jenis'] == 'kredit']['jumlah'].sum()
        saldo = d_val - k_val
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Pemasukan", f"{d_val:,.0f}")
        c2.metric("Pengeluaran", f"{k_val:,.0f}")
        c3.metric("Saldo", f"{saldo:,.0f}")
        
        # Tetap menggunakan dataframe sesuai permintaan sebelumnya agar bisa slider
        st.dataframe(df[['created_at', 'keterangan', 'jenis', 'jumlah']], use_container_width=True)
    
    st.divider()
    with st.expander("➕ Input Transaksi Baru"):
        with st.form("form_jurnal_main", clear_on_submit=True):
            ket_fin = st.text_input("Keterangan")
            jenis_fin = st.selectbox("Tipe", ["Debit", "Kredit"])
            jumlah_fin = st.number_input("Nominal", min_value=0)
            if st.form_submit_button("Simpan", use_container_width=True):
                tipe = "debit" if "Debit" in jenis_fin else "kredit"
                add_jurnal(ket_fin, tipe, jumlah_fin)

# --- TAB 6: RIWAYAT SEMUA (Gaya Expander & Delete Center) ---
with tabs[5]:
    st.subheader("📜 Log Aktivitas & Penghapusan")
    
    # Bagian 2: RIWAYAT KEUANGAN (Expander)
    st.write("### 💰 Riwayat Keuangan")
    # Ambil data keuangan lagi untuk ditampilkan di sini
    all_f = supabase.table("finance_jurnal").select("*").eq("author", current_user).order("created_at", desc=True).limit(30).execute()
    
    if all_f.data:
        for f in all_f.data:
            tgl_f = f['created_at'][5:16]
            tipe_f = "📥 Masuk" if f['jenis'] == 'debit' else "📤 Keluar"
            with st.expander(f"💳 {tgl_f} | {tipe_f} | {f['keterangan'][:20]}..."):
                st.write(f"**Keterangan:** {f['keterangan']}")
                st.write(f"**Tipe:** {f['jenis'].capitalize()}")
                st.write(f"**Nominal:** Rp {f['jumlah']:,.0f}")
                if st.button("🗑️ Hapus Transaksi", key=f"hist_del_f_{f['id']}", use_container_width=True):
                    delete_item("finance_jurnal", f['id'])
    else:
        st.info("Belum ada riwayat keuangan.")

st.text("Data akan tetap tersimpan sampai Anda menghapusnya")

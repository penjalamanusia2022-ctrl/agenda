import streamlit as st
from supabase import create_client, Client
import pandas as pd
import random
import re

# --- 1. KONEKSI SUPABASE ---
# Pastikan URL dan KEY sudah ada di Streamlit Secrets
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- CONFIGURASI HALAMAN ---
st.set_page_config(page_title="Command Center", layout="wide", page_icon="🚀")

# --- 2. LOGIN SESSION ---
if 'user_email' not in st.session_state:
    st.title("🔐 Akses Command Center")
    email_input = st.text_input("Masukkan Email Anda:", placeholder="contoh: wira@email.com")
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
st.title("🚀 Personal Command Center")
tabs = st.tabs(["🔥 Important", "⏰ Urgent", "🤝 Delegate", "🔄 Swip", "💰 Jurnal & Laba Rugi", "📜 Riwayat"])

# --- TAB 1-4: TO-DO SYSTEM ---
categories = ["important", "urgent", "delegate", "swip"]
for i in range(4):
    with tabs[i]:
        cat = categories[i]
        st.subheader(f"Daftar {cat.capitalize()}")
        
        # Form Input
        with st.form(key=f"form_{cat}", clear_on_submit=True):
            content = st.text_input("Tambah Tugas Baru:")
            if st.form_submit_button("Simpan"):
                add_task(content, cat)
        
        st.markdown("---")
        
        # List Data
        res = supabase.table("tasks").select("*").eq("author", current_user).eq("category", cat).order("created_at", desc=True).execute()
        for item in res.data:
            c1, c2 = st.columns([0.85, 0.15])
            c1.write(f"✅ {item['content']}")
            if c2.button("🗑️", key=f"del_{item['id']}"):
                delete_item("tasks", item['id'])

# --- TAB 5: JURNAL & LABA RUGI ---
with tabs[4]:
    st.subheader("📊 Manajemen Keuangan")
    
    # 1. FORM INPUT (Dibuat lebih ringkas)
    with st.expander("➕ Tambah Transaksi Baru", expanded=False):
        with st.form("form_jurnal_baru", clear_on_submit=True):
            col_a, col_b, col_c = st.columns([2, 1, 1.5])
            with col_a:
                ket_fin = st.text_input("Keterangan", placeholder="Contoh: Jual Token $DUIT")
            with col_b:
                jenis_fin = st.selectbox("Tipe", ["Debit (Masuk)", "Kredit (Keluar)"])
            with col_c:
                jumlah_fin = st.number_input("Nominal (Rp)", min_value=0, step=5000)
            
            submit_fin = st.form_submit_button("💾 Simpan ke Cloud")
            if submit_fin:
                tipe = "debit" if "Debit" in jenis_fin else "kredit"
                if ket_fin and jumlah_fin > 0:
                    add_jurnal(ket_fin, tipe, jumlah_fin)
                else:
                    st.warning("Mohon isi keterangan dan nominal.")

    st.divider()
    
    # 2. AMBIL DATA & KALKULASI
    res_fin = supabase.table("finance_jurnal").select("*").eq("author", current_user).order("created_at", desc=True).execute()
    
    if res_fin.data:
        df = pd.DataFrame(res_fin.data)
        total_d = df[df['jenis'] == 'debit']['jumlah'].sum()
        total_k = df[df['jenis'] == 'kredit']['jumlah'].sum()
        saldo = total_d - total_k
        
        # Tampilan Ringkasan (Metrics)
        m1, m2, m3 = st.columns(3)
        m1.metric("Pendapatan (In)", f"Rp {total_d:,.0f}")
        m2.metric("Pengeluaran (Out)", f"Rp {total_k:,.0f}")
        m3.metric("Laba/Rugi Bersih", f"Rp {saldo:,.0f}", delta=float(saldo))
        
        st.markdown("### 📜 Detail Transaksi")
        
        # 3. DAFTAR TRANSAKSI DENGAN TOMBOL HAPUS/EDIT
        for _, item in df.iterrows():
            with st.container():
                # Styling warna berdasarkan jenis
                color = "🟢" if item['jenis'] == 'debit' else "🔴"
                tgl = item['created_at'][:10]
                
                # Baris Transaksi
                c_icon, c_info, c_amt, c_action = st.columns([0.1, 0.5, 0.25, 0.15])
                
                c_icon.write(color)
                c_info.write(f"**{item['keterangan']}** \n_{tgl}_")
                c_amt.write(f"Rp {item['jumlah']:,.0f}")
                
                # Tombol Hapus (Karena Edit di Streamlit cukup kompleks, kita prioritaskan Hapus)
                if c_action.button("🗑️", key=f"del_fin_{item['id']}"):
                    delete_item("finance_jurnal", item['id'])
                
                st.divider()
    else:
        st.info("Belum ada data keuangan terdaftar.")

# --- TAB 6: RIWAYAT SEMUA ---
with tabs[5]:
    st.subheader("Log Aktivitas Global")
    # Menampilkan 20 aktivitas terbaru dari tasks
    st.write("**Recent Tasks:**")
    all_t = supabase.table("tasks").select("*").eq("author", current_user).order("created_at", desc=True).limit(20).execute()
    for t in all_t.data:
        st.caption(f"{t['created_at'][:16]} | [{t['category'].upper()}] {t['content']}")

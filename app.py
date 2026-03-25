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
    st.subheader("💰 Laporan Keuangan")
    
    # 1. Ringkasan Angka (Sangat Padat)
    res_fin = supabase.table("finance_jurnal").select("*").eq("author", current_user).order("created_at", desc=True).execute()
    
    if res_fin.data:
        df = pd.DataFrame(res_fin.data)
        d_val = df[df['jenis'] == 'debit']['jumlah'].sum()
        k_val = df[df['jenis'] == 'kredit']['jumlah'].sum()
        saldo = d_val - k_val
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Pendapatan", f"Rp {d_val:,.0f}")
        m2.metric("Pengeluaran", f"Rp {k_val:,.0f}")
        m3.metric("Saldo Akhir", f"Rp {saldo:,.0f}", delta=float(saldo))
        
        st.divider()

        # 2. Form Input Baris Tunggal (Hemat Tempat)
        with st.expander("➕ Tambah Transaksi", expanded=False):
            with st.form("quick_add_fin", clear_on_submit=True):
                c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
                k_f = c1.text_input("Keterangan")
                j_f = c2.selectbox("Tipe", ["Debit", "Kredit"])
                n_f = c3.number_input("Nominal", min_value=0, step=1000)
                if c4.form_submit_button("Simpan"):
                    if k_f and n_f > 0:
                        add_jurnal(k_f, j_f.lower(), n_f)

        # 3. Tabel Data dengan Tombol Hapus
        # Header Tabel
        h1, h2, h3, h4, h5 = st.columns([2, 3, 1.5, 2, 1])
        h1.write("**Tanggal**")
        h2.write("**Keterangan**")
        h3.write("**Tipe**")
        h4.write("**Jumlah**")
        h5.write("**Aksi**")
        st.markdown("---")

        # Isi Tabel (Looping Baris)
        for _, row in df.iterrows():
            r1, r2, r3, r4, r5 = st.columns([2, 3, 1.5, 2, 1])
            r1.write(row['created_at'][:10]) # Hanya tanggal
            r2.write(row['keterangan'])
            r3.write("🟢 In" if row['jenis'] == 'debit' else "🔴 Out")
            r4.write(f"Rp {row['jumlah']:,.0f}")
            if r5.button("🗑️", key=f"del_fin_{row['id']}"):
                delete_item("finance_jurnal", row['id'])
    else:
        st.info("Belum ada data. Silakan tambah transaksi di atas.")

# --- TAB 6: RIWAYAT SEMUA ---
with tabs[5]:
    st.subheader("Log Aktivitas Global")
    # Menampilkan 20 aktivitas terbaru dari tasks
    st.write("**Recent Tasks:**")
    all_t = supabase.table("tasks").select("*").eq("author", current_user).order("created_at", desc=True).limit(20).execute()
    for t in all_t.data:
        st.caption(f"{t['created_at'][:16]} | [{t['category'].upper()}] {t['content']}")

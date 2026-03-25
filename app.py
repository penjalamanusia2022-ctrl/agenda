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

# 3. LIST TRANSAKSI (Ultra Compact - Single Line Style)
    if res_fin.data:
        st.write("### 📜 Riwayat")
        for _, row in df.iterrows():
            # Pembagian kolom: 4 (Ket) : 2 (Waktu) : 3 (Nilai) : 1 (Del)
            # Rasio ini paling pas untuk layar HP agar tidak bertumpuk
            c1, c2, c3, c4 = st.columns([4, 2, 3, 1])
            
            # Kolom 1: Keterangan
            c1.markdown(f"**{row['keterangan']}**")
            
            # Kolom 2: Tanggal (MM-DD)
            c2.markdown(f"<p style='color: gray; font-size: 0.8rem; margin-top: 5px;'>{row['created_at'][5:10]}</p>", unsafe_allow_html=True)
            
            # Kolom 3: Nilai (+/-)
            pref = "+" if row['jenis'] == 'debit' else "-"
            c3.write(f"{pref}{row['jumlah']:,.0f}")
            
            # Kolom 4: Tombol Delete
            if c4.button("🗑️", key=f"del_fin_{row['id']}"):
                delete_item("finance_jurnal", row['id'])
            
            # Pemisah garis yang sangat tipis
            st.markdown("<hr style='margin: 0px 0px 5px 0px; border-top: 1px dashed #eee;'>", unsafe_allow_html=True)
    else:
        st.info("Belum ada data.")
        
# --- TAB 6: RIWAYAT SEMUA ---
with tabs[5]:
    st.subheader("Log Aktivitas Global")
    # Menampilkan 20 aktivitas terbaru dari tasks
    st.write("**Recent Tasks:**")
    all_t = supabase.table("tasks").select("*").eq("author", current_user).order("created_at", desc=True).limit(20).execute()
    for t in all_t.data:
        st.caption(f"{t['created_at'][:16]} | [{t['category'].upper()}] {t['content']}")

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
    # 1. Ringkasan Saldo (Tetap di atas sebagai referensi cepat)
    res_fin = supabase.table("finance_jurnal").select("*").eq("author", current_user).order("created_at", desc=True).execute()
    
    if res_fin.data:
        df = pd.DataFrame(res_fin.data)
        d_val = df[df['jenis'] == 'debit']['jumlah'].sum()
        k_val = df[df['jenis'] == 'kredit']['jumlah'].sum()
        saldo = d_val - k_val
        
        # Baris Ringkasan Rapat
        c_in, c_out, c_bal = st.columns(3)
        c_in.caption(f"In: {d_val:,.0f}")
        c_out.caption(f"Out: {k_val:,.0f}")
        c_bal.markdown(f"**Saldo: {saldo:,.0f}**")
    
    st.divider()

    # 2. Form Input (Dibuat vertikal agar nyaman di keyboard HP)
    with st.expander("➕ Input Transaksi", expanded=False):
        with st.form("simple_add", clear_on_submit=True):
            k_f = st.text_input("Ket")
            j_f = st.selectbox("Tipe", ["Debit", "Kredit"])
            n_f = st.number_input("Nilai", min_value=0, step=1000)
            if st.form_submit_button("Simpan", use_container_width=True):
                if k_f and n_f > 0:
                    add_jurnal(k_f, j_f.lower(), n_f)

    # 3. List Jurnal Harian (Satu Baris Rapat)
    if res_fin.data:
        for _, row in df.iterrows():
            # Format: Keterangan - Waktu - Nilai - Tombol
            # Pembagian kolom: 4 (Ket) : 2 (Waktu) : 3 (Nilai) : 1 (Del)
            c1, c2, c3, c4 = st.columns([4, 2, 3, 1])
            
            c1.write(f"{row['keterangan']}")
            c2.caption(f"{row['created_at'][5:10]}") # Hanya Bulan-Tanggal (MM-DD)
            c3.write(f"{row['jumlah']:,.0f}")
            
            if c4.button("🗑️", key=f"del_fin_{row['id']}"):
                delete_item("finance_jurnal", row['id'])
            
            st.markdown('<div style="margin-top: -15px;"></div>', unsafe_allow_html=True) # Merapatkan jarak antar baris
            st.divider()
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

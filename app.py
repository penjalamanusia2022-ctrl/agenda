import streamlit as st
from supabase import create_client, Client
import pandas as pd
import re

# --- CONFIGURASI HALAMAN ---
st.set_page_config(page_title="Command Center", layout="wide", page_icon="🚀")

# --- 1. KONEKSI SUPABASE ---
# Diambil dari Settings > Secrets di Streamlit Cloud
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

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
    st.subheader("Manajemen Keuangan")
    
    with st.expander("➕ Input Jurnal Baru"):
        with st.form("form_jurnal", clear_on_submit=True):
            ket_fin = st.text_input("Keterangan")
            jenis_fin = st.selectbox("Tipe", ["Debit (Masuk)", "Kredit (Keluar)"])
            jumlah_fin = st.number_input("Nominal", min_value=0)
            if st.form_submit_button("Simpan Transaksi"):
                tipe = "debit" if "Debit" in jenis_fin else "kredit"
                add_jurnal(ket_fin, tipe, jumlah_fin)

    st.markdown("---")
    
    # Kalkulasi Laba Rugi
    res_fin = supabase.table("finance_jurnal").select("*").eq("author", current_user).execute()
    if res_fin.data:
        df = pd.DataFrame(res_fin.data)
        d_val = df[df['jenis'] == 'debit']['jumlah'].sum()
        k_val = df[df['jenis'] == 'kredit']['jumlah'].sum()
        total = d_val - k_val
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Pendapatan", f"Rp {d_val:,.0f}")
        m2.metric("Pengeluaran", f"Rp {k_val:,.0f}")
        m3.metric("Laba/Rugi", f"Rp {total:,.0f}", delta=float(total))
        
        st.dataframe(df[['created_at', 'keterangan', 'jenis', 'jumlah']], use_container_width=True)
    else:
        st.info("Belum ada catatan keuangan.")

# --- TAB 6: RIWAYAT SEMUA ---
with tabs[5]:
    st.subheader("Log Aktivitas Global")
    # Menampilkan 20 aktivitas terbaru dari tasks
    st.write("**Recent Tasks:**")
    all_t = supabase.table("tasks").select("*").eq("author", current_user).order("created_at", desc=True).limit(20).execute()
    for t in all_t.data:
        st.caption(f"{t['created_at'][:16]} | [{t['category'].upper()}] {t['content']}")

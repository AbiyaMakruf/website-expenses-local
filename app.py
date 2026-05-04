import streamlit as st
from database import Database
from datetime import date
from utils import format_rupiah, render_wallet_card

st.set_page_config(
    page_title="Catatan Keuangan",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize database
if "db" not in st.session_state:
    st.session_state.db = Database()
    st.session_state.db.init_db()

# Load settings
if "app_settings" not in st.session_state:
    st.session_state.app_settings = st.session_state.db.get_all_settings()

# App info in sidebar
with st.sidebar:
    st.markdown("---")
    app_name = st.session_state.app_settings.get("nama_aplikasi", "Catatan Keuangan")
    st.markdown(f"## 💰 {app_name}")
    st.markdown("---")

# Home page
st.title("💰 Selamat Datang")

col1, col2, col3, col4 = st.columns(4)

summary = st.session_state.db.get_summary_bulan_ini()
saldo_total = st.session_state.db.get_saldo_total()
mata_uang = st.session_state.app_settings.get("mata_uang", "Rp")

with col1:
    st.metric("Pemasukan Bulan Ini", format_rupiah(summary["total_pemasukan"], mata_uang))

with col2:
    st.metric("Pengeluaran Bulan Ini", format_rupiah(summary["total_pengeluaran"], mata_uang))

with col3:
    st.metric("Saldo Bulan Ini", format_rupiah(summary["saldo_bulan"], mata_uang))

with col4:
    st.metric("Saldo Total", format_rupiah(saldo_total, mata_uang))

st.markdown("---")

st.subheader("👛 Saldo per Wallet")

df_wallet_saldo = st.session_state.db.get_saldo_semua_wallet()

if df_wallet_saldo:
    n_cols = min(3, len(df_wallet_saldo))
    wallet_cols = st.columns(n_cols)

    for idx, wallet_row in enumerate(df_wallet_saldo):
        with wallet_cols[idx % n_cols]:
            render_wallet_card(wallet_row, mata_uang)

st.markdown("---")

st.markdown("""
### 📊 Navigasi Aplikasi

Gunakan menu di sebelah kiri untuk:
- **Dashboard** - Ringkasan dan grafik keuangan
- **Transaksi** - Tambah transaksi baru
- **Riwayat** - Lihat dan kelola riwayat transaksi
- **Kategori** - Kelola kategori pengeluaran & pemasukan
- **Anggaran** - Atur anggaran per kategori
- **Laporan** - Laporan detail dan ekspor data
- **Pengaturan** - Preferensi aplikasi dan backup database
""")

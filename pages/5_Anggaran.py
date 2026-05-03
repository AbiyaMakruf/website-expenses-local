import streamlit as st
from database import Database
from datetime import date
from utils import format_rupiah, get_bulan_nama
import pandas as pd

st.set_page_config(layout="wide")

if "db" not in st.session_state:
    st.session_state.db = Database()
    st.session_state.db.init_db()

if "app_settings" not in st.session_state:
    st.session_state.app_settings = st.session_state.db.get_all_settings()

st.title("💳 Anggaran Bulanan")

mata_uang = st.session_state.app_settings.get("mata_uang", "Rp")

# Month/Year selector
col_month, col_year = st.columns(2)

today = date.today()
default_bulan = today.month
default_tahun = today.year

with col_month:
    bulan = st.selectbox(
        "Bulan",
        range(1, 13),
        index=default_bulan - 1,
        format_func=lambda x: get_bulan_nama(x),
        key="anggaran_bulan"
    )

with col_year:
    tahun = st.number_input("Tahun", value=default_tahun, min_value=2020, max_value=2100, key="anggaran_tahun")

st.markdown("---")

# Get anggaran data
df_anggaran = st.session_state.db.get_anggaran(bulan, tahun)

# Display budgets
if not df_anggaran.empty:
    st.subheader("📊 Realisasi Anggaran")

    total_anggaran = 0
    total_realisasi = 0

    for idx, row in df_anggaran.iterrows():
        with st.container(border=True):
            col_info, col_progress = st.columns([2, 1])

            with col_info:
                st.markdown(f"### {row['ikon']} {row['nama']}")

                pct = (row['realisasi'] / row['anggaran'] * 100) if row['anggaran'] > 0 else 0
                pct_clamped = min(pct, 100)

                # Progress bar color
                if pct > 100:
                    color = "#ff4444"
                    status = "🔴 Melebihi Anggaran"
                elif pct > 75:
                    color = "#ffaa00"
                    status = "🟡 Mendekati Batas"
                else:
                    color = "#00aa00"
                    status = "🟢 Normal"

                st.progress(pct_clamped / 100, text=status)

            with col_progress:
                st.metric(
                    "Realisasi / Anggaran",
                    f"{pct:.1f}%",
                    delta=f"{format_rupiah(row['realisasi'], mata_uang)} / {format_rupiah(row['anggaran'], mata_uang)}"
                )

            total_anggaran += row['anggaran']
            total_realisasi += row['realisasi']

    # Summary
    st.markdown("---")
    st.subheader("📈 Ringkasan Anggaran")

    col_total_a, col_total_r, col_total_s = st.columns(3)

    with col_total_a:
        st.metric("Total Anggaran", format_rupiah(total_anggaran, mata_uang))

    with col_total_r:
        st.metric("Total Realisasi", format_rupiah(total_realisasi, mata_uang))

    with col_total_s:
        sisa = total_anggaran - total_realisasi
        st.metric("Sisa", format_rupiah(sisa, mata_uang))

else:
    st.info(f"Belum ada anggaran untuk {get_bulan_nama(bulan)} {tahun}")

st.markdown("---")

# Form to set budget
st.subheader("➕ Atur Anggaran")

kategori_list = st.session_state.db.get_all_kategori(jenis="pengeluaran")

if kategori_list:
    with st.form("form_anggaran"):
        kategori_id = st.selectbox(
            "Kategori",
            options=[k['id'] for k in kategori_list],
            format_func=lambda kid: f"{next(k['ikon'] for k in kategori_list if k['id'] == kid)} {next(k['nama'] for k in kategori_list if k['id'] == kid)}"
        )

        # Get existing budget if any
        existing = df_anggaran[df_anggaran['kategori_id'] == kategori_id] if not df_anggaran.empty else pd.DataFrame()
        nominal_default = existing.iloc[0]['anggaran'] if not existing.empty else 0.0

        nominal = st.number_input(
            "Nominal Anggaran",
            min_value=0.0,
            value=nominal_default,
            step=100000.0,
            format="%.0f"
        )

        if st.form_submit_button("💾 Simpan Anggaran", use_container_width=True):
            if nominal > 0:
                st.session_state.db.set_anggaran(kategori_id, bulan, tahun, nominal)
                st.success("✅ Anggaran berhasil disimpan!")
                st.rerun()
            else:
                st.error("Nominal harus lebih dari 0")

else:
    st.info("Belum ada kategori pengeluaran. Silakan buat kategori terlebih dahulu di halaman Kategori.")

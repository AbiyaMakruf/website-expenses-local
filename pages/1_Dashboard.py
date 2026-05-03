import streamlit as st
from database import Database
from datetime import date
from utils import format_rupiah, get_bulan_nama, BULAN_NAMA
import pandas as pd
import altair as alt

st.set_page_config(layout="wide")

if "db" not in st.session_state:
    st.session_state.db = Database()
    st.session_state.db.init_db()

if "app_settings" not in st.session_state:
    st.session_state.app_settings = st.session_state.db.get_all_settings()

st.title("📊 Dashboard Keuangan")

mata_uang = st.session_state.app_settings.get("mata_uang", "Rp")

# Sidebar: Month/Year selector
with st.sidebar:
    st.subheader("📅 Filter Periode")
    col_month, col_year = st.columns(2)

    today = date.today()
    default_bulan = today.month
    default_tahun = today.year

    with col_month:
        bulan = st.selectbox(
            "Bulan",
            range(1, 13),
            index=default_bulan - 1,
            format_func=lambda x: get_bulan_nama(x)
        )

    with col_year:
        tahun = st.number_input("Tahun", value=default_tahun, min_value=2020, max_value=2100)

# Get summary data
summary = st.session_state.db.get_summary_bulan_ini()
saldo_total = st.session_state.db.get_saldo_total()

# Top metrics
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Pemasukan Bulan Ini", format_rupiah(summary["total_pemasukan"], mata_uang))

with col2:
    st.metric("Pengeluaran Bulan Ini", format_rupiah(summary["total_pengeluaran"], mata_uang))

with col3:
    st.metric("Saldo Bulan Ini", format_rupiah(summary["saldo_bulan"], mata_uang))

with col4:
    st.metric("Saldo Total", format_rupiah(saldo_total, mata_uang))

st.markdown("---")

# Charts
chart_col1, chart_col2 = st.columns(2)

# Pie chart: Pengeluaran per Kategori
with chart_col1:
    st.subheader("💰 Pengeluaran per Kategori")

    df_kategori = st.session_state.db.get_pengeluaran_per_kategori(bulan, tahun)

    if not df_kategori.empty:
        pie_chart = alt.Chart(df_kategori).mark_arc().encode(
            theta="total",
            color=alt.Color("nama", scale=alt.Scale(scheme="set2")),
            tooltip=["nama", alt.Tooltip("total", format=".0f")]
        ).properties(height=300)

        st.altair_chart(pie_chart, use_container_width=True)

        # Breakdown table
        display_df = df_kategori.copy()
        display_df['total'] = display_df['total'].apply(lambda x: format_rupiah(x, mata_uang))
        st.dataframe(display_df[['ikon', 'nama', 'total']], use_container_width=True, hide_index=True)

    else:
        st.info("Tidak ada pengeluaran di bulan ini")

# Bar chart: Trend bulanan
with chart_col2:
    st.subheader("📈 Trend 6 Bulan Terakhir")

    df_trend = st.session_state.db.get_trend_bulanan(n_bulan=6)

    if not df_trend.empty:
        # Pivot untuk format yang lebih baik
        df_pivot = df_trend.pivot_table(
            index=['tahun', 'bulan'],
            columns='jenis',
            values='total',
            fill_value=0
        ).reset_index()

        df_pivot['bulan_label'] = df_pivot['bulan'].astype(int).apply(lambda x: get_bulan_nama(x))

        # Unpivot kembali untuk Altair
        value_vars = [col for col in ['pengeluaran', 'pemasukan'] if col in df_pivot.columns]
        df_long = df_pivot.melt(
            id_vars=['tahun', 'bulan', 'bulan_label'],
            value_vars=value_vars,
            var_name='jenis',
            value_name='nominal'
        )

        bar_chart = alt.Chart(df_long).mark_bar().encode(
            x='bulan_label:N',
            y='nominal:Q',
            color='jenis:N',
            tooltip=['bulan_label', 'jenis', alt.Tooltip('nominal', format='.0f')]
        ).properties(height=300)

        st.altair_chart(bar_chart, use_container_width=True)

    else:
        st.info("Belum ada data trend")

# Top 5 Pengeluaran
st.markdown("---")
st.subheader("🏆 Top 5 Pengeluaran Terbesar Bulan Ini")

df_top = st.session_state.db.get_top_pengeluaran(bulan, tahun, limit=5)

if not df_top.empty:
    for idx, (_, row) in enumerate(df_top.iterrows(), 1):
        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
        col_rank, col_icon, col_detail, col_nominal = st.columns([0.5, 0.5, 2.5, 1.5])

        with col_rank:
            st.markdown(f"### {medals[idx-1]}")

        with col_icon:
            st.markdown(f"## {row['ikon']}")

        with col_detail:
            st.markdown(f"**{row['kategori_nama']}**\n{row['tanggal']} — {row['catatan']}")

        with col_nominal:
            st.markdown(f"### {format_rupiah(row['nominal'], mata_uang)}")
else:
    st.info("Tidak ada pengeluaran di bulan ini")

st.markdown("---")

# Saldo per Wallet
st.subheader("👛 Saldo per Wallet")

df_wallet_saldo = st.session_state.db.get_saldo_semua_wallet()

if df_wallet_saldo:
    wallet_cols = st.columns(min(3, len(df_wallet_saldo)))

    for idx, wallet_row in enumerate(df_wallet_saldo):
        with wallet_cols[idx % min(3, len(df_wallet_saldo))]:
            st.metric(
                f"{wallet_row['ikon_bawaan']} {wallet_row['nama']}",
                format_rupiah(wallet_row['saldo_saat_ini'], mata_uang)
            )
else:
    st.info("Tidak ada wallet")

# Summary by jenis
st.markdown("---")
st.subheader("📊 Ringkasan Periode")

col_summary1, col_summary2 = st.columns(2)

# Monthly summary
with col_summary1:
    st.markdown("**Ringkasan Bulan Ini**")

    pemasukan_bulan = summary["total_pemasukan"]
    pengeluaran_bulan = summary["total_pengeluaran"]
    saldo_bulan = summary["saldo_bulan"]

    col_p, col_e, col_s = st.columns(3)
    with col_p:
        st.metric("Pemasukan", format_rupiah(pemasukan_bulan, mata_uang), delta=None)
    with col_e:
        st.metric("Pengeluaran", format_rupiah(pengeluaran_bulan, mata_uang), delta=None)
    with col_s:
        st.metric("Saldo", format_rupiah(saldo_bulan, mata_uang), delta=None)

# Total summary
with col_summary2:
    st.markdown("**Ringkasan Keseluruhan**")

    # Calculate total pemasukan and pengeluaran
    df_all = st.session_state.db.get_transaksi()
    if not df_all.empty:
        total_pemasukan_all = df_all[df_all['jenis'] == 'pemasukan']['nominal'].sum()
        total_pengeluaran_all = df_all[df_all['jenis'] == 'pengeluaran']['nominal'].sum()
    else:
        total_pemasukan_all = 0
        total_pengeluaran_all = 0

    saldo_all = total_pemasukan_all - total_pengeluaran_all

    col_p2, col_e2, col_s2 = st.columns(3)
    with col_p2:
        st.metric("Pemasukan Total", format_rupiah(total_pemasukan_all, mata_uang), delta=None)
    with col_e2:
        st.metric("Pengeluaran Total", format_rupiah(total_pengeluaran_all, mata_uang), delta=None)
    with col_s2:
        st.metric("Saldo Total", format_rupiah(saldo_all, mata_uang), delta=None)

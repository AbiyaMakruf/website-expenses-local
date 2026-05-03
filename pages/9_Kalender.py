import streamlit as st
from database import Database
from datetime import date, timedelta
from utils import format_rupiah, get_bulan_nama
import calendar
import pandas as pd

st.set_page_config(layout="wide")

if "db" not in st.session_state:
    st.session_state.db = Database()
    st.session_state.db.init_db()

if "app_settings" not in st.session_state:
    st.session_state.app_settings = st.session_state.db.get_all_settings()

st.title("📅 Kalender Transaksi")

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
        format_func=lambda x: get_bulan_nama(x)
    )

with col_year:
    tahun = st.number_input("Tahun", value=default_tahun, min_value=2020, max_value=2100)

# Get first and last day of month
first_day = date(tahun, bulan, 1)
last_day = date(tahun, bulan, calendar.monthrange(tahun, bulan)[1])

# Fetch transactions for the month
df_transaksi = st.session_state.db.get_transaksi(
    tanggal_dari=first_day,
    tanggal_sampai=last_day
)

# Build daily data
daily_data = {}
if not df_transaksi.empty:
    for _, row in df_transaksi.iterrows():
        tanggal = pd.to_datetime(row['tanggal']).date()
        day = tanggal.day

        if day not in daily_data:
            daily_data[day] = {"pemasukan": 0, "pengeluaran": 0, "count": 0, "transaksi": []}

        if row['jenis'] == 'pemasukan':
            daily_data[day]["pemasukan"] += row['nominal']
        else:
            daily_data[day]["pengeluaran"] += row['nominal']

        daily_data[day]["count"] += 1
        daily_data[day]["transaksi"].append(row)

st.markdown(f"### {get_bulan_nama(bulan)} {tahun}")

# Calendar grid
col_names = st.columns(7)
day_names = ["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"]

for col, day_name in zip(col_names, day_names):
    with col:
        st.markdown(f"**{day_name}**")

# Set Monday as first day of week
cal = calendar.monthcalendar(tahun, bulan)

for week in cal:
    cols = st.columns(7)

    for col, day in zip(cols, week):
        with col:
            if day == 0:
                st.markdown("")
            else:
                # Check if today
                is_today = (day == today.day and bulan == today.month and tahun == today.year)
                header_style = "### 📍" if is_today else "### "

                st.markdown(f"{header_style}{day}")

                if day in daily_data:
                    data = daily_data[day]
                    st.markdown(f"🔴 {format_rupiah(data['pengeluaran'], mata_uang)}")
                    st.markdown(f"🟢 {format_rupiah(data['pemasukan'], mata_uang)}")

                    if st.button(f"📋 {data['count']} transaksi", key=f"day_{day}"):
                        st.session_state.kalender_selected_day = day
                        st.rerun()
                else:
                    st.markdown("")

st.markdown("---")

# Detail panel untuk hari yang dipilih
if "kalender_selected_day" in st.session_state:
    selected_day = st.session_state.kalender_selected_day

    if selected_day in daily_data:
        st.subheader(f"📋 Transaksi {selected_day} {get_bulan_nama(bulan)} {tahun}")

        transaksi_list = daily_data[selected_day]["transaksi"]

        if transaksi_list:
            # Format for display
            display_data = []
            for row in transaksi_list:
                display_data.append({
                    "Tanggal": row['tanggal'],
                    "Jenis": "Pemasukan" if row['jenis'] == 'pemasukan' else "Pengeluaran",
                    "Kategori": f"{row['ikon']} {row['kategori_nama']}",
                    "Nominal": format_rupiah(row['nominal'], mata_uang),
                    "Catatan": row['catatan'] or "—"
                })

            df_display = pd.DataFrame(display_data)
            st.dataframe(df_display, use_container_width=True, hide_index=True)

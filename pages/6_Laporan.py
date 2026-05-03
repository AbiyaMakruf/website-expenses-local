import streamlit as st
from database import Database
from datetime import date, timedelta
from utils import format_rupiah, get_bulan_nama, BULAN_NAMA
import pandas as pd
import altair as alt
from io import BytesIO
from pathlib import Path

st.set_page_config(layout="wide")

if "db" not in st.session_state:
    st.session_state.db = Database()
    st.session_state.db.init_db()

if "app_settings" not in st.session_state:
    st.session_state.app_settings = st.session_state.db.get_all_settings()

st.title("📈 Laporan & Ekspor")

mata_uang = st.session_state.app_settings.get("mata_uang", "Rp")

# Create tabs
tab_ringkasan, tab_grafik, tab_perbandingan, tab_ekspor = st.tabs(["📊 Ringkasan", "📈 Grafik Detail", "🔄 Perbandingan", "💾 Ekspor"])

# ===== TAB 1: RINGKASAN =====
with tab_ringkasan:
    st.subheader("Ringkasan Periode")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**Pilih Periode**")
        periode_type = st.radio("Tipe Periode", ["Bulan Ini", "Bulan Lalu", "3 Bulan", "Custom"], horizontal=True)

    today = date.today()

    if periode_type == "Bulan Ini":
        tgl_dari = date(today.year, today.month, 1)
        tgl_sampai = today

    elif periode_type == "Bulan Lalu":
        if today.month == 1:
            tgl_dari = date(today.year - 1, 12, 1)
            tgl_sampai = date(today.year - 1, 12, 31)
        else:
            tgl_dari = date(today.year, today.month - 1, 1)
            last_day = (date(today.year, today.month, 1) - timedelta(days=1)).day
            tgl_sampai = date(today.year, today.month - 1, last_day)

    elif periode_type == "3 Bulan":
        tgl_sampai = today
        tgl_dari = today - timedelta(days=90)

    else:  # Custom
        with col2:
            tgl_dari = st.date_input("Dari Tanggal", value=today - timedelta(days=30))
        with col3:
            tgl_sampai = st.date_input("Sampai Tanggal", value=today)

    # Get data for period
    df_periode = st.session_state.db.get_laporan_periode(tgl_dari, tgl_sampai)

    if not df_periode.empty:
        # Ringkasan per kategori
        df_summary = df_periode.groupby("kategori_nama").agg({
            "nominal": "sum"
        }).reset_index().sort_values("nominal", ascending=False)

        st.markdown(f"**Periode: {tgl_dari} s/d {tgl_sampai}**")

        col_total_p, col_total_e, col_total_s = st.columns(3)

        total_pemasukan = df_periode[df_periode['jenis'] == 'pemasukan']['nominal'].sum()
        total_pengeluaran = df_periode[df_periode['jenis'] == 'pengeluaran']['nominal'].sum()
        saldo = total_pemasukan - total_pengeluaran

        with col_total_p:
            st.metric("Total Pemasukan", format_rupiah(total_pemasukan, mata_uang))

        with col_total_e:
            st.metric("Total Pengeluaran", format_rupiah(total_pengeluaran, mata_uang))

        with col_total_s:
            st.metric("Saldo Periode", format_rupiah(saldo, mata_uang))

        st.markdown("---")
        st.subheader("📋 Detail Transaksi")

        display_df = df_periode.copy()
        display_df['tanggal'] = display_df['tanggal'].astype(str)
        display_df['nominal'] = display_df['nominal'].apply(lambda x: format_rupiah(x, mata_uang))
        display_df['jenis'] = display_df['jenis'].map({"pengeluaran": "Pengeluaran", "pemasukan": "Pemasukan"})

        st.dataframe(display_df[['tanggal', 'jenis', 'kategori_nama', 'nominal', 'catatan']], use_container_width=True, hide_index=True)

    else:
        st.info("Tidak ada transaksi dalam periode ini")

# ===== TAB 2: GRAFIK DETAIL =====
with tab_grafik:
    st.subheader("Visualisasi Periode")

    col1, col2 = st.columns(2)

    with col1:
        periode_type_grafik = st.radio("Tipe Periode", ["Bulan Ini", "Bulan Lalu", "3 Bulan", "Custom"], horizontal=False, key="grafik_period")

    today = date.today()

    if periode_type_grafik == "Bulan Ini":
        tgl_dari_grafik = date(today.year, today.month, 1)
        tgl_sampai_grafik = today

    elif periode_type_grafik == "Bulan Lalu":
        if today.month == 1:
            tgl_dari_grafik = date(today.year - 1, 12, 1)
            tgl_sampai_grafik = date(today.year - 1, 12, 31)
        else:
            tgl_dari_grafik = date(today.year, today.month - 1, 1)
            last_day = (date(today.year, today.month, 1) - timedelta(days=1)).day
            tgl_sampai_grafik = date(today.year, today.month - 1, last_day)

    elif periode_type_grafik == "3 Bulan":
        tgl_sampai_grafik = today
        tgl_dari_grafik = today - timedelta(days=90)

    else:  # Custom
        with col2:
            tgl_dari_grafik = st.date_input("Dari Tanggal", value=today - timedelta(days=30), key="grafik_dari")
        with col2:
            tgl_sampai_grafik = st.date_input("Sampai Tanggal", value=today, key="grafik_sampai")

    df_grafik = st.session_state.db.get_laporan_periode(tgl_dari_grafik, tgl_sampai_grafik)

    if not df_grafik.empty:
        # Grafik 1: Bar chart per kategori (pengeluaran only)
        col_chart1, col_chart2 = st.columns(2)

        with col_chart1:
            st.markdown("**Pengeluaran per Kategori**")

            df_pengeluaran = df_grafik[df_grafik['jenis'] == 'pengeluaran'].groupby("kategori_nama")["nominal"].sum().reset_index().sort_values("nominal", ascending=False)

            if not df_pengeluaran.empty:
                chart1 = alt.Chart(df_pengeluaran).mark_bar().encode(
                    x="kategori_nama:N",
                    y="nominal:Q",
                    tooltip=["kategori_nama", alt.Tooltip("nominal", format=".0f")]
                ).properties(height=300, width=400)

                st.altair_chart(chart1, use_container_width=True)

            else:
                st.info("Tidak ada pengeluaran")

        # Grafik 2: Pie chart pemasukan vs pengeluaran
        with col_chart2:
            st.markdown("**Proporsi Pemasukan vs Pengeluaran**")

            df_pie = df_grafik.groupby("jenis")["nominal"].sum().reset_index()
            df_pie['jenis'] = df_pie['jenis'].map({"pengeluaran": "Pengeluaran", "pemasukan": "Pemasukan"})

            if not df_pie.empty:
                chart2 = alt.Chart(df_pie).mark_arc().encode(
                    theta="nominal",
                    color="jenis",
                    tooltip=["jenis", alt.Tooltip("nominal", format=".0f")]
                ).properties(height=300, width=400)

                st.altair_chart(chart2, use_container_width=True)

        # Grafik 3: Line chart trend harian
        st.markdown("**Trend Harian**")

        df_daily = df_grafik.groupby(["tanggal", "jenis"])["nominal"].sum().reset_index()
        df_daily['jenis'] = df_daily['jenis'].map({"pengeluaran": "Pengeluaran", "pemasukan": "Pemasukan"})

        if not df_daily.empty:
            chart3 = alt.Chart(df_daily).mark_line(point=True).encode(
                x="tanggal:T",
                y="nominal:Q",
                color="jenis:N",
                tooltip=["tanggal", "jenis", alt.Tooltip("nominal", format=".0f")]
            ).properties(height=300)

            st.altair_chart(chart3, use_container_width=True)

    else:
        st.info("Tidak ada data untuk periode ini")

# ===== TAB 3: PERBANDINGAN =====
with tab_perbandingan:
    st.subheader("Perbandingan Antar Bulan")

    col_month1, col_month2, col_month3 = st.columns(3)

    today = date.today()

    with col_month1:
        st.markdown("**Bulan 1**")
        month1_input = st.number_input("Bulan 1", min_value=1, max_value=12, value=max(1, today.month - 2), key="comp_month1")
        year1_input = st.number_input("Tahun 1", min_value=2020, max_value=2100, value=today.year, key="comp_year1")

    with col_month2:
        st.markdown("**Bulan 2**")
        month2_input = st.number_input("Bulan 2", min_value=1, max_value=12, value=max(1, today.month - 1), key="comp_month2")
        year2_input = st.number_input("Tahun 2", min_value=2020, max_value=2100, value=today.year, key="comp_year2")

    with col_month3:
        st.markdown("**Bulan 3**")
        month3_input = st.number_input("Bulan 3", min_value=1, max_value=12, value=today.month, key="comp_month3")
        year3_input = st.number_input("Tahun 3", min_value=2020, max_value=2100, value=today.year, key="comp_year3")

    st.markdown("---")

    # Fetch data per kategori per bulan
    df_comp1 = st.session_state.db.get_ringkasan_per_kategori_bulan(month1_input, year1_input)
    df_comp2 = st.session_state.db.get_ringkasan_per_kategori_bulan(month2_input, year2_input)
    df_comp3 = st.session_state.db.get_ringkasan_per_kategori_bulan(month3_input, year3_input)

    # Merge dataframes
    df_merged = pd.concat([df_comp1, df_comp2, df_comp3], ignore_index=False)
    df_merged = df_merged.groupby("kategori_nama").agg({
        "total_pengeluaran": "sum",
        "total_pemasukan": "sum"
    }).reset_index().sort_values("total_pengeluaran", ascending=False)

    if not df_merged.empty:
        st.markdown(f"**Perbandingan Pengeluaran**")

        # Table
        display_comp = df_merged.copy()
        display_comp['total_pengeluaran'] = display_comp['total_pengeluaran'].apply(lambda x: format_rupiah(x, mata_uang))
        display_comp['total_pemasukan'] = display_comp['total_pemasukan'].apply(lambda x: format_rupiah(x, mata_uang))

        st.dataframe(display_comp, use_container_width=True, hide_index=True)

        # Chart
        chart = alt.Chart(df_merged).mark_bar().encode(
            x="kategori_nama:N",
            y="total_pengeluaran:Q",
            color=alt.value("#EF553B"),
            tooltip=["kategori_nama", alt.Tooltip("total_pengeluaran", format=".0f")]
        ).properties(height=300)

        st.altair_chart(chart, use_container_width=True)

    else:
        st.info("Tidak ada data untuk periode ini")

# ===== TAB 4: EKSPOR =====
with tab_ekspor:
    st.subheader("Ekspor Data")

    col1, col2 = st.columns(2)

    with col1:
        format_ekspor = st.radio("Format", ["CSV", "Excel", "PDF"], horizontal=True)

    with col2:
        periode_ekspor = st.selectbox("Periode", ["Bulan Ini", "Bulan Lalu", "3 Bulan", "Custom"])

    today = date.today()

    if periode_ekspor == "Bulan Ini":
        tgl_dari_ekspor = date(today.year, today.month, 1)
        tgl_sampai_ekspor = today

    elif periode_ekspor == "Bulan Lalu":
        if today.month == 1:
            tgl_dari_ekspor = date(today.year - 1, 12, 1)
            tgl_sampai_ekspor = date(today.year - 1, 12, 31)
        else:
            tgl_dari_ekspor = date(today.year, today.month - 1, 1)
            last_day = (date(today.year, today.month, 1) - timedelta(days=1)).day
            tgl_sampai_ekspor = date(today.year, today.month - 1, last_day)

    elif periode_ekspor == "3 Bulan":
        tgl_sampai_ekspor = today
        tgl_dari_ekspor = today - timedelta(days=90)

    else:  # Custom
        col_dari, col_sampai = st.columns(2)
        with col_dari:
            tgl_dari_ekspor = st.date_input("Dari Tanggal", value=today - timedelta(days=30), key="ekspor_dari")
        with col_sampai:
            tgl_sampai_ekspor = st.date_input("Sampai Tanggal", value=today, key="ekspor_sampai")

    df_ekspor = st.session_state.db.get_laporan_periode(tgl_dari_ekspor, tgl_sampai_ekspor)

    if not df_ekspor.empty:
        # Preview
        st.subheader("Preview Data")
        preview_df = df_ekspor.head(10).copy()
        preview_df['tanggal'] = preview_df['tanggal'].astype(str)
        preview_df['nominal'] = preview_df['nominal'].apply(lambda x: format_rupiah(x, mata_uang))

        st.dataframe(preview_df[['tanggal', 'jenis', 'kategori_nama', 'nominal', 'catatan']], use_container_width=True, hide_index=True)

        st.markdown("---")

        # Export button
        if format_ekspor == "CSV":
            csv_data = df_ekspor.to_csv(index=False).encode('utf-8-sig')
            filename = f"Laporan_{tgl_dari_ekspor}_{tgl_sampai_ekspor}.csv"

            st.download_button(
                label="📥 Unduh CSV",
                data=csv_data,
                file_name=filename,
                mime="text/csv",
                use_container_width=True
            )

        elif format_ekspor == "Excel":
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df_ekspor.to_excel(writer, index=False, sheet_name='Transaksi')

            buffer.seek(0)
            filename = f"Laporan_{tgl_dari_ekspor}_{tgl_sampai_ekspor}.xlsx"

            st.download_button(
                label="📥 Unduh Excel",
                data=buffer.getvalue(),
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

        else:  # PDF
            from fpdf import FPDF
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            import tempfile
            import os

            # Hitung summary
            total_pemasukan = df_ekspor[df_ekspor['jenis'] == 'pemasukan']['nominal'].sum()
            total_pengeluaran = df_ekspor[df_ekspor['jenis'] == 'pengeluaran']['nominal'].sum()
            saldo = total_pemasukan - total_pengeluaran

            # Buat pie chart pengeluaran per kategori
            df_pie = df_ekspor[df_ekspor['jenis'] == 'pengeluaran'].groupby('kategori_nama')['nominal'].sum().reset_index()

            class PDF(FPDF):
                def header(self):
                    self.set_font("Helvetica", "B", 14)
                    self.cell(0, 10, "Laporan Keuangan", align="C", new_x="LMARGIN", new_y="NEXT")
                    self.set_font("Helvetica", "", 10)
                    self.cell(0, 7, f"Periode: {tgl_dari_ekspor} s/d {tgl_sampai_ekspor}", align="C", new_x="LMARGIN", new_y="NEXT")
                    self.ln(3)

            pdf = PDF()
            pdf.add_page()

            # Ringkasan
            pdf.set_font("Helvetica", "B", 12)
            pdf.cell(0, 8, "Ringkasan", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 10)
            pdf.cell(60, 7, "Total Pemasukan:")
            pdf.cell(0, 7, format_rupiah(total_pemasukan, mata_uang), new_x="LMARGIN", new_y="NEXT")
            pdf.cell(60, 7, "Total Pengeluaran:")
            pdf.cell(0, 7, format_rupiah(total_pengeluaran, mata_uang), new_x="LMARGIN", new_y="NEXT")
            pdf.cell(60, 7, "Saldo:")
            pdf.cell(0, 7, format_rupiah(saldo, mata_uang), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(5)

            # Pie chart (jika ada pengeluaran)
            if not df_pie.empty:
                fig, ax = plt.subplots(figsize=(5, 3))
                ax.pie(df_pie['nominal'], labels=df_pie['kategori_nama'], autopct='%1.0f%%')
                ax.set_title("Pengeluaran per Kategori")
                chart_buf = BytesIO()
                fig.savefig(chart_buf, format="png", bbox_inches="tight")
                plt.close(fig)
                chart_buf.seek(0)
                # Tulis ke temp file (fpdf2 butuh path)
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                    tmp.write(chart_buf.read())
                    tmp_path = tmp.name
                pdf.image(tmp_path, w=120)
                os.unlink(tmp_path)
                pdf.ln(3)

            # Tabel transaksi
            pdf.set_font("Helvetica", "B", 12)
            pdf.cell(0, 8, "Detail Transaksi", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "B", 9)
            col_widths = [22, 25, 45, 35, 60]
            headers = ["Tanggal", "Jenis", "Kategori", "Nominal", "Catatan"]
            for w, h in zip(col_widths, headers):
                pdf.cell(w, 7, h, border=1)
            pdf.ln()
            pdf.set_font("Helvetica", "", 8)
            for _, row in df_ekspor.iterrows():
                pdf.cell(col_widths[0], 6, str(row['tanggal']), border=1)
                jenis_text = "Pengeluaran" if row['jenis'] == 'pengeluaran' else "Pemasukan"
                pdf.cell(col_widths[1], 6, jenis_text, border=1)
                pdf.cell(col_widths[2], 6, str(row['kategori_nama'])[:20], border=1)
                pdf.cell(col_widths[3], 6, format_rupiah(row['nominal'], mata_uang), border=1)
                catatan_text = str(row['catatan'] or "")[:30]
                pdf.cell(col_widths[4], 6, catatan_text, border=1)
                pdf.ln()

            # Foto struk
            foto_rows = df_ekspor[df_ekspor['foto_path'].notna() & (df_ekspor['foto_path'] != "")]
            if not foto_rows.empty:
                pdf.add_page()
                pdf.set_font("Helvetica", "B", 12)
                pdf.cell(0, 8, "Foto Struk", new_x="LMARGIN", new_y="NEXT")
                for _, row in foto_rows.iterrows():
                    foto_path = row['foto_path']
                    if Path(foto_path).exists():
                        pdf.set_font("Helvetica", "", 9)
                        kategori_name = str(row['kategori_nama'])
                        nominal_text = format_rupiah(row['nominal'], mata_uang)
                        pdf.cell(0, 6, f"{row['tanggal']} - {kategori_name} - {nominal_text}", new_x="LMARGIN", new_y="NEXT")
                        pdf.image(foto_path, w=100)
                        pdf.ln(3)

            pdf_bytes = pdf.output()
            st.download_button(
                "⬇️ Unduh PDF",
                data=bytes(pdf_bytes),
                file_name=f"Laporan_{tgl_dari_ekspor}_{tgl_sampai_ekspor}.pdf",
                mime="application/pdf",
                use_container_width=True
            )

    else:
        st.info("Tidak ada data untuk periode ini")

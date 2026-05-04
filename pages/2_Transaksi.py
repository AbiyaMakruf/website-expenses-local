import streamlit as st
from database import Database
from datetime import date, datetime
from pathlib import Path
from utils import format_rupiah

st.set_page_config(layout="wide")

if "db" not in st.session_state:
    st.session_state.db = Database()
    st.session_state.db.init_db()

if "app_settings" not in st.session_state:
    st.session_state.app_settings = st.session_state.db.get_all_settings()

st.title("➕ Tambah Transaksi")

mata_uang = st.session_state.app_settings.get("mata_uang", "Rp")

# Form to add transaction
with st.form("form_transaksi"):
    col1, col2 = st.columns(2)

    with col1:
        jenis = st.radio("Jenis", ["pengeluaran", "pemasukan"], index=0, horizontal=True)
        tanggal = st.date_input("Tanggal", value=date.today())

    with col2:
        kategori_list = st.session_state.db.get_all_kategori(jenis=jenis)
        if kategori_list:
            kat_map = {k['id']: k for k in kategori_list}
            kategori_id = st.selectbox(
                "Kategori",
                options=[k['id'] for k in kategori_list],
                format_func=lambda kid: f"{kat_map[kid]['ikon']} {kat_map[kid]['nama']}"
            )
        else:
            st.error(f"Tidak ada kategori untuk jenis '{jenis}'")
            kategori_id = None

    col_wallet = st.columns(1)[0]
    with col_wallet:
        wallets = st.session_state.db.get_all_wallets()
        if wallets:
            wallet_map = {w['id']: w for w in wallets}
            wallet_id = st.selectbox(
                "Wallet",
                options=[w['id'] for w in wallets],
                format_func=lambda wid: f"{wallet_map[wid]['ikon_bawaan']} {wallet_map[wid]['nama']}"
            )
        else:
            wallet_id = None

    nominal = st.number_input(
        "Nominal",
        min_value=0.0,
        value=0.0,
        step=1000.0,
        format="%.0f"
    )

    catatan = st.text_area("Catatan (opsional)", max_chars=500, height=100)

    foto = st.file_uploader("📷 Foto Struk/Bukti (opsional)", type=["jpg", "jpeg", "png", "webp"])

    submit = st.form_submit_button("💾 Simpan Transaksi", use_container_width=True)

    if submit:
        if nominal <= 0:
            st.error("Nominal harus lebih dari 0")
        elif not kategori_id:
            st.error("Pilih kategori terlebih dahulu")
        else:
            transaksi_id = st.session_state.db.add_transaksi(
                tanggal=tanggal,
                jenis=jenis,
                kategori_id=kategori_id,
                nominal=nominal,
                catatan=catatan,
                wallet_id=wallet_id
            )

            # Simpan gambar jika ada
            if foto:
                uploads_dir = st.session_state.db.get_uploads_dir()
                ext = foto.name.rsplit(".", 1)[-1].lower()
                filename = f"{transaksi_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.{ext}"
                filepath = uploads_dir / filename
                with open(filepath, "wb") as f:
                    f.write(foto.getbuffer())
                st.session_state.db.update_foto_path(transaksi_id, str(filepath))

            st.success("✅ Transaksi berhasil disimpan!")
            st.rerun()

st.markdown("---")

# Preview: Last 5 transactions
st.subheader("📋 Transaksi Terakhir")

df = st.session_state.db.get_transaksi(limit=5)

if df.empty:
    st.info("Belum ada transaksi")
else:
    # Format display
    display_df = df.copy()
    display_df['tanggal'] = display_df['tanggal'].astype(str)
    display_df['kategori'] = display_df.apply(lambda row: f"{row['ikon']} {row['kategori_nama']}", axis=1)
    display_df['jenis'] = display_df['jenis'].map({"pengeluaran": "Pengeluaran", "pemasukan": "Pemasukan"})
    display_df['nominal'] = display_df['nominal'].apply(lambda x: format_rupiah(x, mata_uang))
    display_df['foto'] = display_df['foto_path'].apply(lambda x: "📷" if x else "—")

    cols_to_show = ['tanggal', 'jenis', 'kategori', 'nominal', 'foto', 'catatan']
    st.dataframe(display_df[cols_to_show], use_container_width=True, hide_index=True)

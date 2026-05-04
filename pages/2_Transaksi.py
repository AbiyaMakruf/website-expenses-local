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

# Jenis + kategori selector OUTSIDE form (dependent selectboxes need re-render)
col_sel1, col_sel2, col_sel3 = st.columns(3)

with col_sel1:
    jenis = st.radio("Jenis", ["pengeluaran", "pemasukan"], index=0, horizontal=True)

# Two-step kategori: parent → optional child
parents = st.session_state.db.get_all_kategori(jenis=jenis, parent_id="root")

with col_sel2:
    if parents:
        parent_map = {p['id']: p for p in parents}
        parent_sel = st.selectbox(
            "Kategori",
            options=[p['id'] for p in parents],
            format_func=lambda pid: f"{parent_map[pid]['ikon']} {parent_map[pid]['nama']}"
        )
    else:
        parent_sel = None
        st.warning(f"Tidak ada kategori untuk '{jenis}'")

with col_sel3:
    children = st.session_state.db.get_all_kategori(parent_id=parent_sel) if parent_sel else []
    if children:
        child_map = {c['id']: c for c in children}
        child_sel = st.selectbox(
            "Sub-kategori",
            options=[c['id'] for c in children],
            format_func=lambda cid: f"{child_map[cid]['ikon']} {child_map[cid]['nama']}"
        )
        kategori_id = child_sel
    else:
        st.markdown("&nbsp;")
        kategori_id = parent_sel

st.markdown("---")

with st.form("form_transaksi"):
    col1, col2 = st.columns(2)

    with col1:
        tanggal = st.date_input("Tanggal", value=date.today())

    with col2:
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

    nominal = st.number_input("Nominal", min_value=0.0, value=0.0, step=1000.0, format="%.0f")
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
st.subheader("📋 Transaksi Terakhir")

df = st.session_state.db.get_transaksi(limit=5)

if df.empty:
    st.info("Belum ada transaksi")
else:
    display_df = df.copy()
    display_df['tanggal'] = display_df['tanggal'].astype(str)
    display_df['kategori'] = display_df.apply(lambda row: f"{row['ikon']} {row['kategori_nama']}", axis=1)
    display_df['jenis'] = display_df['jenis'].map({"pengeluaran": "Pengeluaran", "pemasukan": "Pemasukan"})
    display_df['nominal'] = display_df['nominal'].apply(lambda x: format_rupiah(x, mata_uang))
    display_df['foto'] = display_df['foto_path'].apply(lambda x: "📷" if x else "—")

    cols_to_show = ['tanggal', 'jenis', 'kategori', 'nominal', 'foto', 'catatan']
    st.dataframe(display_df[cols_to_show], use_container_width=True, hide_index=True)

import streamlit as st
from database import Database
from datetime import date, timedelta, datetime
from pathlib import Path
from utils import format_rupiah
import pandas as pd

st.set_page_config(layout="wide")

if "db" not in st.session_state:
    st.session_state.db = Database()
    st.session_state.db.init_db()

if "app_settings" not in st.session_state:
    st.session_state.app_settings = st.session_state.db.get_all_settings()

st.title("📋 Riwayat Transaksi")

mata_uang = st.session_state.app_settings.get("mata_uang", "Rp")

# Reset page if needed
if "riwayat_page" not in st.session_state:
    st.session_state.riwayat_page = 1

# Filter section
col1, col2, col3, col4 = st.columns(4)

with col1:
    tanggal_dari = st.date_input("Dari Tanggal", value=date.today() - timedelta(days=30), key="riwayat_dari")

with col2:
    tanggal_sampai = st.date_input("Sampai Tanggal", value=date.today(), key="riwayat_sampai")

with col3:
    jenis_filter = st.selectbox("Jenis", ["Semua", "pengeluaran", "pemasukan"], index=0)

with col4:
    kategori_list = st.session_state.db.get_all_kategori()
    kategori_map = {k['id']: k for k in kategori_list}
    kategori_selected = st.multiselect(
        "Kategori",
        options=[k['id'] for k in kategori_list],
        format_func=lambda kid: (
            f"  └ {kategori_map[kid]['ikon']} {kategori_map[kid]['nama']}"
            if kategori_map[kid].get('parent_id')
            else f"{kategori_map[kid]['ikon']} {kategori_map[kid]['nama']}"
        )
    )

search_text = st.text_input("Cari catatan atau kategori", "")

# Prepare filters
jenis_param = None if jenis_filter == "Semua" else jenis_filter
kategori_param = kategori_selected if kategori_selected else None

# Get data
df = st.session_state.db.get_transaksi(
    tanggal_dari=tanggal_dari,
    tanggal_sampai=tanggal_sampai,
    jenis=jenis_param,
    kategori_ids=kategori_param,
    search_text=search_text
)

# Pagination
rows_per_page = 25
total_rows = len(df)
total_pages = (total_rows + rows_per_page - 1) // rows_per_page

if total_pages > 0:
    col_page_info, col_pagination = st.columns([3, 1])

    with col_pagination:
        st.session_state.riwayat_page = st.number_input(
            "Halaman",
            min_value=1,
            max_value=max(1, total_pages),
            value=st.session_state.riwayat_page
        )

    start_idx = (st.session_state.riwayat_page - 1) * rows_per_page
    end_idx = start_idx + rows_per_page
    df_page = df.iloc[start_idx:end_idx]

    with col_page_info:
        st.markdown(f"**Total: {total_rows} transaksi** | Halaman {st.session_state.riwayat_page}/{total_pages}")

else:
    df_page = df

st.markdown("---")

# Check if editing
if "edit_id" in st.session_state:
    edit_id = st.session_state.edit_id
    edit_row = df[df['id'] == edit_id].iloc[0] if not df[df['id'] == edit_id].empty else None

    if edit_row is not None:
        with st.expander("✏️ Edit Transaksi", expanded=True):
            # Show current image if exists
            if edit_row['foto_path'] and Path(edit_row['foto_path']).exists():
                st.markdown("**Foto Saat Ini:**")
                st.image(edit_row['foto_path'], use_container_width=False, width=200)

            with st.form(f"form_edit_{edit_id}"):
                jenis_edit = st.radio(
                    "Jenis",
                    ["pengeluaran", "pemasukan"],
                    index=0 if edit_row['jenis'] == 'pengeluaran' else 1,
                    horizontal=True
                )

                kategori_list_edit = st.session_state.db.get_all_kategori(jenis=jenis_edit)
                kat_edit_map = {k['id']: k for k in kategori_list_edit}
                kategori_id_edit = st.selectbox(
                    "Kategori",
                    options=[k['id'] for k in kategori_list_edit],
                    index=[k['id'] for k in kategori_list_edit].index(edit_row['kategori_id']),
                    format_func=lambda kid: f"{kat_edit_map[kid]['ikon']} {kat_edit_map[kid]['nama']}"
                )

                wallets_edit = st.session_state.db.get_all_wallets()
                wallet_edit_map = {w['id']: w for w in wallets_edit}
                wallet_id_edit = st.selectbox(
                    "Wallet",
                    options=[w['id'] for w in wallets_edit],
                    index=[w['id'] for w in wallets_edit].index(edit_row['wallet_id']),
                    format_func=lambda wid: f"{wallet_edit_map[wid]['ikon_bawaan']} {wallet_edit_map[wid]['nama']}"
                )

                tanggal_edit = st.date_input("Tanggal", value=pd.to_datetime(edit_row['tanggal']).date())
                nominal_edit = st.number_input("Nominal", value=edit_row['nominal'], min_value=0.01, step=1000.0, format="%.0f")
                catatan_edit = st.text_area("Catatan", value=edit_row['catatan'] or "", max_chars=500)

                foto_edit = st.file_uploader("🔄 Ganti Foto (opsional)", type=["jpg", "jpeg", "png", "webp"])
                hapus_foto = st.checkbox("Hapus foto saat ini")

                col_save, col_cancel = st.columns(2)
                with col_save:
                    if st.form_submit_button("💾 Simpan Perubahan", use_container_width=True):
                        foto_path_update = None

                        if hapus_foto:
                            # Hapus file lama
                            if edit_row['foto_path'] and Path(edit_row['foto_path']).exists():
                                Path(edit_row['foto_path']).unlink()
                            foto_path_update = ""
                        elif foto_edit:
                            # Hapus file lama, simpan file baru
                            if edit_row['foto_path'] and Path(edit_row['foto_path']).exists():
                                Path(edit_row['foto_path']).unlink()
                            uploads_dir = st.session_state.db.get_uploads_dir()
                            ext = foto_edit.name.rsplit(".", 1)[-1].lower()
                            filename = f"{edit_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.{ext}"
                            filepath = uploads_dir / filename
                            with open(filepath, "wb") as f:
                                f.write(foto_edit.getbuffer())
                            foto_path_update = str(filepath)

                        st.session_state.db.update_transaksi(
                            edit_id, tanggal_edit, jenis_edit, kategori_id_edit, nominal_edit, catatan_edit,
                            foto_path=foto_path_update, wallet_id=wallet_id_edit
                        )
                        del st.session_state.edit_id
                        st.success("✅ Transaksi berhasil diperbarui!")
                        st.rerun()

                with col_cancel:
                    if st.form_submit_button("❌ Batal", use_container_width=True):
                        del st.session_state.edit_id
                        st.rerun()

# Display table
if not df_page.empty:
    display_df = df_page.copy()
    display_df['tanggal'] = display_df['tanggal'].astype(str)
    display_df['kategori'] = display_df.apply(lambda row: f"{row['ikon']} {row['kategori_nama']}", axis=1)
    display_df['jenis'] = display_df['jenis'].map({"pengeluaran": "Pengeluaran", "pemasukan": "Pemasukan"})
    display_df['nominal'] = display_df['nominal'].apply(lambda x: format_rupiah(x, mata_uang))
    display_df['foto'] = display_df['foto_path'].apply(lambda x: "📷" if x else "—")

    cols_to_show = ['tanggal', 'jenis', 'kategori', 'nominal', 'foto', 'catatan']
    st.dataframe(display_df[cols_to_show], use_container_width=True, hide_index=True)

    # Action buttons
    st.markdown("---")
    st.subheader("🔧 Aksi")

    col1, col2 = st.columns(2)

    with col1:
        selected_id = st.selectbox(
            "Pilih transaksi untuk diedit",
            options=df_page['id'].tolist(),
            format_func=lambda tid: f"{df_page[df_page['id'] == tid]['tanggal'].values[0]} - {df_page[df_page['id'] == tid]['nominal'].values[0]}"
        )

        if st.button("✏️ Edit Transaksi", use_container_width=True):
            st.session_state.edit_id = selected_id
            st.rerun()

    with col2:
        if st.button("🗑️ Hapus Transaksi", use_container_width=True):
            st.session_state.confirm_delete_id = selected_id
            st.rerun()

    # Show selected transaction image if exists
    selected_row = df_page[df_page['id'] == selected_id]
    if not selected_row.empty and selected_row.iloc[0]['foto_path']:
        selected_foto_path = selected_row.iloc[0]['foto_path']
        if Path(selected_foto_path).exists():
            st.markdown("---")
            st.markdown("**📷 Foto Struk:**")
            st.image(selected_foto_path, use_container_width=True)

    # Confirm delete
    if "confirm_delete_id" in st.session_state:
        del_id = st.session_state.confirm_delete_id
        st.warning("⚠️ Yakin ingin menghapus transaksi ini?")

        col_yes, col_no = st.columns(2)
        with col_yes:
            if st.button("✓ Hapus", use_container_width=True):
                st.session_state.db.delete_transaksi(del_id)
                del st.session_state.confirm_delete_id
                st.success("✅ Transaksi berhasil dihapus!")
                st.rerun()

        with col_no:
            if st.button("✗ Batal", use_container_width=True):
                del st.session_state.confirm_delete_id
                st.rerun()

else:
    st.info("Tidak ada transaksi yang sesuai dengan filter")

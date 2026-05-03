import streamlit as st
from database import Database
from utils import IKON_OPTIONS, WARNA_OPTIONS, warna_jenis

st.set_page_config(layout="wide")

if "db" not in st.session_state:
    st.session_state.db = Database()
    st.session_state.db.init_db()

st.title("📂 Kelola Kategori")

col_left, col_right = st.columns([1, 1])

# Left: List of categories
with col_left:
    st.subheader("Daftar Kategori")

    kategori_list = st.session_state.db.get_all_kategori()

    for kat in kategori_list:
        with st.container(border=True):
            col_info, col_actions = st.columns([3, 1])

            with col_info:
                st.markdown(f"### {kat['ikon']} {kat['nama']}")

                jenis_color = warna_jenis(kat['jenis'])
                jenis_label = {
                    "pengeluaran": "Pengeluaran",
                    "pemasukan": "Pemasukan",
                    "keduanya": "Keduanya"
                }.get(kat['jenis'], kat['jenis'])

                st.markdown(f"**Jenis:** `{jenis_label}`")
                if kat['is_default']:
                    st.caption("🔒 Kategori default (tidak bisa dihapus)")

            with col_actions:
                col_edit, col_delete = st.columns(2)
                with col_edit:
                    if st.button("✏️ Edit", key=f"edit_{kat['id']}", use_container_width=True):
                        st.session_state.edit_kategori_id = kat['id']
                        st.rerun()

                with col_delete:
                    if not kat['is_default']:
                        if st.button("🗑️", key=f"del_{kat['id']}", use_container_width=True):
                            st.session_state.confirm_delete_id = kat['id']
                            st.rerun()

# Right: Add/Edit form
with col_right:
    # Check if deleting
    if "confirm_delete_id" in st.session_state:
        del_id = st.session_state.confirm_delete_id
        st.warning(f"⚠️ Akan menghapus kategori ini. Pastikan tidak digunakan oleh transaksi.")

        col_yes, col_no = st.columns(2)
        with col_yes:
            if st.button("✓ Hapus", use_container_width=True):
                try:
                    st.session_state.db.delete_kategori(del_id)
                    del st.session_state.confirm_delete_id
                    st.success("Kategori berhasil dihapus!")
                    st.rerun()
                except ValueError as e:
                    st.error(f"Error: {e}")
                    del st.session_state.confirm_delete_id
                    st.rerun()

        with col_no:
            if st.button("✗ Batal", use_container_width=True):
                del st.session_state.confirm_delete_id
                st.rerun()

    # Edit mode
    elif "edit_kategori_id" in st.session_state:
        edit_id = st.session_state.edit_kategori_id
        kat = next((k for k in kategori_list if k['id'] == edit_id), None)

        if kat:
            st.subheader("✏️ Edit Kategori")

            with st.form(f"form_edit_{edit_id}"):
                nama = st.text_input("Nama Kategori", value=kat['nama'])
                jenis = st.selectbox(
                    "Jenis",
                    ["pengeluaran", "pemasukan", "keduanya"],
                    index=["pengeluaran", "pemasukan", "keduanya"].index(kat['jenis'])
                )
                ikon = st.selectbox("Ikon", IKON_OPTIONS, index=IKON_OPTIONS.index(kat['ikon']))
                warna = st.color_picker("Warna", value=kat['warna'])

                col_save, col_cancel = st.columns(2)
                with col_save:
                    submit = st.form_submit_button("💾 Simpan", use_container_width=True)
                with col_cancel:
                    if st.form_submit_button("❌ Batal", use_container_width=True):
                        del st.session_state.edit_kategori_id
                        st.rerun()

                if submit:
                    try:
                        st.session_state.db.update_kategori(edit_id, nama, jenis, ikon, warna)
                        del st.session_state.edit_kategori_id
                        st.success("Kategori berhasil diperbarui!")
                        st.rerun()
                    except ValueError as e:
                        st.error(f"Error: {e}")

    # Add mode
    else:
        st.subheader("➕ Tambah Kategori Baru")

        with st.form("form_tambah_kategori"):
            nama = st.text_input("Nama Kategori", placeholder="Contoh: Belanja Online")
            jenis = st.selectbox("Jenis", ["pengeluaran", "pemasukan", "keduanya"])
            ikon = st.selectbox("Ikon", IKON_OPTIONS, index=0)
            warna = st.color_picker("Warna", value="#636EFA")

            if st.form_submit_button("➕ Tambah Kategori", use_container_width=True):
                if not nama.strip():
                    st.error("Nama kategori tidak boleh kosong")
                else:
                    try:
                        st.session_state.db.add_kategori(nama, jenis, ikon, warna)
                        st.success(f"Kategori '{nama}' berhasil ditambahkan!")
                        st.rerun()
                    except ValueError as e:
                        st.error(f"Error: {e}")

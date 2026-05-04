import streamlit as st
from database import Database
from utils import IKON_OPTIONS, WARNA_OPTIONS, warna_jenis

st.set_page_config(layout="wide")

if "db" not in st.session_state:
    st.session_state.db = Database()
    st.session_state.db.init_db()

st.title("📂 Kelola Kategori")

col_left, col_right = st.columns([1.2, 1])

with col_left:
    st.subheader("Daftar Kategori")

    tree = st.session_state.db.get_kategori_tree()

    for parent in tree:
        with st.container(border=True):
            col_info, col_actions = st.columns([3, 1])

            with col_info:
                st.markdown(f"### {parent['ikon']} {parent['nama']}")
                jenis_label = {"pengeluaran": "Pengeluaran", "pemasukan": "Pemasukan", "keduanya": "Keduanya"}.get(parent['jenis'], parent['jenis'])
                st.markdown(f"**Jenis:** `{jenis_label}`")
                if parent['is_default']:
                    st.caption("🔒 Default")

            with col_actions:
                if st.button("✏️", key=f"edit_parent_{parent['id']}", use_container_width=True, help="Edit"):
                    st.session_state.edit_kategori_id = parent['id']
                    st.session_state.pop("add_sub_parent_id", None)
                    st.rerun()
                if not parent['is_default']:
                    if st.button("🗑️", key=f"del_parent_{parent['id']}", use_container_width=True, help="Hapus"):
                        st.session_state.confirm_delete_id = parent['id']
                        st.rerun()
                if st.button("➕ Sub", key=f"sub_{parent['id']}", use_container_width=True, help="Tambah sub-kategori"):
                    st.session_state.add_sub_parent_id = parent['id']
                    st.session_state.pop("edit_kategori_id", None)
                    st.rerun()

            # Sub-categories
            for child in parent.get('children', []):
                with st.container():
                    c_info, c_actions = st.columns([3, 1])
                    with c_info:
                        st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;└ {child['ikon']} **{child['nama']}**")
                        if child['is_default']:
                            st.caption("&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;🔒 Default")
                    with c_actions:
                        if st.button("✏️", key=f"edit_child_{child['id']}", use_container_width=True, help="Edit"):
                            st.session_state.edit_kategori_id = child['id']
                            st.session_state.pop("add_sub_parent_id", None)
                            st.rerun()
                        if not child['is_default']:
                            if st.button("🗑️", key=f"del_child_{child['id']}", use_container_width=True, help="Hapus"):
                                st.session_state.confirm_delete_id = child['id']
                                st.rerun()

with col_right:
    # Confirm delete
    if "confirm_delete_id" in st.session_state:
        del_id = st.session_state.confirm_delete_id
        st.warning("⚠️ Akan menghapus kategori ini.")
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
        all_kat = st.session_state.db.get_all_kategori()
        kat = next((k for k in all_kat if k['id'] == edit_id), None)

        if kat:
            st.subheader("✏️ Edit Kategori")

            # Parent selector (outside form not needed — parent rarely changes)
            parents = [k for k in all_kat if k.get('parent_id') is None and k['id'] != edit_id]
            parent_options = [None] + [p['id'] for p in parents]
            parent_map = {p['id']: p for p in parents}
            current_parent = kat.get('parent_id')
            parent_index = parent_options.index(current_parent) if current_parent in parent_options else 0

            with st.form(f"form_edit_{edit_id}"):
                nama = st.text_input("Nama Kategori", value=kat['nama'])
                jenis = st.selectbox(
                    "Jenis",
                    ["pengeluaran", "pemasukan", "keduanya"],
                    index=["pengeluaran", "pemasukan", "keduanya"].index(kat['jenis'])
                )
                ikon_idx = IKON_OPTIONS.index(kat['ikon']) if kat['ikon'] in IKON_OPTIONS else 0
                ikon = st.selectbox("Ikon", IKON_OPTIONS, index=ikon_idx)
                warna = st.color_picker("Warna", value=kat['warna'])
                parent_sel = st.selectbox(
                    "Parent Kategori (kosong = kategori utama)",
                    options=parent_options,
                    index=parent_index,
                    format_func=lambda pid: "— (Kategori Utama)" if pid is None else f"{parent_map[pid]['ikon']} {parent_map[pid]['nama']}"
                )

                submit = st.form_submit_button("💾 Simpan", use_container_width=True)

                if submit:
                    try:
                        st.session_state.db.update_kategori(edit_id, nama, jenis, ikon, warna, parent_id=parent_sel)
                        del st.session_state.edit_kategori_id
                        st.success("Kategori berhasil diperbarui!")
                        st.rerun()
                    except ValueError as e:
                        st.error(f"Error: {e}")

            if st.button("❌ Batal", use_container_width=True, key="batal_edit_kat"):
                del st.session_state.edit_kategori_id
                st.rerun()

    # Add sub-category mode
    elif "add_sub_parent_id" in st.session_state:
        parent_id = st.session_state.add_sub_parent_id
        all_kat = st.session_state.db.get_all_kategori()
        parent_kat = next((k for k in all_kat if k['id'] == parent_id), None)

        if parent_kat:
            st.subheader(f"➕ Sub-kategori dari: {parent_kat['ikon']} {parent_kat['nama']}")

            with st.form("form_tambah_sub"):
                nama = st.text_input("Nama Sub-kategori", placeholder="Contoh: Makan Siang")
                ikon = st.selectbox("Ikon", IKON_OPTIONS, index=0)
                warna = st.color_picker("Warna", value=parent_kat['warna'])

                submit = st.form_submit_button("➕ Tambah", use_container_width=True)

                if submit:
                    if not nama.strip():
                        st.error("Nama tidak boleh kosong")
                    else:
                        try:
                            st.session_state.db.add_kategori(nama, parent_kat['jenis'], ikon, warna, parent_id=parent_id)
                            del st.session_state.add_sub_parent_id
                            st.success(f"Sub-kategori '{nama}' berhasil ditambahkan!")
                            st.rerun()
                        except ValueError as e:
                            st.error(f"Error: {e}")

            if st.button("❌ Batal", use_container_width=True, key="batal_sub_kat"):
                del st.session_state.add_sub_parent_id
                st.rerun()

    # Add new parent category
    else:
        st.subheader("➕ Tambah Kategori Baru")

        with st.form("form_tambah_kategori"):
            nama = st.text_input("Nama Kategori", placeholder="Contoh: Hiburan")
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

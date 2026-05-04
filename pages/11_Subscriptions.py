import streamlit as st
from database import Database
from pathlib import Path
from utils import format_rupiah
import pandas as pd

st.set_page_config(layout="wide")

if "db" not in st.session_state:
    st.session_state.db = Database()
    st.session_state.db.init_db()

if "app_settings" not in st.session_state:
    st.session_state.app_settings = st.session_state.db.get_all_settings()

st.title("📡 Langganan")

mata_uang = st.session_state.app_settings.get("mata_uang", "Rp")

# Summary
total_per_bulan = st.session_state.db.get_total_subscription_per_bulan()
st.metric("💰 Total per Bulan", format_rupiah(total_per_bulan, mata_uang))

st.markdown("---")

col_list, col_form = st.columns([1.5, 1])

with col_list:
    st.subheader("Langganan Aktif")

    subscriptions = st.session_state.db.get_all_subscriptions(aktif_only=False)

    if "edit_subscription_id" in st.session_state:
        edit_id = st.session_state.edit_subscription_id
        edit_sub = st.session_state.db.get_subscription(edit_id)

        if edit_sub:
            st.write(f"**Edit: {edit_sub['nama']}**")

            with st.form("form_edit_subscription"):
                nama_edit = st.text_input("Nama", value=edit_sub['nama'])
                nominal_edit = st.number_input("Nominal", value=edit_sub['nominal'], min_value=0.01, step=1000.0, format="%.0f")
                tgl_bayar_edit = st.slider("Tanggal Bayar", 1, 31, value=edit_sub['tanggal_bayar'])
                catatan_edit = st.text_area("Catatan", value=edit_sub['catatan'] or "", max_chars=500)
                aktif_edit = st.checkbox("Aktif", value=edit_sub['aktif'] == 1)

                ikon_file_edit = st.file_uploader("Ganti Icon (opsional)", type=["jpg", "jpeg", "png", "webp"], key=f"icon_edit_{edit_id}")

                if st.form_submit_button("💾 Simpan Perubahan", use_container_width=True):
                    ikon_path_update = edit_sub['ikon_path']

                    if ikon_file_edit:
                        icons_dir = st.session_state.db.get_subscription_icons_dir()
                        ext = ikon_file_edit.name.rsplit(".", 1)[-1].lower()
                        filepath = icons_dir / f"sub_{edit_id}.{ext}"

                        with open(filepath, "wb") as f:
                            f.write(ikon_file_edit.getbuffer())

                        ikon_path_update = str(filepath)

                    try:
                        st.session_state.db.update_subscription(
                            edit_id, nama_edit, nominal_edit, tgl_bayar_edit, catatan_edit, ikon_path_update, 1 if aktif_edit else 0
                        )
                        st.success("✅ Langganan berhasil diupdate!")
                        del st.session_state.edit_subscription_id
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")

            if st.button("❌ Batal", use_container_width=True):
                del st.session_state.edit_subscription_id
                st.rerun()

    else:
        for sub in subscriptions:
            with st.container(border=True):
                col_icon, col_info = st.columns([0.15, 0.85])

                with col_icon:
                    if sub['ikon_path'] and Path(sub['ikon_path']).exists():
                        st.image(sub['ikon_path'], width=50)
                    else:
                        st.markdown("📡")

                with col_info:
                    st.markdown(f"### {sub['nama']}")
                    st.markdown(f"💰 **{format_rupiah(sub['nominal'], mata_uang)}** • bayar tiap tgl **{sub['tanggal_bayar']}**")
                    if sub['catatan']:
                        st.caption(sub['catatan'])

                    col_btn1, col_btn2, col_btn3 = st.columns(3)
                    with col_btn1:
                        if st.button("✏️ Edit", key=f"edit_{sub['id']}", use_container_width=True):
                            st.session_state.edit_subscription_id = sub['id']
                            st.rerun()

                    with col_btn2:
                        if st.button("🗑️ Hapus", key=f"del_{sub['id']}", use_container_width=True):
                            try:
                                st.session_state.db.delete_subscription(sub['id'])
                                st.success("✅ Langganan dihapus")
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Error: {str(e)}")

                    with col_btn3:
                        new_aktif = 0 if sub['aktif'] == 1 else 1
                        label = "Nonaktifkan" if sub['aktif'] == 1 else "Aktifkan"
                        if st.button(label, key=f"toggle_{sub['id']}", use_container_width=True):
                            try:
                                st.session_state.db.update_subscription(
                                    sub['id'], sub['nama'], sub['nominal'], sub['tanggal_bayar'],
                                    sub['catatan'], sub['ikon_path'], new_aktif
                                )
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Error: {str(e)}")

with col_form:
    st.subheader("➕ Langganan Baru")

    with st.form("form_add_subscription"):
        nama = st.text_input("Nama Langganan")
        nominal = st.number_input("Nominal per Bulan", min_value=0.01, step=1000.0, format="%.0f")
        tanggal_bayar = st.slider("Tanggal Bayar", 1, 31, value=1)
        catatan = st.text_area("Catatan", max_chars=500)
        ikon_file = st.file_uploader("Icon (opsional)", type=["jpg", "jpeg", "png", "webp"])

        if st.form_submit_button("➕ Tambah Langganan", use_container_width=True):
            if not nama:
                st.error("Nama langganan tidak boleh kosong")
            elif nominal <= 0:
                st.error("Nominal harus lebih dari 0")
            else:
                try:
                    sub_id = st.session_state.db.add_subscription(nama, nominal, tanggal_bayar, catatan)

                    if ikon_file:
                        icons_dir = st.session_state.db.get_subscription_icons_dir()
                        ext = ikon_file.name.rsplit(".", 1)[-1].lower()
                        filepath = icons_dir / f"sub_{sub_id}.{ext}"

                        with open(filepath, "wb") as f:
                            f.write(ikon_file.getbuffer())

                        st.session_state.db.update_subscription(
                            sub_id, nama, nominal, tanggal_bayar, catatan, str(filepath), 1
                        )

                    st.success("✅ Langganan berhasil ditambahkan!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")

import streamlit as st
from database import Database
from utils import IKON_OPTIONS, WARNA_OPTIONS, format_rupiah
from pathlib import Path

st.set_page_config(layout="wide")

if "db" not in st.session_state:
    st.session_state.db = Database()
    st.session_state.db.init_db()

if "app_settings" not in st.session_state:
    st.session_state.app_settings = st.session_state.db.get_all_settings()

st.title("👛 Wallet & Rekening")

mata_uang = st.session_state.app_settings.get("mata_uang", "Rp")

col_left, col_right = st.columns([1, 1])

# Left: List of wallets
with col_left:
    st.subheader("Daftar Wallet")

    wallets = st.session_state.db.get_all_wallets()

    for wallet in wallets:
        with st.container(border=True):
            col_info, col_actions = st.columns([3, 1])

            with col_info:
                # Display icon: custom image if exists, otherwise emoji
                if wallet['ikon_path'] and Path(wallet['ikon_path']).exists():
                    col_icon, col_text = st.columns([0.15, 2.85])
                    with col_icon:
                        st.image(wallet['ikon_path'], use_container_width=True, width=40)
                    with col_text:
                        st.markdown(f"### {wallet['nama']}")
                else:
                    st.markdown(f"### {wallet['ikon_bawaan']} {wallet['nama']}")

                jenis_label = {
                    "bank": "Bank",
                    "e-wallet": "E-Wallet",
                    "cash": "Tunai",
                    "investasi": "Investasi"
                }.get(wallet['jenis'], wallet['jenis'])

                st.markdown(f"**Jenis:** `{jenis_label}`")

                # Calculate current balance
                saldo = st.session_state.db.get_saldo_wallet(wallet['id'])
                st.metric("Saldo Saat Ini", format_rupiah(saldo, mata_uang))

            with col_actions:
                col_edit, col_delete = st.columns(2)
                with col_edit:
                    if st.button("✏️ Edit", key=f"edit_wallet_{wallet['id']}", use_container_width=True):
                        st.session_state.edit_wallet_id = wallet['id']
                        st.rerun()

                with col_delete:
                    if st.button("🗑️", key=f"del_wallet_{wallet['id']}", use_container_width=True):
                        st.session_state.confirm_delete_wallet_id = wallet['id']
                        st.rerun()

# Right: Add/Edit form
with col_right:
    # Check if deleting
    if "confirm_delete_wallet_id" in st.session_state:
        del_id = st.session_state.confirm_delete_wallet_id
        st.warning("⚠️ Akan menghapus wallet ini.")

        col_yes, col_no = st.columns(2)
        with col_yes:
            if st.button("✓ Hapus", use_container_width=True):
                try:
                    st.session_state.db.delete_wallet(del_id)
                    del st.session_state.confirm_delete_wallet_id
                    st.success("Wallet berhasil dihapus!")
                    st.rerun()
                except ValueError as e:
                    st.error(f"Error: {e}")
                    del st.session_state.confirm_delete_wallet_id
                    st.rerun()

        with col_no:
            if st.button("✗ Batal", use_container_width=True):
                del st.session_state.confirm_delete_wallet_id
                st.rerun()

    # Edit mode
    elif "edit_wallet_id" in st.session_state:
        edit_id = st.session_state.edit_wallet_id
        wallet = next((w for w in wallets if w['id'] == edit_id), None)

        if wallet:
            st.subheader("✏️ Edit Wallet")

            with st.form(f"form_edit_wallet_{edit_id}"):
                nama = st.text_input("Nama Wallet", value=wallet['nama'])
                jenis = st.selectbox(
                    "Jenis",
                    ["bank", "e-wallet", "cash", "investasi"],
                    index=["bank", "e-wallet", "cash", "investasi"].index(wallet['jenis'])
                )
                ikon_bawaan = st.selectbox("Ikon Emoji", IKON_OPTIONS, index=IKON_OPTIONS.index(wallet['ikon_bawaan']))
                saldo_awal = st.number_input("Saldo Awal", value=wallet['saldo_awal'], min_value=0.0, step=1000.0, format="%.0f")
                warna = st.color_picker("Warna", value=wallet['warna'])

                st.markdown("**Ikon Custom (Gambar):**")
                if wallet['ikon_path'] and Path(wallet['ikon_path']).exists():
                    st.image(wallet['ikon_path'], width=100)
                    hapus_icon = st.checkbox("Hapus icon custom saat ini")
                else:
                    hapus_icon = False

                ikon_file = st.file_uploader("Upload icon baru (jpg, png, webp)", type=["jpg", "jpeg", "png", "webp"])

                col_save, col_cancel = st.columns(2)
                with col_save:
                    submit = st.form_submit_button("💾 Simpan", use_container_width=True)
                with col_cancel:
                    if st.form_submit_button("❌ Batal", use_container_width=True):
                        del st.session_state.edit_wallet_id
                        st.rerun()

                if submit:
                    if not nama.strip():
                        st.error("Nama wallet tidak boleh kosong")
                    else:
                        try:
                            ikon_path_update = wallet['ikon_path']

                            if hapus_icon and ikon_path_update and Path(ikon_path_update).exists():
                                Path(ikon_path_update).unlink()
                                ikon_path_update = None
                            elif ikon_file:
                                if ikon_path_update and Path(ikon_path_update).exists():
                                    Path(ikon_path_update).unlink()
                                uploads_dir = st.session_state.db.get_wallet_icons_dir()
                                ext = ikon_file.name.rsplit(".", 1)[-1].lower()
                                filename = f"wallet_{edit_id}.{ext}"
                                filepath = uploads_dir / filename
                                with open(filepath, "wb") as f:
                                    f.write(ikon_file.getbuffer())
                                ikon_path_update = str(filepath)

                            st.session_state.db.update_wallet(edit_id, nama, jenis, ikon_bawaan, ikon_path_update, saldo_awal, warna)
                            del st.session_state.edit_wallet_id
                            st.success("Wallet berhasil diperbarui!")
                            st.rerun()
                        except ValueError as e:
                            st.error(f"Error: {e}")

    # Add mode
    else:
        st.subheader("➕ Tambah Wallet Baru")

        with st.form("form_tambah_wallet"):
            nama = st.text_input("Nama Wallet", placeholder="Contoh: BCA, GoPay, Tunai")
            jenis = st.selectbox("Jenis", ["bank", "e-wallet", "cash", "investasi"])
            ikon_bawaan = st.selectbox("Ikon Emoji", IKON_OPTIONS, index=0)
            saldo_awal = st.number_input("Saldo Awal", value=0.0, min_value=0.0, step=1000.0, format="%.0f")
            warna = st.color_picker("Warna", value="#636EFA")

            st.markdown("**Ikon Custom (Gambar) - Opsional:**")
            ikon_file = st.file_uploader("Upload icon (jpg, png, webp)", type=["jpg", "jpeg", "png", "webp"])

            if st.form_submit_button("➕ Tambah Wallet", use_container_width=True):
                if not nama.strip():
                    st.error("Nama wallet tidak boleh kosong")
                else:
                    try:
                        ikon_path = None
                        new_wallet_id = st.session_state.db.add_wallet(nama, jenis, ikon_bawaan, None, saldo_awal, warna)

                        if ikon_file:
                            uploads_dir = st.session_state.db.get_wallet_icons_dir()
                            ext = ikon_file.name.rsplit(".", 1)[-1].lower()
                            filename = f"wallet_{new_wallet_id}.{ext}"
                            filepath = uploads_dir / filename
                            with open(filepath, "wb") as f:
                                f.write(ikon_file.getbuffer())
                            ikon_path = str(filepath)
                            st.session_state.db.update_wallet(new_wallet_id, nama, jenis, ikon_bawaan, ikon_path, saldo_awal, warna)

                        st.success(f"Wallet '{nama}' berhasil ditambahkan!")
                        st.rerun()
                    except ValueError as e:
                        st.error(f"Error: {e}")

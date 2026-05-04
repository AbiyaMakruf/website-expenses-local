import streamlit as st
from database import Database
from datetime import date
from utils import format_rupiah
import pandas as pd

st.set_page_config(layout="wide")

if "db" not in st.session_state:
    st.session_state.db = Database()
    st.session_state.db.init_db()

if "app_settings" not in st.session_state:
    st.session_state.app_settings = st.session_state.db.get_all_settings()

st.title("↔️ Transfer Dana")

mata_uang = st.session_state.app_settings.get("mata_uang", "Rp")
wallets = st.session_state.db.get_all_wallets()

if not wallets or len(wallets) < 2:
    st.error("Anda perlu minimal 2 wallet untuk melakukan transfer")
else:
    with st.form("form_transfer"):
        col1, col2 = st.columns(2)

        with col1:
            tanggal = st.date_input("Tanggal", value=date.today())

        with col2:
            nominal = st.number_input(
                "Nominal",
                min_value=0.01,
                step=1000.0,
                format="%.0f"
            )

        col_dari, col_ke = st.columns(2)

        with col_dari:
            wallet_map = {w['id']: w for w in wallets}
            dari_wallet_id = st.selectbox(
                "Dari Wallet",
                options=[w['id'] for w in wallets],
                format_func=lambda wid: f"{wallet_map[wid]['ikon_bawaan']} {wallet_map[wid]['nama']}"
            )

        with col_ke:
            ke_wallet_id = st.selectbox(
                "Ke Wallet",
                options=[w['id'] for w in wallets if w['id'] != dari_wallet_id],
                format_func=lambda wid: f"{wallet_map[wid]['ikon_bawaan']} {wallet_map[wid]['nama']}"
            )

        catatan = st.text_area("Catatan (opsional)", max_chars=500)

        if st.form_submit_button("🔄 Transfer Sekarang", use_container_width=True):
            if nominal <= 0:
                st.error("Nominal harus lebih dari 0")
            elif dari_wallet_id == ke_wallet_id:
                st.error("Wallet asal dan tujuan tidak boleh sama")
            else:
                try:
                    id_keluar, id_masuk = st.session_state.db.add_transfer(
                        tanggal=tanggal,
                        dari_wallet_id=dari_wallet_id,
                        ke_wallet_id=ke_wallet_id,
                        nominal=nominal,
                        catatan=catatan
                    )
                    st.success(f"✅ Transfer berhasil! Rp {nominal:,.0f} dari {wallet_map[dari_wallet_id]['nama']} ke {wallet_map[ke_wallet_id]['nama']}")
                    st.balloons()
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")

    st.markdown("---")
    st.subheader("📋 Riwayat Transfer")

    transfer_list = st.session_state.db.get_transfer_list(limit=20)

    if transfer_list:
        display_data = []
        for t in transfer_list:
            display_data.append({
                "Tanggal": t['tanggal'],
                "Dari": t['dari_wallet'],
                "Ke": t['ke_wallet'],
                "Nominal": format_rupiah(t['nominal'], mata_uang),
                "Catatan": t['catatan'] or "—"
            })

        df_display = pd.DataFrame(display_data)
        st.dataframe(df_display, use_container_width=True, hide_index=True)
    else:
        st.info("Belum ada riwayat transfer")

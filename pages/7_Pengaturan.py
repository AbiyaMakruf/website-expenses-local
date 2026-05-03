import streamlit as st
from database import Database
from datetime import datetime
from io import BytesIO
import os

st.set_page_config(layout="wide")

if "db" not in st.session_state:
    st.session_state.db = Database()
    st.session_state.db.init_db()

if "app_settings" not in st.session_state:
    st.session_state.app_settings = st.session_state.db.get_all_settings()

st.title("⚙️ Pengaturan")

# ===== PREFERENSI APLIKASI =====
with st.expander("🎨 Preferensi Aplikasi", expanded=True):
    st.subheader("Pengaturan Umum")

    with st.form("form_preferensi"):
        nama_app = st.text_input(
            "Nama Aplikasi",
            value=st.session_state.app_settings.get("nama_aplikasi", "Catatan Keuangan"),
            max_chars=100
        )

        mata_uang = st.selectbox(
            "Simbol Mata Uang",
            ["Rp", "$", "€", "¥", "£"],
            index=["Rp", "$", "€", "¥", "£"].index(st.session_state.app_settings.get("mata_uang", "Rp"))
        )

        format_tanggal = st.selectbox(
            "Format Tanggal",
            ["DD/MM/YYYY", "YYYY-MM-DD", "MM/DD/YYYY"],
            index=["DD/MM/YYYY", "YYYY-MM-DD", "MM/DD/YYYY"].index(st.session_state.app_settings.get("format_tanggal", "DD/MM/YYYY"))
        )

        if st.form_submit_button("💾 Simpan Preferensi", use_container_width=True):
            st.session_state.db.set_setting("nama_aplikasi", nama_app)
            st.session_state.db.set_setting("mata_uang", mata_uang)
            st.session_state.db.set_setting("format_tanggal", format_tanggal)

            # Reload settings
            st.session_state.app_settings = st.session_state.db.get_all_settings()

            st.success("✅ Preferensi berhasil disimpan!")
            st.rerun()

# ===== BACKUP DATABASE =====
with st.expander("💾 Backup Database"):
    st.subheader("Unduh Backup Database")

    st.markdown("""
    Backup database memudahkan Anda untuk:
    - Menyimpan salinan data keuangan
    - Mentransfer data ke komputer lain
    - Melindungi dari kehilangan data
    """)

    if st.button("📥 Unduh Backup", use_container_width=True):
        backup_filename = f"backup_expenses_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"

        try:
            # Read the database file
            db_path = st.session_state.db.db_path
            with open(db_path, 'rb') as f:
                db_data = f.read()

            st.download_button(
                label=f"💾 {backup_filename}",
                data=db_data,
                file_name=backup_filename,
                mime="application/octet-stream",
                use_container_width=True
            )

            st.success("✅ File siap diunduh!")

        except Exception as e:
            st.error(f"Error: {e}")

# ===== RESTORE DATABASE =====
with st.expander("🔄 Restore Database"):
    st.subheader("Pulihkan Database dari Backup")

    st.warning("⚠️ **Peringatan**: Proses restore akan mengganti semua data saat ini dengan data dari file backup yang dipilih. Pastikan Anda telah membackup data saat ini sebelum melanjutkan.")

    uploaded_file = st.file_uploader("Pilih file backup (.db)", type=['db'])

    if uploaded_file:
        st.markdown("**File yang dipilih:**")
        st.write(f"- Nama: {uploaded_file.name}")
        st.write(f"- Ukuran: {uploaded_file.size} bytes")

        confirm_restore = st.checkbox("✓ Saya yakin ingin restore database dari file ini")

        if confirm_restore:
            if st.button("🔄 Restore Sekarang", use_container_width=True, type="primary"):
                try:
                    # Save uploaded file temporarily
                    temp_path = st.session_state.db.db_path.parent / "temp_restore.db"
                    with open(temp_path, 'wb') as f:
                        f.write(uploaded_file.getbuffer())

                    # Restore
                    st.session_state.db.restore_db(temp_path)

                    # Clean temp file
                    temp_path.unlink()

                    # Reload settings
                    st.session_state.app_settings = st.session_state.db.get_all_settings()

                    st.success("✅ Database berhasil di-restore!")
                    st.rerun()

                except Exception as e:
                    st.error(f"Error: {e}")

# ===== GITHUB BACKUP =====
with st.expander("🐙 Backup ke GitHub"):
    st.subheader("Sinkronisasi Database ke GitHub")

    st.markdown("""
    Otomatis backup database ke repository GitHub Anda untuk keamanan ekstra.
    """)

    st.warning("🔐 **Keamanan**: Token GitHub disimpan lokal di database. Gunakan Personal Access Token (PAT) dengan scope 'repo' saja.")

    with st.form("form_github_backup"):
        github_token = st.text_input(
            "GitHub Token (Personal Access Token)",
            value=st.session_state.app_settings.get("github_token", ""),
            type="password",
            placeholder="ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxx"
        )

        github_repo = st.text_input(
            "Repository (format: username/repo)",
            value=st.session_state.app_settings.get("github_repo", ""),
            placeholder="Contoh: abiyamf/expenses-backup"
        )

        github_path = st.text_input(
            "Path di Repository",
            value=st.session_state.app_settings.get("github_path", "backup/expenses.db"),
            placeholder="backup/expenses.db"
        )

        if st.form_submit_button("💾 Simpan Konfigurasi", use_container_width=True):
            st.session_state.db.set_setting("github_token", github_token)
            st.session_state.db.set_setting("github_repo", github_repo)
            st.session_state.db.set_setting("github_path", github_path)
            st.session_state.app_settings = st.session_state.db.get_all_settings()
            st.success("✅ Konfigurasi GitHub berhasil disimpan!")
            st.rerun()

    # Backup button
    if st.button("🚀 Backup Sekarang", use_container_width=True):
        github_token = st.session_state.app_settings.get("github_token", "")
        github_repo = st.session_state.app_settings.get("github_repo", "")
        github_path = st.session_state.app_settings.get("github_path", "")

        if not github_token or not github_repo or not github_path:
            st.error("⚠️ Lengkapi semua field konfigurasi terlebih dahulu!")
        elif "/" not in github_repo:
            st.error("⚠️ Format repository salah (gunakan format: username/repo)")
        else:
            try:
                import base64
                import requests

                # Validasi file size
                db_path = st.session_state.db.db_path
                file_size_mb = os.path.getsize(db_path) / (1024 * 1024)

                if file_size_mb > 50:
                    st.warning(f"⚠️ File database terlalu besar ({file_size_mb:.2f} MB). GitHub limit untuk file adalah 100 MB per file.")
                else:
                    # Read and encode database file
                    with open(db_path, 'rb') as f:
                        db_content = f.read()

                    content_encoded = base64.b64encode(db_content).decode('utf-8')

                    # GitHub API endpoints
                    headers = {
                        "Authorization": f"token {github_token}",
                        "Accept": "application/vnd.github.v3+json"
                    }

                    # Get current file to check SHA
                    owner, repo = github_repo.split("/")
                    get_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{github_path}"

                    sha = None
                    try:
                        response = requests.get(get_url, headers=headers, timeout=30)
                        if response.status_code == 200:
                            sha = response.json().get("sha")
                    except:
                        pass

                    # Create or update file
                    put_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{github_path}"
                    payload = {
                        "message": f"Backup database - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                        "content": content_encoded
                    }

                    if sha:
                        payload["sha"] = sha

                    response = requests.put(put_url, json=payload, headers=headers, timeout=30)

                    if response.status_code in [201, 200]:
                        file_url = f"https://github.com/{github_repo}/blob/main/{github_path}"
                        st.success(f"✅ Backup sukses! File tersimpan di GitHub")
                        st.markdown(f"[📂 Lihat file di GitHub]({file_url})")
                    else:
                        error_msg = response.json().get("message", "Unknown error")
                        st.error(f"❌ Backup gagal: {error_msg}")

            except ImportError:
                st.error("❌ Library 'requests' tidak ditemukan. Pastikan sudah melakukan pip install.")
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")

# ===== DANGEROUS ZONE =====
with st.expander("🚨 Zona Berbahaya", expanded=False):
    st.subheader("⚠️ Operasi Berbahaya")

    st.markdown("""
    Operasi di bagian ini **tidak dapat dibatalkan** dan akan menghapus semua data.
    Gunakan dengan sangat hati-hati!
    """)

    st.markdown("**Reset Semua Data**")

    col1, col2 = st.columns(2)

    with col1:
        confirm_text = st.text_input(
            "Ketik 'HAPUS SEMUA' untuk mengaktifkan tombol reset",
            type="password",
            placeholder="HAPUS SEMUA"
        )

    with col2:
        if confirm_text == "HAPUS SEMUA":
            if st.button("🗑️ HAPUS SEMUA DATA", use_container_width=True, type="secondary"):
                try:
                    # Get db path and reinitialize
                    db_path = st.session_state.db.db_path

                    # Drop and recreate
                    st.session_state.db.init_db()

                    st.success("✅ Semua data berhasil dihapus dan database telah direset!")
                    st.rerun()

                except Exception as e:
                    st.error(f"Error: {e}")

        else:
            st.button("🗑️ HAPUS SEMUA DATA", use_container_width=True, disabled=True)

# ===== INFORMASI SISTEM =====
st.markdown("---")

with st.expander("ℹ️ Informasi Sistem"):
    st.subheader("Detail Aplikasi")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Aplikasi**")
        st.write(f"- Nama: {st.session_state.app_settings.get('nama_aplikasi', 'Catatan Keuangan')}")
        st.write(f"- Framework: Streamlit")
        st.write(f"- Database: SQLite")

    with col2:
        st.markdown("**Database**")
        db_path = st.session_state.db.db_path
        st.write(f"- Lokasi: {db_path}")

        try:
            db_size = os.path.getsize(db_path) / 1024  # KB
            st.write(f"- Ukuran: {db_size:.2f} KB")
        except:
            st.write(f"- Ukuran: N/A")

        st.write(f"- Format: SQLite 3")

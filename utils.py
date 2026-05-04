from locale import currency

IKON_OPTIONS = [
    # Makanan & minuman
    "🍽️", "🍕", "🍔", "🍜", "🍛", "🍱", "🥗", "🍣", "🥩", "🍗",
    "☕", "🧋", "🥤", "🍺", "🍷", "🧃",
    # Transportasi
    "🚗", "🚕", "🏍️", "🚌", "🚆", "✈️", "⛽", "🅿️",
    # Belanja & rumah tangga
    "🛍️", "🛒", "🏠", "🛋️", "🪴", "🧹", "💡", "💧", "🔧",
    # Hiburan & gaya hidup
    "🎬", "🎵", "🎮", "📚", "⚽", "🎭", "🎨", "🏖️", "🏕️",
    # Kesehatan & kebugaran
    "💊", "🏥", "🏋️", "🧘", "🚴", "🏃", "🩺",
    # Fashion & kecantikan
    "👗", "👞", "👜", "💅", "💄", "⌚", "🕶️",
    # Teknologi
    "📱", "💻", "🖥️", "🎧", "📷", "🖨️",
    # Pendidikan & pekerjaan
    "🎓", "📝", "📋", "💼", "🏢", "📦",
    # Wallet / keuangan
    "💵", "💴", "💶", "💷", "💳", "🏦", "🏧", "💸", "🪙", "💎",
    "💰", "📊", "📈", "📉", "🏪", "🏬",
    # Lain-lain
    "🎁", "🌟", "⭐", "❤️", "🔑", "🧾", "📡", "🌐",
]

WARNA_OPTIONS = [
    "#FF6B6B", "#4ECDC4", "#FFE66D", "#95E1D3",
    "#F38181", "#AA96DA", "#00D2FC", "#8FD14F",
    "#FF9FF3", "#54A0FF", "#48DBFB", "#636EFA"
]

BULAN_NAMA = [
    "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember"
]


def format_rupiah(amount, symbol="Rp"):
    if amount == 0:
        return f"{symbol} 0"

    is_negative = amount < 0
    amount = abs(amount)

    int_part = int(amount)
    dec_part = round((amount - int_part) * 100)

    int_str = f"{int_part:,}".replace(",", ".")

    if dec_part > 0:
        return f"{'−' if is_negative else ''}{symbol} {int_str},{dec_part:02d}"
    else:
        return f"{'−' if is_negative else ''}{symbol} {int_str}"


def parse_rupiah(text):
    text = text.strip()
    if not text:
        return 0.0

    text = text.replace("Rp", "").replace("$", "").replace("€", "").strip()
    text = text.replace(".", "").replace(",", ".")

    try:
        return float(text)
    except ValueError:
        return 0.0


def get_bulan_nama(bulan_int):
    if 1 <= bulan_int <= 12:
        return BULAN_NAMA[bulan_int - 1]
    return ""


def warna_jenis(jenis):
    if jenis == "pengeluaran":
        return "#EF553B"
    elif jenis == "pemasukan":
        return "#00CC96"
    else:
        return "#636EFA"


def format_tanggal(tanggal, format_str="DD/MM/YYYY"):
    if not tanggal:
        return ""

    from datetime import datetime
    if isinstance(tanggal, str):
        tanggal = datetime.strptime(tanggal, "%Y-%m-%d").date()

    if format_str == "DD/MM/YYYY":
        return tanggal.strftime("%d/%m/%Y")
    elif format_str == "YYYY-MM-DD":
        return tanggal.strftime("%Y-%m-%d")
    elif format_str == "MM/DD/YYYY":
        return tanggal.strftime("%m/%d/%Y")
    else:
        return tanggal.strftime("%d/%m/%Y")


def render_wallet_card(wallet_row, mata_uang):
    """Render wallet balance card with image icon or emoji fallback."""
    import streamlit as st
    from pathlib import Path

    ikon_path = wallet_row.get('ikon_path')
    if ikon_path and Path(ikon_path).exists():
        img_col, txt_col = st.columns([0.25, 0.75])
        with img_col:
            st.image(ikon_path, width=40)
        with txt_col:
            st.markdown(f"**{wallet_row['nama']}**")
            st.markdown(f"**{format_rupiah(wallet_row['saldo_saat_ini'], mata_uang)}**")
    else:
        st.metric(
            label=f"{wallet_row['ikon_bawaan']} {wallet_row['nama']}",
            value=format_rupiah(wallet_row['saldo_saat_ini'], mata_uang)
        )

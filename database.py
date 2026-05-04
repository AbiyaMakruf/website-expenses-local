import sqlite3
import pandas as pd
from datetime import datetime, date
from pathlib import Path
import shutil


class Database:
    def __init__(self):
        self.db_path = Path(__file__).parent / "data" / "expenses.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _connect(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("PRAGMA foreign_keys = ON")
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        conn = self._connect()
        c = conn.cursor()

        # Create kategori table
        c.execute("""
        CREATE TABLE IF NOT EXISTS kategori (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            nama    TEXT    NOT NULL UNIQUE,
            jenis   TEXT    NOT NULL CHECK(jenis IN ('pengeluaran','pemasukan','keduanya')),
            ikon    TEXT    DEFAULT '📦',
            warna   TEXT    DEFAULT '#636EFA',
            is_default INTEGER DEFAULT 0
        );
        """)

        # Create transactions table
        c.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            tanggal     DATE    NOT NULL,
            jenis       TEXT    NOT NULL CHECK(jenis IN ('pengeluaran','pemasukan')),
            kategori_id INTEGER NOT NULL REFERENCES kategori(id),
            nominal     REAL    NOT NULL CHECK(nominal > 0),
            catatan     TEXT,
            foto_path   TEXT    DEFAULT NULL,
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Migration: Add foto_path column if not exists
        try:
            c.execute("ALTER TABLE transactions ADD COLUMN foto_path TEXT DEFAULT NULL")
        except sqlite3.OperationalError:
            pass

        # Migration: Add parent_id to kategori for sub-categories
        try:
            c.execute("ALTER TABLE kategori ADD COLUMN parent_id INTEGER REFERENCES kategori(id) DEFAULT NULL")
        except sqlite3.OperationalError:
            pass

        # Migration: Add transfer_pair_id to transactions for transfer tracking
        try:
            c.execute("ALTER TABLE transactions ADD COLUMN transfer_pair_id INTEGER DEFAULT NULL")
        except sqlite3.OperationalError:
            pass

        # Create anggaran table
        c.execute("""
        CREATE TABLE IF NOT EXISTS anggaran (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            kategori_id INTEGER NOT NULL REFERENCES kategori(id),
            bulan       INTEGER NOT NULL CHECK(bulan BETWEEN 1 AND 12),
            tahun       INTEGER NOT NULL,
            nominal     REAL    NOT NULL CHECK(nominal > 0),
            UNIQUE(kategori_id, bulan, tahun)
        );
        """)

        # Create pengaturan table
        c.execute("""
        CREATE TABLE IF NOT EXISTS pengaturan (
            kunci TEXT PRIMARY KEY,
            nilai TEXT NOT NULL
        );
        """)

        # Create wallet table
        c.execute("""
        CREATE TABLE IF NOT EXISTS wallet (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            nama        TEXT    NOT NULL UNIQUE,
            jenis       TEXT    NOT NULL CHECK(jenis IN ('bank','e-wallet','cash','investasi')),
            ikon_bawaan TEXT    DEFAULT '💳',
            ikon_path   TEXT    DEFAULT NULL,
            saldo_awal  REAL    NOT NULL DEFAULT 0,
            warna       TEXT    DEFAULT '#636EFA',
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Create subscription table
        c.execute("""
        CREATE TABLE IF NOT EXISTS subscription (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            nama          TEXT    NOT NULL,
            nominal       REAL    NOT NULL CHECK(nominal > 0),
            tanggal_bayar INTEGER NOT NULL CHECK(tanggal_bayar BETWEEN 1 AND 31),
            catatan       TEXT    DEFAULT '',
            ikon_path     TEXT    DEFAULT NULL,
            aktif         INTEGER DEFAULT 1,
            created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Seed default kategoris if not exist
        c.execute("SELECT COUNT(*) as count FROM kategori;")
        if c.fetchone()["count"] == 0:
            # Create 2 parent categories
            c.execute("INSERT INTO kategori (nama, jenis, ikon, warna, is_default) VALUES ('Makanan', 'pengeluaran', '🍽️', '#FF6B6B', 1)")
            makanan_id = c.lastrowid
            c.execute("INSERT INTO kategori (nama, jenis, ikon, warna, is_default) VALUES ('Pemasukan', 'pemasukan', '💰', '#00D2FC', 1)")
            pemasukan_id = c.lastrowid

            # Create 4 subcategories (2 per parent)
            sub_defaults = [
                ("Makan Berat", "pengeluaran", "🍛", "#FF6B6B", 1, makanan_id),
                ("Minuman",     "pengeluaran", "☕", "#F38181", 1, makanan_id),
                ("Gaji",        "pemasukan",   "💼", "#00D2FC", 1, pemasukan_id),
                ("Freelance",   "pemasukan",   "💻", "#8FD14F", 1, pemasukan_id),
            ]
            c.executemany(
                "INSERT INTO kategori (nama, jenis, ikon, warna, is_default, parent_id) VALUES (?, ?, ?, ?, ?, ?)",
                sub_defaults
            )

        # Seed Transfer Dana kategori if not exist
        c.execute("SELECT id FROM kategori WHERE nama = 'Transfer Dana'")
        if not c.fetchone():
            c.execute("INSERT INTO kategori (nama, jenis, ikon, warna, is_default) VALUES ('Transfer Dana', 'keduanya', '↔️', '#636EFA', 1)")

        # Seed default settings if not exist
        c.execute("SELECT COUNT(*) as count FROM pengaturan;")
        if c.fetchone()["count"] == 0:
            defaults = [
                ("nama_aplikasi", "Catatan Keuangan"),
                ("mata_uang", "Rp"),
                ("format_tanggal", "DD/MM/YYYY"),
                ("tema_warna", "biru"),
            ]
            c.executemany(
                "INSERT INTO pengaturan (kunci, nilai) VALUES (?, ?)",
                defaults
            )

        # Seed default wallet if not exist
        c.execute("SELECT COUNT(*) as count FROM wallet;")
        if c.fetchone()["count"] == 0:
            c.execute("""
                INSERT INTO wallet (nama, jenis, ikon_bawaan, saldo_awal, warna)
                VALUES ('Tunai', 'cash', '💵', 0, '#8FD14F')
            """)
            c.execute("""
                INSERT INTO wallet (nama, jenis, ikon_bawaan, saldo_awal, warna)
                VALUES ('Bank', 'bank', '🏦', 0, '#636EFA')
            """)

        # Migration: Add wallet_id to transactions
        try:
            c.execute("ALTER TABLE transactions ADD COLUMN wallet_id INTEGER REFERENCES wallet(id)")
            c.execute("UPDATE transactions SET wallet_id = 1 WHERE wallet_id IS NULL")
        except sqlite3.OperationalError:
            pass

        conn.commit()
        conn.close()

    # ===== KATEGORI OPERATIONS =====

    def get_all_kategori(self, jenis=None, parent_id=None, only_leaf=False):
        """Get kategori with optional filtering.
        parent_id='root' → WHERE parent_id IS NULL
        parent_id=<int>  → WHERE parent_id = ?
        only_leaf=True   → exclude rows that are parents
        """
        conn = self._connect()
        c = conn.cursor()

        query = "SELECT * FROM kategori WHERE 1=1"
        params = []

        if jenis:
            query += " AND jenis IN (?, 'keduanya')"
            params.append(jenis)

        if parent_id == 'root':
            query += " AND parent_id IS NULL"
        elif parent_id is not None:
            query += " AND parent_id = ?"
            params.append(parent_id)

        if only_leaf:
            query += " AND id NOT IN (SELECT DISTINCT parent_id FROM kategori WHERE parent_id IS NOT NULL)"

        query += " ORDER BY nama"
        c.execute(query, params)
        rows = c.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def add_kategori(self, nama, jenis, ikon="📦", warna="#636EFA", parent_id=None):
        conn = self._connect()
        c = conn.cursor()

        try:
            c.execute("""
                INSERT INTO kategori (nama, jenis, ikon, warna, parent_id)
                VALUES (?, ?, ?, ?, ?)
            """, (nama, jenis, ikon, warna, parent_id))
            conn.commit()
            new_id = c.lastrowid
            conn.close()
            return new_id
        except sqlite3.IntegrityError as e:
            conn.close()
            raise ValueError(f"Kategori '{nama}' sudah ada") from e

    def update_kategori(self, id, nama, jenis, ikon, warna, parent_id=None):
        conn = self._connect()
        c = conn.cursor()

        c.execute("SELECT is_default FROM kategori WHERE id = ?", (id,))
        row = c.fetchone()
        if row and row["is_default"]:
            conn.close()
            raise ValueError("Kategori default tidak bisa diubah")

        try:
            c.execute("""
                UPDATE kategori
                SET nama = ?, jenis = ?, ikon = ?, warna = ?, parent_id = ?
                WHERE id = ?
            """, (nama, jenis, ikon, warna, parent_id, id))
            conn.commit()
            conn.close()
        except sqlite3.IntegrityError as e:
            conn.close()
            raise ValueError(f"Kategori '{nama}' sudah ada") from e

    def delete_kategori(self, id):
        conn = self._connect()
        c = conn.cursor()

        c.execute("SELECT is_default FROM kategori WHERE id = ?", (id,))
        row = c.fetchone()
        if row and row["is_default"]:
            conn.close()
            raise ValueError("Kategori default tidak bisa dihapus")

        # Check if it has children (is a parent)
        c.execute("SELECT COUNT(*) as count FROM kategori WHERE parent_id = ?", (id,))
        if c.fetchone()["count"] > 0:
            conn.close()
            raise ValueError("Hapus subkategori terlebih dahulu sebelum menghapus kategori parent")

        c.execute("SELECT COUNT(*) as count FROM transactions WHERE kategori_id = ?", (id,))
        if c.fetchone()["count"] > 0:
            conn.close()
            raise ValueError("Kategori masih digunakan oleh transaksi")

        c.execute("DELETE FROM kategori WHERE id = ?", (id,))
        conn.commit()
        conn.close()

    # ===== TRANSACTIONS OPERATIONS =====

    def get_uploads_dir(self):
        uploads_dir = self.db_path.parent / "uploads"
        uploads_dir.mkdir(parents=True, exist_ok=True)
        return uploads_dir

    def add_transaksi(self, tanggal, jenis, kategori_id, nominal, catatan="", foto_path=None, wallet_id=None):
        conn = self._connect()
        c = conn.cursor()

        c.execute("""
            INSERT INTO transactions (tanggal, jenis, kategori_id, nominal, catatan, foto_path, wallet_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (tanggal, jenis, kategori_id, nominal, catatan, foto_path, wallet_id))
        conn.commit()
        new_id = c.lastrowid
        conn.close()
        return new_id

    def update_transaksi(self, id, tanggal, jenis, kategori_id, nominal, catatan="", foto_path=None, wallet_id=None):
        conn = self._connect()
        c = conn.cursor()

        if foto_path is None and wallet_id is None:
            c.execute("""
                UPDATE transactions
                SET tanggal = ?, jenis = ?, kategori_id = ?, nominal = ?, catatan = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (tanggal, jenis, kategori_id, nominal, catatan, id))
        elif foto_path is None:
            c.execute("""
                UPDATE transactions
                SET tanggal = ?, jenis = ?, kategori_id = ?, nominal = ?, catatan = ?, wallet_id = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (tanggal, jenis, kategori_id, nominal, catatan, wallet_id, id))
        elif wallet_id is None:
            c.execute("""
                UPDATE transactions
                SET tanggal = ?, jenis = ?, kategori_id = ?, nominal = ?, catatan = ?, foto_path = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (tanggal, jenis, kategori_id, nominal, catatan, foto_path, id))
        else:
            c.execute("""
                UPDATE transactions
                SET tanggal = ?, jenis = ?, kategori_id = ?, nominal = ?, catatan = ?, foto_path = ?, wallet_id = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (tanggal, jenis, kategori_id, nominal, catatan, foto_path, wallet_id, id))
        conn.commit()
        conn.close()

    def update_foto_path(self, id, foto_path):
        conn = self._connect()
        c = conn.cursor()

        c.execute("""
            UPDATE transactions
            SET foto_path = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (foto_path, id))
        conn.commit()
        conn.close()

    def delete_transaksi(self, id):
        conn = self._connect()
        c = conn.cursor()

        # Get transfer_pair_id if this is a transfer
        c.execute("SELECT foto_path, transfer_pair_id FROM transactions WHERE id = ?", (id,))
        row = c.fetchone()
        if row and row["foto_path"]:
            foto_path = Path(row["foto_path"])
            if foto_path.exists():
                foto_path.unlink()

        # If transfer, delete paired transaction too
        if row and row["transfer_pair_id"]:
            c.execute("DELETE FROM transactions WHERE id = ?", (row["transfer_pair_id"],))

        c.execute("DELETE FROM transactions WHERE id = ?", (id,))
        conn.commit()
        conn.close()

    def get_transaksi(self, tanggal_dari=None, tanggal_sampai=None, jenis=None,
                      kategori_ids=None, search_text="", limit=None, offset=0, wallet_id=None):
        conn = self._connect()
        c = conn.cursor()

        query = """
            SELECT t.id, t.tanggal, t.jenis, t.kategori_id, k.nama as kategori_nama,
                   k.ikon, k.warna, t.nominal, t.catatan, t.foto_path, t.wallet_id, t.created_at, t.updated_at
            FROM transactions t
            JOIN kategori k ON t.kategori_id = k.id
            WHERE 1=1
        """
        params = []

        if tanggal_dari:
            query += " AND t.tanggal >= ?"
            params.append(tanggal_dari)
        if tanggal_sampai:
            query += " AND t.tanggal <= ?"
            params.append(tanggal_sampai)
        if jenis:
            query += " AND t.jenis = ?"
            params.append(jenis)
        if kategori_ids:
            placeholders = ",".join("?" * len(kategori_ids))
            query += f" AND t.kategori_id IN ({placeholders})"
            params.extend(kategori_ids)
        if search_text:
            query += " AND (t.catatan LIKE ? OR k.nama LIKE ?)"
            search = f"%{search_text}%"
            params.extend([search, search])
        if wallet_id:
            query += " AND t.wallet_id = ?"
            params.append(wallet_id)

        query += " ORDER BY t.tanggal DESC, t.id DESC"

        if limit:
            query += f" LIMIT {limit} OFFSET {offset}"

        c.execute(query, params)
        rows = c.fetchall()
        conn.close()

        df = pd.DataFrame([dict(row) for row in rows])
        if df.empty:
            return pd.DataFrame()
        return df

    # ===== DASHBOARD AGGREGATES =====

    def get_summary_bulan_ini(self):
        conn = self._connect()
        c = conn.cursor()

        today = date.today()
        bulan = today.month
        tahun = today.year

        # Total pemasukan bulan ini
        c.execute("""
            SELECT COALESCE(SUM(nominal), 0) as total
            FROM transactions
            WHERE jenis = 'pemasukan'
            AND strftime('%m', tanggal) = ?
            AND strftime('%Y', tanggal) = ?
        """, (f"{bulan:02d}", str(tahun)))
        total_pemasukan = c.fetchone()["total"]

        # Total pengeluaran bulan ini
        c.execute("""
            SELECT COALESCE(SUM(nominal), 0) as total
            FROM transactions
            WHERE jenis = 'pengeluaran'
            AND strftime('%m', tanggal) = ?
            AND strftime('%Y', tanggal) = ?
        """, (f"{bulan:02d}", str(tahun)))
        total_pengeluaran = c.fetchone()["total"]

        saldo_bulan = total_pemasukan - total_pengeluaran

        conn.close()
        return {
            "total_pemasukan": total_pemasukan,
            "total_pengeluaran": total_pengeluaran,
            "saldo_bulan": saldo_bulan
        }

    def get_saldo_total(self):
        conn = self._connect()
        c = conn.cursor()
        c.execute("""
            SELECT
                COALESCE(SUM(CASE WHEN jenis='pemasukan' THEN nominal ELSE 0 END), 0) as total_pemasukan,
                COALESCE(SUM(CASE WHEN jenis='pengeluaran' THEN nominal ELSE 0 END), 0) as total_pengeluaran
            FROM transactions
        """)
        row = c.fetchone()
        conn.close()
        return row["total_pemasukan"] - row["total_pengeluaran"]

    def get_ringkasan_keseluruhan(self):
        conn = self._connect()
        c = conn.cursor()
        c.execute("""
            SELECT
                COALESCE(SUM(CASE WHEN jenis='pemasukan' THEN nominal ELSE 0 END), 0) as total_pemasukan,
                COALESCE(SUM(CASE WHEN jenis='pengeluaran' THEN nominal ELSE 0 END), 0) as total_pengeluaran
            FROM transactions
        """)
        row = c.fetchone()
        conn.close()
        total_pemasukan = row["total_pemasukan"]
        total_pengeluaran = row["total_pengeluaran"]
        return {
            "total_pemasukan": total_pemasukan,
            "total_pengeluaran": total_pengeluaran,
            "saldo": total_pemasukan - total_pengeluaran,
        }

    def get_pengeluaran_per_kategori(self, bulan, tahun):
        conn = self._connect()
        c = conn.cursor()

        c.execute("""
            SELECT k.id, k.nama, k.ikon, k.warna, COALESCE(SUM(t.nominal), 0) as total
            FROM kategori k
            LEFT JOIN transactions t ON k.id = t.kategori_id
                AND t.jenis = 'pengeluaran'
                AND strftime('%m', t.tanggal) = ?
                AND strftime('%Y', t.tanggal) = ?
            WHERE k.jenis IN ('pengeluaran', 'keduanya')
            GROUP BY k.id, k.nama, k.ikon, k.warna
            HAVING total > 0
            ORDER BY total DESC
        """, (f"{bulan:02d}", str(tahun)))

        rows = c.fetchall()
        conn.close()

        df = pd.DataFrame([dict(row) for row in rows])
        if df.empty:
            return pd.DataFrame(columns=["id", "nama", "ikon", "warna", "total"])
        return df

    def get_trend_bulanan(self, n_bulan=6):
        conn = self._connect()
        c = conn.cursor()

        c.execute("""
            SELECT
                strftime('%m', tanggal) as bulan,
                strftime('%Y', tanggal) as tahun,
                jenis,
                COALESCE(SUM(nominal), 0) as total
            FROM transactions
            WHERE tanggal >= date('now', '-' || ? || ' months')
            GROUP BY bulan, tahun, jenis
            ORDER BY tahun ASC, bulan ASC
        """, (n_bulan,))

        rows = c.fetchall()
        conn.close()

        df = pd.DataFrame([dict(row) for row in rows])
        if df.empty:
            return pd.DataFrame()
        return df

    # ===== ANGGARAN OPERATIONS =====

    def get_anggaran(self, bulan, tahun):
        conn = self._connect()
        c = conn.cursor()

        c.execute("""
            SELECT
                a.id, a.kategori_id, k.nama, k.ikon, k.warna,
                a.nominal as anggaran,
                COALESCE(SUM(t.nominal), 0) as realisasi
            FROM anggaran a
            JOIN kategori k ON a.kategori_id = k.id
            LEFT JOIN transactions t ON a.kategori_id = t.kategori_id
                AND t.jenis = 'pengeluaran'
                AND strftime('%m', t.tanggal) = ?
                AND strftime('%Y', t.tanggal) = ?
            WHERE a.bulan = ? AND a.tahun = ?
            GROUP BY a.id, a.kategori_id, k.nama, k.ikon, k.warna, a.nominal
            ORDER BY k.nama
        """, (f"{bulan:02d}", str(tahun), bulan, tahun))

        rows = c.fetchall()
        conn.close()

        df = pd.DataFrame([dict(row) for row in rows])
        if df.empty:
            return pd.DataFrame()
        return df

    def set_anggaran(self, kategori_id, bulan, tahun, nominal):
        conn = self._connect()
        c = conn.cursor()

        c.execute("""
            INSERT OR REPLACE INTO anggaran (kategori_id, bulan, tahun, nominal)
            VALUES (?, ?, ?, ?)
        """, (kategori_id, bulan, tahun, nominal))
        conn.commit()
        conn.close()

    def delete_anggaran(self, id):
        conn = self._connect()
        c = conn.cursor()

        c.execute("DELETE FROM anggaran WHERE id = ?", (id,))
        conn.commit()
        conn.close()

    # ===== LAPORAN OPERATIONS =====

    def get_laporan_periode(self, tgl_dari, tgl_sampai):
        conn = self._connect()
        c = conn.cursor()

        c.execute("""
            SELECT t.id, t.tanggal, t.jenis, t.kategori_id, k.nama as kategori_nama,
                   t.nominal, t.catatan, t.foto_path, t.wallet_id, t.created_at
            FROM transactions t
            JOIN kategori k ON t.kategori_id = k.id
            WHERE t.tanggal BETWEEN ? AND ?
            ORDER BY t.tanggal DESC
        """, (tgl_dari, tgl_sampai))

        rows = c.fetchall()
        conn.close()

        df = pd.DataFrame([dict(row) for row in rows])
        if df.empty:
            return pd.DataFrame()
        return df

    # ===== PENGATURAN OPERATIONS =====

    def get_setting(self, kunci):
        conn = self._connect()
        c = conn.cursor()

        c.execute("SELECT nilai FROM pengaturan WHERE kunci = ?", (kunci,))
        row = c.fetchone()
        conn.close()

        return row["nilai"] if row else None

    def set_setting(self, kunci, nilai):
        conn = self._connect()
        c = conn.cursor()

        c.execute("""
            INSERT OR REPLACE INTO pengaturan (kunci, nilai)
            VALUES (?, ?)
        """, (kunci, nilai))
        conn.commit()
        conn.close()

    def get_all_settings(self):
        conn = self._connect()
        c = conn.cursor()

        c.execute("SELECT kunci, nilai FROM pengaturan")
        rows = c.fetchall()
        conn.close()

        return {row["kunci"]: row["nilai"] for row in rows}

    # ===== WALLET OPERATIONS =====

    def get_all_wallets(self):
        conn = self._connect()
        c = conn.cursor()
        c.execute("SELECT * FROM wallet ORDER BY nama")
        rows = c.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_wallet(self, wallet_id):
        conn = self._connect()
        c = conn.cursor()
        c.execute("SELECT * FROM wallet WHERE id = ?", (wallet_id,))
        row = c.fetchone()
        conn.close()
        return dict(row) if row else None

    def add_wallet(self, nama, jenis, ikon_bawaan='💳', ikon_path=None, saldo_awal=0, warna='#636EFA'):
        conn = self._connect()
        c = conn.cursor()
        try:
            c.execute("""
                INSERT INTO wallet (nama, jenis, ikon_bawaan, ikon_path, saldo_awal, warna)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (nama, jenis, ikon_bawaan, ikon_path, saldo_awal, warna))
            conn.commit()
            new_id = c.lastrowid
            conn.close()
            return new_id
        except sqlite3.IntegrityError as e:
            conn.close()
            raise ValueError(f"Wallet '{nama}' sudah ada") from e

    def update_wallet(self, id, nama, jenis, ikon_bawaan, ikon_path, saldo_awal, warna):
        conn = self._connect()
        c = conn.cursor()
        try:
            c.execute("""
                UPDATE wallet
                SET nama=?, jenis=?, ikon_bawaan=?, ikon_path=?, saldo_awal=?, warna=?
                WHERE id=?
            """, (nama, jenis, ikon_bawaan, ikon_path, saldo_awal, warna, id))
            conn.commit()
            conn.close()
        except sqlite3.IntegrityError as e:
            conn.close()
            raise ValueError(f"Wallet '{nama}' sudah ada") from e

    def delete_wallet(self, id):
        conn = self._connect()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) as cnt FROM wallet")
        if c.fetchone()["cnt"] <= 1:
            conn.close()
            raise ValueError("Tidak bisa menghapus wallet terakhir")
        c.execute("SELECT COUNT(*) as cnt FROM transactions WHERE wallet_id = ?", (id,))
        if c.fetchone()["cnt"] > 0:
            conn.close()
            raise ValueError("Wallet masih memiliki transaksi. Pindahkan transaksi terlebih dahulu.")
        c.execute("DELETE FROM wallet WHERE id = ?", (id,))
        conn.commit()
        conn.close()

    def get_wallet_icons_dir(self):
        icons_dir = self.db_path.parent / "wallet_icons"
        icons_dir.mkdir(parents=True, exist_ok=True)
        return icons_dir

    def get_saldo_wallet(self, wallet_id):
        conn = self._connect()
        c = conn.cursor()
        c.execute("""
            SELECT w.saldo_awal
                 + COALESCE(SUM(CASE WHEN t.jenis='pemasukan' THEN t.nominal ELSE 0 END), 0)
                 - COALESCE(SUM(CASE WHEN t.jenis='pengeluaran' THEN t.nominal ELSE 0 END), 0)
                 AS saldo_saat_ini
            FROM wallet w
            LEFT JOIN transactions t ON t.wallet_id = w.id
            WHERE w.id = ?
            GROUP BY w.id
        """, (wallet_id,))
        row = c.fetchone()
        conn.close()
        return row["saldo_saat_ini"] if row else 0.0

    def get_saldo_semua_wallet(self):
        conn = self._connect()
        c = conn.cursor()
        c.execute("""
            SELECT w.id, w.nama, w.jenis, w.ikon_bawaan, w.ikon_path, w.warna, w.saldo_awal,
                   w.saldo_awal
                   + COALESCE(SUM(CASE WHEN t.jenis='pemasukan' THEN t.nominal ELSE 0 END), 0)
                   - COALESCE(SUM(CASE WHEN t.jenis='pengeluaran' THEN t.nominal ELSE 0 END), 0)
                   AS saldo_saat_ini
            FROM wallet w
            LEFT JOIN transactions t ON t.wallet_id = w.id
            GROUP BY w.id, w.nama, w.jenis, w.ikon_bawaan, w.ikon_path, w.warna, w.saldo_awal
            ORDER BY w.nama
        """)
        rows = c.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_top_pengeluaran(self, bulan, tahun, limit=5):
        conn = self._connect()
        c = conn.cursor()
        c.execute("""
            SELECT t.id, t.tanggal, t.nominal, t.catatan,
                   k.nama as kategori_nama, k.ikon, k.warna
            FROM transactions t
            JOIN kategori k ON t.kategori_id = k.id
            WHERE t.jenis = 'pengeluaran'
              AND strftime('%m', t.tanggal) = ?
              AND strftime('%Y', t.tanggal) = ?
            ORDER BY t.nominal DESC
            LIMIT ?
        """, (f"{bulan:02d}", str(tahun), limit))
        rows = c.fetchall()
        conn.close()
        df = pd.DataFrame([dict(row) for row in rows])
        if df.empty:
            return pd.DataFrame(columns=["id","tanggal","nominal","catatan","kategori_nama","ikon","warna"])
        return df

    def get_ringkasan_per_kategori_bulan(self, bulan, tahun):
        conn = self._connect()
        c = conn.cursor()
        c.execute("""
            SELECT k.id as kategori_id, k.nama as kategori_nama, k.ikon, k.warna,
                   COALESCE(SUM(CASE WHEN t.jenis='pengeluaran' THEN t.nominal ELSE 0 END), 0) as total_pengeluaran,
                   COALESCE(SUM(CASE WHEN t.jenis='pemasukan' THEN t.nominal ELSE 0 END), 0) as total_pemasukan
            FROM kategori k
            LEFT JOIN transactions t ON t.kategori_id = k.id
                AND strftime('%m', t.tanggal) = ?
                AND strftime('%Y', t.tanggal) = ?
            GROUP BY k.id, k.nama, k.ikon, k.warna
            HAVING total_pengeluaran > 0 OR total_pemasukan > 0
            ORDER BY total_pengeluaran DESC
        """, (f"{bulan:02d}", str(tahun)))
        rows = c.fetchall()
        conn.close()
        df = pd.DataFrame([dict(row) for row in rows])
        if df.empty:
            return pd.DataFrame(columns=["kategori_id","kategori_nama","ikon","warna","total_pengeluaran","total_pemasukan"])
        return df

    # ===== KATEGORI HIERARCHY =====

    def get_kategori_tree(self, jenis=None):
        """Return kategori as tree: parents with children list."""
        all_kat = self.get_all_kategori(jenis=jenis)
        parents = [k for k in all_kat if k.get('parent_id') is None]
        tree = []
        for parent in parents:
            children = [k for k in all_kat if k.get('parent_id') == parent['id']]
            tree.append({**parent, 'children': children})
        return tree

    # ===== TRANSFER OPERATIONS =====

    def get_transfer_kategori_id(self):
        """Get ID of the special 'Transfer Dana' kategori."""
        conn = self._connect()
        c = conn.cursor()
        c.execute("SELECT id FROM kategori WHERE nama = 'Transfer Dana'")
        row = c.fetchone()
        conn.close()
        return row['id'] if row else None

    def add_transfer(self, tanggal, dari_wallet_id, ke_wallet_id, nominal, catatan=""):
        """Create paired transfer: pengeluaran on dari_wallet, pemasukan on ke_wallet."""
        if dari_wallet_id == ke_wallet_id:
            raise ValueError("Wallet asal dan tujuan tidak boleh sama")

        transfer_kat_id = self.get_transfer_kategori_id()
        conn = self._connect()
        c = conn.cursor()

        try:
            # Insert pengeluaran on dari_wallet
            c.execute("""
                INSERT INTO transactions (tanggal, jenis, kategori_id, nominal, catatan, wallet_id)
                VALUES (?, 'pengeluaran', ?, ?, ?, ?)
            """, (tanggal, transfer_kat_id, nominal, f"Transfer ke {ke_wallet_id}: {catatan}", dari_wallet_id))
            id_keluar = c.lastrowid

            # Insert pemasukan on ke_wallet
            c.execute("""
                INSERT INTO transactions (tanggal, jenis, kategori_id, nominal, catatan, wallet_id)
                VALUES (?, 'pemasukan', ?, ?, ?, ?)
            """, (tanggal, transfer_kat_id, nominal, f"Transfer dari {dari_wallet_id}: {catatan}", ke_wallet_id))
            id_masuk = c.lastrowid

            # Link both transactions
            c.execute("UPDATE transactions SET transfer_pair_id = ? WHERE id = ?", (id_masuk, id_keluar))
            c.execute("UPDATE transactions SET transfer_pair_id = ? WHERE id = ?", (id_keluar, id_masuk))

            conn.commit()
            conn.close()
            return (id_keluar, id_masuk)
        except Exception as e:
            conn.close()
            raise e

    def get_transfer_list(self, limit=10):
        """Get list of transfers as tuples (pengeluaran_row, pemasukan_row)."""
        conn = self._connect()
        c = conn.cursor()
        c.execute("""
            SELECT
                t1.id as id_keluar,
                t1.tanggal,
                t1.nominal,
                t1.catatan,
                w1.nama as dari_wallet,
                w2.nama as ke_wallet,
                t2.id as id_masuk
            FROM transactions t1
            JOIN wallet w1 ON t1.wallet_id = w1.id
            JOIN transactions t2 ON t1.transfer_pair_id = t2.id
            JOIN wallet w2 ON t2.wallet_id = w2.id
            WHERE t1.jenis = 'pengeluaran' AND t1.transfer_pair_id IS NOT NULL
            ORDER BY t1.tanggal DESC
            LIMIT ?
        """, (limit,))
        rows = c.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    # ===== SUBSCRIPTION =====

    def get_subscription_icons_dir(self):
        """Return/create data/subscription_icons/ directory."""
        icons_dir = self.db_path.parent / "subscription_icons"
        icons_dir.mkdir(parents=True, exist_ok=True)
        return icons_dir

    def get_all_subscriptions(self, aktif_only=True):
        """Get all subscriptions, optionally filtered to active only."""
        conn = self._connect()
        c = conn.cursor()
        if aktif_only:
            c.execute("SELECT * FROM subscription WHERE aktif = 1 ORDER BY tanggal_bayar")
        else:
            c.execute("SELECT * FROM subscription ORDER BY tanggal_bayar")
        rows = c.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_subscription(self, sub_id):
        """Get a single subscription by ID."""
        conn = self._connect()
        c = conn.cursor()
        c.execute("SELECT * FROM subscription WHERE id = ?", (sub_id,))
        row = c.fetchone()
        conn.close()
        return dict(row) if row else None

    def add_subscription(self, nama, nominal, tanggal_bayar, catatan="", ikon_path=None, aktif=1):
        """Add a new subscription."""
        conn = self._connect()
        c = conn.cursor()
        try:
            c.execute("""
                INSERT INTO subscription (nama, nominal, tanggal_bayar, catatan, ikon_path, aktif)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (nama, nominal, tanggal_bayar, catatan, ikon_path, aktif))
            conn.commit()
            new_id = c.lastrowid
            conn.close()
            return new_id
        except Exception as e:
            conn.close()
            raise e

    def update_subscription(self, sub_id, nama, nominal, tanggal_bayar, catatan, ikon_path, aktif):
        """Update an existing subscription."""
        conn = self._connect()
        c = conn.cursor()
        try:
            c.execute("""
                UPDATE subscription
                SET nama=?, nominal=?, tanggal_bayar=?, catatan=?, ikon_path=?, aktif=?
                WHERE id=?
            """, (nama, nominal, tanggal_bayar, catatan, ikon_path, aktif, sub_id))
            conn.commit()
            conn.close()
        except Exception as e:
            conn.close()
            raise e

    def delete_subscription(self, sub_id):
        """Delete a subscription and its icon file if exists."""
        sub = self.get_subscription(sub_id)
        if sub and sub['ikon_path']:
            icon_path = Path(sub['ikon_path'])
            if icon_path.exists():
                icon_path.unlink()

        conn = self._connect()
        c = conn.cursor()
        c.execute("DELETE FROM subscription WHERE id = ?", (sub_id,))
        conn.commit()
        conn.close()

    def get_total_subscription_per_bulan(self):
        """Get total nominal of all active subscriptions."""
        conn = self._connect()
        c = conn.cursor()
        c.execute("SELECT COALESCE(SUM(nominal), 0) as total FROM subscription WHERE aktif = 1")
        row = c.fetchone()
        conn.close()
        return row['total'] if row else 0

    # ===== BACKUP / RESTORE =====

    def backup_db(self, dest_path):
        shutil.copy(str(self.db_path), str(dest_path))

    def restore_db(self, src_path):
        shutil.copy(str(src_path), str(self.db_path))

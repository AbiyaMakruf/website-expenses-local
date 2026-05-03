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

        # Seed default kategoris if not exist
        c.execute("SELECT COUNT(*) as count FROM kategori;")
        if c.fetchone()["count"] == 0:
            defaults = [
                ("Makanan & Minuman", "pengeluaran", "🍽️", "#FF6B6B", 1),
                ("Transportasi", "pengeluaran", "🚗", "#4ECDC4", 1),
                ("Belanja", "pengeluaran", "🛍️", "#FFE66D", 1),
                ("Hiburan", "pengeluaran", "🎬", "#95E1D3", 1),
                ("Kesehatan", "pengeluaran", "💊", "#F38181", 1),
                ("Tagihan", "pengeluaran", "💡", "#AA96DA", 1),
                ("Gaji", "pemasukan", "💰", "#00D2FC", 1),
                ("Freelance", "pemasukan", "💻", "#8FD14F", 1),
                ("Lainnya", "keduanya", "📦", "#636EFA", 1),
            ]
            c.executemany(
                "INSERT INTO kategori (nama, jenis, ikon, warna, is_default) VALUES (?, ?, ?, ?, ?)",
                defaults
            )

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
                VALUES ('Default', 'cash', '💵', 0, '#8FD14F')
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

    def get_all_kategori(self, jenis=None):
        conn = self._connect()
        c = conn.cursor()

        if jenis:
            c.execute("""
                SELECT * FROM kategori
                WHERE jenis IN (?, 'keduanya')
                ORDER BY nama
            """, (jenis,))
        else:
            c.execute("SELECT * FROM kategori ORDER BY nama")

        rows = c.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def add_kategori(self, nama, jenis, ikon="📦", warna="#636EFA"):
        conn = self._connect()
        c = conn.cursor()

        try:
            c.execute("""
                INSERT INTO kategori (nama, jenis, ikon, warna)
                VALUES (?, ?, ?, ?)
            """, (nama, jenis, ikon, warna))
            conn.commit()
            new_id = c.lastrowid
            conn.close()
            return new_id
        except sqlite3.IntegrityError as e:
            conn.close()
            raise ValueError(f"Kategori '{nama}' sudah ada") from e

    def update_kategori(self, id, nama, jenis, ikon, warna):
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
                SET nama = ?, jenis = ?, ikon = ?, warna = ?
                WHERE id = ?
            """, (nama, jenis, ikon, warna, id))
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

        c.execute("SELECT foto_path FROM transactions WHERE id = ?", (id,))
        row = c.fetchone()
        if row and row["foto_path"]:
            foto_path = Path(row["foto_path"])
            if foto_path.exists():
                foto_path.unlink()

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

        c.execute("SELECT COALESCE(SUM(nominal), 0) as total FROM transactions WHERE jenis = 'pemasukan'")
        total_pemasukan = c.fetchone()["total"]

        c.execute("SELECT COALESCE(SUM(nominal), 0) as total FROM transactions WHERE jenis = 'pengeluaran'")
        total_pengeluaran = c.fetchone()["total"]

        conn.close()
        return total_pemasukan - total_pengeluaran

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

    # ===== BACKUP / RESTORE =====

    def backup_db(self, dest_path):
        shutil.copy(str(self.db_path), str(dest_path))

    def restore_db(self, src_path):
        shutil.copy(str(src_path), str(self.db_path))

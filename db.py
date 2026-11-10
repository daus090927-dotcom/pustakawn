import sqlite3

DATABASE = "perpustakaan.db"

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # Tabel User (Pustakawan & Anggota)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin', 'member')),
            nama_lengkap TEXT NOT NULL
        );
    """)

    # Tabel Buku
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            judul TEXT NOT NULL,
            penulis TEXT NOT NULL,
            kategori TEXT NOT NULL,
            stok INTEGER NOT NULL DEFAULT 0
        );
    """)

    # Tabel Peminjaman
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS loans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            book_id INTEGER NOT NULL,
            tanggal_pinjam DATE DEFAULT (DATE('now')),
            tanggal_kembali DATE,
            status TEXT NOT NULL CHECK(status IN ('dipinjam', 'dikembalikan')),
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (book_id) REFERENCES books (id)
        );
    """)

    # Akun default jika tabel masih kosong
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO users (username, password, role, nama_lengkap)
            VALUES 
                ('admin', 'admin123', 'admin', 'Kepala Perpustakaan'),
                ('member', 'user123', 'member', 'Anggota Utama')
        """)

    # Data buku awal jika tabel kosong
    cursor.execute("SELECT COUNT(*) FROM books")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO books (judul, penulis, kategori, stok)
            VALUES 
                ('Sistem Basis Data Lanjutan', 'R. Elmasri', 'Teknologi', 5),
                ('Clean Architecture & Patterns', 'Robert C. Martin', 'Pemrograman', 3),
                ('Struktur Data Terapan', 'Mark Allen Weiss', 'Komputer', 4)
        """)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database SQLite berhasil diinisialisasi.")
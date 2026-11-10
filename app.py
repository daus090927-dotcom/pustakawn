from flask import Flask, render_template, request, redirect, url_for, session, flash
from functools import wraps
from db import get_db, init_db

app = Flask(__name__)
app.secret_key = "kunci_rahasia_perpustakaan_modern"

# Inisialisasi DB saat start
init_db()

def login_required(role=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "user_id" not in session:
                flash("Harap login terlebih dahulu.", "warning")
                return redirect(url_for("login"))
            if role and session.get("role") != role:
                flash("Akses ditolak: Anda tidak memiliki izin untuk halaman ini.", "danger")
                return redirect(url_for("index"))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE username = ? AND password = ?",
            (username, password)
        ).fetchone()
        conn.close()

        if user:
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]
            session["nama_lengkap"] = user["nama_lengkap"]
            flash(f"Selamat datang, {user['nama_lengkap']}!", "success")
            return redirect(url_for("books"))
        else:
            flash("Username atau password salah.", "danger")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Anda telah logout.", "info")
    return redirect(url_for("login"))

@app.route("/books")
@login_required()
def books():
    conn = get_db()
    books = conn.execute("SELECT * FROM books").fetchall()
    conn.close()
    return render_template("books.html", books=books)

@app.route("/borrow/<int:book_id>", methods=["POST"])
@login_required(role="member")
def borrow_book(book_id):
    conn = get_db()
    cursor = conn.cursor()

    book = cursor.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()

    if not book or book["stok"] <= 0:
        conn.close()
        flash("Buku tidak tersedia atau stok habis.", "danger")
        return redirect(url_for("books"))

    # Cek apakah sedang meminjam buku yang sama dan belum kembali
    existing_loan = cursor.execute("""
        SELECT id FROM loans 
        WHERE user_id = ? AND book_id = ? AND status = 'dipinjam'
    """, (session["user_id"], book_id)).fetchone()

    if existing_loan:
        conn.close()
        flash("Anda sedang meminjam buku ini. Harap kembalikan terlebih dahulu.", "warning")
        return redirect(url_for("loans"))

    # Catat peminjaman & kurangi stok
    cursor.execute("""
        INSERT INTO loans (user_id, book_id, status)
        VALUES (?, ?, 'dipinjam')
    """, (session["user_id"], book_id))

    cursor.execute("UPDATE books SET stok = stok - 1 WHERE id = ?", (book_id,))
    conn.commit()
    conn.close()

    flash("Buku berhasil dipinjam!", "success")
    return redirect(url_for("loans"))

@app.route("/loans")
@login_required()
def loans():
    conn = get_db()
    cursor = conn.cursor()

    if session["role"] == "admin":
        loans = cursor.execute("""
            SELECT l.id, u.nama_lengkap, b.judul, l.tanggal_pinjam, l.tanggal_kembali, l.status
            FROM loans l
            JOIN users u ON l.user_id = u.id
            JOIN books b ON l.book_id = b.id
            ORDER BY l.id DESC
        """).fetchall()
    else:
        loans = cursor.execute("""
            SELECT l.id, u.nama_lengkap, b.judul, l.tanggal_pinjam, l.tanggal_kembali, l.status
            FROM loans l
            JOIN users u ON l.user_id = u.id
            JOIN books b ON l.book_id = b.id
            WHERE l.user_id = ?
            ORDER BY l.id DESC
        """, (session["user_id"],)).fetchall()

    conn.close()
    return render_template("loans.html", loans=loans)

@app.route("/return/<int:loan_id>", methods=["POST"])
@login_required()
def return_book(loan_id):
    conn = get_db()
    cursor = conn.cursor()

    loan = cursor.execute("SELECT * FROM loans WHERE id = ?", (loan_id,)).fetchone()

    if not loan or loan["status"] == "dikembalikan":
        conn.close()
        flash("Data peminjaman tidak valid atau sudah dikembalikan.", "danger")
        return redirect(url_for("loans"))

    # Member hanya boleh mengembalikan bukunya sendiri
    if session["role"] == "member" and loan["user_id"] != session["user_id"]:
        conn.close()
        flash("Aksi tidak valid.", "danger")
        return redirect(url_for("loans"))

    cursor.execute("""
        UPDATE loans 
        SET status = 'dikembalikan', tanggal_kembali = DATE('now')
        WHERE id = ?
    """, (loan_id,))

    cursor.execute("UPDATE books SET stok = stok + 1 WHERE id = ?", (loan["book_id"],))
    conn.commit()
    conn.close()

    flash("Buku telah berhasil dikembalikan.", "success")
    return redirect(url_for("loans"))

@app.route("/admin/books", methods=["GET", "POST"])
@login_required(role="admin")
def admin_books():
    conn = get_db()
    cursor = conn.cursor()

    if request.method == "POST":
        judul = request.form["judul"]
        penulis = request.form["penulis"]
        kategori = request.form["kategori"]
        stok = int(request.form["stok"])

        cursor.execute("""
            INSERT INTO books (judul, penulis, kategori, stok)
            VALUES (?, ?, ?, ?)
        """, (judul, penulis, kategori, stok))
        conn.commit()
        flash("Koleksi buku baru berhasil ditambahkan.", "success")
        return redirect(url_for("admin_books"))

    books = cursor.execute("SELECT * FROM books ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("admin_books.html", books=books)

@app.route("/admin/books/delete/<int:book_id>", methods=["POST"])
@login_required(role="admin")
def delete_book(book_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM books WHERE id = ?", (book_id,))
    conn.commit()
    conn.close()
    flash("Buku berhasil dihapus dari inventaris.", "info")
    return redirect(url_for("admin_books"))

if __name__ == "__main__":
    app.run(debug=True, port=5000)
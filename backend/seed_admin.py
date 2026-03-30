import sqlite3
import bcrypt
import uuid
import os

DB_PATH = "auth.db"

def get_password_hash(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def create_admin():
    if not os.path.exists(DB_PATH):
        print("Database not found! Run the backend first.")
        return

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    admin_email = "admin@proffinder.com"
    admin_name = "Super Admin"
    admin_password = "admin"
    pw_hash = get_password_hash(admin_password)

    c.execute("SELECT id FROM users WHERE email = ?", (admin_email,))
    existing = c.fetchone()
    
    if existing:
        c.execute("UPDATE users SET role = 'admin', password_hash = ? WHERE email = ?", (pw_hash, admin_email))
        print("Existing admin account updated!")
    else:
        admin_id = str(uuid.uuid4())
        c.execute(
            "INSERT INTO users (id, email, name, password_hash, role) VALUES (?, ?, ?, ?, ?)",
            (admin_id, admin_email, admin_name, pw_hash, "admin")
        )
        print("New admin account created!")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    create_admin()

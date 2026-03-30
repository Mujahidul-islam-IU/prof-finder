import sqlite3
import jwt
from datetime import datetime, timedelta, timezone
import bcrypt
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
import os

from typing import List
from app.models.schemas import UserCreate, UserLogin, Token, UserOut, UserUpdateAdmin
from app.config import get_settings

router = APIRouter()

# ── Setup SQLite for Auth ────────────────────────────────────
DB_PATH = "auth.db"

def init_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'user'
        )
    ''')
    
    # Ensure backwards compatibility by adding the role column if it's missing
    c.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in c.fetchall()]
    if "role" not in columns:
        c.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")

    # Seed default admin
    c.execute("SELECT * FROM users WHERE email='admin@proffinder.com'")
    if not c.fetchone():
        import bcrypt
        import uuid
        hashed = bcrypt.hashpw('admin'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        c.execute("""
            INSERT INTO users (id, email, name, password_hash, role)
            VALUES (?, 'admin@proffinder.com', 'System Admin', ?, 'admin')
        """, (str(uuid.uuid4()), hashed,))

    conn.commit()
    conn.close()

# Initialize DB on import
init_db()

def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# ── JWT Utility ──────────────────────────────────────────────
# We'll use the supabase anon key or a random secret for JWT signing locally
SECRET_KEY = getattr(get_settings(), "jwt_secret", "local_super_secret_prof_finder_key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_password(plain_password, hashed_password):
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def get_password_hash(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Dependency to get user from token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return payload
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")

async def get_admin_user(current_user: dict = Depends(get_current_user)):
    """Dependency to verify admin privileges."""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return current_user



# ── Routes ───────────────────────────────────────────────────

@router.post("/register", response_model=Token)
async def register(user: UserCreate, db: sqlite3.Connection = Depends(get_db)):
    """Register a new user and return JWT."""
    # Check if exists
    c = db.cursor()
    c.execute("SELECT email FROM users WHERE email = ?", (user.email,))
    if c.fetchone():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    import uuid
    user_id = str(uuid.uuid4())
    pw_hash = get_password_hash(user.password)
    
    c.execute(
        "INSERT INTO users (id, email, name, password_hash, role) VALUES (?, ?, ?, ?, ?)",
        (user_id, user.email, user.name, pw_hash, "user")
    )
    db.commit()
    
    # Create token
    access_token = create_access_token(data={"sub": user_id, "name": user.name, "email": user.email, "role": "user"})
    return {"access_token": access_token, "token_type": "bearer", "user_id": user_id, "name": user.name, "role": "user"}


@router.post("/login", response_model=Token)
async def login(user: UserLogin, db: sqlite3.Connection = Depends(get_db)):
    """Login and return JWT."""
    c = db.cursor()
    c.execute("SELECT id, email, name, password_hash, role FROM users WHERE email = ?", (user.email,))
    row = c.fetchone()
    
    if not row or not verify_password(user.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    user_id = row["id"]
    name = row["name"]
    email = row["email"]
    role = row["role"]
    
    access_token = create_access_token(data={"sub": user_id, "name": name, "email": email, "role": role})
    return {"access_token": access_token, "token_type": "bearer", "user_id": user_id, "name": name, "role": role}


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """Return info about the currently logged-in user."""
    return current_user


@router.get("/make-me-admin")
async def make_me_admin(current_user: dict = Depends(get_current_user), db: sqlite3.Connection = Depends(get_db)):
    """Temporary debug endpoint to elevate privileges."""
    c = db.cursor()
    c.execute("UPDATE users SET role = 'admin' WHERE id = ?", (current_user["sub"],))
    db.commit()
    return {"message": "You are now an admin. Please log out and back in to refresh your token."}


@router.get("/users", response_model=List[UserOut])
async def list_users(admin_user: dict = Depends(get_admin_user), db: sqlite3.Connection = Depends(get_db)):
    """Admin only: list all users."""
    c = db.cursor()
    c.execute("SELECT id, email, name, role FROM users")
    rows = c.fetchall()
    return [{"id": r["id"], "email": r["email"], "name": r["name"], "role": r["role"]} for r in rows]


@router.put("/users/{user_id}", response_model=UserOut)
async def update_user(user_id: str, updates: UserUpdateAdmin, admin_user: dict = Depends(get_admin_user), db: sqlite3.Connection = Depends(get_db)):
    """Admin only: update any user's profile or role."""
    c = db.cursor()
    # Check if exists
    c.execute("SELECT id, email, name, role FROM users WHERE id = ?", (user_id,))
    row = c.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
        
    new_name = updates.name if updates.name is not None else row["name"]
    new_email = updates.email if updates.email is not None else row["email"]
    new_role = updates.role if updates.role is not None else row["role"]
    
    if updates.password:
        pw_hash = get_password_hash(updates.password)
        c.execute("UPDATE users SET name=?, email=?, role=?, password_hash=? WHERE id=?", 
                  (new_name, new_email, new_role, pw_hash, user_id))
    else:
        c.execute("UPDATE users SET name=?, email=?, role=? WHERE id=?", 
                  (new_name, new_email, new_role, user_id))
    db.commit()
    
    return {"id": user_id, "email": new_email, "name": new_name, "role": new_role}


@router.delete("/users/{user_id}")
async def delete_user(user_id: str, admin_user: dict = Depends(get_admin_user), db: sqlite3.Connection = Depends(get_db)):
    """Admin only: delete a user."""
    c = db.cursor()
    c.execute("DELETE FROM users WHERE id = ?", (user_id,))
    db.commit()
    return {"message": "User deleted"}


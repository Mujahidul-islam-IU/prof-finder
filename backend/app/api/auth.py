import jwt
from datetime import datetime, timedelta, timezone
import bcrypt
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
import os
import uuid
from typing import List

from app.models.schemas import UserCreate, UserLogin, Token, UserOut, UserUpdateAdmin
from app.config import get_settings
from app.services.supabase_client import get_supabase

router = APIRouter()

# ── Setup Supabase for Auth ───────────────────────────────────

def init_admin():
    """Seed the default admin in Supabase if it doesn't exist."""
    try:
        db = get_supabase()
        # Use simple select to check if admin exists
        result = db.table("users").select("*").eq("email", "admin@proffinder.com").execute()
        
        if not result.data:
            print("[AUTH] Seeding default admin into Supabase...")
            hashed = bcrypt.hashpw('admin'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            db.table("users").insert({
                "id": str(uuid.uuid4()),
                "email": "admin@proffinder.com",
                "name": "System Admin",
                "password_hash": hashed,
                "role": "admin"
            }).execute()
    except Exception as e:
        print(f"[AUTH] Error seeding admin: {e}")

# Seed admin on import
init_admin()


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

# ── Routes ───────────────────────────────────────────────────

@router.post("/register", response_model=Token)
async def register(user: UserCreate):
    """Register a new user and return JWT."""
    db = get_supabase()
    
    # Check if exists
    existing = db.table("users").select("email").eq("email", user.email).execute()
    if existing.data:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_id = str(uuid.uuid4())
    pw_hash = get_password_hash(user.password)
    
    db.table("users").insert({
        "id": user_id, 
        "email": user.email, 
        "name": user.name, 
        "password_hash": pw_hash, 
        "role": "user"
    }).execute()
    
    # Create token
    access_token = create_access_token(data={"sub": user_id, "name": user.name, "email": user.email, "role": "user"})
    return {"access_token": access_token, "token_type": "bearer", "user_id": user_id, "name": user.name, "role": "user"}


@router.post("/login", response_model=Token)
async def login(user: UserLogin):
    """Login and return JWT."""
    db = get_supabase()
    result = db.table("users").select("*").eq("email", user.email).execute()
    
    if not result.data or not verify_password(user.password, result.data[0]["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    row = result.data[0]
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
async def make_me_admin(current_user: dict = Depends(get_current_user)):
    """Temporary debug endpoint to elevate privileges."""
    db = get_supabase()
    db.table("users").update({"role": "admin"}).eq("id", current_user["sub"]).execute()
    return {"message": "You are now an admin. Please log out and back in to refresh your token."}


@router.get("/users", response_model=List[UserOut])
async def list_users(admin_user: dict = Depends(get_admin_user)):
    """Admin only: list all users."""
    db = get_supabase()
    result = db.table("users").select("id, email, name, role").execute()
    return result.data or []


@router.put("/users/{user_id}", response_model=UserOut)
async def update_user(user_id: str, updates: UserUpdateAdmin, admin_user: dict = Depends(get_admin_user)):
    """Admin only: update any user's profile or role."""
    db = get_supabase()
    
    # Check if exists
    result = db.table("users").select("*").eq("id", user_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="User not found")
        
    row = result.data[0]
    new_data = {
        "name": updates.name if updates.name is not None else row["name"],
        "email": updates.email if updates.email is not None else row["email"],
        "role": updates.role if updates.role is not None else row["role"],
    }
    
    if updates.password:
        new_data["password_hash"] = get_password_hash(updates.password)
        
    db.table("users").update(new_data).eq("id", user_id).execute()
    
    return {"id": user_id, "email": new_data["email"], "name": new_data["name"], "role": new_data["role"]}


@router.delete("/users/{user_id}")
async def delete_user(user_id: str, admin_user: dict = Depends(get_admin_user)):
    """Admin only: delete a user."""
    db = get_supabase()
    db.table("users").delete().eq("id", user_id).execute()
    return {"message": "User deleted"}


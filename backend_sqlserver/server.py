"""
Temple Feedback Management System - SQL Server Backend
========================================================
FastAPI backend with SQL Server database support
"""

from fastapi import FastAPI, HTTPException, Depends, Header, UploadFile, File, Form, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from jose import JWTError, jwt
import bcrypt
import pyodbc
import uuid
import os
import json
import logging
import aiofiles
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database Configuration
DB_SERVER = os.environ.get('DB_SERVER', 'DESKTOP-JGCUNUE\\SQLEXPRESS')
DB_NAME = os.environ.get('DB_NAME', 'ts_feedbackdb')
DB_USER = os.environ.get('DB_USER', 'ts_feedback_user')
DB_PASSWORD = os.environ.get('DB_PASSWORD', 'TsFeedback@2026!')

# Connection string (Azure SQL compatible)
CONNECTION_STRING = (
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    f"SERVER={DB_SERVER};"
    f"DATABASE={DB_NAME};"
    f"UID={DB_USER};"
    f"PWD={DB_PASSWORD};"
    "Encrypt=yes;"
    "TrustServerCertificate=no;"
    "Connection Timeout=30;"
)

# JWT Configuration
SECRET_KEY = os.environ.get('JWT_SECRET', 'temple_feedback_secret_key_2026')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# Password hashing
# Use direct bcrypt; enforce 72-byte truncation for algorithm compatibility.
BCRYPT_ROUNDS = 12

# File upload configuration
UPLOAD_DIR = os.environ.get('UPLOAD_DIR', 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(f"{UPLOAD_DIR}/logos", exist_ok=True)
os.makedirs(f"{UPLOAD_DIR}/videos", exist_ok=True)

# Initialize FastAPI
app = FastAPI(title="Temple Feedback System API", version="2.0.0")

# CORS Configuration
_default_cors = (
    'http://localhost:3000,'
    'http://localhost:8080,'
    'http://localhost,'
    'https://localhost,'
    'capacitor://localhost,'
    'https://yellow-ocean-07bef8000.1.azurestaticapps.net,'
    'https://aatreyainfo-feedback-fefbeqcve3dahrg2.centralindia-01.azurewebsites.net,'
    'https://aatreya.org,'
    'https://www.aatreya.org'
)
_required_cors = {
    'http://localhost',
    'https://localhost',
    'capacitor://localhost',
    'https://yellow-ocean-07bef8000.1.azurestaticapps.net',
    'https://aatreyainfo-feedback-fefbeqcve3dahrg2.centralindia-01.azurewebsites.net',
    'https://aatreya.org',
    'https://www.aatreya.org',
}
_env_cors = os.environ.get('CORS_ORIGINS', '')
cors_origins = sorted({
    origin.strip()
    for origin in f"{_default_cors},{_env_cors}".split(',')
    if origin.strip()
}.union(_required_cors))
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Range", "Accept-Ranges", "Content-Length", "Content-Disposition"],
)

# Mount static files
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# =====================================================
# DATABASE HELPER FUNCTIONS
# =====================================================

def get_db_connection():
    """Get database connection"""
    try:
        conn = pyodbc.connect(CONNECTION_STRING)
        return conn
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise HTTPException(status_code=500, detail="Database connection failed")

def execute_query(query: str, params: tuple = None, fetch_one: bool = False, fetch_all: bool = False):
    """Execute a SQL query"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        if fetch_one:
            row = cursor.fetchone()
            if row:
                columns = [column[0] for column in cursor.description]
                return dict(zip(columns, row))
            return None
        elif fetch_all:
            rows = cursor.fetchall()
            columns = [column[0] for column in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
        else:
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"Query error: {e}")
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

# =====================================================
# PYDANTIC MODELS
# =====================================================

class UserLogin(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user: dict

class TempleCreate(BaseModel):
    name: str
    location: str
    email: Optional[str] = None
    logo_path: Optional[str] = None

class TempleUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    email: Optional[str] = None
    logo_path: Optional[str] = None

class OfficerCreate(BaseModel):
    name: str
    email: str
    password: str
    temple_id: Optional[str] = None
    role: Optional[str] = "officer"
    permissions: Optional[List[str]] = ["view_feedback", "update_status"]

class OfficerRoleUpdate(BaseModel):
    role: str
    permissions: List[str]

class FeedbackCreate(BaseModel):
    temple_id: str
    user_name: str
    user_mobile: str
    service: str
    rating: int
    message: Optional[str] = None
    video_url: Optional[str] = None

class FeedbackStatusUpdate(BaseModel):
    status: str
    resolution_notes: Optional[str] = None
    officer_notes: Optional[str] = None

class FeedbackAssign(BaseModel):
    officer_id: str

# =====================================================
# HELPER FUNCTIONS
# =====================================================

def hash_password(password: str) -> str:
    password_bytes = password.encode('utf-8', errors='ignore')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt(rounds=BCRYPT_ROUNDS))
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        password_bytes = plain_password.encode('utf-8', errors='ignore')
        if len(password_bytes) > 72:
            password_bytes = password_bytes[:72]

        return bcrypt.checkpw(password_bytes, hashed_password.encode('utf-8'))
    except (ValueError, TypeError) as e:
        logger.error(f"Password verify error: {e}")
        return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def generate_complaint_id():
    """Generate unique complaint ID"""
    count = execute_query("SELECT COUNT(*) as count FROM feedback", fetch_one=True)
    num = (count['count'] if count else 0) + 1
    return f"TF{str(num).zfill(5)}"

# =====================================================
# AUTHENTICATION DEPENDENCIES
# =====================================================

async def get_current_admin(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing token")
    
    try:
        token = authorization.replace("Bearer ", "")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        role = payload.get("role")
        
        if role != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        
        return {"id": user_id, "role": role}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_current_officer(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing token")
    
    try:
        token = authorization.replace("Bearer ", "")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        role = payload.get("role")
        
        if role != "officer":
            raise HTTPException(status_code=403, detail="Officer access required")
        
        officer = execute_query("SELECT * FROM officers WHERE id = ?", (user_id,), fetch_one=True)
        return officer
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# =====================================================
# AUTH ENDPOINTS
# =====================================================

@app.get("/api/auth/login")
async def login_help():
    """Login helper for browser GETs"""
    return {
        "message": "Use POST /api/auth/login with JSON {\"email\":..., \"password\":...} to authenticate"
    }

@app.post("/api/auth/login")
@app.post("/api/auth/admin/login")
async def login(user_data: UserLogin):
    """Admin login"""
    user = execute_query(
        "SELECT * FROM users WHERE email = ?",
        (user_data.email,),
        fetch_one=True
    )
    
    if not user or not verify_password(user_data.password, user['password']):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token(
        data={"sub": str(user['id']), "role": user['role']}
    )
    
    return {
        "access_token": access_token,
        "token": access_token,
        "token_type": "bearer",
        "user": {
            "id": str(user['id']),
            "email": user['email'],
            "role": user['role']
        }
    }

@app.post("/api/auth/officer/login")
async def officer_login(user_data: UserLogin):
    """Officer login"""
    officer = execute_query(
        "SELECT * FROM officers WHERE email = ?",
        (user_data.email,),
        fetch_one=True
    )
    
    if not officer or not verify_password(user_data.password, officer['password']):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token(
        data={"sub": str(officer['id']), "role": "officer"}
    )
    
    return {
        "access_token": access_token,
        "token": access_token,
        "token_type": "bearer",
        "user": {
            "id": str(officer['id']),
            "email": officer['email'],
            "role": "officer",
            "officer": {
                "name": officer['name'],
                "temple_id": str(officer['temple_id']) if officer['temple_id'] else None,
                "temple_name": officer['temple_name']
            }
        }
    }

# =====================================================
# TEMPLE ENDPOINTS
# =====================================================

@app.get("/api/temples")
async def get_temples():
    """Get all temples"""
    temples = execute_query("SELECT * FROM temples ORDER BY created_at DESC", fetch_all=True)
    return [
        {
            "id": str(t['id']),
            "name": t['name'],
            "location": t['location'],
            "email": t['email'],
            "logo_path": t['logo_path'],
            "officer_id": str(t['officer_id']) if t['officer_id'] else None,
            "created_at": t['created_at'].isoformat() if t['created_at'] else None
        }
        for t in temples
    ]

@app.post("/api/temples")
async def create_temple(temple: TempleCreate, current_admin = Depends(get_current_admin)):
    """Create a new temple"""
    temple_id = str(uuid.uuid4())
    
    execute_query(
        "INSERT INTO temples (id, name, location, email, logo_path) VALUES (?, ?, ?, ?, ?)",
        (temple_id, temple.name, temple.location, temple.email, temple.logo_path)
    )
    
    return {
        "id": temple_id,
        "name": temple.name,
        "location": temple.location,
        "email": temple.email,
        "logo_path": temple.logo_path,
        "message": "Temple created successfully"
    }

@app.get("/api/temples/{temple_id}")
async def get_temple(temple_id: str):
    """Get temple by ID"""
    temple = execute_query("SELECT * FROM temples WHERE id = ?", (temple_id,), fetch_one=True)
    if not temple:
        raise HTTPException(status_code=404, detail="Temple not found")
    
    return {
        "id": str(temple['id']),
        "name": temple['name'],
        "location": temple['location'],
        "email": temple['email'],
        "logo_path": temple['logo_path'],
        "officer_id": str(temple['officer_id']) if temple['officer_id'] else None,
        "created_at": temple['created_at'].isoformat() if temple['created_at'] else None
    }

@app.get("/api/temples/by-email/{email}")
async def get_temple_by_email(email: str):
    """Get temple by email"""
    temple = execute_query("SELECT * FROM temples WHERE email = ?", (email,), fetch_one=True)
    if not temple:
        raise HTTPException(status_code=404, detail="Temple not found")
    
    return {
        "id": str(temple['id']),
        "name": temple['name'],
        "location": temple['location'],
        "email": temple['email'],
        "logo_path": temple['logo_path']
    }

@app.put("/api/temples/{temple_id}")
async def update_temple(temple_id: str, temple: TempleUpdate, current_admin = Depends(get_current_admin)):
    """Update temple"""
    updates = []
    params = []
    
    if temple.name:
        updates.append("name = ?")
        params.append(temple.name)
    if temple.location:
        updates.append("location = ?")
        params.append(temple.location)
    if temple.email:
        updates.append("email = ?")
        params.append(temple.email)
    if temple.logo_path:
        updates.append("logo_path = ?")
        params.append(temple.logo_path)
    
    if updates:
        updates.append("updated_at = GETUTCDATE()")
        params.append(temple_id)
        query = f"UPDATE temples SET {', '.join(updates)} WHERE id = ?"
        execute_query(query, tuple(params))
    
    return {"message": "Temple updated successfully"}

@app.delete("/api/temples/{temple_id}")
async def delete_temple(temple_id: str, current_admin = Depends(get_current_admin)):
    """Delete temple"""
    execute_query("DELETE FROM temples WHERE id = ?", (temple_id,))
    return {"message": "Temple deleted successfully"}

@app.post("/api/temples/{temple_id}/logo")
async def upload_temple_logo(temple_id: str, file: UploadFile = File(...), current_admin = Depends(get_current_admin)):
    """Upload temple logo"""
    filename = f"{uuid.uuid4()}{os.path.splitext(file.filename)[1]}"
    file_path = f"logos/{filename}"
    full_path = f"{UPLOAD_DIR}/{file_path}"
    
    async with aiofiles.open(full_path, 'wb') as f:
        content = await file.read()
        await f.write(content)
    
    execute_query(
        "UPDATE temples SET logo_path = ?, updated_at = GETUTCDATE() WHERE id = ?",
        (file_path, temple_id)
    )
    
    return {"logo_path": file_path}

# =====================================================
# TABLET REGISTRATION (FIX YOUR ERROR)
# =====================================================

class RegisterTablet(BaseModel):
    email: str

@app.post("/api/register-tablet")
async def register_tablet(data: RegisterTablet):
    """Register tablet using temple email"""

    temple = execute_query(
        "SELECT * FROM temples WHERE email = ?",
        (data.email,),
        fetch_one=True
    )

    if not temple:
        raise HTTPException(status_code=404, detail="Temple not found")

    return {
        "temple_id": str(temple['id']),
        "temple_name": temple['name'],
        "message": "Tablet registered successfully"
    }    

# =====================================================
# OFFICER ENDPOINTS
# =====================================================

@app.get("/api/officers")
async def get_officers():
    """Get all officers"""
    officers = execute_query("SELECT * FROM officers ORDER BY created_at DESC", fetch_all=True)
    return [
        {
            "id": str(o['id']),
            "name": o['name'],
            "email": o['email'],
            "temple_id": str(o['temple_id']) if o['temple_id'] else None,
            "temple_name": o['temple_name'],
            "role": o['role'] or 'officer',
            "permissions": json.loads(o['permissions']) if o['permissions'] else ['view_feedback', 'update_status'],
            "created_at": o['created_at'].isoformat() if o['created_at'] else None
        }
        for o in officers
    ]

@app.post("/api/officers")
async def create_officer(officer: OfficerCreate, current_admin = Depends(get_current_admin)):
    """Create a new officer"""
    # Check if email exists
    existing = execute_query("SELECT id FROM officers WHERE email = ?", (officer.email,), fetch_one=True)
    if existing:
        raise HTTPException(status_code=400, detail="Email already exists")
    
    # Get temple name
    temple_name = None
    if officer.temple_id:
        temple = execute_query("SELECT name FROM temples WHERE id = ?", (officer.temple_id,), fetch_one=True)
        if temple:
            temple_name = temple['name']
    
    officer_id = str(uuid.uuid4())
    hashed_pw = hash_password(officer.password)
    permissions_json = json.dumps(officer.permissions or ['view_feedback', 'update_status'])
    
    execute_query(
        """INSERT INTO officers (id, name, email, password, temple_id, temple_name, role, permissions)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (officer_id, officer.name, officer.email, hashed_pw, officer.temple_id, temple_name, officer.role or 'officer', permissions_json)
    )
    
    return {
        "id": officer_id,
        "name": officer.name,
        "email": officer.email,
        "temple_name": temple_name,
        "role": officer.role,
        "message": "Officer created successfully"
    }

@app.put("/api/officers/{officer_id}/role")
async def update_officer_role(officer_id: str, role_update: OfficerRoleUpdate, current_admin = Depends(get_current_admin)):
    """Update officer role and permissions"""
    permissions_json = json.dumps(role_update.permissions)
    
    execute_query(
        "UPDATE officers SET role = ?, permissions = ?, updated_at = GETUTCDATE() WHERE id = ?",
        (role_update.role, permissions_json, officer_id)
    )
    
    return {"message": "Role updated successfully"}

@app.delete("/api/officers/{officer_id}")
async def delete_officer(officer_id: str, current_admin = Depends(get_current_admin)):
    """Delete officer"""
    execute_query("DELETE FROM officers WHERE id = ?", (officer_id,))
    return {"message": "Officer deleted successfully"}

# =====================================================
# SERVICE ENDPOINTS
# =====================================================

@app.get("/api/services")
async def get_services():
    """Get all services"""
    services = execute_query("SELECT * FROM services WHERE is_active = 1 ORDER BY display_order", fetch_all=True)
    return [
        {
            "id": str(s['id']),
            "name": s['name'],
            "order": s['display_order'],
            "created_at": s['created_at'].isoformat() if s['created_at'] else None
        }
        for s in services
    ]

@app.post("/api/services")
async def create_service(name: str = Query(...), current_admin = Depends(get_current_admin)):
    """Create a new service"""
    # Get max order
    max_order = execute_query("SELECT MAX(display_order) as max_order FROM services", fetch_one=True)
    order = (max_order['max_order'] or 0) + 1
    
    service_id = str(uuid.uuid4())
    
    execute_query(
        "INSERT INTO services (id, name, display_order) VALUES (?, ?, ?)",
        (service_id, name, order)
    )
    
    return {
        "id": service_id,
        "name": name,
        "order": order
    }

@app.delete("/api/services/{service_id}")
async def delete_service(service_id: str, current_admin = Depends(get_current_admin)):
    """Delete service"""
    execute_query("DELETE FROM services WHERE id = ?", (service_id,))
    return {"message": "Service deleted successfully"}

# =====================================================
# FEEDBACK ENDPOINTS
# =====================================================

@app.get("/api/feedback")
async def get_feedback(
    temple_id: Optional[str] = None,
    status: Optional[str] = None,
    officer_id: Optional[str] = None
):
    """Get all feedback with filters"""
    query = "SELECT * FROM feedback WHERE 1=1"
    params = []
    
    if temple_id:
        query += " AND temple_id = ?"
        params.append(temple_id)
    if status:
        query += " AND status = ?"
        params.append(status)
    if officer_id:
        query += " AND officer_id = ?"
        params.append(officer_id)
    
    query += " ORDER BY created_at DESC"
    
    feedback_list = execute_query(query, tuple(params) if params else None, fetch_all=True)
    
    return [
        {
            "id": str(f['id']),
            "complaint_id": f['complaint_id'],
            "temple_id": str(f['temple_id']) if f['temple_id'] else None,
            "temple_name": f['temple_name'],
            "user_name": f['user_name'],
            "user_mobile": f['user_mobile'],
            "service": f['service'],
            "rating": f['rating'],
            "message": f['message'],
            "video_url": f.get('video_url') or f.get('video_path'),
            "video_path": f.get('video_url') or f.get('video_path'),
            "status": f['status'],
            "officer_id": str(f['officer_id']) if f['officer_id'] else None,
            "officer_name": f['officer_name'],
            "assigned_officer_id": str(f['officer_id']) if f['officer_id'] else None,
            "assigned_officer_name": f['officer_name'],
            "resolution_notes": f['resolution_notes'],
            "officer_notes": f.get('officer_notes') or f.get('resolution_notes'),
            "created_at": f['created_at'].isoformat() if f['created_at'] else None,
            "resolved_at": f['resolved_at'].isoformat() if f['resolved_at'] else None
        }
        for f in feedback_list
    ]


@app.get("/api/feedback/officer")
async def get_officer_feedback(current_officer = Depends(get_current_officer)):
    """Get feedback assigned to current officer"""
    officer_id = str(current_officer['id'])
    return await get_feedback(officer_id=officer_id)

@app.post("/api/feedback")
async def create_feedback(feedback: FeedbackCreate):
    """Submit new feedback"""
    feedback_id = str(uuid.uuid4())
    complaint_id = generate_complaint_id()
    
    # Get temple name
    temple = execute_query("SELECT name FROM temples WHERE id = ?", (feedback.temple_id,), fetch_one=True)
    temple_name = temple['name'] if temple else None
    
    execute_query(
        """INSERT INTO feedback (id, complaint_id, temple_id, temple_name, user_name, user_mobile, service, rating, message, video_url)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (feedback_id, complaint_id, feedback.temple_id, temple_name, feedback.user_name, 
         feedback.user_mobile, feedback.service, feedback.rating, feedback.message, feedback.video_url)
    )
    
    # Log WhatsApp notification (mocked)
    whatsapp_id = str(uuid.uuid4())
    message = f"Thank you for your feedback! Your complaint ID is {complaint_id}. We will resolve it soon."
    execute_query(
        "INSERT INTO whatsapp_logs (id, feedback_id, phone_number, message, status, message_type) VALUES (?, ?, ?, ?, ?, ?)",
        (whatsapp_id, feedback_id, feedback.user_mobile, message, 'Sent', 'notification')
    )    
    return {
        "id": feedback_id,
        "complaint_id": complaint_id,
        "video_path": feedback.video_url,
        "message": "Feedback submitted successfully"
    }

@app.post("/api/feedback/with-video")
async def create_feedback_with_video(
    temple_id: str = Form(...),
    user_name: str = Form(...),
    user_mobile: str = Form(...),
    service: str = Form(...),
    rating: int = Form(...),
    message: Optional[str] = Form(None),
    video: UploadFile = File(...)
):
    """Submit feedback with video"""
    # Save video
    video_filename = f"{uuid.uuid4()}{os.path.splitext(video.filename)[1]}"
    video_path = f"videos/{video_filename}"
    full_path = f"{UPLOAD_DIR}/{video_path}"
    
    async with aiofiles.open(full_path, 'wb') as f:
        content = await video.read()
        await f.write(content)
    
    feedback_id = str(uuid.uuid4())
    complaint_id = generate_complaint_id()
    
    # Get temple name
    temple = execute_query("SELECT name FROM temples WHERE id = ?", (temple_id,), fetch_one=True)
    temple_name = temple['name'] if temple else None
    
    execute_query(
        """INSERT INTO feedback (id, complaint_id, temple_id, temple_name, user_name, user_mobile, service, rating, message, video_url)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (feedback_id, complaint_id, temple_id, temple_name, user_name, user_mobile, service, rating, message, video_path)
    )
    
    # Log WhatsApp notification (mocked)
    whatsapp_id = str(uuid.uuid4())
    whatsapp_message = f"Thank you for your feedback! Your complaint ID is {complaint_id}. We will resolve it soon."
    execute_query(
        "INSERT INTO whatsapp_logs (id, feedback_id, phone_number, message, status, message_type) VALUES (?, ?, ?, ?, ?, ?)",
        (whatsapp_id, feedback_id, user_mobile, whatsapp_message, 'Sent', 'notification')
    )
    
    return {
        "id": feedback_id,
        "complaint_id": complaint_id,
        "video_url": video_path,
        "video_path": video_path,
        "message": "Feedback submitted successfully"
    }

@app.put("/api/feedback/{feedback_id}/status")
async def update_feedback_status(feedback_id: str, status_update: FeedbackStatusUpdate, authorization: str = Header(None)):
    """Update feedback status by admin or assigned officer"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing token")

    try:
        token = authorization.replace("Bearer ", "")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user_id = payload.get("sub")
    role = payload.get("role")

    if role not in ["admin", "officer"]:
        raise HTTPException(status_code=403, detail="Access denied")

    if role == "officer":
        assigned = execute_query("SELECT officer_id FROM feedback WHERE id = ?", (feedback_id,), fetch_one=True)
        if not assigned or not assigned.get("officer_id") or str(assigned.get("officer_id")) != str(user_id):
            raise HTTPException(status_code=403, detail="Officer can update only assigned feedback")

    notes_value = status_update.resolution_notes or status_update.officer_notes
    resolved_at = "GETUTCDATE()" if status_update.status == 'Resolved' else "NULL"

    execute_query(
        f"""UPDATE feedback 
            SET status = ?, resolution_notes = ?, officer_notes = ?, resolved_at = {resolved_at}, updated_at = GETUTCDATE() 
            WHERE id = ?""",
        (status_update.status, notes_value, status_update.officer_notes, feedback_id)
    )
    
    # Get feedback details for WhatsApp
    feedback = execute_query("SELECT * FROM feedback WHERE id = ?", (feedback_id,), fetch_one=True)
    if feedback:
        whatsapp_id = str(uuid.uuid4())
        message = f"Your complaint {feedback['complaint_id']} has been updated to: {status_update.status}"
        execute_query(
            "INSERT INTO whatsapp_logs (id, feedback_id, phone_number, message, status, message_type) VALUES (?, ?, ?, ?, ?, ?)",
            (whatsapp_id, feedback_id, feedback['user_mobile'], message, 'Sent', 'status_update')
        )
    
    return {"message": "Status updated successfully"}

@app.put("/api/feedback/{feedback_id}/assign")
async def assign_officer(feedback_id: str, assign: FeedbackAssign, current_admin = Depends(get_current_admin)):
    """Assign officer to feedback"""
    # Get officer name
    officer = execute_query("SELECT name FROM officers WHERE id = ?", (assign.officer_id,), fetch_one=True)
    officer_name = officer['name'] if officer else None
    
    execute_query(
        """UPDATE feedback 
           SET officer_id = ?, officer_name = ?, status = 'In Progress', updated_at = GETUTCDATE() 
           WHERE id = ?""",
        (assign.officer_id, officer_name, feedback_id)
    )
    
    return {"message": "Officer assigned successfully"}

# =====================================================
# STATS ENDPOINTS
# =====================================================

@app.get("/api/stats")
async def get_stats(current_admin = Depends(get_current_admin)):
    """Get dashboard statistics"""
    stats = {
        "total_temples": execute_query("SELECT COUNT(*) as count FROM temples", fetch_one=True)['count'],
        "total_officers": execute_query("SELECT COUNT(*) as count FROM officers", fetch_one=True)['count'],
        "total_feedback": execute_query("SELECT COUNT(*) as count FROM feedback", fetch_one=True)['count'],
        "pending": execute_query("SELECT COUNT(*) as count FROM feedback WHERE status = 'Pending'", fetch_one=True)['count'],
        "in_progress": execute_query("SELECT COUNT(*) as count FROM feedback WHERE status = 'In Progress'", fetch_one=True)['count'],
        "resolved": execute_query("SELECT COUNT(*) as count FROM feedback WHERE status = 'Resolved'", fetch_one=True)['count'],
        "rejected": execute_query("SELECT COUNT(*) as count FROM feedback WHERE status = 'Rejected'", fetch_one=True)['count'],
    }
    
    # Temple-wise feedback
    temple_stats = execute_query(
        """SELECT t.name as temple, COUNT(f.id) as feedback
           FROM temples t
           LEFT JOIN feedback f ON t.id = f.temple_id
           GROUP BY t.id, t.name
           ORDER BY feedback DESC""",
        fetch_all=True
    )
    
    stats["temple_stats"] = [{"_id": t["temple"], "count": t["feedback"]} for t in temple_stats]
    
    return stats


@app.get("/api/dashboard/stats")
async def get_dashboard_stats(current_admin = Depends(get_current_admin)):
    """Alias endpoint for dashboard statistics"""
    return await get_stats(current_admin)

    
    return stats

@app.get("/api/officer/stats")
async def get_officer_stats(current_officer = Depends(get_current_officer)):
    """Get officer-specific statistics"""
    officer_id = str(current_officer['id'])
    
    stats = {
        "total_assigned": execute_query(
            "SELECT COUNT(*) as count FROM feedback WHERE officer_id = ?",
            (officer_id,), fetch_one=True
        )['count'],
        "pending": execute_query(
            "SELECT COUNT(*) as count FROM feedback WHERE officer_id = ? AND status = 'Pending'",
            (officer_id,), fetch_one=True
        )['count'],
        "in_progress": execute_query(
            "SELECT COUNT(*) as count FROM feedback WHERE officer_id = ? AND status = 'In Progress'",
            (officer_id,), fetch_one=True
        )['count'],
        "resolved": execute_query(
            "SELECT COUNT(*) as count FROM feedback WHERE officer_id = ? AND status = 'Resolved'",
            (officer_id,), fetch_one=True
        )['count'],
    }
    
    return stats


@app.get("/api/dashboard/officer-stats")
async def get_dashboard_officer_stats(current_officer = Depends(get_current_officer)):
    """Alias endpoint for officer dashboard stats"""
    return await get_officer_stats(current_officer)

# =====================================================
# WHATSAPP LOGS ENDPOINTS
# =====================================================

@app.get("/api/whatsapp-logs")
async def get_whatsapp_logs(current_admin = Depends(get_current_admin)):
    """Get all WhatsApp logs"""
    logs = execute_query("SELECT * FROM whatsapp_logs ORDER BY created_at DESC", fetch_all=True)
    return [
        {
            "id": str(log['id']),
            "feedback_id": str(log['feedback_id']) if log['feedback_id'] else None,
            "phone_number": log['phone_number'],
            "message": log['message'],
            "status": log['status'],
            "message_type": log['message_type'],
            "created_at": log['created_at'].isoformat() if log['created_at'] else None
        }
        for log in logs
    ]


@app.get("/api/whatsapp/logs")
async def get_whatsapp_logs_alias(current_admin = Depends(get_current_admin)):
    """Alias endpoint used by frontend"""
    logs = await get_whatsapp_logs(current_admin)
    return [
        {
            **log,
            "mobile": log.get("phone_number"),
            "sent_at": log.get("created_at"),
        }
        for log in logs
    ]

# =====================================================
# FILE ENDPOINTS
# =====================================================

@app.post("/upload/logo")
async def upload_logo(file: UploadFile = File(...), authorization: str = Header(None)):
    """Upload temple logo using frontend upload flow"""
    # Optional auth check for admin/officer token
    if authorization:
        token = authorization.replace("Bearer ", "")
        try:
            jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid token")

    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ['.png', '.jpg', '.jpeg', '.gif']:
        raise HTTPException(status_code=400, detail="Invalid file type")

    file_content = await file.read()
    if len(file_content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large")

    output_name = f"logos/{uuid.uuid4()}{file_ext}"
    path = os.path.join(UPLOAD_DIR, output_name)
    os.makedirs(os.path.dirname(path), exist_ok=True)

    async with aiofiles.open(path, 'wb') as f:
        await f.write(file_content)

    # Log upload in DB file_uploads table
    uploaded_by = None
    if authorization:
        try:
            payload = jwt.decode(authorization.replace('Bearer ', ''), SECRET_KEY, algorithms=[ALGORITHM])
            uploaded_by = payload.get('sub')
        except JWTError:
            uploaded_by = None

    execute_query(
        "INSERT INTO file_uploads (id, filename, original_filename, file_path, file_type, file_size, uploaded_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, GETUTCDATE())",
        (str(uuid.uuid4()), os.path.basename(path), file.filename, output_name, file_ext, len(file_content), uploaded_by)
    )

    return {"path": output_name}


@app.post("/api/upload/logo")
async def api_upload_logo(file: UploadFile = File(...), authorization: str = Header(None)):
    """Upload temple logo using frontend upload flow with /api prefix"""
    return await upload_logo(file, authorization)


@app.post("/upload/video")
async def upload_video(file: UploadFile = File(...), authorization: str = Header(None)):
    """Upload recorded feedback video"""
    if authorization:
        token = authorization.replace("Bearer ", "")
        try:
            jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid token")

    file_ext = os.path.splitext(file.filename)[1].lower() or '.webm'
    if file_ext not in ['.webm', '.mp4', '.mov', '.mkv']:
        raise HTTPException(status_code=400, detail="Invalid video type")

    file_content = await file.read()
    if len(file_content) > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large")

    output_name = f"videos/{uuid.uuid4()}{file_ext}"
    path = os.path.join(UPLOAD_DIR, output_name)
    os.makedirs(os.path.dirname(path), exist_ok=True)

    async with aiofiles.open(path, 'wb') as f:
        await f.write(file_content)

    uploaded_by = None
    if authorization:
        try:
            payload = jwt.decode(authorization.replace('Bearer ', ''), SECRET_KEY, algorithms=[ALGORITHM])
            uploaded_by = payload.get('sub')
        except JWTError:
            uploaded_by = None

    execute_query(
        "INSERT INTO file_uploads (id, filename, original_filename, file_path, file_type, file_size, uploaded_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, GETUTCDATE())",
        (str(uuid.uuid4()), os.path.basename(path), file.filename, output_name, file_ext, len(file_content), uploaded_by)
    )

    return {"path": output_name}


@app.post("/api/upload/video")
async def api_upload_video(file: UploadFile = File(...), authorization: str = Header(None)):
    """Upload video with /api prefix"""
    return await upload_video(file, authorization)


@app.get("/api/files/{file_path:path}")
async def get_file(file_path: str, request: Request):
    """Serve uploaded files with Range request support for video streaming"""
    full_path = os.path.join(UPLOAD_DIR, file_path)
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="File not found")

    ext = os.path.splitext(file_path)[1].lower()
    media_type = 'application/octet-stream'
    if ext == '.webm':
        media_type = 'video/webm'
    elif ext == '.mp4':
        media_type = 'video/mp4'
    elif ext in ['.jpg', '.jpeg']:
        media_type = 'image/jpeg'
    elif ext == '.png':
        media_type = 'image/png'
    elif ext == '.gif':
        media_type = 'image/gif'

    file_size = os.path.getsize(full_path)
    range_header = request.headers.get('range')

    if range_header and media_type.startswith('video/'):
        # Parse Range header e.g. "bytes=0-1023"
        try:
            byte_range = range_header.replace('bytes=', '')
            start_str, end_str = byte_range.split('-')
            start = int(start_str)
            end = int(end_str) if end_str else file_size - 1
            end = min(end, file_size - 1)
            chunk_size = end - start + 1

            def iter_file():
                with open(full_path, 'rb') as f:
                    f.seek(start)
                    remaining = chunk_size
                    while remaining > 0:
                        data = f.read(min(65536, remaining))
                        if not data:
                            break
                        remaining -= len(data)
                        yield data

            headers = {
                'Content-Range': f'bytes {start}-{end}/{file_size}',
                'Accept-Ranges': 'bytes',
                'Content-Length': str(chunk_size),
            }
            return StreamingResponse(iter_file(), status_code=206, media_type=media_type, headers=headers)
        except Exception:
            pass  # Fall through to normal FileResponse

    return FileResponse(full_path, media_type=media_type, headers={'Accept-Ranges': 'bytes'})

# =====================================================
# STARTUP
# =====================================================

@app.on_event("startup")
async def startup():
    """Initialize on startup"""
    logger.info("=" * 50)
    logger.info("Temple Feedback System API - SQL Server")
    logger.info(f"Database: {DB_NAME}")
    logger.info(f"Server: {DB_SERVER}")
    logger.info("=" * 50)
    
    # Test database connection
    try:
        conn = get_db_connection()
        conn.close()
        logger.info("Database connection successful!")

        # Ensure default services (seva) exist
        # Ensure officer_notes column exists for feedback updates from officer dashboard.
        execute_query(
            """
            IF COL_LENGTH('feedback', 'officer_notes') IS NULL
            BEGIN
                ALTER TABLE feedback ADD officer_notes NVARCHAR(MAX) NULL;
            END
            """
        )

        default_services = [
            'Annadhanam', 'Darshan', 'Prasadam', 'Pooja', 'Donation', 'Seva', 'Other', 'General'
        ]
        for s in default_services:
            existing = execute_query("SELECT id FROM services WHERE name = ?", (s,), fetch_one=True)
            if not existing:
                service_id = str(uuid.uuid4())
                execute_query("INSERT INTO services (id, name, display_order, is_active) VALUES (?, ?, ?, ?)", (service_id, s, 0, 1))

    except Exception as e:
        logger.error(f"Database connection failed: {e}")

@app.get("/")
async def root():
    return {"message": "Temple Feedback System API - SQL Server Version", "status": "running"}

@app.get("/api/health")
async def health():
    return {"status": "healthy", "database": "SQL Server"}

# =====================================================
# RUN SERVER
# =====================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

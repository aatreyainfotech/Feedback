"""
Temple Feedback Management System - SQL Server Backend
========================================================
FastAPI backend with SQL Server database support
"""

from fastapi import FastAPI, HTTPException, Depends, Header, UploadFile, File, Form, Query, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response, StreamingResponse
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
from urllib.parse import urlparse, unquote
from dotenv import load_dotenv

from backfill_upload_blobs import run_backfill

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
# On Azure App Service, WEBSITE_SITE_NAME is set; use /home/uploads so files
# persist across deployments (Azure Files mount). Fall back to 'uploads' locally.
_azure_site = os.environ.get('WEBSITE_SITE_NAME')
_default_upload_dir = '/home/uploads' if _azure_site else 'uploads'
UPLOAD_DIR = os.environ.get('UPLOAD_DIR', _default_upload_dir)
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(f"{UPLOAD_DIR}/logos", exist_ok=True)
os.makedirs(f"{UPLOAD_DIR}/videos", exist_ok=True)

SERVER_DIR = os.path.dirname(os.path.abspath(__file__))
_upload_roots = [
    UPLOAD_DIR,
    os.path.join(SERVER_DIR, 'uploads'),
    os.path.join(os.getcwd(), 'uploads'),
]
if _azure_site:
    _upload_roots.extend([
        '/home/site/wwwroot/uploads',
    ])
UPLOAD_ROOTS = list(dict.fromkeys(os.path.abspath(path) for path in _upload_roots if path))
BACKFILL_JOBS: dict[str, dict] = {}


def normalize_upload_path(file_path: str) -> str:
    """Convert stored upload values into a safe relative path under uploads."""
    if not file_path:
        raise HTTPException(status_code=404, detail="File not found")

    parsed = urlparse(str(file_path))
    raw_path = parsed.path or str(file_path)
    normalized = unquote(raw_path).replace('\\', '/').strip()

    api_marker = '/api/files/'
    uploads_marker = '/uploads/'
    if api_marker in normalized:
        normalized = normalized.split(api_marker, 1)[1]
    elif uploads_marker in normalized:
        normalized = normalized.split(uploads_marker, 1)[1]

    normalized = normalized.lstrip('/')
    while normalized.startswith('uploads/'):
        normalized = normalized[len('uploads/'):]

    normalized = os.path.normpath(normalized).replace('\\', '/')
    if normalized in ('', '.'):
        raise HTTPException(status_code=404, detail="File not found")
    if normalized.startswith('../') or normalized == '..' or os.path.isabs(normalized):
        raise HTTPException(status_code=400, detail="Invalid file path")

    return normalized


def get_primary_upload_path(file_path: str) -> str:
    """Return the canonical location for new uploads."""
    normalized = normalize_upload_path(file_path)
    return os.path.join(UPLOAD_DIR, normalized)


def resolve_existing_upload_path(file_path: str) -> tuple[str, str]:
    """Resolve an uploaded file from the current or legacy storage locations."""
    normalized = normalize_upload_path(file_path)
    for root in UPLOAD_ROOTS:
        candidate = os.path.abspath(os.path.join(root, normalized))
        if os.path.commonpath([root, candidate]) != root:
            continue
        if os.path.exists(candidate):
            return normalized, candidate

    raise HTTPException(status_code=404, detail="File not found")


def get_media_type(file_path: str) -> str:
    """Infer response content type from file extension."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.webm':
        return 'video/webm'
    if ext == '.mp4':
        return 'video/mp4'
    if ext == '.mov':
        return 'video/quicktime'
    if ext == '.mkv':
        return 'video/x-matroska'
    if ext in ['.jpg', '.jpeg']:
        return 'image/jpeg'
    if ext == '.png':
        return 'image/png'
    if ext == '.gif':
        return 'image/gif'
    return 'application/octet-stream'


def save_upload_record(file_path: str, original_filename: str, file_ext: str, file_size: int, uploaded_by: Optional[str], file_content: bytes):
    """Persist upload metadata and a durable SQL copy for Azure retention."""
    normalized_path = normalize_upload_path(file_path)
    execute_query(
        """INSERT INTO file_uploads (
               id, filename, original_filename, file_path, file_type, file_size, uploaded_by, file_blob, created_at
           ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, GETUTCDATE())""",
        (
            str(uuid.uuid4()),
            os.path.basename(normalized_path),
            original_filename,
            normalized_path,
            file_ext,
            file_size,
            uploaded_by,
            pyodbc.Binary(file_content),
        )
    )


def get_upload_blob(file_path: str):
    """Load durable upload content from Azure SQL when the filesystem copy is missing."""
    normalized = normalize_upload_path(file_path)
    normalized_forward_slashes = normalized.replace('\\', '/')
    basename = os.path.basename(normalized)
    return execute_query(
        """SELECT TOP 1 file_blob, file_size, file_type
           FROM file_uploads
           WHERE file_blob IS NOT NULL
             AND (
                 file_path = ?
                 OR REPLACE(file_path, '\\', '/') = ?
                 OR REPLACE(file_path, '\\', '/') LIKE ?
                 OR REPLACE(file_path, '\\', '/') LIKE ?
                 OR filename = ?
             )
           ORDER BY CASE
                        WHEN file_path = ? THEN 0
                        WHEN REPLACE(file_path, '\\', '/') = ? THEN 1
                        WHEN filename = ? THEN 2
                        ELSE 3
                    END,
                    created_at DESC""",
        (
            normalized,
            normalized_forward_slashes,
            f"%/uploads/{normalized_forward_slashes}",
            f"%/{normalized_forward_slashes}",
            basename,
            normalized,
            normalized_forward_slashes,
            basename,
        ),
        fetch_one=True,
    )


def get_bounded_edit_distance(left: str, right: str, max_distance: int = 3) -> Optional[int]:
    """Return a small edit distance for near-matching filenames, otherwise None."""
    if abs(len(left) - len(right)) > max_distance:
        return None

    previous_row = list(range(len(right) + 1))
    for left_index, left_char in enumerate(left, start=1):
        current_row = [left_index]
        smallest_value = left_index
        for right_index, right_char in enumerate(right, start=1):
            substitution_cost = 0 if left_char == right_char else 1
            value = min(
                previous_row[right_index] + 1,
                current_row[right_index - 1] + 1,
                previous_row[right_index - 1] + substitution_cost,
            )
            current_row.append(value)
            if value < smallest_value:
                smallest_value = value

        if smallest_value > max_distance:
            return None
        previous_row = current_row

    distance = previous_row[-1]
    return distance if distance <= max_distance else None


def find_nearest_upload_path(file_path: str, created_at: Optional[datetime] = None) -> Optional[str]:
    """Recover a likely intended upload path when stored feedback paths contain minor typos."""
    normalized = normalize_upload_path(file_path)
    expected_name = os.path.basename(normalized)
    expected_ext = os.path.splitext(expected_name)[1].lower()
    if not expected_name or not expected_ext:
        return None

    params = [f"%{expected_ext}"]
    query = """
        SELECT TOP 200
            file_path,
            created_at,
            CASE WHEN file_blob IS NULL THEN 0 ELSE 1 END AS has_blob
        FROM file_uploads
        WHERE file_path LIKE ?
    """
    if created_at:
        query += """
          AND created_at BETWEEN DATEADD(HOUR, -6, ?) AND DATEADD(HOUR, 6, ?)
        """
        params.extend([created_at, created_at])

    query += " ORDER BY created_at DESC"
    upload_rows = execute_query(query, tuple(params), fetch_all=True)

    best_match = None
    best_distance = None
    best_time_delta = None

    for upload_row in upload_rows:
        candidate_path = upload_row.get('file_path')
        if not candidate_path:
            continue

        try:
            candidate_path = normalize_upload_path(candidate_path)
        except HTTPException:
            continue

        candidate_name = os.path.basename(candidate_path)
        if os.path.splitext(candidate_name)[1].lower() != expected_ext:
            continue

        distance = get_bounded_edit_distance(expected_name, candidate_name)
        if distance is None:
            continue

        try:
            resolve_existing_upload_path(candidate_path)
            available = True
        except HTTPException:
            available = bool(upload_row.get('has_blob'))

        if not available:
            continue

        candidate_created_at = upload_row.get('created_at')
        time_delta = abs((candidate_created_at - created_at).total_seconds()) if candidate_created_at and created_at else float('inf')

        if (
            best_match is None
            or distance < best_distance
            or (distance == best_distance and time_delta < best_time_delta)
        ):
            best_match = candidate_path
            best_distance = distance
            best_time_delta = time_delta

    return best_match


def get_feedback_video_path(feedback_record: dict) -> Optional[str]:
    """Choose the first valid stored video path for a feedback record."""
    candidates = []
    for key in ('video_url', 'video_path'):
        value = feedback_record.get(key)
        if value and value not in candidates:
            candidates.append(value)

    for candidate in candidates:
        try:
            normalized = normalize_upload_path(candidate)
        except HTTPException:
            continue

        try:
            resolve_existing_upload_path(normalized)
            return normalized
        except HTTPException:
            blob_record = get_upload_blob(normalized)
            if blob_record and blob_record.get('file_blob') is not None:
                return normalized

    fallback_created_at = feedback_record.get('created_at')
    for candidate in candidates:
        try:
            repaired_path = find_nearest_upload_path(candidate, fallback_created_at)
        except HTTPException:
            repaired_path = None
        if repaired_path:
            return repaired_path

    return None


def build_blob_response(file_path: str, file_content: bytes, request: Request):
    """Serve SQL-stored content with optional byte range support for videos."""
    media_type = get_media_type(file_path)
    file_size = len(file_content)
    headers = {'Accept-Ranges': 'bytes'}
    range_header = request.headers.get('range')

    if range_header and media_type.startswith('video/') and file_size > 0:
        try:
            byte_range = range_header.replace('bytes=', '')
            start_str, end_str = byte_range.split('-')
            start = int(start_str) if start_str else 0
            end = int(end_str) if end_str else file_size - 1
            end = min(end, file_size - 1)
            if start < 0 or start > end:
                raise ValueError('Invalid range')

            chunk = file_content[start:end + 1]
            headers.update({
                'Content-Range': f'bytes {start}-{end}/{file_size}',
                'Content-Length': str(len(chunk)),
            })
            return Response(content=chunk, status_code=206, media_type=media_type, headers=headers)
        except Exception:
            pass

    headers['Content-Length'] = str(file_size)
    return Response(content=file_content, media_type=media_type, headers=headers)

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


def trim_backfill_logs(messages: list[str], limit: int = 200) -> list[str]:
    """Keep the most recent backfill log lines small enough for API responses."""
    if len(messages) <= limit:
        return messages
    return messages[-limit:]


def run_backfill_job(job_id: str, request: 'UploadBackfillRequest') -> None:
    """Execute a backfill job and persist the latest status in memory."""
    job = BACKFILL_JOBS.get(job_id)
    if not job:
        return

    job['status'] = 'running'
    job['started_at'] = datetime.utcnow().isoformat()
    job['messages'] = trim_backfill_logs(job.get('messages', []) + ['Backfill started'])

    try:
        result = run_backfill(
            dry_run=request.dry_run,
            limit=request.limit,
            include_existing=request.include_existing,
            verbose=request.verbose,
            log=lambda message: job.__setitem__(
                'messages',
                trim_backfill_logs(job.get('messages', []) + [message]),
            ),
        )
        job['status'] = 'completed' if result.get('success') else 'failed'
        job['result'] = result
    except Exception as exc:
        logger.exception('Upload blob backfill failed')
        job['status'] = 'failed'
        job['error'] = str(exc)
        job['messages'] = trim_backfill_logs(job.get('messages', []) + [f'ERROR: {exc}'])
    finally:
        job['finished_at'] = datetime.utcnow().isoformat()

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

class OfficerUpdate(BaseModel):
    name: str
    email: str
    password: Optional[str] = None
    temple_id: Optional[str] = None
    role: Optional[str] = "officer"
    permissions: Optional[List[str]] = ["view_feedback", "update_status"]

class OfficerPasswordReset(BaseModel):
    password: str

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


class UploadBackfillRequest(BaseModel):
    dry_run: bool = True
    limit: int = Field(default=100, ge=0, le=10000)
    include_existing: bool = False
    verbose: bool = False

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
    full_path = get_primary_upload_path(file_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    content = await file.read()
    
    async with aiofiles.open(full_path, 'wb') as f:
        await f.write(content)

    save_upload_record(file_path, file.filename or filename, os.path.splitext(filename)[1].lower(), len(content), None, content)
    
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

@app.put("/api/officers/{officer_id}")
async def update_officer(officer_id: str, officer: OfficerUpdate, current_admin = Depends(get_current_admin)):
    """Update officer details"""
    existing_officer = execute_query(
        "SELECT id FROM officers WHERE id = ?",
        (officer_id,),
        fetch_one=True
    )
    if not existing_officer:
        raise HTTPException(status_code=404, detail="Officer not found")

    duplicate_email = execute_query(
        "SELECT id FROM officers WHERE email = ? AND id <> ?",
        (officer.email, officer_id),
        fetch_one=True
    )
    if duplicate_email:
        raise HTTPException(status_code=400, detail="Email already exists")

    temple_name = None
    if officer.temple_id:
        temple = execute_query("SELECT name FROM temples WHERE id = ?", (officer.temple_id,), fetch_one=True)
        if temple:
            temple_name = temple['name']

    permissions_json = json.dumps(officer.permissions or ['view_feedback', 'update_status'])

    if officer.password:
        hashed_pw = hash_password(officer.password)
        execute_query(
            """UPDATE officers
               SET name = ?, email = ?, password = ?, temple_id = ?, temple_name = ?, role = ?, permissions = ?, updated_at = GETUTCDATE()
               WHERE id = ?""",
            (officer.name, officer.email, hashed_pw, officer.temple_id, temple_name, officer.role or 'officer', permissions_json, officer_id)
        )
    else:
        execute_query(
            """UPDATE officers
               SET name = ?, email = ?, temple_id = ?, temple_name = ?, role = ?, permissions = ?, updated_at = GETUTCDATE()
               WHERE id = ?""",
            (officer.name, officer.email, officer.temple_id, temple_name, officer.role or 'officer', permissions_json, officer_id)
        )

    return {
        "id": officer_id,
        "name": officer.name,
        "email": officer.email,
        "temple_name": temple_name,
        "role": officer.role or 'officer',
        "message": "Officer updated successfully"
    }

@app.put("/api/officers/{officer_id}/reset-password")
async def reset_officer_password(officer_id: str, payload: OfficerPasswordReset, current_admin = Depends(get_current_admin)):
    """Reset officer password"""
    existing_officer = execute_query(
        "SELECT id FROM officers WHERE id = ?",
        (officer_id,),
        fetch_one=True
    )
    if not existing_officer:
        raise HTTPException(status_code=404, detail="Officer not found")

    hashed_pw = hash_password(payload.password)
    execute_query(
        "UPDATE officers SET password = ?, updated_at = GETUTCDATE() WHERE id = ?",
        (hashed_pw, officer_id)
    )

    return {"message": "Password reset successfully"}

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

    response_items = []
    for feedback_item in feedback_list:
        video_path = get_feedback_video_path(feedback_item)
        response_items.append(
            {
                "id": str(feedback_item['id']),
                "complaint_id": feedback_item['complaint_id'],
                "temple_id": str(feedback_item['temple_id']) if feedback_item['temple_id'] else None,
                "temple_name": feedback_item['temple_name'],
                "user_name": feedback_item['user_name'],
                "user_mobile": feedback_item['user_mobile'],
                "service": feedback_item['service'],
                "rating": feedback_item['rating'],
                "message": feedback_item['message'],
                "video_url": video_path,
                "video_path": video_path,
                "status": feedback_item['status'],
                "officer_id": str(feedback_item['officer_id']) if feedback_item['officer_id'] else None,
                "officer_name": feedback_item['officer_name'],
                "assigned_officer_id": str(feedback_item['officer_id']) if feedback_item['officer_id'] else None,
                "assigned_officer_name": feedback_item['officer_name'],
                "resolution_notes": feedback_item['resolution_notes'],
                "officer_notes": feedback_item.get('officer_notes') or feedback_item.get('resolution_notes'),
                "created_at": feedback_item['created_at'].isoformat() if feedback_item['created_at'] else None,
                "resolved_at": feedback_item['resolved_at'].isoformat() if feedback_item['resolved_at'] else None,
            }
        )

    return response_items


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
    full_path = get_primary_upload_path(video_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    
    async with aiofiles.open(full_path, 'wb') as f:
        content = await video.read()
        await f.write(content)

    save_upload_record(video_path, video.filename or video_filename, os.path.splitext(video_filename)[1].lower(), len(content), None, content)
    
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


@app.post("/api/admin/uploads/backfill")
async def trigger_upload_backfill(
    request: UploadBackfillRequest,
    background_tasks: BackgroundTasks,
    current_admin = Depends(get_current_admin),
):
    """Trigger a one-time upload blob backfill into Azure SQL."""
    active_job = next(
        (
            job for job in BACKFILL_JOBS.values()
            if job.get('status') in {'queued', 'running'}
        ),
        None,
    )
    if active_job:
        raise HTTPException(
            status_code=409,
            detail={
                'message': 'A backfill job is already in progress',
                'job_id': active_job['job_id'],
            },
        )

    job_id = str(uuid.uuid4())
    BACKFILL_JOBS[job_id] = {
        'job_id': job_id,
        'status': 'queued',
        'requested_at': datetime.utcnow().isoformat(),
        'requested_by': current_admin['id'],
        'request': request.model_dump(),
        'messages': ['Backfill queued'],
        'result': None,
        'error': None,
    }
    background_tasks.add_task(run_backfill_job, job_id, request)

    return {
        'job_id': job_id,
        'status': 'queued',
        'message': 'Upload blob backfill started',
        'request': request.model_dump(),
    }


@app.get("/api/admin/uploads/backfill/{job_id}")
async def get_upload_backfill_status(job_id: str, current_admin = Depends(get_current_admin)):
    """Get the status of a previously triggered upload blob backfill job."""
    job = BACKFILL_JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail='Backfill job not found')
    return job

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
    path = get_primary_upload_path(output_name)
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

    save_upload_record(output_name, file.filename, file_ext, len(file_content), uploaded_by, file_content)

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
    path = get_primary_upload_path(output_name)
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

    save_upload_record(output_name, file.filename, file_ext, len(file_content), uploaded_by, file_content)

    return {"path": output_name}


@app.post("/api/upload/video")
async def api_upload_video(file: UploadFile = File(...), authorization: str = Header(None)):
    """Upload video with /api prefix"""
    return await upload_video(file, authorization)


@app.get("/api/files/{file_path:path}")
async def get_file(file_path: str, request: Request):
    """Serve uploaded files with Range request support for video streaming"""
    normalized_path = normalize_upload_path(file_path)
    media_type = get_media_type(normalized_path)

    try:
        file_path, full_path = resolve_existing_upload_path(normalized_path)
    except HTTPException:
        repaired_path = find_nearest_upload_path(normalized_path)
        if repaired_path:
            try:
                file_path, full_path = resolve_existing_upload_path(repaired_path)
            except HTTPException:
                blob_record = get_upload_blob(repaired_path)
                if blob_record and blob_record.get('file_blob') is not None:
                    return build_blob_response(repaired_path, bytes(blob_record['file_blob']), request)

        blob_record = get_upload_blob(normalized_path)
        if blob_record and blob_record.get('file_blob') is not None:
            return build_blob_response(normalized_path, bytes(blob_record['file_blob']), request)
        raise

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

        execute_query(
            """
            IF COL_LENGTH('file_uploads', 'file_blob') IS NULL
            BEGIN
                ALTER TABLE file_uploads ADD file_blob VARBINARY(MAX) NULL;
            END
            """
        )

        execute_query(
            """
            IF COL_LENGTH('feedback', 'video_path') IS NOT NULL
            BEGIN
                UPDATE feedback
                SET video_path = video_url
                WHERE video_url IS NOT NULL
                  AND (video_path IS NULL OR video_path <> video_url);
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

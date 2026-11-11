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
from starlette.middleware.gzip import GZipMiddleware
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from jose import JWTError, jwt
import bcrypt
import pyodbc
import uuid
import os
import re
import json
import logging
import time
import asyncio
import secrets
import urllib.request
import urllib.error
import aiofiles
from threading import Lock
from urllib.parse import urlparse, unquote
from dotenv import load_dotenv

from backfill_upload_blobs import run_backfill

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

pyodbc.pooling = True

AZURE_SITE_NAME = os.environ.get('WEBSITE_SITE_NAME')
IS_AZURE_APP = bool(AZURE_SITE_NAME)

# Database Configuration
DB_SERVER = os.environ.get('DB_SERVER', 'DESKTOP-JGCUNUE\\SQLEXPRESS')
DB_NAME = os.environ.get('DB_NAME', 'ts_feedbackdb')
DB_USER = os.environ.get('DB_USER', 'ts_feedback_user')
DB_PASSWORD = os.environ.get('DB_PASSWORD', 'TsFeedback@2026!')
LOCAL_DB_SERVER = os.environ.get('LOCAL_DB_SERVER', '')
LOCAL_DB_NAME = os.environ.get('LOCAL_DB_NAME', 'ts_feedbackdb')
LOCAL_DB_USER = os.environ.get('LOCAL_DB_USER', 'ts_feedback_user')
LOCAL_DB_PASSWORD = os.environ.get('LOCAL_DB_PASSWORD', 'TsFeedback@2026!')
DB_PORT = os.environ.get('DB_PORT', '1433')
# Azure SQL serverless tier can take 30-60s to wake from auto-pause; default timeout must accommodate that.
DB_CONNECTION_TIMEOUT = int(os.environ.get('DB_CONNECTION_TIMEOUT', '60'))
DB_CONNECTION_RETRIES = max(1, int(os.environ.get('DB_CONNECTION_RETRIES', '4')))
DB_CONNECTION_RETRY_DELAY = float(os.environ.get('DB_CONNECTION_RETRY_DELAY', '1.5'))
DB_LOCAL_FALLBACK = os.environ.get('DB_LOCAL_FALLBACK', 'true').strip().lower() in {'1', 'true', 'yes', 'on'}
READ_CACHE_TTL_SECONDS = max(1, int(os.environ.get('READ_CACHE_TTL_SECONDS', '15')))
FEEDBACK_QUERY_LIMIT_MAX = max(50, int(os.environ.get('FEEDBACK_QUERY_LIMIT_MAX', '500')))

AVAILABLE_SQL_DRIVERS = [driver for driver in pyodbc.drivers() if 'SQL Server' in driver]
SQL_DRIVER = os.environ.get('DB_DRIVER') or (
    'ODBC Driver 18 for SQL Server'
    if 'ODBC Driver 18 for SQL Server' in AVAILABLE_SQL_DRIVERS
    else 'ODBC Driver 17 for SQL Server'
)

RESPONSE_CACHE: dict[str, tuple[float, object]] = {}
CACHE_LOCK = Lock()
ACTIVE_DB_CONNECTION_STRING: Optional[str] = None
ACTIVE_DB_TARGET: Optional[str] = None

# JWT Configuration
SECRET_KEY = os.environ.get('JWT_SECRET', 'temple_feedback_secret_key_2026')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# WhatsApp Cloud API (Meta) for password reset OTPs
WHATSAPP_ACCESS_TOKEN = os.environ.get('WHATSAPP_ACCESS_TOKEN', '')
WHATSAPP_PHONE_NUMBER_ID = os.environ.get('WHATSAPP_PHONE_NUMBER_ID', '')
WHATSAPP_COUNTRY_CODE = os.environ.get('WHATSAPP_COUNTRY_CODE', '91')
WHATSAPP_API_VERSION = os.environ.get('WHATSAPP_API_VERSION', 'v21.0')
META_OTP_TEMPLATE_NAME = os.environ.get('META_OTP_TEMPLATE_NAME', 'sri_otp')
META_OTP_TEMPLATE_LANG = os.environ.get('META_OTP_TEMPLATE_LANG', 'en_US')
META_OTP_TEMPLATE_HAS_BUTTON = os.environ.get('META_OTP_TEMPLATE_HAS_BUTTON', 'true').strip().lower() in {'1', 'true', 'yes', 'on'}
OTP_TTL_MINUTES = 10
OTP_MAX_ATTEMPTS = 5
OTP_RESEND_SECONDS = 60
OTP_MAX_PER_HOUR = 5

# Password hashing
# Use direct bcrypt; enforce 72-byte truncation for algorithm compatibility.
BCRYPT_ROUNDS = 12

# File upload configuration
# On Azure App Service, WEBSITE_SITE_NAME is set; use /home/uploads so files
# persist across deployments (Azure Files mount). Fall back to 'uploads' locally.
_azure_site = AZURE_SITE_NAME
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
    if ext == '.webp':
        return 'image/webp'
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


def normalize_optional_upload_reference(file_path: Optional[str]) -> Optional[str]:
    """Normalize stored upload references without forcing expensive existence checks."""
    if not file_path:
        return None

    try:
        return normalize_upload_path(str(file_path))
    except HTTPException:
        return str(file_path).replace('\\', '/').strip()


def serialize_feedback_item(feedback_item: dict) -> dict:
    """Convert a feedback row into the API response shape quickly."""
    video_ref = normalize_optional_upload_reference(
        feedback_item.get('video_url') or feedback_item.get('video_path')
    )

    return {
        "id": str(feedback_item['id']),
        "complaint_id": feedback_item['complaint_id'],
        "temple_id": str(feedback_item['temple_id']) if feedback_item['temple_id'] else None,
        "temple_name": feedback_item['temple_name'],
        "user_name": feedback_item['user_name'],
        "user_mobile": feedback_item['user_mobile'],
        "service": feedback_item['service'],
        "rating": feedback_item['rating'],
        "message": feedback_item['message'],
        "video_url": video_ref,
        "video_path": video_ref,
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
app.add_middleware(GZipMiddleware, minimum_size=1024, compresslevel=5)

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

def is_azure_sql_server(server_name: str) -> bool:
    return '.database.windows.net' in (server_name or '').lower()


def build_connection_string(server_name: str) -> str:
    """Build a SQL Server connection string for Azure SQL or local SQL Express."""
    azure_target = is_azure_sql_server(server_name)
    normalized_server = (server_name or '').strip()

    if azure_target:
        normalized_server = normalized_server.removeprefix('tcp:')
        if ',' not in normalized_server:
            normalized_server = f"tcp:{normalized_server},{DB_PORT}"
        else:
            normalized_server = f"tcp:{normalized_server}"

    encrypt_value = os.environ.get('DB_ENCRYPT', 'yes' if azure_target else 'no')
    trust_cert_value = os.environ.get('DB_TRUST_SERVER_CERTIFICATE', 'no' if azure_target else 'yes')

    database_name = DB_NAME if azure_target else LOCAL_DB_NAME
    db_user = DB_USER if azure_target else LOCAL_DB_USER
    db_password = DB_PASSWORD if azure_target else LOCAL_DB_PASSWORD

    parts = [
        f"DRIVER={{{SQL_DRIVER}}}",
        f"SERVER={normalized_server}",
        f"DATABASE={database_name}",
    ]

    if db_user and db_password:
        parts.extend([
            f"UID={db_user}",
            f"PWD={db_password}",
        ])
    else:
        parts.append('Trusted_Connection=yes')

    parts.extend([
        f"Encrypt={encrypt_value}",
        f"TrustServerCertificate={trust_cert_value}",
        'MARS_Connection=yes',
    ])

    return ';'.join(parts) + ';'


def get_db_server_candidates() -> list[str]:
    """Return preferred DB targets, falling back to local SQL Express for local development."""
    candidates = [DB_SERVER]

    if not IS_AZURE_APP and DB_LOCAL_FALLBACK:
        local_machine = os.environ.get('COMPUTERNAME', 'localhost')
        candidates.extend([
            LOCAL_DB_SERVER,
            f'{local_machine}\\SQLEXPRESS',
            'localhost\\SQLEXPRESS',
            '.\\SQLEXPRESS',
        ])

    unique_candidates: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        normalized = (candidate or '').strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            unique_candidates.append(normalized)

    return unique_candidates


def format_db_connection_error(error: Exception) -> str:
    """Convert low-level ODBC failures into a clear API message."""
    message = str(error)
    lowered = message.lower()

    if '40615' in message or 'not allowed to access the server' in lowered:
        return (
            'Azure SQL firewall is blocking this machine. Add your current public IP to the SQL Server firewall '
            'or let the app use the local SQL Express fallback.'
        )

    if 'login failed for user' in lowered:
        return 'Database login failed. Verify DB_USER and DB_PASSWORD.'

    if 'server was not found' in lowered or 'instance-specific error' in lowered:
        return 'Database server was not found. Verify DB_SERVER and that SQL Server is running.'

    if (
        '40613' in message
        or 'is not currently available' in lowered
        or 'database is not currently available' in lowered
        or 'login timeout expired' in lowered
        or 'unable to complete login process' in lowered
    ):
        return 'Database is waking up, please try again in a moment.'

    return f'Database connection failed: {message}'


def _is_transient_db_error(exc: Exception) -> bool:
    """Detect Azure SQL cold-start / transient errors that justify a retry."""
    message = str(exc).lower()
    transient_markers = (
        '40613',           # database currently unavailable (paused / resuming)
        '40197', '40501', '49918', '49919', '49920',
        '10928', '10929',  # resource limits
        '10053', '10054', '10060',  # network drops
        '08001', '08s01', 'hyt00', 'hyt01',  # ODBC connect/timeout states
        'login timeout expired',
        'tcp provider',
        'communication link failure',
        'is not currently available',
        'database is not currently available',
        'unable to complete login process',
    )
    return any(marker in message for marker in transient_markers)


def get_db_connection():
    """Get a pooled database connection with local SQL Express fallback for development.

    Retries transient Azure SQL cold-start errors so the first request after
    auto-pause does not surface as 'Database connection failed' to the user.
    """
    global ACTIVE_DB_CONNECTION_STRING, ACTIVE_DB_TARGET

    candidates: list[tuple[str, str]] = []
    if ACTIVE_DB_CONNECTION_STRING and ACTIVE_DB_TARGET:
        candidates.append((ACTIVE_DB_TARGET, ACTIVE_DB_CONNECTION_STRING))
    else:
        candidates.extend((server_name, build_connection_string(server_name)) for server_name in get_db_server_candidates())

    last_error: Optional[Exception] = None

    for server_name, connection_string in candidates:
        for attempt in range(1, DB_CONNECTION_RETRIES + 1):
            try:
                conn = pyodbc.connect(connection_string, timeout=DB_CONNECTION_TIMEOUT)
                if ACTIVE_DB_TARGET != server_name:
                    logger.info('Using database server: %s (%s)', server_name, SQL_DRIVER)
                ACTIVE_DB_CONNECTION_STRING = connection_string
                ACTIVE_DB_TARGET = server_name
                return conn
            except Exception as exc:
                last_error = exc
                transient = _is_transient_db_error(exc)
                logger.warning(
                    'Database connection attempt %s/%s failed for %s (transient=%s): %s',
                    attempt, DB_CONNECTION_RETRIES, server_name, transient, exc,
                )
                if ACTIVE_DB_TARGET == server_name:
                    ACTIVE_DB_CONNECTION_STRING = None
                    ACTIVE_DB_TARGET = None
                if not transient or attempt >= DB_CONNECTION_RETRIES:
                    break
                # Exponential backoff to give Azure SQL serverless time to resume.
                time.sleep(DB_CONNECTION_RETRY_DELAY * attempt)

    logger.error('Database connection error: %s', last_error)
    raise HTTPException(status_code=503, detail=format_db_connection_error(last_error or Exception('Unknown database error')))


def get_cached_response(cache_key: Optional[str]):
    """Return a short-lived cached payload when available."""
    if not cache_key:
        return None

    now = time.time()
    with CACHE_LOCK:
        entry = RESPONSE_CACHE.get(cache_key)
        if not entry:
            return None

        expires_at, payload = entry
        if expires_at <= now:
            RESPONSE_CACHE.pop(cache_key, None)
            return None

        return payload


def set_cached_response(cache_key: Optional[str], payload, ttl: int = READ_CACHE_TTL_SECONDS):
    """Store a payload in the in-memory response cache."""
    if not cache_key:
        return

    with CACHE_LOCK:
        RESPONSE_CACHE[cache_key] = (time.time() + max(1, ttl), payload)


def clear_cached_responses():
    """Invalidate cached GET responses after writes."""
    with CACHE_LOCK:
        RESPONSE_CACHE.clear()


def execute_query(query: str, params: tuple = None, fetch_one: bool = False, fetch_all: bool = False):
    """Execute a SQL query with pooled connections and automatic cache invalidation."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.arraysize = 250

    try:
        if params is not None:
            cursor.execute(query, params)
        else:
            cursor.execute(query)

        if fetch_one:
            row = cursor.fetchone()
            if row:
                columns = [column[0] for column in cursor.description]
                return dict(zip(columns, row))
            return None

        if fetch_all:
            rows = cursor.fetchall()
            columns = [column[0] for column in cursor.description]
            return [dict(zip(columns, row)) for row in rows]

        conn.commit()
        clear_cached_responses()
        return True
    except Exception as e:
        logger.error(f"Query error: {e}")
        try:
            conn.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


def ensure_database_indexes():
    """Create the main read-performance indexes used by the busiest API endpoints."""
    index_statements = [
        """
        IF OBJECT_ID('feedback', 'U') IS NOT NULL
           AND NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_feedback_created_at' AND object_id = OBJECT_ID('feedback'))
        BEGIN
            CREATE INDEX IX_feedback_created_at ON feedback (created_at DESC);
        END
        """,
        """
        IF OBJECT_ID('feedback', 'U') IS NOT NULL
           AND NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_feedback_status_created_at' AND object_id = OBJECT_ID('feedback'))
        BEGIN
            CREATE INDEX IX_feedback_status_created_at ON feedback (status, created_at DESC);
        END
        """,
        """
        IF OBJECT_ID('feedback', 'U') IS NOT NULL
           AND NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_feedback_officer_status_created_at' AND object_id = OBJECT_ID('feedback'))
        BEGIN
            CREATE INDEX IX_feedback_officer_status_created_at ON feedback (officer_id, status, created_at DESC);
        END
        """,
        """
        IF OBJECT_ID('feedback', 'U') IS NOT NULL
           AND NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_feedback_temple_created_at' AND object_id = OBJECT_ID('feedback'))
        BEGIN
            CREATE INDEX IX_feedback_temple_created_at ON feedback (temple_id, created_at DESC);
        END
        """,
        """
        IF OBJECT_ID('users', 'U') IS NOT NULL
           AND NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_users_email' AND object_id = OBJECT_ID('users'))
        BEGIN
            CREATE INDEX IX_users_email ON users (email);
        END
        """,
        """
        IF OBJECT_ID('officers', 'U') IS NOT NULL
           AND NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_officers_email' AND object_id = OBJECT_ID('officers'))
        BEGIN
            CREATE INDEX IX_officers_email ON officers (email);
        END
        """,
        """
        IF OBJECT_ID('temples', 'U') IS NOT NULL
           AND NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_temples_email' AND object_id = OBJECT_ID('temples'))
        BEGIN
            CREATE INDEX IX_temples_email ON temples (email);
        END
        """,
        """
        IF OBJECT_ID('services', 'U') IS NOT NULL
           AND NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_services_active_display_order' AND object_id = OBJECT_ID('services'))
        BEGIN
            CREATE INDEX IX_services_active_display_order ON services (is_active, display_order);
        END
        """,
        """
        IF OBJECT_ID('whatsapp_logs', 'U') IS NOT NULL
           AND NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_whatsapp_logs_created_at' AND object_id = OBJECT_ID('whatsapp_logs'))
        BEGIN
            CREATE INDEX IX_whatsapp_logs_created_at ON whatsapp_logs (created_at DESC);
        END
        """,
        """
        IF OBJECT_ID('file_uploads', 'U') IS NOT NULL
           AND NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_file_uploads_path_created_at' AND object_id = OBJECT_ID('file_uploads'))
        BEGIN
            CREATE INDEX IX_file_uploads_path_created_at ON file_uploads (file_path, created_at DESC);
        END
        """,
    ]

    for statement in index_statements:
        try:
            execute_query(statement)
        except HTTPException as exc:
            logger.warning("Skipped optional index creation: %s", exc.detail)


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

# Sidebar permission keys controlled by Super Admin
ALL_ADMIN_PERMISSIONS = [
    "dashboard",
    "temples",
    "officers",
    "services",
    "feedback",
    "whatsapp_logs",
    "reports",
    "administration",
    # Action permission (not a sidebar page): Feedback Monitoring > Action > Assign / Reassign EO / Officer
    "feedback_assign",
]

class ForgotPasswordRequest(BaseModel):
    identifier: str  # email or mobile number

class ResetPasswordRequest(BaseModel):
    identifier: str
    otp: str
    new_password: str = Field(min_length=6)

class AdminCreate(BaseModel):
    username: str
    email: str
    password: str
    mobile: Optional[str] = None
    role: Optional[str] = "admin"  # 'admin' or 'superadmin'
    permissions: Optional[List[str]] = None
    temple_id: Optional[str] = None  # admin limited to one temple; empty / 'all' = all temples

class AdminUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    mobile: Optional[str] = None
    role: Optional[str] = None
    permissions: Optional[List[str]] = None
    temple_id: Optional[str] = None  # '' or 'all' = all temples

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
    mobile: Optional[str] = None
    temple_id: Optional[str] = None
    role: Optional[str] = "officer"
    permissions: Optional[List[str]] = ["view_feedback", "update_status"]

class OfficerUpdate(BaseModel):
    name: str
    email: str
    password: Optional[str] = None
    mobile: Optional[str] = None
    temple_id: Optional[str] = None
    role: Optional[str] = "officer"
    permissions: Optional[List[str]] = ["view_feedback", "update_status"]

class OfficerPasswordReset(BaseModel):
    password: str

class OfficerRoleUpdate(BaseModel):
    role: str
    permissions: List[str]
    name: Optional[str] = None  # Role & Permission Management also edits the officer's name

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

def normalize_mobile(value: Optional[str]) -> Optional[str]:
    """Store mobiles as 10 local digits; the country code is added when sending WhatsApp."""
    digits = re.sub(r'\D', '', value or '')
    if not digits:
        return None
    if len(digits) == 10 + len(WHATSAPP_COUNTRY_CODE) and digits.startswith(WHATSAPP_COUNTRY_CODE):
        digits = digits[len(WHATSAPP_COUNTRY_CODE):]
    if len(digits) != 10:
        raise HTTPException(status_code=400, detail="Mobile number must be 10 digits")
    return digits

def generate_complaint_id():
    """Generate a unique complaint ID without scanning the feedback table."""
    timestamp = datetime.utcnow().strftime("%y%m%d%H%M%S")
    suffix = uuid.uuid4().hex[:4].upper()
    return f"TF{timestamp}{suffix}"

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
        
        if role not in ("admin", "superadmin"):
            raise HTTPException(status_code=403, detail="Admin access required")
        
        return {"id": user_id, "role": role}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_current_superadmin(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing token")
    try:
        token = authorization.replace("Bearer ", "")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("role") != "superadmin":
            raise HTTPException(status_code=403, detail="Super Admin access required")
        return {"id": payload.get("sub"), "role": "superadmin"}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def _admin_temple_id(user_id) -> Optional[str]:
    """The one temple an admin is limited to (None = all temples). Read fresh from the users table."""
    if not user_id:
        return None
    try:
        row = execute_query("SELECT temple_id FROM users WHERE id = ?", (str(user_id),), fetch_one=True)
    except Exception:
        return None
    value = (row or {}).get('temple_id')
    return str(value).strip().lower() if value and str(value).strip() else None


def admin_scope_from_header(authorization: Optional[str]) -> Optional[str]:
    """Temple id when the caller is an admin limited to one temple; None for everyone else
    (Super Admin, all-temple admins, kiosks / devotees without an admin token)."""
    if not authorization:
        return None
    try:
        payload = jwt.decode(authorization.replace("Bearer ", ""), SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None
    if payload.get("role") != "admin":
        return None
    return _admin_temple_id(payload.get("sub"))


def _same_id(a, b) -> bool:
    return bool(a) and bool(b) and str(a).strip().lower() == str(b).strip().lower()


def _normalize_admin_temple(temple_id: Optional[str]) -> Optional[str]:
    if temple_id is None or str(temple_id).strip().lower() in ('', 'all'):
        return None
    temple = execute_query("SELECT id FROM temples WHERE id = ?", (temple_id,), fetch_one=True)
    if not temple:
        raise HTTPException(status_code=400, detail="Temple not found")
    return str(temple['id']).lower()


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
        
        officer = execute_query(
            "SELECT id, name, email, temple_id, temple_name, role, permissions FROM officers WHERE id = ?",
            (user_id,),
            fetch_one=True,
        )
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
    """Admin / Super Admin login"""
    user = execute_query(
        "SELECT * FROM users WHERE email = ?",
        (user_data.email,),
        fetch_one=True
    )
    
    if not user or not verify_password(user_data.password, user['password']):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    role = user.get('role') or 'admin'
    raw_perms = user.get('permissions') if isinstance(user, dict) else None
    if raw_perms:
        try:
            permissions = json.loads(raw_perms)
        except Exception:
            permissions = []
    else:
        permissions = []
    if role == 'superadmin':
        permissions = ALL_ADMIN_PERMISSIONS
    admin_temple_id = None if role == 'superadmin' else _admin_temple_id(user['id'])
    admin_temple_name = None
    if admin_temple_id:
        trow = execute_query("SELECT name FROM temples WHERE id = ?", (admin_temple_id,), fetch_one=True)
        admin_temple_name = trow['name'] if trow else None

    access_token = create_access_token(
        data={"sub": str(user['id']), "role": role}
    )
    
    return {
        "access_token": access_token,
        "token": access_token,
        "token_type": "bearer",
        "user": {
            "id": str(user['id']),
            "email": user['email'],
            "role": role,
            "permissions": permissions,
            "temple_id": admin_temple_id,
            "temple_name": admin_temple_name,
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
# FORGOT PASSWORD (WhatsApp OTP)
# =====================================================

PASSWORD_RESET_GENERIC_MESSAGE = (
    "If this account has a mobile number, an OTP has been sent to it on WhatsApp."
)


def ensure_account_schema():
    """Add mobile numbers to admins and officers and create the OTP table, tolerating worker races."""
    statements = [
        """
        IF COL_LENGTH('users', 'mobile') IS NULL
        BEGIN
            ALTER TABLE users ADD mobile NVARCHAR(20) NULL;
        END
        """,
        """
        IF COL_LENGTH('users', 'temple_id') IS NULL
        BEGIN
            ALTER TABLE users ADD temple_id NVARCHAR(36) NULL;
        END
        """,
        """
        IF OBJECT_ID('officer_roles', 'U') IS NULL
        BEGIN
            CREATE TABLE officer_roles (
                role_key NVARCHAR(50) NOT NULL PRIMARY KEY,
                label NVARCHAR(100) NOT NULL,
                access NVARCHAR(20) NOT NULL DEFAULT 'assigned',
                color NVARCHAR(20) NOT NULL DEFAULT 'green',
                sort_order INT NOT NULL DEFAULT 100,
                created_at DATETIME2 DEFAULT GETUTCDATE(),
                updated_at DATETIME2 DEFAULT GETUTCDATE()
            );
            INSERT INTO officer_roles (role_key, label, access, color, sort_order) VALUES
                ('officer', 'Officer', 'assigned', 'green', 10),
                ('supervisor', 'Supervisor', 'temple', 'blue', 20),
                ('eo', 'Executive Officer', 'temple', 'purple', 30),
                ('asst_commissioner', 'Asst Commissioner', 'all', 'amber', 40),
                ('commissioner', 'Commissioner', 'all', 'red', 50);
        END
        """,
        """
        IF COL_LENGTH('officers', 'mobile') IS NULL
        BEGIN
            ALTER TABLE officers ADD mobile NVARCHAR(20) NULL;
        END
        """,
        """
        IF OBJECT_ID('password_reset_otps', 'U') IS NULL
        BEGIN
            CREATE TABLE password_reset_otps (
                id NVARCHAR(36) NOT NULL PRIMARY KEY,
                account_type NVARCHAR(10) NOT NULL,
                account_id NVARCHAR(36) NOT NULL,
                otp_hash NVARCHAR(100) NOT NULL,
                attempts INT NOT NULL DEFAULT 0,
                used BIT NOT NULL DEFAULT 0,
                expires_at DATETIME2 NOT NULL,
                created_at DATETIME2 NOT NULL DEFAULT GETUTCDATE()
            );
            CREATE INDEX IX_password_reset_otps_account ON password_reset_otps (account_type, account_id, created_at DESC);
        END
        """,
    ]
    for query in statements:
        try:
            execute_query(query)
        except HTTPException as exc:
            if any(code in str(exc.detail) for code in ('2714', '2627', '2705', '1913')):
                logger.info('Account schema already created by another worker')
            else:
                logger.error('Account schema setup failed: %s', exc.detail)


def find_account_for_reset(identifier: str) -> Optional[dict]:
    """Find an admin first, then an officer, by email or mobile (same order as login)."""
    identifier = (identifier or '').strip()
    if not identifier:
        return None
    if '@' in identifier:
        column, value = 'email', identifier
    else:
        column, value = 'mobile', normalize_mobile(identifier)
    for account_type, table in (('admin', 'users'), ('officer', 'officers')):
        row = execute_query(
            f"SELECT TOP 1 id, mobile FROM {table} WHERE {column} = ? ORDER BY created_at ASC",
            (value,),
            fetch_one=True,
        )
        if row:
            return {"type": account_type, "table": table, "id": str(row['id']), "mobile": row.get('mobile')}
    return None


def send_whatsapp_otp(mobile: str, otp: str) -> None:
    """Send the OTP with the approved Meta authentication template."""
    components = [{"type": "body", "parameters": [{"type": "text", "text": otp}]}]
    if META_OTP_TEMPLATE_HAS_BUTTON:
        # Authentication templates with a copy-code button need the code repeated on the button.
        components.append({
            "type": "button",
            "sub_type": "url",
            "index": "0",
            "parameters": [{"type": "text", "text": otp}],
        })
    body = json.dumps({
        "messaging_product": "whatsapp",
        "to": f"{WHATSAPP_COUNTRY_CODE}{mobile}",
        "type": "template",
        "template": {
            "name": META_OTP_TEMPLATE_NAME,
            "language": {"code": META_OTP_TEMPLATE_LANG},
            "components": components,
        },
    }).encode('utf-8')
    request = urllib.request.Request(
        f"https://graph.facebook.com/{WHATSAPP_API_VERSION}/{WHATSAPP_PHONE_NUMBER_ID}/messages",
        data=body,
        headers={"Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            response.read()
    except urllib.error.HTTPError as exc:
        logger.error('WhatsApp OTP send failed (%s): %s', exc.code, exc.read().decode('utf-8', errors='replace'))
        raise


@app.post("/api/auth/forgot-password")
async def forgot_password(payload: ForgotPasswordRequest):
    """Send a password reset OTP on WhatsApp to the account's mobile number."""
    if not (WHATSAPP_ACCESS_TOKEN and WHATSAPP_PHONE_NUMBER_ID):
        raise HTTPException(status_code=503, detail="WhatsApp OTP is not configured on the server")

    account = find_account_for_reset(payload.identifier)
    # The same reply whether or not the account exists, so the form cannot be used to discover accounts.
    if not account or not account['mobile']:
        return {"message": PASSWORD_RESET_GENERIC_MESSAGE}

    recent = execute_query(
        """SELECT COUNT(*) AS sent_last_hour,
                  SUM(CASE WHEN created_at > DATEADD(second, ?, GETUTCDATE()) THEN 1 ELSE 0 END) AS sent_last_minute
           FROM password_reset_otps
           WHERE account_type = ? AND account_id = ? AND created_at > DATEADD(hour, -1, GETUTCDATE())""",
        (-OTP_RESEND_SECONDS, account['type'], account['id']),
        fetch_one=True,
    ) or {}
    if (recent.get('sent_last_minute') or 0) > 0:
        raise HTTPException(status_code=429, detail="Please wait a minute before requesting another OTP")
    if (recent.get('sent_last_hour') or 0) >= OTP_MAX_PER_HOUR:
        raise HTTPException(status_code=429, detail="Too many OTP requests. Try again in an hour")

    otp = f"{secrets.randbelow(1000000):06d}"
    otp_id = str(uuid.uuid4())
    execute_query(
        """INSERT INTO password_reset_otps (id, account_type, account_id, otp_hash, expires_at)
           VALUES (?, ?, ?, ?, DATEADD(minute, ?, GETUTCDATE()))""",
        (otp_id, account['type'], account['id'], hash_password(otp), OTP_TTL_MINUTES),
    )
    try:
        await asyncio.to_thread(send_whatsapp_otp, account['mobile'], otp)
    except Exception as exc:
        logger.error('WhatsApp OTP send error: %s', exc)
        execute_query("DELETE FROM password_reset_otps WHERE id = ?", (otp_id,))
        raise HTTPException(status_code=502, detail="Could not send the WhatsApp OTP. Please try again later")

    return {"message": PASSWORD_RESET_GENERIC_MESSAGE}


@app.post("/api/auth/reset-password")
async def reset_password_with_otp(payload: ResetPasswordRequest):
    """Set a new password after checking the WhatsApp OTP."""
    invalid = HTTPException(status_code=400, detail="Invalid or expired OTP")
    account = find_account_for_reset(payload.identifier)
    if not account:
        raise invalid

    otp_row = execute_query(
        """SELECT TOP 1 id, otp_hash, attempts FROM password_reset_otps
           WHERE account_type = ? AND account_id = ? AND used = 0 AND expires_at > GETUTCDATE()
           ORDER BY created_at DESC""",
        (account['type'], account['id']),
        fetch_one=True,
    )
    if not otp_row or otp_row['attempts'] >= OTP_MAX_ATTEMPTS:
        raise invalid

    if not verify_password(payload.otp.strip(), otp_row['otp_hash']):
        execute_query("UPDATE password_reset_otps SET attempts = attempts + 1 WHERE id = ?", (otp_row['id'],))
        raise invalid

    execute_query(
        f"UPDATE {account['table']} SET password = ?, updated_at = GETUTCDATE() WHERE id = ?",
        (hash_password(payload.new_password), account['id']),
    )
    execute_query(
        "UPDATE password_reset_otps SET used = 1 WHERE account_type = ? AND account_id = ?",
        (account['type'], account['id']),
    )
    return {"message": "Password changed. You can now log in."}

# =====================================================
# SUPER ADMIN ENDPOINTS (manage admins & sidebar perms)
# =====================================================

def _serialize_admin(row: dict) -> dict:
    raw = row.get('permissions') if isinstance(row, dict) else None
    try:
        perms = json.loads(raw) if raw else []
    except Exception:
        perms = []
    role = row.get('role') or 'admin'
    if role == 'superadmin':
        perms = ALL_ADMIN_PERMISSIONS
    return {
        "id": str(row['id']),
        "username": row.get('username'),
        "email": row.get('email'),
        "mobile": row.get('mobile'),
        "role": role,
        "permissions": perms,
        "temple_id": (str(row['temple_id']).lower() if row.get('temple_id') else None) if role != 'superadmin' else None,
        "created_at": row['created_at'].isoformat() if row.get('created_at') else None,
    }


@app.get("/api/admins")
async def list_admins(current_superadmin = Depends(get_current_superadmin)):
    """List all admin / super admin users (Super Admin only)."""
    rows = execute_query(
        "SELECT id, username, email, mobile, role, permissions, temple_id, created_at FROM users ORDER BY created_at DESC",
        fetch_all=True,
    ) or []
    return [_serialize_admin(r) for r in rows]


@app.post("/api/admins")
async def create_admin(payload: AdminCreate, current_superadmin = Depends(get_current_superadmin)):
    """Create a new admin / super admin user (Super Admin only)."""
    existing = execute_query(
        "SELECT id FROM users WHERE email = ? OR username = ?",
        (payload.email, payload.username),
        fetch_one=True,
    )
    if existing:
        raise HTTPException(status_code=400, detail="Email or username already exists")

    role = payload.role if payload.role in ("admin", "superadmin") else "admin"
    perms = payload.permissions if payload.permissions is not None else (
        ALL_ADMIN_PERMISSIONS if role == "superadmin" else ["dashboard"]
    )
    perms = [p for p in perms if p in ALL_ADMIN_PERMISSIONS]
    if role == "superadmin":
        perms = ALL_ADMIN_PERMISSIONS

    mobile = normalize_mobile(payload.mobile)
    temple_id = None if role == "superadmin" else _normalize_admin_temple(payload.temple_id)
    new_id = str(uuid.uuid4())
    execute_query(
        """INSERT INTO users (id, username, email, mobile, password, role, permissions, temple_id)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (new_id, payload.username, payload.email, mobile, hash_password(payload.password), role, json.dumps(perms), temple_id)
    )
    return {"id": new_id, "username": payload.username, "email": payload.email, "mobile": mobile, "role": role, "permissions": perms, "temple_id": temple_id}


@app.put("/api/admins/{admin_id}")
async def update_admin(admin_id: str, payload: AdminUpdate, current_superadmin = Depends(get_current_superadmin)):
    """Update an admin user (Super Admin only)."""
    row = execute_query("SELECT id, role FROM users WHERE id = ?", (admin_id,), fetch_one=True)
    if not row:
        raise HTTPException(status_code=404, detail="Admin not found")

    fields, params = [], []
    if payload.username is not None:
        fields.append("username = ?"); params.append(payload.username)
    if payload.email is not None:
        fields.append("email = ?"); params.append(payload.email)
    if payload.password:
        fields.append("password = ?"); params.append(hash_password(payload.password))
    if payload.mobile is not None:
        fields.append("mobile = ?"); params.append(normalize_mobile(payload.mobile))

    new_role = payload.role if payload.role in ("admin", "superadmin") else None
    if new_role:
        fields.append("role = ?"); params.append(new_role)

    effective_role = new_role or row.get('role') or 'admin'
    if payload.permissions is not None or effective_role == "superadmin":
        perms = payload.permissions if payload.permissions is not None else []
        perms = [p for p in perms if p in ALL_ADMIN_PERMISSIONS]
        if effective_role == "superadmin":
            perms = ALL_ADMIN_PERMISSIONS
        fields.append("permissions = ?"); params.append(json.dumps(perms))

    if effective_role == "superadmin":
        fields.append("temple_id = NULL")
    elif payload.temple_id is not None:
        fields.append("temple_id = ?"); params.append(_normalize_admin_temple(payload.temple_id))

    if not fields:
        return {"message": "No changes"}

    fields.append("updated_at = GETUTCDATE()")
    params.append(admin_id)
    execute_query(f"UPDATE users SET {', '.join(fields)} WHERE id = ?", tuple(params))
    return {"message": "Admin updated"}


@app.put("/api/admins/{admin_id}/permissions")
async def update_admin_permissions(admin_id: str, payload: AdminUpdate, current_superadmin = Depends(get_current_superadmin)):
    """Convenience endpoint to update only sidebar permissions."""
    row = execute_query("SELECT id, role FROM users WHERE id = ?", (admin_id,), fetch_one=True)
    if not row:
        raise HTTPException(status_code=404, detail="Admin not found")

    perms = payload.permissions or []
    perms = [p for p in perms if p in ALL_ADMIN_PERMISSIONS]
    if (row.get('role') or 'admin') == "superadmin":
        perms = ALL_ADMIN_PERMISSIONS
    execute_query(
        "UPDATE users SET permissions = ?, updated_at = GETUTCDATE() WHERE id = ?",
        (json.dumps(perms), admin_id)
    )
    return {"message": "Permissions updated", "permissions": perms}


@app.delete("/api/admins/{admin_id}")
async def delete_admin(admin_id: str, current_superadmin = Depends(get_current_superadmin)):
    """Delete an admin user (Super Admin only)."""
    if str(current_superadmin.get('id')) == str(admin_id):
        raise HTTPException(status_code=400, detail="Cannot delete the currently signed-in Super Admin")
    row = execute_query("SELECT id FROM users WHERE id = ?", (admin_id,), fetch_one=True)
    if not row:
        raise HTTPException(status_code=404, detail="Admin not found")
    execute_query("DELETE FROM users WHERE id = ?", (admin_id,))
    return {"message": "Admin deleted"}


# =====================================================
# TEMPLE ENDPOINTS
# =====================================================

@app.get("/api/temples")
async def get_temples(authorization: str = Header(None)):
    """Get all temples (an admin limited to one temple gets only that temple)."""
    scope = admin_scope_from_header(authorization)
    if scope:
        return [t for t in await get_temples(None) if _same_id(t['id'], scope)]
    cache_key = "temples:list"
    cached = get_cached_response(cache_key)
    if cached is not None:
        return cached

    temples = execute_query(
        "SELECT id, name, location, email, logo_path, officer_id, created_at FROM temples ORDER BY created_at DESC",
        fetch_all=True,
    )
    response = [
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
    set_cached_response(cache_key, response)
    return response

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

# =====================================================
# OFFICER ROLES (Super Admin adds / edits them)
#   access: 'assigned' = only feedback assigned to the officer,
#           'temple'   = all feedback of the officer's temple,
#           'all'      = all temples
# =====================================================

BUILTIN_ROLE_ACCESS = {
    'officer': 'assigned', 'supervisor': 'temple', 'eo': 'temple',
    'asst_commissioner': 'all', 'commissioner': 'all',
}
ROLE_ACCESS_LEVELS = ('assigned', 'temple', 'all')
ROLE_COLORS = ('green', 'blue', 'purple', 'amber', 'red', 'teal', 'pink', 'slate')


class OfficerRoleIn(BaseModel):
    label: str = Field(min_length=1, max_length=100)
    access: str = 'assigned'
    color: Optional[str] = 'green'


def _list_officer_roles():
    cached = get_cached_response("officer-roles:list")
    if cached is not None:
        return cached
    try:
        rows = execute_query(
            "SELECT role_key, label, access, color, sort_order FROM officer_roles ORDER BY sort_order, label",
            fetch_all=True,
        ) or []
    except Exception:
        rows = []
    roles = [
        {"value": r['role_key'], "label": r['label'], "access": r['access'], "color": r['color'], "sort_order": r['sort_order']}
        for r in rows
    ]
    set_cached_response("officer-roles:list", roles, ttl=10)
    return roles


def role_access(role: Optional[str]) -> str:
    """What an officer with this role sees (falls back to the built-in rules)."""
    role = role or 'officer'
    for r in _list_officer_roles():
        if r['value'] == role:
            return r['access'] if r['access'] in ROLE_ACCESS_LEVELS else 'assigned'
    return BUILTIN_ROLE_ACCESS.get(role, 'assigned')


def _clean_role_input(payload: OfficerRoleIn):
    label = re.sub(r'\s+', ' ', payload.label or '').strip()
    if not label:
        raise HTTPException(status_code=400, detail="Enter the role name")
    if payload.access not in ROLE_ACCESS_LEVELS:
        raise HTTPException(status_code=400, detail="Choose what this role can see")
    color = payload.color if payload.color in ROLE_COLORS else 'green'
    return label, payload.access, color


@app.get("/api/officer-roles")
async def get_officer_roles():
    """Officer roles for the role pickers (Officers, Administration, Super Admin)."""
    return _list_officer_roles()


@app.post("/api/officer-roles")
async def create_officer_role(payload: OfficerRoleIn, current_superadmin = Depends(get_current_superadmin)):
    """Add an officer role (Super Admin only)."""
    label, access, color = _clean_role_input(payload)
    key = re.sub(r'[^a-z0-9]+', '_', label.lower()).strip('_')[:50] or 'role'
    existing = execute_query("SELECT role_key FROM officer_roles WHERE role_key = ? OR label = ?", (key, label), fetch_one=True)
    if existing:
        raise HTTPException(status_code=400, detail="A role with this name already exists")
    order = execute_query("SELECT COALESCE(MAX(sort_order), 0) + 10 AS n FROM officer_roles", fetch_one=True)
    execute_query(
        "INSERT INTO officer_roles (role_key, label, access, color, sort_order) VALUES (?, ?, ?, ?, ?)",
        (key, label, access, color, (order or {}).get('n', 100)),
    )
    clear_cached_responses()
    return {"value": key, "label": label, "access": access, "color": color}


@app.put("/api/officer-roles/{role_key}")
async def update_officer_role_def(role_key: str, payload: OfficerRoleIn, current_superadmin = Depends(get_current_superadmin)):
    """Edit an officer role's name, access or colour (Super Admin only). The key stays, so officers keep the role."""
    label, access, color = _clean_role_input(payload)
    row = execute_query("SELECT role_key FROM officer_roles WHERE role_key = ?", (role_key,), fetch_one=True)
    if not row:
        raise HTTPException(status_code=404, detail="Role not found")
    clash = execute_query("SELECT role_key FROM officer_roles WHERE label = ? AND role_key <> ?", (label, role_key), fetch_one=True)
    if clash:
        raise HTTPException(status_code=400, detail="A role with this name already exists")
    execute_query(
        "UPDATE officer_roles SET label = ?, access = ?, color = ?, updated_at = GETUTCDATE() WHERE role_key = ?",
        (label, access, color, role_key),
    )
    clear_cached_responses()
    return {"value": role_key, "label": label, "access": access, "color": color}


@app.delete("/api/officer-roles/{role_key}")
async def delete_officer_role_def(role_key: str, current_superadmin = Depends(get_current_superadmin)):
    """Remove an officer role no officer uses (Super Admin only). "Officer" is the default and stays."""
    if role_key == 'officer':
        raise HTTPException(status_code=400, detail="Officer is the default role and cannot be removed")
    used = execute_query("SELECT COUNT(*) AS c FROM officers WHERE role = ?", (role_key,), fetch_one=True)
    if used and used.get('c'):
        raise HTTPException(status_code=400, detail=f"{used['c']} officer(s) have this role. Change their role first.")
    execute_query("DELETE FROM officer_roles WHERE role_key = ?", (role_key,))
    clear_cached_responses()
    return {"message": "Role removed"}


@app.get("/api/officers")
async def get_officers(authorization: str = Header(None)):
    """Get all officers (an admin limited to one temple gets that temple's and the all-temple officers)."""
    scope = admin_scope_from_header(authorization)
    if scope:
        return [o for o in await get_officers(None) if not o['temple_id'] or _same_id(o['temple_id'], scope)]
    cache_key = "officers:list"
    cached = get_cached_response(cache_key)
    if cached is not None:
        return cached

    officers = execute_query(
        "SELECT id, name, email, mobile, temple_id, temple_name, role, permissions, created_at FROM officers ORDER BY created_at DESC",
        fetch_all=True,
    )
    response = [
        {
            "id": str(o['id']),
            "name": o['name'],
            "email": o['email'],
            "mobile": o['mobile'],
            "temple_id": str(o['temple_id']) if o['temple_id'] else None,
            "temple_name": o['temple_name'],
            "role": o['role'] or 'officer',
            "permissions": json.loads(o['permissions']) if o['permissions'] else ['view_feedback', 'update_status'],
            "created_at": o['created_at'].isoformat() if o['created_at'] else None
        }
        for o in officers
    ]
    set_cached_response(cache_key, response)
    return response

@app.post("/api/officers")
async def create_officer(officer: OfficerCreate, current_admin = Depends(get_current_admin)):
    """Create a new officer"""
    # Check if email exists
    existing = execute_query("SELECT id FROM officers WHERE email = ?", (officer.email,), fetch_one=True)
    if existing:
        raise HTTPException(status_code=400, detail="Email already exists")
    
    scope = _admin_temple_id(current_admin.get('id')) if current_admin.get('role') == 'admin' else None
    if scope:
        officer.temple_id = scope  # a temple admin adds officers only for their temple
    if current_admin.get('role') != 'superadmin':
        # Only the Super Admin gives roles and permissions; others add officers with the defaults.
        officer.role = 'officer'
        officer.permissions = ['view_feedback', 'update_status']

    # Get temple name
    temple_name = None
    if officer.temple_id in ('all', '', None):
        if officer.temple_id == 'all':
            temple_name = 'All Temples'
        officer.temple_id = None
    else:
        temple = execute_query("SELECT name FROM temples WHERE id = ?", (officer.temple_id,), fetch_one=True)
        if temple:
            temple_name = temple['name']
    
    mobile = normalize_mobile(officer.mobile)
    officer_id = str(uuid.uuid4())
    hashed_pw = hash_password(officer.password)
    permissions_json = json.dumps(officer.permissions or ['view_feedback', 'update_status'])

    execute_query(
        """INSERT INTO officers (id, name, email, mobile, password, temple_id, temple_name, role, permissions)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (officer_id, officer.name, officer.email, mobile, hashed_pw, officer.temple_id, temple_name, officer.role or 'officer', permissions_json)
    )

    return {
        "id": officer_id,
        "name": officer.name,
        "email": officer.email,
        "mobile": mobile,
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
    if officer.temple_id in ('all', '', None):
        if officer.temple_id == 'all':
            temple_name = 'All Temples'
        officer.temple_id = None
    else:
        temple = execute_query("SELECT name FROM temples WHERE id = ?", (officer.temple_id,), fetch_one=True)
        if temple:
            temple_name = temple['name']

    if current_admin.get('role') != 'superadmin':
        # Roles and permissions are changed only by the Super Admin; keep the officer's current ones.
        current = execute_query("SELECT role, permissions FROM officers WHERE id = ?", (officer_id,), fetch_one=True) or {}
        officer.role = current.get('role') or 'officer'
        try:
            officer.permissions = json.loads(current['permissions']) if current.get('permissions') else None
        except Exception:
            officer.permissions = None

    permissions_json = json.dumps(officer.permissions or ['view_feedback', 'update_status'])
    mobile = normalize_mobile(officer.mobile)

    if officer.password:
        hashed_pw = hash_password(officer.password)
        execute_query(
            """UPDATE officers
               SET name = ?, email = ?, mobile = ?, password = ?, temple_id = ?, temple_name = ?, role = ?, permissions = ?, updated_at = GETUTCDATE()
               WHERE id = ?""",
            (officer.name, officer.email, mobile, hashed_pw, officer.temple_id, temple_name, officer.role or 'officer', permissions_json, officer_id)
        )
    else:
        execute_query(
            """UPDATE officers
               SET name = ?, email = ?, mobile = ?, temple_id = ?, temple_name = ?, role = ?, permissions = ?, updated_at = GETUTCDATE()
               WHERE id = ?""",
            (officer.name, officer.email, mobile, officer.temple_id, temple_name, officer.role or 'officer', permissions_json, officer_id)
        )

    return {
        "id": officer_id,
        "name": officer.name,
        "email": officer.email,
        "mobile": mobile,
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
async def update_officer_role(officer_id: str, role_update: OfficerRoleUpdate, current_superadmin = Depends(get_current_superadmin)):
    """Update an officer's name, role and permissions (Super Admin only)"""
    existing = execute_query("SELECT id FROM officers WHERE id = ?", (officer_id,), fetch_one=True)
    if not existing:
        raise HTTPException(status_code=404, detail="Officer not found")
    permissions_json = json.dumps(role_update.permissions)
    name = re.sub(r'\s+', ' ', role_update.name or '').strip() if role_update.name is not None else None
    if role_update.name is not None and not name:
        raise HTTPException(status_code=400, detail="Enter the officer name")

    if name:
        execute_query(
            "UPDATE officers SET name = ?, role = ?, permissions = ?, updated_at = GETUTCDATE() WHERE id = ?",
            (name, role_update.role, permissions_json, officer_id)
        )
    else:
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
    """Get all services."""
    cache_key = "services:list"
    cached = get_cached_response(cache_key)
    if cached is not None:
        return cached

    services = execute_query(
        "SELECT id, name, display_order, created_at FROM services WHERE is_active = 1 ORDER BY display_order",
        fetch_all=True,
    )
    response = [
        {
            "id": str(s['id']),
            "name": s['name'],
            "order": s['display_order'],
            "created_at": s['created_at'].isoformat() if s['created_at'] else None
        }
        for s in services
    ]
    set_cached_response(cache_key, response)
    return response

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
    officer_id: Optional[str] = None,
    limit: Optional[int] = Query(None, ge=1, le=FEEDBACK_QUERY_LIMIT_MAX),
    offset: int = Query(0, ge=0),
    authorization: str = Header(None),
):
    """Get feedback quickly with optional filters and pagination."""
    scope = admin_scope_from_header(authorization)
    if scope:
        temple_id = scope  # an admin limited to one temple sees only that temple's feedback
    return _query_feedback(
        temple_id=temple_id,
        status=status,
        officer_id=officer_id,
        limit=limit,
        offset=offset,
    )


def _query_feedback(
    temple_id: Optional[str] = None,
    status: Optional[str] = None,
    officer_id: Optional[str] = None,
    limit: Optional[int] = None,
    offset: int = 0,
):
    """Internal helper that returns feedback list (safe to call from other handlers)."""
    cache_key = f"feedback:list:{temple_id or 'all'}:{status or 'all'}:{officer_id or 'all'}:{limit or 'all'}:{offset}"
    cached = get_cached_response(cache_key)
    if cached is not None:
        return cached

    query = """
        SELECT id, complaint_id, temple_id, temple_name, user_name, user_mobile,
               service, rating, message, COALESCE(video_url, video_path) AS video_url,
               video_path, status, officer_id, officer_name, resolution_notes,
               officer_notes, created_at, resolved_at
        FROM feedback
        WHERE 1=1
    """
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
    if limit is not None:
        query += f" OFFSET {int(offset)} ROWS FETCH NEXT {int(limit)} ROWS ONLY"

    feedback_list = execute_query(query, tuple(params) if params else None, fetch_all=True)
    response_items = [serialize_feedback_item(feedback_item) for feedback_item in feedback_list]
    set_cached_response(cache_key, response_items, ttl=5)
    return response_items


@app.get("/api/feedback/officer")
async def get_officer_feedback(current_officer = Depends(get_current_officer)):
    """Get feedback for current officer.

    Scope rules:
      * Commissioner / Asst Commissioner / officers with no temple assignment -> all feedback
      * Supervisor / Executive Officer (eo) -> all feedback for their temple
      * Officer -> only feedback assigned to them
    """
    if not current_officer:
        raise HTTPException(status_code=404, detail="Officer not found")

    temple_id = current_officer.get('temple_id') if isinstance(current_officer, dict) else None
    role = (current_officer.get('role') if isinstance(current_officer, dict) else None) or 'officer'

    access = role_access(role)
    if (not temple_id) or access == 'all':
        return _query_feedback()

    if access == 'temple':
        return _query_feedback(temple_id=str(temple_id))

    officer_id = str(current_officer['id'])
    return _query_feedback(officer_id=officer_id)


@app.get("/api/display/live-feed")
async def get_display_live_feed(limit: int = Query(12, ge=1, le=50)):
    """Public live feed for the display screen with the latest feedback entries."""
    safe_limit = max(1, min(limit, 50))
    cache_key = f"display:live-feed:{safe_limit}"
    cached = get_cached_response(cache_key)
    if cached is not None:
        return cached

    rows = execute_query(
        f"""
        SELECT TOP {safe_limit}
            id, complaint_id, temple_id, temple_name, user_name, user_mobile,
            service, rating, message, COALESCE(video_url, video_path) AS video_url,
            video_path, status, officer_id, officer_name, resolution_notes,
            officer_notes, created_at, resolved_at
        FROM feedback
        ORDER BY created_at DESC
        """,
        fetch_all=True,
    )

    payload = [serialize_feedback_item(row) for row in rows]
    set_cached_response(cache_key, payload, ttl=5)
    return payload

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

    if role == "admin":
        scope = _admin_temple_id(user_id)
        if scope:
            fb = execute_query("SELECT temple_id FROM feedback WHERE id = ?", (feedback_id,), fetch_one=True)
            if not fb or not _same_id(fb.get('temple_id'), scope):
                raise HTTPException(status_code=403, detail="This feedback belongs to another temple")

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
    """Assign officer to feedback (Super Admin, or an admin given the feedback_assign permission)"""
    if current_admin.get("role") != "superadmin":
        row = execute_query("SELECT permissions FROM users WHERE id = ?", (current_admin.get("id"),), fetch_one=True)
        try:
            perms = json.loads(row['permissions']) if row and row.get('permissions') else []
        except Exception:
            perms = []
        if "feedback_assign" not in perms:
            raise HTTPException(status_code=403, detail="You do not have permission to assign EO / Officer. Ask the Super Admin.")
        scope = _admin_temple_id(current_admin.get("id"))
        if scope:
            fb = execute_query("SELECT temple_id FROM feedback WHERE id = ?", (feedback_id,), fetch_one=True)
            if not fb or not _same_id(fb.get('temple_id'), scope):
                raise HTTPException(status_code=403, detail="This feedback belongs to another temple")
            off = execute_query("SELECT temple_id FROM officers WHERE id = ?", (assign.officer_id,), fetch_one=True)
            if not off or (off.get('temple_id') and not _same_id(off.get('temple_id'), scope)):
                raise HTTPException(status_code=403, detail="Choose an EO / Officer of your temple")
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
    """Get dashboard statistics with minimal database round-trips."""
    scope = _admin_temple_id(current_admin.get('id')) if current_admin.get('role') == 'admin' else None
    if scope:
        return _temple_stats(scope)
    cache_key = "stats:admin"
    cached = get_cached_response(cache_key)
    if cached is not None:
        return cached

    summary = execute_query(
        """
        SELECT
            (SELECT COUNT(*) FROM temples) AS total_temples,
            (SELECT COUNT(*) FROM officers) AS total_officers,
            COUNT(*) AS total_feedback,
            COALESCE(SUM(CASE WHEN status = 'Pending' THEN 1 ELSE 0 END), 0) AS pending,
            COALESCE(SUM(CASE WHEN status = 'In Progress' THEN 1 ELSE 0 END), 0) AS in_progress,
            COALESCE(SUM(CASE WHEN status = 'Resolved' THEN 1 ELSE 0 END), 0) AS resolved,
            COALESCE(SUM(CASE WHEN status = 'Rejected' THEN 1 ELSE 0 END), 0) AS rejected
        FROM feedback
        """,
        fetch_one=True,
    ) or {}

    stats = {
        "total_temples": summary.get('total_temples', 0),
        "total_officers": summary.get('total_officers', 0),
        "total_feedback": summary.get('total_feedback', 0),
        "pending": summary.get('pending', 0),
        "in_progress": summary.get('in_progress', 0),
        "resolved": summary.get('resolved', 0),
        "rejected": summary.get('rejected', 0),
    }
    
    temple_stats = execute_query(
        """SELECT t.name as temple, COUNT(f.id) as feedback
           FROM temples t
           LEFT JOIN feedback f ON t.id = f.temple_id
           GROUP BY t.id, t.name
           ORDER BY feedback DESC""",
        fetch_all=True
    )
    
    stats["temple_stats"] = [{"_id": t["temple"], "count": t["feedback"]} for t in temple_stats]
    set_cached_response(cache_key, stats, ttl=10)
    return stats


def _temple_stats(temple_id: str):
    """Dashboard numbers for an admin limited to one temple."""
    cache_key = f"stats:temple:{temple_id}"
    cached = get_cached_response(cache_key)
    if cached is not None:
        return cached
    summary = execute_query(
        """
        SELECT
            (SELECT COUNT(*) FROM officers WHERE temple_id = ?) AS total_officers,
            COUNT(*) AS total_feedback,
            COALESCE(SUM(CASE WHEN status = 'Pending' THEN 1 ELSE 0 END), 0) AS pending,
            COALESCE(SUM(CASE WHEN status = 'In Progress' THEN 1 ELSE 0 END), 0) AS in_progress,
            COALESCE(SUM(CASE WHEN status = 'Resolved' THEN 1 ELSE 0 END), 0) AS resolved,
            COALESCE(SUM(CASE WHEN status = 'Rejected' THEN 1 ELSE 0 END), 0) AS rejected
        FROM feedback WHERE temple_id = ?
        """,
        (temple_id, temple_id),
        fetch_one=True,
    ) or {}
    temple = execute_query("SELECT name FROM temples WHERE id = ?", (temple_id,), fetch_one=True)
    stats = {
        "total_temples": 1 if temple else 0,
        "total_officers": summary.get('total_officers', 0),
        "total_feedback": summary.get('total_feedback', 0),
        "pending": summary.get('pending', 0),
        "in_progress": summary.get('in_progress', 0),
        "resolved": summary.get('resolved', 0),
        "rejected": summary.get('rejected', 0),
        "temple_stats": [{"_id": temple['name'], "count": summary.get('total_feedback', 0)}] if temple else [],
    }
    set_cached_response(cache_key, stats, ttl=10)
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
    """Get officer-specific statistics with a single aggregate query."""
    if not current_officer:
        raise HTTPException(status_code=404, detail="Officer not found")

    officer_id = str(current_officer['id'])
    temple_id = current_officer.get('temple_id') if isinstance(current_officer, dict) else None
    role = (current_officer.get('role') if isinstance(current_officer, dict) else None) or 'officer'
    access = role_access(role)
    all_scope = (not temple_id) or access == 'all'
    temple_scope = (not all_scope) and access == 'temple'

    if all_scope:
        cache_key = "stats:officer:all"
    elif temple_scope:
        cache_key = f"stats:officer:temple:{temple_id}"
    else:
        cache_key = f"stats:officer:{officer_id}"

    cached = get_cached_response(cache_key)
    if cached is not None:
        return cached

    if all_scope:
        summary = execute_query(
            """
            SELECT
                COUNT(*) AS total_assigned,
                COALESCE(SUM(CASE WHEN status = 'Pending' THEN 1 ELSE 0 END), 0) AS pending,
                COALESCE(SUM(CASE WHEN status = 'In Progress' THEN 1 ELSE 0 END), 0) AS in_progress,
                COALESCE(SUM(CASE WHEN status = 'Resolved' THEN 1 ELSE 0 END), 0) AS resolved
            FROM feedback
            """,
            fetch_one=True,
        ) or {}
    elif temple_scope:
        summary = execute_query(
            """
            SELECT
                COUNT(*) AS total_assigned,
                COALESCE(SUM(CASE WHEN status = 'Pending' THEN 1 ELSE 0 END), 0) AS pending,
                COALESCE(SUM(CASE WHEN status = 'In Progress' THEN 1 ELSE 0 END), 0) AS in_progress,
                COALESCE(SUM(CASE WHEN status = 'Resolved' THEN 1 ELSE 0 END), 0) AS resolved
            FROM feedback
            WHERE temple_id = ?
            """,
            (str(temple_id),),
            fetch_one=True,
        ) or {}
    else:
        summary = execute_query(
            """
            SELECT
                COUNT(*) AS total_assigned,
                COALESCE(SUM(CASE WHEN status = 'Pending' THEN 1 ELSE 0 END), 0) AS pending,
                COALESCE(SUM(CASE WHEN status = 'In Progress' THEN 1 ELSE 0 END), 0) AS in_progress,
                COALESCE(SUM(CASE WHEN status = 'Resolved' THEN 1 ELSE 0 END), 0) AS resolved
            FROM feedback
            WHERE officer_id = ?
            """,
            (officer_id,),
            fetch_one=True,
        ) or {}

    stats = {
        "total_assigned": summary.get('total_assigned', 0),
        "pending": summary.get('pending', 0),
        "in_progress": summary.get('in_progress', 0),
        "resolved": summary.get('resolved', 0),
    }
    set_cached_response(cache_key, stats, ttl=10)
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
    """Get all WhatsApp logs (an admin limited to one temple gets only that temple's)."""
    scope = _admin_temple_id(current_admin.get('id')) if current_admin.get('role') == 'admin' else None
    cache_key = f"whatsapp-logs:list:{scope or 'all'}"
    cached = get_cached_response(cache_key)
    if cached is not None:
        return cached

    if scope:
        logs = execute_query(
            "SELECT id, feedback_id, phone_number, message, status, message_type, created_at FROM whatsapp_logs "
            "WHERE feedback_id IN (SELECT id FROM feedback WHERE temple_id = ?) ORDER BY created_at DESC",
            (scope,),
            fetch_all=True,
        )
    else:
        logs = execute_query(
            "SELECT id, feedback_id, phone_number, message, status, message_type, created_at FROM whatsapp_logs ORDER BY created_at DESC",
            fetch_all=True,
        )
    response = [
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
    set_cached_response(cache_key, response, ttl=10)
    return response


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
# KIOSK SCREENSAVER ENDPOINTS
# =====================================================

KIOSK_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}
KIOSK_VIDEO_EXTENSIONS = {'.mp4', '.webm'}
KIOSK_MAX_IMAGE_BYTES = 10 * 1024 * 1024
KIOSK_MAX_VIDEO_BYTES = 100 * 1024 * 1024
KIOSK_DEFAULT_SETTINGS = {"idle_seconds": 60, "image_seconds": 10}
KIOSK_PLAYLIST_PATH = os.path.join(UPLOAD_DIR, 'kiosk', 'playlist.json')
KIOSK_APP_PATH = os.path.join(UPLOAD_DIR, 'app', 'temple-feedback.apk')


class KioskSettings(BaseModel):
    idle_seconds: int = Field(ge=10, le=3600)
    image_seconds: int = Field(ge=3, le=300)


class KioskMediaOrder(BaseModel):
    ids: List[str]


def ensure_kiosk_schema():
    """Create the kiosk tables without ever blocking the rest of startup.

    Every gunicorn worker runs startup at once, so another worker can win the
    race between the existence check and the create (SQL errors 2714, 2627, 2705).
    """
    statements = [
        (
            """
            IF OBJECT_ID('kiosk_media', 'U') IS NULL
            BEGIN
                CREATE TABLE kiosk_media (
                    id NVARCHAR(36) NOT NULL PRIMARY KEY,
                    file_path NVARCHAR(500) NOT NULL,
                    media_type NVARCHAR(10) NOT NULL,
                    display_order INT NOT NULL DEFAULT 0,
                    created_at DATETIME2 NOT NULL DEFAULT GETUTCDATE()
                );
            END
            """,
            None,
        ),
        (
            """
            IF OBJECT_ID('kiosk_settings', 'U') IS NULL
            BEGIN
                CREATE TABLE kiosk_settings (
                    id INT NOT NULL PRIMARY KEY,
                    idle_seconds INT NOT NULL,
                    image_seconds INT NOT NULL
                );
            END
            """,
            None,
        ),
        (
            """
            IF NOT EXISTS (SELECT 1 FROM kiosk_settings WHERE id = 1)
            BEGIN
                INSERT INTO kiosk_settings (id, idle_seconds, image_seconds) VALUES (1, ?, ?);
            END
            """,
            (KIOSK_DEFAULT_SETTINGS['idle_seconds'], KIOSK_DEFAULT_SETTINGS['image_seconds']),
        ),
        (
            """
            IF COL_LENGTH('kiosk_media', 'temple_id') IS NULL
            BEGIN
                ALTER TABLE kiosk_media ADD temple_id NVARCHAR(36) NULL;
            END
            """,
            None,
        ),
    ]
    for query, params in statements:
        try:
            execute_query(query, params)
        except HTTPException as exc:
            if any(code in str(exc.detail) for code in ('2714', '2627', '2705')):
                logger.info('Kiosk schema already created by another worker')
            else:
                logger.error('Kiosk schema setup failed: %s', exc.detail)


def rebuild_kiosk_playlist() -> dict:
    """Publish the playlist from SQL to a shared JSON file.

    Tablets poll the playlist around the clock, so reads come from this file
    to keep that traffic off the database.
    """
    rows = execute_query(
        "SELECT id, file_path, media_type, temple_id FROM kiosk_media ORDER BY display_order, created_at",
        fetch_all=True,
    ) or []
    settings = execute_query(
        "SELECT idle_seconds, image_seconds FROM kiosk_settings WHERE id = 1",
        fetch_one=True,
    ) or KIOSK_DEFAULT_SETTINGS
    playlist = {
        "idle_seconds": settings['idle_seconds'],
        "image_seconds": settings['image_seconds'],
        "media": [
            {
                "id": str(row['id']),
                "path": row['file_path'],
                "type": row['media_type'],
                "temple_id": str(row['temple_id']).lower() if row['temple_id'] else None,
            }
            for row in rows
        ],
    }

    temp_path = f"{KIOSK_PLAYLIST_PATH}.{uuid.uuid4()}.tmp"
    try:
        os.makedirs(os.path.dirname(KIOSK_PLAYLIST_PATH), exist_ok=True)
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(playlist, f)
        os.replace(temp_path, KIOSK_PLAYLIST_PATH)
    except OSError as exc:
        logger.error('Failed to publish kiosk playlist: %s', exc)
    return playlist


def read_kiosk_playlist() -> dict:
    try:
        with open(KIOSK_PLAYLIST_PATH, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return rebuild_kiosk_playlist()


@app.get("/api/kiosk/playlist")
async def get_kiosk_playlist(temple_id: Optional[str] = None):
    """Public: what a registered tablet shows while idle.

    A temple with its own media shows only that; any other tablet shows the
    media uploaded for all temples.
    """
    playlist = read_kiosk_playlist()
    media = playlist['media']
    own_media = [m for m in media if temple_id and m.get('temple_id') == temple_id.lower()]
    shared_media = [m for m in media if not m.get('temple_id')]
    return {**playlist, "media": own_media or shared_media}


@app.get("/api/kiosk/app/info")
async def get_kiosk_app_info():
    """Public: whether the tablet APK has been published on this server."""
    try:
        stat = os.stat(KIOSK_APP_PATH)
    except OSError:
        return {"available": False}
    return {
        "available": True,
        "size": stat.st_size,
        "updated_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
    }


@app.get("/api/kiosk/app")
async def download_kiosk_app():
    """Public, so a tablet browser can install the app without an admin login."""
    if not os.path.isfile(KIOSK_APP_PATH):
        raise HTTPException(status_code=404, detail="Tablet app has not been published")
    return FileResponse(
        KIOSK_APP_PATH,
        media_type='application/vnd.android.package-archive',
        filename='temple-feedback.apk',
        # Cloudflare caches .apk files by default, which would keep serving an old version.
        headers={'Cache-Control': 'no-store'},
    )


@app.get("/api/kiosk/media")
async def list_kiosk_media(current_superadmin = Depends(get_current_superadmin)):
    """Everything uploaded for every temple (Super Admin only)."""
    return read_kiosk_playlist()


@app.post("/api/kiosk/media")
async def upload_kiosk_media(
    file: UploadFile = File(...),
    temple_id: Optional[str] = Form(None),
    current_superadmin = Depends(get_current_superadmin),
):
    """Add an image or video to the kiosk screensaver (Super Admin only).

    Without temple_id the item plays on every temple without its own media.
    """
    if temple_id:
        try:
            temple_id = str(uuid.UUID(temple_id))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid temple")
        if not execute_query("SELECT id FROM temples WHERE id = ?", (temple_id,), fetch_one=True):
            raise HTTPException(status_code=404, detail="Temple not found")
    else:
        temple_id = None

    file_ext = os.path.splitext(file.filename or '')[1].lower()
    if file_ext in KIOSK_IMAGE_EXTENSIONS:
        media_type, max_bytes = 'image', KIOSK_MAX_IMAGE_BYTES
    elif file_ext in KIOSK_VIDEO_EXTENSIONS:
        media_type, max_bytes = 'video', KIOSK_MAX_VIDEO_BYTES
    else:
        raise HTTPException(status_code=400, detail="Use a JPG, PNG, WEBP or GIF image, or an MP4 or WEBM video")

    file_content = await file.read()
    if not file_content:
        raise HTTPException(status_code=400, detail="File is empty")
    if len(file_content) > max_bytes:
        raise HTTPException(status_code=400, detail=f"{media_type.capitalize()} must be {max_bytes // (1024 * 1024)} MB or smaller")

    output_name = f"kiosk/{uuid.uuid4()}{file_ext}"
    path = get_primary_upload_path(output_name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    async with aiofiles.open(path, 'wb') as f:
        await f.write(file_content)

    save_upload_record(output_name, file.filename, file_ext, len(file_content), current_superadmin.get('id'), file_content)
    next_order = execute_query(
        "SELECT ISNULL(MAX(display_order), 0) + 1 AS next_order FROM kiosk_media",
        fetch_one=True,
    )['next_order']
    execute_query(
        "INSERT INTO kiosk_media (id, file_path, media_type, display_order, temple_id) VALUES (?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), output_name, media_type, next_order, temple_id),
    )
    return rebuild_kiosk_playlist()


@app.put("/api/kiosk/media/order")
async def reorder_kiosk_media(payload: KioskMediaOrder, current_superadmin = Depends(get_current_superadmin)):
    """Set the screensaver play order (Super Admin only)."""
    for position, media_id in enumerate(payload.ids, start=1):
        execute_query("UPDATE kiosk_media SET display_order = ? WHERE id = ?", (position, media_id))
    return rebuild_kiosk_playlist()


@app.delete("/api/kiosk/media/{media_id}")
async def delete_kiosk_media(media_id: str, current_superadmin = Depends(get_current_superadmin)):
    """Remove an image or video from the screensaver (Super Admin only)."""
    row = execute_query("SELECT file_path FROM kiosk_media WHERE id = ?", (media_id,), fetch_one=True)
    if not row:
        raise HTTPException(status_code=404, detail="Media not found")

    execute_query("DELETE FROM kiosk_media WHERE id = ?", (media_id,))
    execute_query("DELETE FROM file_uploads WHERE file_path = ?", (row['file_path'],))
    try:
        os.remove(get_primary_upload_path(row['file_path']))
    except OSError as exc:
        logger.warning('Could not remove kiosk file %s: %s', row['file_path'], exc)
    return rebuild_kiosk_playlist()


@app.put("/api/kiosk/settings")
async def update_kiosk_settings(payload: KioskSettings, current_superadmin = Depends(get_current_superadmin)):
    """Set screensaver timings (Super Admin only)."""
    execute_query(
        "UPDATE kiosk_settings SET idle_seconds = ?, image_seconds = ? WHERE id = 1",
        (payload.idle_seconds, payload.image_seconds),
    )
    return rebuild_kiosk_playlist()

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
    
    # Test database connection (warm up Azure SQL serverless if it is paused)
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
            IF COL_LENGTH('feedback', 'video_path') IS NULL
            BEGIN
                ALTER TABLE feedback ADD video_path NVARCHAR(MAX) NULL;
            END
            """
        )

        execute_query(
            """
            IF COL_LENGTH('users', 'permissions') IS NULL
            BEGIN
                ALTER TABLE users ADD permissions NVARCHAR(MAX) NULL;
            END
            """
        )

        ensure_kiosk_schema()
        ensure_account_schema()

        # Backfill: any existing admin without explicit permissions gets full access
        execute_query(
            """
            UPDATE users
            SET permissions = ?
            WHERE permissions IS NULL OR LTRIM(RTRIM(permissions)) = ''
            """,
            (json.dumps(ALL_ADMIN_PERMISSIONS),),
        )

        # Bootstrap: if no superadmin exists yet, promote the oldest admin to Super Admin
        existing_super = execute_query(
            "SELECT TOP 1 id FROM users WHERE role = 'superadmin'", fetch_one=True
        )
        if not existing_super:
            execute_query(
                """
                UPDATE users
                SET role = 'superadmin', permissions = ?
                WHERE id = (
                    SELECT TOP 1 id FROM users ORDER BY created_at ASC
                )
                """,
                (json.dumps(ALL_ADMIN_PERMISSIONS),),
            )

        execute_query(
            """
            UPDATE feedback
            SET video_path = video_url
            WHERE video_url IS NOT NULL
              AND (video_path IS NULL OR video_path <> video_url);
            """
        )

        ensure_database_indexes()

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

"""One-time backfill for upload blobs stored in Azure SQL.

Copies existing logo/video files from disk into the file_uploads.file_blob column so
older records remain available even if App Service filesystem copies disappear.
"""

from __future__ import annotations

import argparse
import mimetypes
import os
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Optional
from urllib.parse import unquote, urlparse

import pyodbc
from dotenv import load_dotenv


load_dotenv()


DB_SERVER = os.environ.get('DB_SERVER', 'DESKTOP-JGCUNUE\\SQLEXPRESS')
DB_NAME = os.environ.get('DB_NAME', 'ts_feedbackdb')
DB_USER = os.environ.get('DB_USER', 'ts_feedback_user')
DB_PASSWORD = os.environ.get('DB_PASSWORD', 'TsFeedback@2026!')
LOCAL_DB_SERVER = os.environ.get('LOCAL_DB_SERVER', '')
LOCAL_DB_NAME = os.environ.get('LOCAL_DB_NAME', 'ts_feedbackdb')
LOCAL_DB_USER = os.environ.get('LOCAL_DB_USER', 'ts_feedback_user')
LOCAL_DB_PASSWORD = os.environ.get('LOCAL_DB_PASSWORD', 'TsFeedback@2026!')
DB_PORT = os.environ.get('DB_PORT', '1433')
DB_CONNECTION_TIMEOUT = int(os.environ.get('DB_CONNECTION_TIMEOUT', '5'))
DB_LOCAL_FALLBACK = os.environ.get('DB_LOCAL_FALLBACK', 'true').strip().lower() in {'1', 'true', 'yes', 'on'}
IS_AZURE_APP = bool(os.environ.get('WEBSITE_SITE_NAME'))

AVAILABLE_SQL_DRIVERS = [driver for driver in pyodbc.drivers() if 'SQL Server' in driver]
SQL_DRIVER = os.environ.get('DB_DRIVER') or (
    'ODBC Driver 18 for SQL Server'
    if 'ODBC Driver 18 for SQL Server' in AVAILABLE_SQL_DRIVERS
    else 'ODBC Driver 17 for SQL Server'
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill uploaded files into Azure SQL blob storage")
    parser.add_argument('--dry-run', action='store_true', help='Report actions without writing to SQL Server')
    parser.add_argument('--limit', type=int, default=0, help='Maximum number of paths to process')
    parser.add_argument('--include-existing', action='store_true', help='Also overwrite rows that already have file_blob data')
    parser.add_argument('--verbose', action='store_true', help='Print each processed path')
    return parser.parse_args()


def is_azure_sql_server(server_name: str) -> bool:
    return '.database.windows.net' in (server_name or '').lower()


def build_connection_string(server_name: str) -> str:
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


def get_connection_candidates() -> list[str]:
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


def get_connection() -> pyodbc.Connection:
    last_error: Exception | None = None
    for server_name in get_connection_candidates():
        try:
            return pyodbc.connect(build_connection_string(server_name), timeout=DB_CONNECTION_TIMEOUT)
        except Exception as exc:
            last_error = exc

    raise RuntimeError(f'Unable to connect to SQL Server: {last_error}')


def normalize_upload_path(file_path: str) -> str:
    parsed = urlparse(str(file_path))
    raw_path = parsed.path or str(file_path)
    normalized = unquote(raw_path).replace('\\', '/').strip()

    for marker in ('/api/files/', '/uploads/'):
        if marker in normalized:
            normalized = normalized.split(marker, 1)[1]
            break

    normalized = normalized.lstrip('/')
    while normalized.startswith('uploads/'):
        normalized = normalized[len('uploads/'):]

    normalized = os.path.normpath(normalized).replace('\\', '/')
    if normalized in ('', '.', '..') or normalized.startswith('../') or os.path.isabs(normalized):
        raise ValueError(f'Invalid upload path: {file_path}')

    return normalized


def get_upload_roots() -> list[Path]:
    script_dir = Path(__file__).resolve().parent
    azure_site = os.environ.get('WEBSITE_SITE_NAME')
    default_upload_dir = '/home/uploads' if azure_site else 'uploads'
    configured_upload_dir = os.environ.get('UPLOAD_DIR', default_upload_dir)

    roots = [
        Path(configured_upload_dir),
        script_dir / 'uploads',
        Path.cwd() / 'uploads',
    ]
    if azure_site:
        roots.append(Path('/home/site/wwwroot/uploads'))

    unique_roots: list[Path] = []
    seen: set[str] = set()
    for root in roots:
        resolved = str(root.resolve(strict=False))
        if resolved not in seen:
            seen.add(resolved)
            unique_roots.append(root)
    return unique_roots


def resolve_disk_path(normalized_path: str, upload_roots: list[Path]) -> Optional[Path]:
    for root in upload_roots:
        candidate = (root / normalized_path).resolve(strict=False)
        try:
            candidate.relative_to(root.resolve(strict=False))
        except ValueError:
            continue
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


def infer_file_type(normalized_path: str) -> str:
    ext = Path(normalized_path).suffix.lower()
    if ext:
        return ext
    guessed, _ = mimetypes.guess_type(normalized_path)
    return guessed or 'application/octet-stream'


def ensure_blob_column(cursor: pyodbc.Cursor, dry_run: bool) -> None:
    sql = """
    IF COL_LENGTH('file_uploads', 'file_blob') IS NULL
    BEGIN
        ALTER TABLE file_uploads ADD file_blob VARBINARY(MAX) NULL;
    END
    """
    if not dry_run:
        cursor.execute(sql)


def fetch_candidate_paths(cursor: pyodbc.Cursor) -> dict[str, dict]:
    candidates: dict[str, dict] = {}

    def merge_candidate(path_value: Optional[str], source: str, original_filename: Optional[str] = None, file_type: Optional[str] = None, file_size: Optional[int] = None, uploaded_by: Optional[str] = None):
        if not path_value:
            return
        try:
            normalized = normalize_upload_path(path_value)
        except ValueError:
            return

        existing = candidates.setdefault(
            normalized,
            {
                'file_path': normalized,
                'source': source,
                'original_filename': original_filename,
                'file_type': file_type,
                'file_size': file_size,
                'uploaded_by': uploaded_by,
            },
        )
        if not existing.get('original_filename') and original_filename:
            existing['original_filename'] = original_filename
        if not existing.get('file_type') and file_type:
            existing['file_type'] = file_type
        if not existing.get('file_size') and file_size:
            existing['file_size'] = file_size
        if not existing.get('uploaded_by') and uploaded_by:
            existing['uploaded_by'] = uploaded_by

    cursor.execute(
        "SELECT file_path, original_filename, file_type, file_size, uploaded_by FROM file_uploads WHERE file_path IS NOT NULL"
    )
    for row in cursor.fetchall():
        merge_candidate(row.file_path, 'file_uploads', row.original_filename, row.file_type, row.file_size, row.uploaded_by)

    cursor.execute("SELECT video_url FROM feedback WHERE video_url IS NOT NULL AND LTRIM(RTRIM(video_url)) <> ''")
    for row in cursor.fetchall():
        merge_candidate(row.video_url, 'feedback', file_type=infer_file_type(row.video_url))

    cursor.execute("SELECT logo_path FROM temples WHERE logo_path IS NOT NULL AND LTRIM(RTRIM(logo_path)) <> ''")
    for row in cursor.fetchall():
        merge_candidate(row.logo_path, 'temples', file_type=infer_file_type(row.logo_path))

    return candidates


def fetch_existing_upload_row(cursor: pyodbc.Cursor, normalized_path: str) -> Optional[dict]:
    cursor.execute(
        """
        SELECT TOP 1 id, original_filename, file_type, file_size, uploaded_by, file_blob
        FROM file_uploads
        WHERE file_path = ?
        ORDER BY created_at DESC
        """,
        (normalized_path,),
    )
    row = cursor.fetchone()
    if not row:
        return None
    return {
        'id': str(row.id),
        'original_filename': row.original_filename,
        'file_type': row.file_type,
        'file_size': row.file_size,
        'uploaded_by': row.uploaded_by,
        'has_blob': row.file_blob is not None,
    }


def update_blob(cursor: pyodbc.Cursor, row_id: str, file_content: bytes, file_size: int) -> None:
    cursor.execute(
        "UPDATE file_uploads SET file_blob = ?, file_size = ? WHERE id = ?",
        (pyodbc.Binary(file_content), file_size, row_id),
    )


def insert_blob(cursor: pyodbc.Cursor, metadata: dict, file_content: bytes, file_size: int) -> None:
    cursor.execute(
        """
        INSERT INTO file_uploads (
            id, filename, original_filename, file_path, file_type, file_size, uploaded_by, file_blob, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, GETUTCDATE())
        """,
        (
            str(uuid.uuid4()),
            Path(metadata['file_path']).name,
            metadata.get('original_filename') or Path(metadata['file_path']).name,
            metadata['file_path'],
            metadata.get('file_type') or infer_file_type(metadata['file_path']),
            file_size,
            metadata.get('uploaded_by'),
            pyodbc.Binary(file_content),
        ),
    )


def run_backfill(
    dry_run: bool = False,
    limit: int = 0,
    include_existing: bool = False,
    verbose: bool = False,
    log: Optional[Callable[[str], None]] = None,
) -> dict:
    upload_roots = get_upload_roots()

    def emit(message: str) -> None:
        if log:
            log(message)
        else:
            print(message)

    conn = get_connection()
    cursor = conn.cursor()

    found_candidates = 0
    processed = 0
    written = 0
    skipped_missing = 0
    skipped_existing = 0
    failed = 0

    try:
        ensure_blob_column(cursor, dry_run)
        candidates = fetch_candidate_paths(cursor)
        paths = sorted(candidates)
        found_candidates = len(paths)
        if limit > 0:
            paths = paths[:limit]

        emit(f'Found {len(paths)} candidate upload paths')
        for normalized_path in paths:
            metadata = candidates[normalized_path]
            processed += 1
            existing_row = fetch_existing_upload_row(cursor, normalized_path)

            if existing_row and existing_row['has_blob'] and not include_existing:
                skipped_existing += 1
                if verbose:
                    emit(f'SKIP existing blob: {normalized_path}')
                continue

            disk_path = resolve_disk_path(normalized_path, upload_roots)
            if not disk_path:
                skipped_missing += 1
                emit(f'MISSING file on disk: {normalized_path}')
                continue

            try:
                file_content = disk_path.read_bytes()
            except OSError as exc:
                failed += 1
                emit(f'ERROR reading {normalized_path}: {exc}')
                continue

            if dry_run:
                action = 'UPDATE' if existing_row else 'INSERT'
                emit(f'{action} {normalized_path} <- {disk_path}')
                continue

            try:
                if existing_row:
                    update_blob(cursor, existing_row['id'], file_content, len(file_content))
                else:
                    insert_blob(cursor, metadata, file_content, len(file_content))
                written += 1
                if verbose:
                    emit(f'OK {normalized_path}')
            except pyodbc.Error as exc:
                failed += 1
                emit(f'ERROR writing {normalized_path}: {exc}')

        if dry_run:
            conn.rollback()
        else:
            conn.commit()

        emit(
            f'Processed={processed} Written={written} '
            f'SkippedExisting={skipped_existing} SkippedMissing={skipped_missing} Failed={failed}'
        )
        return {
            'dry_run': dry_run,
            'limit': limit,
            'include_existing': include_existing,
            'verbose': verbose,
            'found_candidates': found_candidates,
            'processed': processed,
            'written': written,
            'skipped_existing': skipped_existing,
            'skipped_missing': skipped_missing,
            'failed': failed,
            'success': failed == 0,
        }
    finally:
        cursor.close()
        conn.close()


def main() -> int:
    args = parse_args()
    result = run_backfill(
        dry_run=args.dry_run,
        limit=args.limit,
        include_existing=args.include_existing,
        verbose=args.verbose,
    )
    return 0 if result['success'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
import os
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SharedFile
from app.services.auth import generate_short_code

MAX_UPLOAD_BYTES = 25 * 1024 * 1024
IMAGE_QUOTA_BYTES = 500 * 1024 * 1024

# (mime_type, magic-byte signatures the content must start with — None means
# the type has no reliable magic-byte signature to sniff; txt/csv fall back
# to a null-byte check instead, see validate_upload()).
FILE_EXTENSIONS: dict[str, tuple[str, tuple[bytes, ...] | None]] = {
    "pdf": ("application/pdf", (b"%PDF-",)),
    "txt": ("text/plain", None),
    "csv": ("text/csv", None),
    "zip": ("application/zip", (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")),
    "docx": (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        (b"PK\x03\x04",),
    ),
    "xlsx": (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        (b"PK\x03\x04",),
    ),
    "pptx": (
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        (b"PK\x03\x04",),
    ),
}

IMAGE_EXTENSIONS: dict[str, tuple[str, tuple[bytes, ...] | None]] = {
    "jpg": ("image/jpeg", (b"\xff\xd8\xff",)),
    "jpeg": ("image/jpeg", (b"\xff\xd8\xff",)),
    "png": ("image/png", (b"\x89PNG\r\n\x1a\n",)),
    "gif": ("image/gif", (b"GIF87a", b"GIF89a")),
    "webp": ("image/webp", None),  # RIFF....WEBP checked separately (signature isn't a fixed prefix)
}


def _storage_dir() -> Path:
    # Read at call-time (not cached at import) so tests can point this at a
    # scratch tmp_path via monkeypatch.setenv without reloading the module.
    d = Path(os.getenv("FILE_STORAGE_DIR", "data/files"))
    d.mkdir(parents=True, exist_ok=True)
    return d


def validate_upload(kind: str, filename: str, data: bytes) -> str:
    """Validate an upload's extension against the kind's allowlist and sniff its
    magic bytes to confirm the content actually matches. Returns the resolved
    mime_type, or raises ValueError with a user-facing message."""
    if kind not in ("image", "file"):
        raise ValueError("kind must be 'image' or 'file'")
    table = IMAGE_EXTENSIONS if kind == "image" else FILE_EXTENSIONS
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in table:
        allowed = ", ".join(sorted(table))
        raise ValueError(f"'.{ext or filename}' is not an allowed {kind} type (allowed: {allowed})")
    mime_type, signatures = table[ext]
    if ext == "webp":
        if not (data[:4] == b"RIFF" and data[8:12] == b"WEBP"):
            raise ValueError("File content does not match a valid webp image")
    elif ext in ("txt", "csv"):
        # Plain text has no magic-byte signature to sniff, but a null byte
        # is never valid in text content — reject binary data renamed to
        # .txt/.csv rather than trusting the extension alone.
        if b"\x00" in data:
            raise ValueError(f"File content does not look like a valid .{ext} file")
    elif signatures is not None and not any(data.startswith(sig) for sig in signatures):
        raise ValueError(f"File content does not match a valid .{ext} file")
    return mime_type


async def read_capped(file: UploadFile, max_bytes: int = MAX_UPLOAD_BYTES) -> bytes:
    """Read an upload in chunks, aborting as soon as it exceeds max_bytes rather
    than buffering an arbitrarily large body into memory first."""
    chunks = bytearray()
    while True:
        chunk = await file.read(1_048_576)
        if not chunk:
            break
        chunks.extend(chunk)
        if len(chunks) > max_bytes:
            raise ValueError(f"File exceeds the {max_bytes // (1024 * 1024)}MB upload limit")
    return bytes(chunks)


async def get_unique_file_code(db: AsyncSession, length: int = 8) -> str:
    for _ in range(10):
        code = generate_short_code(length)
        result = await db.execute(select(SharedFile).where(SharedFile.short_code == code))
        if result.scalar_one_or_none() is None:
            return code
    raise RuntimeError("Failed to generate unique short code after 10 attempts")


async def image_quota_used(db: AsyncSession, user_id: int) -> int:
    total = await db.scalar(
        select(func.coalesce(func.sum(SharedFile.size_bytes), 0)).where(
            SharedFile.user_id == user_id, SharedFile.kind == "image"
        )
    )
    return int(total or 0)


def save_blob(short_code: str, data: bytes) -> str:
    path = _storage_dir() / short_code
    path.write_bytes(data)
    return str(path)


def delete_blob(storage_path: str) -> None:
    Path(storage_path).unlink(missing_ok=True)

from __future__ import annotations

import base64
import ctypes
import sys
from ctypes import wintypes
from typing import Any


class DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]


def _bytes_to_blob(data: bytes) -> DATA_BLOB:
    if not data:
        return DATA_BLOB(0, ctypes.POINTER(ctypes.c_byte)())
    buffer = (ctypes.c_byte * len(data)).from_buffer_copy(data)
    return DATA_BLOB(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte)))


def _blob_to_bytes(blob: DATA_BLOB) -> bytes:
    if not blob.cbData:
        return b""
    pointer = ctypes.cast(blob.pbData, ctypes.POINTER(ctypes.c_char))
    return ctypes.string_at(pointer, blob.cbData)


def _protect_with_dpapi(data: bytes) -> bytes:
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    in_blob = _bytes_to_blob(data)
    out_blob = DATA_BLOB()
    if not crypt32.CryptProtectData(ctypes.byref(in_blob), None, None, None, None, 0, ctypes.byref(out_blob)):
        raise ctypes.WinError()
    try:
        return _blob_to_bytes(out_blob)
    finally:
        if out_blob.pbData:
            kernel32.LocalFree(out_blob.pbData)


def _unprotect_with_dpapi(data: bytes) -> bytes:
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    in_blob = _bytes_to_blob(data)
    out_blob = DATA_BLOB()
    if not crypt32.CryptUnprotectData(ctypes.byref(in_blob), None, None, None, None, 0, ctypes.byref(out_blob)):
        raise ctypes.WinError()
    try:
        return _blob_to_bytes(out_blob)
    finally:
        if out_blob.pbData:
            kernel32.LocalFree(out_blob.pbData)


def protect_text(text: str) -> str:
    raw = text.encode("utf-8")
    if sys.platform == "win32":
        try:
            return base64.b64encode(_protect_with_dpapi(raw)).decode("ascii")
        except Exception:
            pass
    return base64.b64encode(raw).decode("ascii")


def unprotect_text(payload: str) -> str:
    if not payload:
        return ""
    raw = base64.b64decode(payload.encode("ascii"))
    if sys.platform == "win32":
        try:
            return _unprotect_with_dpapi(raw).decode("utf-8")
        except Exception:
            pass
    return raw.decode("utf-8")


def mask_cookie(cookie: str) -> str:
    if not cookie:
        return ""
    if len(cookie) <= 12:
        return "***"
    return f"{cookie[:6]}***{cookie[-4:]}"


def mask_share_url(url: str) -> str:
    if not url:
        return ""
    if len(url) <= 24:
        return url[:8] + "***"
    return f"{url[:20]}***{url[-6:]}"


def mask_hash(value: str) -> str:
    if not value:
        return ""
    return f"{value[:8]}..." if len(value) > 8 else value


def sanitize_log_value(key: str, value: Any) -> Any:
    lowered = key.lower()
    if isinstance(value, str):
        if "cookie" in lowered:
            return mask_cookie(value)
        if "share_url" in lowered or lowered == "url":
            return mask_share_url(value)
        if lowered in {"md5", "sha1"}:
            return mask_hash(value)
    return value


def sanitize_log_extra(extra: dict[str, Any]) -> dict[str, Any]:
    return {key: sanitize_log_value(key, value) for key, value in extra.items()}

"""Storage abstraction.

Everything that reads or writes a "file" (the published catalogue today;
artwork uploads if you wire this in later) goes through a `StorageBackend`
rather than touching the filesystem directly. That's the whole point: swap
`LocalDiskStorage` for an `R2Storage` class that implements the same
interface and nothing else in the app has to change.

The interface is intentionally tiny - just what this project needs:
    - write_bytes / write_json: durable, atomic writes
    - read_bytes / read_json: reads, raising FileNotFoundError if missing
    - exists: existence check
    - key_path: where a key physically lives (used for logging/debugging)

Atomicity: `write_bytes` never lets a reader observe a partially-written
file. It writes to a temp file in the same directory as the destination,
flushes + fsyncs it, then does an `os.replace` onto the final path.
`os.replace` is atomic on POSIX and Windows as long as source and
destination are on the same filesystem - which they are here, since the
temp file is created as a sibling of the destination.
"""

from __future__ import annotations

import json
import os
import tempfile
from abc import ABC, abstractmethod
from typing import Any


class StorageBackend(ABC):
    @abstractmethod
    def write_bytes(self, key: str, data: bytes) -> None: ...

    @abstractmethod
    def read_bytes(self, key: str) -> bytes: ...

    @abstractmethod
    def exists(self, key: str) -> bool: ...

    @abstractmethod
    def key_path(self, key: str) -> str: ...

    def write_json(self, key: str, obj: Any) -> None:
        payload = json.dumps(obj, indent=2, default=str).encode("utf-8")
        self.write_bytes(key, payload)

    def read_json(self, key: str) -> Any:
        return json.loads(self.read_bytes(key))


class LocalDiskStorage(StorageBackend):
    """Local-filesystem storage. Swap for MinIO/R2 in prod by pointing
    STORAGE_ROOT at a mounted bucket, or by writing an R2Storage class with
    the same interface (boto3 / the S3-compatible R2 API) and constructing
    that instead in api/catalog.py and api/publish.py. Nothing else in the
    app needs to know the difference.
    """

    def __init__(self, root: str):
        self.root = os.path.abspath(root)
        os.makedirs(self.root, exist_ok=True)

    def key_path(self, key: str) -> str:
        # Keys are always forward-slash paths relative to the storage root.
        # Reject anything that could escape the root.
        normalized = os.path.normpath(key)
        if normalized.startswith("..") or os.path.isabs(normalized):
            raise ValueError(f"invalid storage key: {key!r}")
        return os.path.join(self.root, normalized)

    def write_bytes(self, key: str, data: bytes) -> None:
        dest = self.key_path(key)
        os.makedirs(os.path.dirname(dest), exist_ok=True)

        fd, tmp_path = tempfile.mkstemp(
            dir=os.path.dirname(dest),
            prefix=".tmp-",
        )
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, dest)  # atomic on POSIX + Windows
        except Exception:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise

    def read_bytes(self, key: str) -> bytes:
        path = self.key_path(key)
        if not os.path.exists(path):
            raise FileNotFoundError(key)
        with open(path, "rb") as f:
            return f.read()

    def exists(self, key: str) -> bool:
        return os.path.exists(self.key_path(key))


def get_storage() -> StorageBackend:
    from app.config import STORAGE_ROOT

    return LocalDiskStorage(STORAGE_ROOT)

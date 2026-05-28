"""Detects file changes because the system needs to know if the cache is valid.
"""
from __future__ import annotations

import hashlib
from pathlib import Path


# Sets chunk size to 64 KB because we want to avoid loading huge files into memory.
_CHUNK_SIZE: int = 65_536


class FileChangeDetector:
    """Detects source file changes because we must avoid using outdated data."""

    def compute_hash(self, path: str | Path) -> str:
        """Computes the file's SHA-256 hash because we need a unique identifier for its content."""
        hasher = hashlib.sha256()
        with Path(path).open("rb") as f:
            while chunk := f.read(_CHUNK_SIZE):
                hasher.update(chunk)
        return hasher.hexdigest()

    def compute_hashes(self, paths: list[str | Path]) -> dict[str, str]:
        """Computes hashes for all files because the app relies on multiple sources."""
        # Converts paths to strings because dictionary keys must be strings for saving.
        return {str(p): self.compute_hash(p) for p in paths}

    def has_changed(
        self,
        paths: list[str | Path],
        stored_hashes: dict[str, str],
    ) -> bool:
        """Checks if files differ from stored hashes because we need to know if we should re-parse them."""
        
        # Returns True if stored_hashes is empty because it means this is the first run.
        if not stored_hashes:
            return True

        current_hashes = self.compute_hashes(paths)
        
        # Compares the dictionaries because any missing, added, or changed key means the cache is outdated.
        return current_hashes != stored_hashes
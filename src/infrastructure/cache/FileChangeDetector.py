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
        # Creates a new SHA-256 hasher object because we need to calculate a unique fingerprint for the file.
        hasher = hashlib.sha256()
        # Opens the file in binary read mode because hashing functions require raw bytes instead of text strings.
        with Path(path).open("rb") as f:
            # Reads the file in small parts because we want to save memory when processing large input files.
            while chunk := f.read(_CHUNK_SIZE):
                # Feeds the current part into the hasher because the algorithm needs to process all data to get the correct result.
                hasher.update(chunk)
        # Returns the final hash as a readable string because we need a simple text format to save and compare later.
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
        """Checks whether any of the given files differ from their stored hashes.

        Only the files in `paths` are checked. Extra entries in `stored_hashes`
        (belonging to files not yet loaded in this session) are intentionally
        ignored, so a partial load does not cause a spurious cache miss.
        """
        if not stored_hashes:
            return True

        for path in paths:
            key = str(path)
            # A file that was never hashed before is treated as changed.
            if key not in stored_hashes:
                return True
            # Stop immediately on the first content mismatch.
            if self.compute_hash(path) != stored_hashes[key]:
                return True

        return False
import fcntl
import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path

@contextmanager
def with_lock(filepath: Path):
    """Acquires a file lock on a lockfile corresponding to the given filepath."""
    lock_file = filepath.with_suffix('.lock')
    with open(lock_file, 'w') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)

def write_json_atomic(filepath: Path | str, data: dict | list):
    """Writes data to a temporary file and atomically renames it to filepath."""
    filepath = Path(filepath)
    fd, temp_path = tempfile.mkstemp(dir=filepath.parent, text=True)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        os.replace(temp_path, filepath)
    except Exception as e:
        os.remove(temp_path)
        raise e

def append_jsonl(filepath: Path | str, data: dict):
    """Appends a JSON object as a new line to a file securely using a lock."""
    filepath = Path(filepath)
    with with_lock(filepath):
        with open(filepath, 'a', encoding='utf-8') as f:
            f.write(json.dumps(data) + '\n')

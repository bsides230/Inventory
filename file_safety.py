import json
import os
import tempfile
from contextlib import contextmanager
import fcntl

def write_json_atomic(path, payload):
    dir_name = os.path.dirname(path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
    fd, temp_path = tempfile.mkstemp(dir=dir_name, prefix="tmp_", suffix=".json")
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(payload, f, indent=4)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_path, path)
    except Exception:
        os.remove(temp_path)
        raise

def append_jsonl(path, payload):
    dir_name = os.path.dirname(path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
    with open(path, 'a') as f:
        f.write(json.dumps(payload) + '\n')
        f.flush()
        os.fsync(f.fileno())

@contextmanager
def with_lock(lock_path):
    dir_name = os.path.dirname(lock_path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
    lock_file = open(lock_path, 'w')
    try:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        lock_file.close()
    try:
        os.remove(lock_path)
    except OSError:
        pass

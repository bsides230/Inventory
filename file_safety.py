import json
import os
import tempfile
from contextlib import contextmanager
import time

try:
    import fcntl
    _has_fcntl = True
except ImportError:
    _has_fcntl = False
    import msvcrt

def _lock_file(f):
    if _has_fcntl:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
    else:
        while True:
            try:
                msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
                break
            except OSError:
                time.sleep(0.01)

def _unlock_file(f):
    if _has_fcntl:
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    else:
        try:
            msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
        except OSError:
            pass

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
        _lock_file(lock_file)
        yield
    finally:
        _unlock_file(lock_file)
        lock_file.close()
    try:
        os.remove(lock_path)
    except OSError:
        pass

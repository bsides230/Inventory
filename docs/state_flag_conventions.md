# State Flag Conventions

1. **State directory:** Flags and locks are stored in the `global_flags` directory.
2. **Atomic writes:** Configuration files and state updates use write-to-temp-and-rename semantics (`write_json_atomic`).
3. **Locking:** For processes that require mutual exclusion, an `flock` based context manager is used to acquire an exclusive lock (`with_lock`) on a designated file before accessing shared mutable resources.

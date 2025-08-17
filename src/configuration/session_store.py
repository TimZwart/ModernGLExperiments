import os


def _project_root():
    # src/configuration/session_store.py -> project root is two levels up
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))


def _last_file_path():
    return os.path.join(_project_root(), 'last_file.txt')


def get_last_file():
    path = _last_file_path()
    try:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                stored = f.read().strip()
                return stored if stored else None
    except Exception:
        return None
    return None


def set_last_file(filename):
    try:
        if not filename:
            return
        abs_path = os.path.abspath(filename)
        with open(_last_file_path(), 'w', encoding='utf-8') as f:
            f.write(abs_path)
    except Exception:
        # Best-effort; ignore persistence failures
        pass



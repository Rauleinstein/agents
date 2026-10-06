"""Reviewed artifact staging; Python 3.11+ standard library only."""
import hashlib
from pathlib import Path
import stat


class SafetyError(ValueError):
    """Invalid configuration or unsafe filesystem state."""


def files(path):
    """Return regular payload files, rejecting links and special files."""
    mode = path.lstat().st_mode
    if stat.S_ISREG(mode):
        return [("", path)]
    if not stat.S_ISDIR(mode):
        raise SafetyError(f"not a regular file/directory: {path}")
    result = []
    for child in sorted(path.iterdir()):
        for name, item in files(child):
            result.append((child.name + ('/' + name if name else ''), item))
    return result


def digest(path):
    h = hashlib.sha256()
    for name, item in files(Path(path)):
        encoded = name.encode('utf-8')
        data = item.read_bytes()
        h.update(len(encoded).to_bytes(8, 'big'))
        h.update(encoded)
        h.update(len(data).to_bytes(8, 'big'))
        h.update(data)
    return h.hexdigest()

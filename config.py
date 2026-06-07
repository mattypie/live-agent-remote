"""Configuration loader for LiveAgent Remote.

Priority:
1. config.local.py (user-specific, gitignored)
2. Environment variables (SAMPLES_PATH, ABLETON_USER_LIBRARY)
3. Defaults (empty — user must configure)
"""

import os

_REPO_DIR = os.path.dirname(os.path.abspath(__file__))


def _load_local_config():
    """Try to load config.local.py."""
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "config_local",
            os.path.join(_REPO_DIR, "config.local.py"),
        )
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    except FileNotFoundError:
        pass
    except Exception:
        pass
    return None


_local = _load_local_config()


def get_samples_path():
    """Get the sample library path."""
    if _local and getattr(_local, "SAMPLES_PATH", ""):
        return _local.SAMPLES_PATH
    return os.environ.get("SAMPLES_PATH", "")


def get_ableton_user_library():
    """Get the Ableton User Library path."""
    if _local and getattr(_local, "ABLETON_USER_LIBRARY", ""):
        return _local.ABLETON_USER_LIBRARY
    env = os.environ.get("ABLETON_USER_LIBRARY", "")
    if env:
        return env
    # Default macOS path
    default = os.path.expanduser("~/Music/Ableton/User Library")
    if os.path.isdir(default):
        return default
    return ""


def get_repo_dir():
    """Get the repository root directory."""
    return _REPO_DIR

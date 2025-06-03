"""
=========
Utilities
=========

This module provides utility functions and classes for various common tasks.

The utilities are supportive functions and classes that ease certain operations
across the entire application. These include standard I/O operations, data
serialization, and other common procedures that are frequently used in different
parts of the application's codebase.
"""

import os
import sys


def user_data_dir(appname: str) -> str:
    """Return user data directory according to OS conventions (Python stdlib only)."""
    if sys.platform == "win32":
        base_dir = os.environ.get(
            "LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local")
        )
    elif sys.platform == "darwin":
        base_dir = os.path.expanduser("~/Library/Application Support")
    else:  # Linux and other Unix
        base_dir = os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))

    return os.path.join(base_dir, appname)

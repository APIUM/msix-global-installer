"""Functions to assist using Pyinstaller."""

import os
import sys


def resource_path(*relative_paths) -> str:  # type: ignore
    """Get absolute path to resource, works for dev and for PyInstaller."""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS  # pylint: disable=protected-access # type: ignore
    except AttributeError:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, *relative_paths)

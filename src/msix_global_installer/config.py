import pathlib
from msix_global_installer import pyinstaller_helper

EXTRACTED_DATA_PATH: pathlib.Path = pyinstaller_helper.resource_path(
    "extracted/data.pkl"
)

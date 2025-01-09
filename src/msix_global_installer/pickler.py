import pathlib
import pickle
from msix_global_installer import msix


def save_metadata(data_file_path: pathlib.Path, metadata_list: list[msix.MsixMetadata]):
    """Save MSIX metadata to a pickle file."""
    with open(data_file_path, "wb") as file:
        pickle.dump(metadata_list, file)


def load_metadata(data_file_path: pathlib.Path) -> list[msix.MsixMetadata]:
    """Load MSIX metadata from a pickle file."""
    with open(data_file_path, "rb") as file:
        return pickle.load(file)

import pathlib
import pickle
from msix_global_installer import msix


def save_metadata(data_file_path: pathlib.Path, metadata: msix.MsixMetadata):
    """Save MSIX metadata to a pickle file."""
    with open(data_file_path, 'wb') as file:
        pickle.dump(metadata, file)


def load_metadata(data_file_path: pathlib.Path) -> msix.MsixMetadata:
    """Load MSIX metadata from a pickle file."""
    with open(data_file_path, 'rb') as file:
        return pickle.load(file)

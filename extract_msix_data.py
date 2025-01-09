# Helper script to create data for the application
#
# This avoids runtime extraction/processing of data
#
# Usage: python extract_msix_data.py path_to_msix.msix
#

from msix_global_installer import msix, pickler, image
import sys
import pathlib


def get_metadata(paths: list[str]) -> list[msix.MsixMetadata]:
    """Get the metadata from a list of items."""
    return [msix.get_msix_metadata(path) for path in paths]


path = sys.argv[1]
print("Extracting data from %s" % path)

data_output_path = pathlib.Path("extracted")
if not data_output_path.exists():
    data_output_path.mkdir()
data_file = data_output_path / "data.pkl"

metadata = msix.get_msix_metadata(path, data_output_path)
dependency_paths = sys.argv[2:]
dependency_metadata = []
if dependency_paths:
    dependency_metadata = get_metadata(paths=dependency_paths)
all_metadata = [metadata] + dependency_metadata

# Scale the image, save and add to metadata
scaled_image = image.scale_image(metadata.icon_path, 100, 100)
scaled_image_path = pathlib.Path(metadata.icon_path.parent) / pathlib.Path(
    metadata.icon_path.stem + "_scaled" + metadata.icon_path.suffix
)
image.save_image(scaled_image, scaled_image_path)
metadata.scaled_icon_path = scaled_image_path

pickler.save_metadata(data_file_path=data_file, metadata_list=all_metadata)

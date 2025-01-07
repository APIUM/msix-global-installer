import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass

@dataclass
class MsixMetadata:
    package_name: str
    version: str
    publisher: str

def get_msix_metadata(msix_path: str) -> MsixMetadata:
    """
    Extract Metadata from MSIX package.
    
    Note this does not support APPXBUNDLE.
    """
    try:
        with zipfile.ZipFile(msix_path, 'r') as msix:
            with msix.open('AppxManifest.xml') as manifest:
                tree = ET.parse(manifest)
                root = tree.getroot()
                
                # Define namespace for querying XML
                namespace = {'default': 'http://schemas.microsoft.com/appx/manifest/foundation/windows10'}
                
                # Extract DisplayName
                display_name = root.find('default:Properties/default:DisplayName', namespace)
                package_name = display_name.text if display_name is not None else "DisplayName not found"
                
                # Extract Version (Attribute of the Identity element)
                identity = root.find('default:Identity', namespace)
                version = identity.attrib.get('Version', "Version not found") if identity is not None else "Version not found"
                
                # Extract Publisher (Attribute of the Identity element)
                publisher = identity.attrib.get('Publisher', "Publisher not found") if identity is not None else "Publisher not found"
                
                return MsixMetadata(package_name, version, publisher)
    except Exception as e:
        return MsixMetadata("Error", "Error", str(e))

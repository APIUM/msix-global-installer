from dataclasses import dataclass
import logging
import pathlib
import events
import subprocess
import xml.etree.ElementTree as ET
import zipfile


logger = logging.getLogger(__name__)


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
                publisher_full = identity.attrib.get('Publisher', "Publisher not found") if identity is not None else "Publisher not found"
                publisher = get_name_from_publisher(publisher_full)
                
                return MsixMetadata(package_name, version, publisher)
    except Exception as e:
        return MsixMetadata("Error", "Error", str(e))


def get_name_from_publisher(publisher: str) -> str:
    """
    Get the name such as 'Contoso Corporation' from a publisher string seen below.
    
    Eg:
    CN=Contoso Software (FOR LAB USE ONLY), O=Contoso Corporation, C=US
    """
    parts = publisher.split(sep=", ")
    try:
        # This gets the first (should be only) item that starts with O=, then strips O=
        name = [item for item in parts if item.startswith('O=')][0][2:]
    except IndexError:
        # The publisher is probably "Publisher not found"
        return publisher
    return name


def install_msix(path: pathlib.Path, global_install: bool = False):
    """Install an MSIX package."""
    # TODO: If global install ensure we are running as admin
    global_install_command = "Add-AppxProvisionedPackage -PackagePath %s -Online -SkipLicense" % path
    local_install_command = "Add-AppxPackage -Path %s" % path
    command_string = local_install_command if not global_install else global_install_command
    p = subprocess.Popen(
        [
            "powershell.exe",
            "-Command",
            command_string,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        text=True
    )
    # stdout, stderr = p.communicate()
    error_lines = ""
    while p.poll() is None:
        # Add errors
        errline = p.stderr.readline()
        error_lines += errline
        logger.info("Err line is %s", errline)
        # Parse output
        for line in p.stdout:
            line = line.strip()
            logger.info("Line is %s", line)
            event = events.Event(name=events.EventType.INSTALL_PROGRESS_TEXT, data={"text": line})
            events.post_event_sync(event, event_queue=events.gui_event_queue)

    if p.returncode != 0:
        logger.error("Returned error!")
        try:
            parse_error(error_lines)
        except RuntimeError as e:
            logger.exception("Error installing")
            event = events.Event(name=events.EventType.INSTALL_PROGRESS_TEXT, data={"text": e.args[0], "progress": 100})
            events.post_event_sync(event, event_queue=events.gui_event_queue)
            pass
    else:
        logger.info("Should have installed successfully!")
        # logger.info(stdout)


def parse_error(error_string: str):
    logger.warning("Error string: %s" % error_string)
    if "0x80074CF0" in error_string:
        raise RuntimeError("Certificate error")
    elif "0x800B0109" in error_string:
        raise RuntimeError("The root certificate of the signature in the app package or bundle must be trusted.")
    elif "Add-AppxProvisionedPackage : The requested operation requires elevation" in error_string:
        raise RuntimeError("The requested operation requires elevation")
    raise RuntimeError("Unknown error!")

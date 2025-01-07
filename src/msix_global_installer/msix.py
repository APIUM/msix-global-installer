from dataclasses import dataclass
from math import ceil
from msix_global_installer import events
from winpty import PtyProcess
import logging
import os
import pathlib
import re
import xml.etree.ElementTree as ET
import zipfile


logger = logging.getLogger(__name__)


@dataclass
class MsixMetadata:
    package_path: pathlib.Path
    package_name: str
    version: str
    publisher: str
    icon_path: pathlib.Path | None = None
    scaled_icon_path: pathlib.Path | None = None


@dataclass
class ProgressResult:
    progress: int


@dataclass
class ErrorResult:
    error: Exception


@dataclass
class ReturnCodeResult:
    return_code: int


def get_msix_metadata(msix_path: str, output_path: pathlib.Path) -> MsixMetadata:
    """
    Extract Metadata from MSIX package.
    
    Note this does not support APPXBUNDLE.
    """
    if not output_path.exists():
        raise Exception("Path doesn't exist")

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

                # Extract Icon Path
                icon_element = root.find('default:Properties/default:Logo', namespace)
                icon_path_in_msix = icon_element.text if icon_element is not None else None

                extracted_icon_path = None
                if icon_path_in_msix:
                    # Extract the icon from the MSIX package
                    icon_path_in_msix = icon_path_in_msix.replace('\\', '/')
                    output_icon_path = pathlib.Path(output_path) / pathlib.Path(icon_path_in_msix).name
                    with msix.open(icon_path_in_msix) as icon_file:
                        with open(output_icon_path, 'wb') as out_file:
                            out_file.write(icon_file.read())
                    extracted_icon_path = pathlib.Path(output_icon_path)
                
                return MsixMetadata(msix_path, package_name, version, publisher, extracted_icon_path)
    except Exception as e:
        return MsixMetadata("Error", "Error", str(e), "Error")


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


def count_progress(line: str, max_count:int) -> int | None:
    """Returns progress out of 100, None for invalid line."""
    # Regex pattern
    pattern = r"\[([o ]+)\]"
    matches = re.findall(pattern, line)
    if not matches:
        return None
    first_match = str(matches[0])
    count = first_match.count('o')
    try:
        percentage = count / max_count * 100
    except ZeroDivisionError:
        return 0
    return ceil(percentage)


def install_msix(path: pathlib.Path, global_install: bool = False):
    """Install an MSIX package."""
    # TODO: If global install ensure we are running as admin
    global_install_command = "Add-AppxProvisionedPackage -PackagePath %s -Online -SkipLicense | Out-String" % path
    local_install_command = "Add-AppxPackage -Path %s | Out-String" % path
    command_string = local_install_command if not global_install else global_install_command
    save_returncode_string = "; $installRetcode = $LastExitCode"
    print_return_code = "; echo RETCODE=$installRetcode"
    wait_string = "; Start-Sleep -Milliseconds 1500"
    exit_string = "; Exit"

    # We must use a psudo terminal as otherwise
    # the written lines are not going to stdout, just appearing on the terminal for the progress
    # This method ensures we can write the progress to the progress bar.
    proc = PtyProcess.spawn("powershell.exe")
    # Here we incorperate a wait which allows us to capture the lines before the terminal closes
    # As we need the last lines which are the return code
    proc.write(command_string + save_returncode_string + print_return_code*10 + wait_string + exit_string + os.linesep)

    error = None
    retcode = None
    while proc.isalive():
        line = proc.readline()
        logger.debug("%r\n\r", line)
        result = process_line(line)
        if isinstance(result, ProgressResult):
            event = events.Event(name=events.EventType.INSTALL_PROGRESS_TEXT, data={"text": "Installing", "progress": result.progress})
            events.post_event_sync(event, event_queue=events.gui_event_queue)
        elif isinstance(result, ErrorResult):
            error = result.error
            event = events.Event(name=events.EventType.INSTALL_PROGRESS_TEXT, data={"text": result.error.args[0], "progress": 100})
            events.post_event_sync(event, event_queue=events.gui_event_queue)
        elif isinstance(result, ReturnCodeResult):
            retcode = result.return_code
            if retcode > 1 and error is None:
                event = events.Event(name=events.EventType.INSTALL_PROGRESS_TEXT, data={"text": "Error Occurred", "progress": 100})
                events.post_event_sync(event, event_queue=events.gui_event_queue)
            break
    
    logger.debug("Process is closed")

    if retcode == 0 and not error:
        logger.info("Should have installed successfully!")
        install_complete_text = "Install Complete"
        event = events.Event(name=events.EventType.INSTALL_PROGRESS_TEXT, data={"text": install_complete_text, "progress": 100})
        events.post_event_sync(event, event_queue=events.gui_event_queue)
    else:
        logger.error("Install failed")
        logger.error("Retcode is: %s", retcode)
        logger.error("Error is: %s", error)


def process_line(line) -> ProgressResult | ErrorResult | ReturnCodeResult:
    progress = count_progress(line=line, max_count=68)
    if progress:
        return ProgressResult(progress=progress)
    elif "error" in line or "CategoryInfo" in line:
        try:
            parse_error(line)
        except RuntimeError as e:
            return ErrorResult(e)
    elif "RETCODE=" in line:
        return_code = parse_retcode(line)
        logger.info("Retcode found: %s", return_code)
        if return_code != None:
            return ReturnCodeResult(return_code)


def parse_error(error_string: str):
    logger.warning("Error string: %s" % error_string)
    if "0x80074CF0" in error_string:
        raise RuntimeError("Certificate error")
    elif "0x800B0109" in error_string:
        raise RuntimeError("The root certificate of the signature in the app package or bundle must be trusted.")
    elif "Add-AppxProvisionedPackage : The requested operation requires elevation" in error_string:
        raise RuntimeError("The requested operation requires elevation")
    elif "ObjectNotFound" in error_string:
        raise RuntimeError("Installer file not found!")
    raise RuntimeError("Unknown error!")


def parse_retcode(line: str) -> int:
    """Get the retcode out of a string.
    
    Expects RETCODE=x where x is the retcode and any
    amount of values either side.
    """
    split = line.split("RETCODE=")
    returncode = split[1][0]
    try:
        # Line can sometimes be the command which gives an incorrect value
        # Such as ...ho\x1b[m RETCODE=\x1b[9...
        int_retcode = int(returncode)
    except ValueError:
        return None
    return int_retcode

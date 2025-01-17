from dataclasses import dataclass
from math import ceil
from msix_global_installer import events, config
import io
import logging
import os
import pathlib
import re
import sys
import xml.etree.ElementTree as ET
import zipfile

if sys.platform == "win32":
    from winpty import PtyProcess


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
    install_success: bool


def get_msix_metadata(msix_path: str, output_icon_path: pathlib.Path | None = None) -> MsixMetadata:
    """
    Extract Metadata from MSIX package.

    Output path is used for the icon.

    Note this does not support APPXBUNDLE.
    """
    if output_icon_path and not output_icon_path.exists():
        raise Exception("Path doesn't exist")

    try:
        is_bundle = msix_path.endswith(".msixbundle") or msix_path.endswith(".appxbundle")
        with zipfile.ZipFile(msix_path, "r") as msix:
            if is_bundle:
                for file in msix.namelist():
                    # Get the first msix file in the bundle and use that as the reference
                    # TODO: Support localisation
                    if file.endswith(".msix") or file.endswith(".appx"):
                        with msix.open(file) as inner_msix:
                            # This opens a ZipFileObject so we need to open it as bytes like object in memory
                            # If the MSIX file is huge this will cause trouble opening on very low memory computers I expect
                            inner_msix_filedata = io.BytesIO(inner_msix.read())
                            with zipfile.ZipFile(inner_msix_filedata, "r") as working_msix:
                                return extract_metadata_from_manifest(
                                    working_msix, pathlib.Path(msix_path), output_icon_path
                                )
                raise FileNotFoundError("No APPX or MSIX in bundle!")
            else:
                return extract_metadata_from_manifest(msix, pathlib.Path(msix_path), output_icon_path)
    except Exception as e:
        raise e


def extract_metadata_from_manifest(
    open_msix_path_object, msix_path: pathlib.Path, output_icon_path: pathlib.Path | None
):
    """Extract details from a given manifest."""
    with open_msix_path_object.open("AppxManifest.xml") as manifest:
        tree = ET.parse(manifest)
        root = tree.getroot()

        # Define namespace for querying XML
        namespace = {"default": "http://schemas.microsoft.com/appx/manifest/foundation/windows10"}

        # Extract DisplayName
        display_name = root.find("default:Properties/default:DisplayName", namespace)
        package_name = str(display_name.text) if display_name is not None else "DisplayName not found"

        # Extract Version (Attribute of the Identity element)
        identity = root.find("default:Identity", namespace)
        version = identity.attrib.get("Version", "Version not found") if identity is not None else "Version not found"

        # Extract Publisher (Attribute of the Identity element)
        publisher_full = (
            identity.attrib.get("Publisher", "Publisher not found") if identity is not None else "Publisher not found"
        )
        publisher = get_name_from_publisher(publisher_full)

        # Extract Icon Path
        icon_element = root.find("default:Properties/default:Logo", namespace)
        icon_path_in_msix = icon_element.text if icon_element is not None else None

        extracted_icon_path = None
        if output_icon_path is not None:
            if icon_path_in_msix:
                # Get the correct name
                icon_path_in_msix = icon_path_in_msix.replace("\\", "/")
                # Extract the icon from the MSIX package
                try:
                    qualified_icon_path = find_qualified_logo_file(open_msix_path_object, icon_path_in_msix)
                except FileNotFoundError:
                    print("No logo found...")
                    extracted_icon_path = None
                else:
                    # Build the name to extract to
                    output_icon_path = pathlib.Path(output_icon_path) / pathlib.Path(icon_path_in_msix).name
                    # Extract
                    with open_msix_path_object.open(qualified_icon_path) as icon_file:
                        with open(output_icon_path, "wb") as out_file:
                            out_file.write(icon_file.read())
                    extracted_icon_path = pathlib.Path(output_icon_path)

        return MsixMetadata(str(msix_path), package_name, version, publisher, extracted_icon_path)


def find_qualified_logo_file(manifest: zipfile.ZipFile, resource_path: str) -> str:
    """
    Searches for the best match for a resource file with qualifiers in the ZIP archive.

    Eg would be assets/AppPackageLogo.png would find assets/AppPackageLogo.scale200.png
    """
    # Strip .png extension if it exists
    base_name = resource_path.rsplit(".png", 1)[0]

    # Generate potential qualified file names
    candidates = [
        f"{resource_path}",  # Ensure we check if it's available with the given name first
        # Then try different sizes
        f"{base_name}.scale-100.png",
        f"{base_name}.scale-200.png",
        f"{base_name}.scale-400.png",
    ]

    # List all files in the archive
    all_files = manifest.namelist()

    # Check for matches
    for candidate in candidates:
        if candidate in all_files:
            return candidate

    # If no matches found, raise an error
    raise FileNotFoundError(f"No qualified file found for {resource_path} in archive.")


def get_name_from_publisher(publisher: str) -> str:
    """
    Get the name such as 'Contoso Corporation' from a publisher string seen below.

    Eg:
    CN=Contoso Software (FOR LAB USE ONLY), O=Contoso Corporation, C=US
    """
    parts = publisher.split(sep=", ")
    try:
        # This gets the first (should be only) item that starts with O=, then strips O=
        name = [item for item in parts if item.startswith("O=")][0][2:]
    except IndexError:
        # The publisher is probably "Publisher not found"
        return publisher
    return name


def count_progress(line: str, max_count: int) -> int | None:
    """Returns progress out of 100, None for invalid line."""
    # Regex pattern
    pattern = r"\[([o ]+)\]"
    matches = re.findall(pattern, line)
    if not matches:
        return None
    first_match = str(matches[0])
    count = first_match.count("o")
    try:
        percentage = count / max_count * 100
    except ZeroDivisionError:
        return 0

    return ceil(percentage)


def install_msix(
    path: pathlib.Path,
    title: str,
    global_install: bool = False,
    packages_to_install: int = 1,
    package_number: int = 1,
):
    """Install an MSIX package."""
    # TODO: If global install ensure we are running as admin
    global_install_command = (
        "Add-AppxProvisionedPackage -PackagePath %s -Online -SkipLicense -ErrorAction Continue | Out-String" % path
    )
    local_install_command = "Add-AppxPackage -Path %s -ErrorAction Continue | Out-String" % path
    command_string = local_install_command if not global_install else global_install_command
    # Use a q after the success int to confirm that we have read the right thing
    save_returncode_string = "; $success_tail='q' ; $success=[int][bool]::Parse($?)"
    print_return_code = "; echo INSTALL_SUCCESS===$success$success_tail"
    wait_string = "; Start-Sleep -Milliseconds 1500"
    exit_string = "; echo Exiting with code $LASTEXITCODE; Exit"

    # We must use a psudo terminal as otherwise
    # the written lines are not going to stdout, just appearing on the terminal for the progress
    # This method ensures we can write the progress to the progress bar.
    proc = PtyProcess.spawn("powershell.exe")
    # Here we incorperate a wait which allows us to capture the lines before the terminal closes
    # As we need the last lines which are the return code
    proc.write(
        command_string + save_returncode_string + print_return_code * 10 + wait_string + exit_string + os.linesep
    )

    error: str | None = None
    install_succeeded: bool | None = None
    while proc.isalive():
        line = proc.readline()
        logger.debug("%r\n\r", line)
        is_dependency = packages_to_install > 1 and package_number != packages_to_install
        result = process_line(line, is_dependency)
        # Return code will also come with a False for should continue so it doesn't
        # matter that we are overwriting this
        should_continue, returned_install_result = process_result(
            result=result,
            package_title=title,
            current_error=error,
            packages_to_install=packages_to_install,
            package_number=package_number,
        )
        install_succeeded = returned_install_result
        if isinstance(result, ErrorResult):
            error = result.error if not error else error
        if not should_continue:
            logger.info("Received request to not continue!")
            # proc.write(exit_string + os.linesep)
            break
        logger.info("Continuing")

    # TODO Work out if this actually returns the exit status of the terminal
    # It appears to always return 0
    logger.info("EXIT STATUS : %s", proc.exitstatus)
    if not install_succeeded:
        install_succeeded = True if proc.exitstatus == 0 else None
    logger.debug("Process is closed")

    # Set progress to 100
    progress = progress_mincer(100, packages_to_install, package_number)
    logger.error("Progress: " + str(progress))
    event = events.Event(
        name=events.EventType.INSTALL_PROGRESS_TEXT,
        data={"progress": progress},
    )
    events.post_event_sync(event, event_queue=events.gui_event_queue)

    return check_has_succeeded(install_succeeded=install_succeeded, error=error, package_title=title)


def check_has_succeeded(install_succeeded: bool | None, error: str, package_title: str):
    """
    Return success.

    Post update to GUI on result.
    """
    if install_succeeded is not None and install_succeeded and not error:
        logger.info("Should have installed successfully!")
        install_complete_text = f"Install of {package_title} complete"
        event = events.Event(
            name=events.EventType.INSTALL_PROGRESS_TEXT,
            data={"title": install_complete_text},
        )
        events.post_event_sync(event, event_queue=events.gui_event_queue)
        return True
    else:
        logger.error("Install failed")
        logger.error("App reported install succeeded: %s", install_succeeded)
        logger.error("Error is: %s", error)
        if error is None and install_succeeded is None:
            # Terminal must have force quit - won't have an error message
            logger.warning("Stopping install - terminal must have force quit.")
            install_complete_text = f"Install of {package_title} failed"
            event = events.Event(
                name=events.EventType.INSTALL_PROGRESS_TEXT,
                data={"title": install_complete_text},
            )
            events.post_event_sync(event, event_queue=events.gui_event_queue)
        return False


def process_result(
    result: ProgressResult | ErrorResult | ReturnCodeResult | None,
    current_error: str | None,
    package_title,
    packages_to_install,
    package_number,
) -> tuple[bool, bool | None]:
    """Process a Result and return data to the GUI.

    ::returns:: (should_continue, install_success)
    Should Continue: Break on False return.
    Install Success: Reported success of the script
    """
    if isinstance(result, ProgressResult):
        event = events.Event(
            name=events.EventType.INSTALL_PROGRESS_TEXT,
            data={
                "title": f"Installing {package_title}",
                "progress": progress_mincer(result.progress, packages_to_install, package_number),
            },
        )
        events.post_event_sync(event, event_queue=events.gui_event_queue)
        return (True, None)
    elif isinstance(result, ErrorResult):
        # Only need to push the first error, otherwise it will keep finding errors
        # in the output and switch quickly
        if not current_error:
            event = events.Event(
                name=events.EventType.INSTALL_PROGRESS_TEXT,
                data={
                    "title": f"Failed to install {package_title}",
                    "subtitle": result.error.args[0],
                    "progress": 100,
                },
            )
            events.post_event_sync(event, event_queue=events.gui_event_queue)
            logger.warning("Stoppping install due to new error: %s", result.error)
            return (False, None)
        return (True, None)
    elif isinstance(result, ReturnCodeResult):
        install_succeeded = result.install_success
        if install_succeeded is not None and not install_succeeded and current_error is None:
            event = events.Event(
                name=events.EventType.INSTALL_PROGRESS_TEXT,
                data={"title": f"Failed to install {package_title}", "progress": 100},
            )
            events.post_event_sync(event, event_queue=events.gui_event_queue)
            logger.warning(
                "Stopping install - script reported success-(%s) and current error (%s)",
                install_succeeded,
                current_error,
            )
            return (False, install_succeeded)
        # Success return code recieved
        return (False, install_succeeded)
    # Not a matching line - continue
    return (True, None)


def process_line(line, is_dependency: bool) -> ProgressResult | ErrorResult | ReturnCodeResult | None:
    progress = count_progress(line=line, max_count=68)
    if progress:
        return ProgressResult(progress=progress)
    elif "error" in line or "CategoryInfo" in line or "HRESULT" in line:
        try:
            parse_error(line)
        # Must parse this first as it's derived from RuntimeError
        except RecovorableRuntimeError as e:
            logger.info("Got a recoverable error: %s", e)
            if is_dependency and config.ALLOW_DEPENDENCIES_TO_FAIL_DUE_TO_NEWER_VERSION_INSTALLED:
                logger.info("Settings allow for success to be returned")
                # Fudge progress to say it's installed successfully if
                # we are happy to ignore the error as it's a dependency
                # and the error says that it's already installed.
                return ReturnCodeResult(True)
            else:
                logger.warning("Settings insist this is a true failure")
                return ErrorResult(e)
        except RuntimeError as e:
            return ErrorResult(e)
    elif "INSTALL_SUCCESS===" in line:
        install_succeeded = parse_retcode(line)
        if install_succeeded is not None:
            logger.info("Success state %s found from line", install_succeeded)
            return ReturnCodeResult(install_succeeded)


class RecovorableRuntimeError(RuntimeError):
    """Used when an error is raised but it needs to be parsed differently."""

    pass


def parse_error(error_string: str):
    logger.warning("Error string: %s" % error_string)
    if "0x80074CF0" in error_string:
        raise RuntimeError("Certificate error")
    elif "0x800B0109" in error_string:
        raise RuntimeError("The root certificate of the signature in the app package or bundle must be trusted.")
    elif "0x80073D06" in error_string:
        raise RecovorableRuntimeError("A newer version of this package is already installed!")
    elif "0x80073D02" in error_string:
        raise RecovorableRuntimeError("A conflicting application is open!")
    elif "Add-AppxProvisionedPackage : The requested operation requires elevation" in error_string:
        raise RuntimeError("The requested operation requires elevation")
    elif "ObjectNotFound" in error_string:
        raise RuntimeError("Installer file not found!")
    raise RuntimeError("Unknown error!")


def parse_retcode(line: str) -> bool | None:
    """Get the retcode out of a string.

    Expects RETCODE=x where x is the retcode and any
    amount of values either side.
    """
    split = line.split("INSTALL_SUCCESS===")
    install_result = split[1][0]
    install_result_confirmation_tail = split[1][1]
    try:
        logger.info("Parsing return value %s from %s", install_result, split)
        # Line can sometimes be the command which gives an incorrect value
        # Such as ...ho\x1b[m RETCODE=\x1b[9...
        bool_success = bool(int(install_result))
        if install_result_confirmation_tail == "q":
            logger.debug("Line rejected, don't have expected tail.")
            return None
    except ValueError:
        logger.debug("Value is not a bool")
        return None
    return bool(bool_success)


def progress_mincer(package_progress: int, packages_to_install: int, package_number: int) -> int:
    """Get progress as part of the total packages to install."""
    total_for_stage = 1 / packages_to_install * 100
    zero_point = 100 * ((package_number - 1) / packages_to_install)
    stage_progress = total_for_stage * (package_progress / 100)
    overall_progress = zero_point + stage_progress
    return ceil(overall_progress)

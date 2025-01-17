from msix_global_installer import config, events, gui, msix, pickler, pyinstaller_helper
import asyncio
import logging
import threading
import platformdirs
import pathlib


if config.ENABLE_LOGS:
    log_dir_path = pathlib.Path(
        platformdirs.user_log_dir(appname="msix_global_installer", appauthor="msix_global_installer")
    )
    log_dir_path.mkdir(parents=True)
    log_path = log_dir_path / "installer.log"
    logging.basicConfig(
        level=logging.NOTSET,
        filename=log_path,
        filemode="a",
        format="%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )
else:
    logging.basicConfig(
        level=logging.NOTSET,
        format="%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )
logger = logging.getLogger(__name__)


def process_event(event: events.Event):
    if event.name == events.EventType.REQUEST_MSIX_METADATA:
        meta = pickler.load_metadata(config.EXTRACTED_DATA_PATH)
        logger.info("Got metadata %s", meta)
        metadata_event = events.Event(name=events.EventType.MSIX_METADATA_RECEIVED, data=meta)
        events.post_event_sync(event=metadata_event, event_queue=events.gui_event_queue)
    elif event.name == events.EventType.INSTALL_MSIX:
        install_globally = event.data["global"]
        meta = pickler.load_metadata(config.EXTRACTED_DATA_PATH)
        paths = [
            (
                metadata.package_name,
                pyinstaller_helper.resource_path(metadata.package_path),
            )
            for metadata in meta
        ]
        # TODO: Break this into a function in MSIX
        paths.reverse()
        number_of_packages = len(paths)
        for i, path in enumerate(paths):
            logger.info("Installing app: %s", path)
            success = msix.install_msix(
                path=path[1],
                title=path[0],
                global_install=install_globally,
                packages_to_install=number_of_packages,
                package_number=i + 1,
            )
            if not success:
                break
        logger.info("Installing app: %s... DONE", path)


def start_worker():
    """Run the worker in a separate thread."""
    while True:
        # Wait for a request
        event = events.receive_event_sync(event_queue=events.backend_event_queue)
        if event:
            process_event(event)


# Start the async worker in a separate thread
worker_thread = threading.Thread(target=start_worker, daemon=True)


class MainApp:
    """Run the main application threads."""

    worker_thread.start()
    asyncio.run(gui.main())

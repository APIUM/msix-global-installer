from msix_global_installer import config, events, gui, msix, pickler, pyinstaller_helper
import asyncio
import logging
import threading


logging.basicConfig(level=logging.NOTSET)
logger = logging.getLogger(__name__)


def process_event(event: events.Event):
    if event.name == events.EventType.REQUEST_MSIX_METADATA:
        meta = pickler.load_metadata(config.EXTRACTED_DATA_PATH)
        logger.info("Got metadata %s", meta)
        metadata_event = events.Event(
            name=events.EventType.MSIX_METADATA_RECEIVED, data=meta
        )
        events.post_event_sync(event=metadata_event, event_queue=events.gui_event_queue)
    elif event.name == events.EventType.INSTALL_MSIX:
        install_globally = event.data["global"]
        meta = pickler.load_metadata(config.EXTRACTED_DATA_PATH)
        path = pyinstaller_helper.resource_path(meta.package_path)
        logger.info("Installing app: %s", path)
        meta = msix.install_msix(path=path, global_install=install_globally)
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

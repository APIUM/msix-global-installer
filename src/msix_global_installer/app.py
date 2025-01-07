from msix_global_installer import config, events, gui, msix, pickler
import asyncio
import logging
import pathlib
import threading


logging.basicConfig(level=logging.NOTSET)
logger = logging.getLogger(__name__)


def process_event(event: events.Event):
    if event.name == events.EventType.REQUEST_MSIX_METADATA:
        base_path = pathlib.Path(__file__).parent.parent.resolve()
        path = base_path / config.MSIX_PACKAGE_PATH
        print(pathlib.Path().absolute())
        meta = pickler.load_metadata("extracted/data.pkl")
        logger.info("Got metadata %s", meta)
        metadata_event = events.Event(name=events.EventType.MSIX_METADATA_RECEIVED, data=meta)
        events.post_event_sync(event=metadata_event, event_queue=events.gui_event_queue)
    elif event.name == events.EventType.INSTALL_MSIX:
        install_globally = event.data["global"]
        # Base path required as when we elevate the privileges the path changes
        base_path = pathlib.Path(__file__).parent.parent.resolve()
        path = base_path / config.MSIX_PACKAGE_PATH
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


class MainApp():
    """Run the main application threads."""
    worker_thread.start()
    asyncio.run(gui.main())

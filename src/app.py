import gui
import asyncio
import threading
import events
import msix
import pathlib
import logging


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def process_event_sync(event):
    if event.name == events.EventType.REQUEST_MSIX_METADATA:
        meta = msix.get_msix_metadata(pathlib.Path("./tests/TestMsixPackage.msix"))
        logger.info("Got metadata %s", meta)
        metadata_event = events.Event(name=events.EventType.MSIX_METADATA_RECEIVED, data=meta)
        events.post_event_sync(event=metadata_event, event_queue=events.gui_event_queue)


def start_worker():
    """Run the worker in a separate thread."""
    while True:
        # Wait for a request
        event = events.receive_event_sync(event_queue=events.backend_event_queue)
        if event:
            process_event_sync(event)


# Start the async worker in a separate thread
worker_thread = threading.Thread(target=start_worker, daemon=True)


class MainApp():
    """Run the main application threads."""
    worker_thread.start()
    asyncio.run(gui.main())

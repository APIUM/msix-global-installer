import asyncio
import events
import msix
import tkinter
from tkinter import ttk
import logging

# Theme
import sv_ttk


logger = logging.getLogger(__name__)


class MainApplication(ttk.Frame):
    def __init__(self, parent, *args, **kwargs):
        ttk.Frame.__init__(self, parent, *args, **kwargs)
        self.parent: tkinter.Tk = parent
        self._frame: ttk.Frame = None

        self.parent.title("Install MSIX Application")

        self.switch_frame(InfoScreen)
        sv_ttk.set_theme("dark")

        # Start the asyncio loop
        self.parent.after(100, self.check_queue)

    def check_queue(self):
        """Check the event queue."""
        event = events.receive_event_sync(events.gui_event_queue)
        if event != None:
            logger.info("Handling gui event: %s", event)
            self._frame.handle_event(event)
        self.parent.after(100, self.check_queue)

    def switch_frame(self, frame: ttk.Frame):
        logger.info("Switching to frame %s", frame)
        new_frame = frame(self)
        if self._frame is not None:
            logger.info("Destroying frame %s", self._frame)
            self._frame.destroy()
        self._frame: ttk.Frame = new_frame
        self._frame.grid(row=0, column=0, sticky="nsew", **frame.pad_parameters)


class InfoScreen(ttk.Frame, events.EventHandler):
    pad_parameters = {"padx": 12, "pady": 24}

    def __init__(self, parent, *args, **kwargs):
        ttk.Frame.__init__(self, parent, *args, **kwargs)
        self.parent: tkinter.Tk = parent
        self.post_backend_event(events.Event(events.EventType.REQUEST_MSIX_METADATA, data=events.EventData()))

        self.title = ttk.Label(self, text="Install MSIX Application")
        self.title.grid(row=0, column=0, sticky="W")

        author = ttk.Label(self, text="Author:")
        author.grid(row=1, column=0, sticky="W")

        self.author_content = ttk.Label(self, text="XYZ")
        self.author_content.grid(row=1, column=1, sticky="W")

        version = ttk.Label(self, text="Version:")
        version.grid(row=2, column=0, sticky="W")

        self.version_content = ttk.Label(self, text="v0.0.0.0")
        self.version_content.grid(row=2, column=1, sticky="W")

        install_type_label = ttk.Label(self, text="Install Globally")
        install_type_label.grid(row=3, column=0, sticky="W")

        self.global_install_checkbox_state = tkinter.BooleanVar(self)
        self.global_install_checkbox_state.set(False)
        global_install_checkbox = ttk.Checkbutton(
            self, variable=self.global_install_checkbox_state
        )
        global_install_checkbox.grid(row=3, column=1, sticky="W")

        button = ttk.Button(
            self,
            text="Install",
            command=lambda: self.parent.switch_frame(InstallScreen),
        )
        button.grid(row=4, column=2)

    def handle_event(self, event: events.Event):
        """Handle events on the queue."""
        if event.name == events.EventType.MSIX_METADATA_RECEIVED:
            data: msix.MsixMetadata = event.data
            title_text = f"Install {data.package_name}"
            self.title.configure(text=title_text)
            self.version_content.configure(text=data.version)
            self.author_content.configure(text=data.publisher)
    
    def post_backend_event(self, event: events.Event):
        events.post_event_sync(event, events.backend_event_queue)


class InstallScreen(ttk.Frame):
    pad_parameters = {"padx": 48, "pady": 54}

    def __init__(self, parent, *args, **kwargs):
        ttk.Frame.__init__(self, parent, *args, **kwargs)
        self.parent: tkinter.Tk = parent

        progress = ttk.Progressbar(self, length=200)
        progress.grid(row=0, column=0)
        progress.step(10)

        done_button = ttk.Button(
            self, text="Done", command=lambda: self.parent.switch_frame(InfoScreen)
        )
        done_button.grid(row=1, column=0)
    
    def handle_event(self):
        pass


async def main():
    root = tkinter.Tk()
    MainApplication(root).grid()
    root.geometry("300x150")
    root.mainloop()


if __name__ == "__main__":
    main()

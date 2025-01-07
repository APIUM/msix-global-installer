from tkinter import ttk
from PIL import ImageTk, Image
from msix_global_installer import config, events, msix, pyinstaller_helper, pickler
import logging
import pyuac
import tkinter

# Theme
import sv_ttk


logger = logging.getLogger(__name__)


def post_backend_event(event: events.Event):
    events.post_event_sync(event, events.backend_event_queue)


class MainApplication(ttk.Frame):
    def __init__(self, parent, *args, **kwargs):
        ttk.Frame.__init__(self, parent, *args, **kwargs)
        self.parent: tkinter.Tk = parent
        self._frame: ttk.Frame = None

        self.parent.title("Install MSIX Application")

        self.switch_frame(InfoScreenContainer)
        sv_ttk.set_theme("dark")
        self.set_icon()

        # Start the asyncio loop
        self.parent.after(100, self.check_queue)
    
    def set_icon(self):
        """Set the window icon."""
        meta = pickler.load_metadata(config.EXTRACTED_DATA_PATH)
        image_to_iconify = Image.open(pyinstaller_helper.resource_path(meta.icon_path))
        icon_in_correct_format = ImageTk.PhotoImage(image_to_iconify)
        self.parent.wm_iconphoto(False, icon_in_correct_format)

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

    
class InfoScreenContainer(ttk.Frame, events.EventHandler):
    pad_parameters = {"padx": 12, "pady": 24}

    def __init__(self, parent: tkinter.Tk, *args, **kwargs):
        ttk.Frame.__init__(self, parent, *args, **kwargs)
        self.parent: tkinter.Tk = parent

        self.left_frame = InfoScreenImage(self)
        self.left_frame.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)

        self.right_frame = InfoScreen(self)
        self.right_frame.grid(row=0, column=1, sticky="nsew", padx=12, pady=12)
    
    def switch_frame(self, frame):
        self.parent.switch_frame(frame)

    def handle_event(self, event: events.Event):
        """Handle events on the queue."""
        # This will split the event so both get it
        self.left_frame.handle_event(event)
        self.right_frame.handle_event(event)


class InfoScreenImage(ttk.Frame, events.EventHandler):

    def __init__(self, parent: tkinter.Tk, *args, **kwargs):
        ttk.Frame.__init__(self, parent, *args, **kwargs)
        self.parent: tkinter.Tk = parent


    def handle_event(self, event: events.Event):
        """Handle events on the queue."""
        if event.name == events.EventType.MSIX_METADATA_RECEIVED:
            metadata: msix.MsixMetadata = event.data
            image_path = pyinstaller_helper.resource_path(metadata.scaled_icon_path)
            scaled_image = Image.open(image_path)
            self.img = ImageTk.PhotoImage(scaled_image)
            panel = ttk.Label(self.parent, image = self.img)
            panel.grid(row=0, column=0)


class InfoScreen(ttk.Frame, events.EventHandler):
    pad_parameters = {"padx": 12, "pady": 24}

    def __init__(self, parent: tkinter.Tk, *args, **kwargs):
        ttk.Frame.__init__(self, parent, *args, **kwargs)
        self.parent: tkinter.Tk = parent
        post_backend_event(events.Event(events.EventType.REQUEST_MSIX_METADATA, data=events.EventData()))

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

        # Not sure what's causing these to get cut off
        install_type_label = ttk.Label(self, text="Installnstall Globally")
        install_type_label.grid(row=3, column=0, sticky="W")

        self.global_install_checkbox_state = tkinter.BooleanVar(self)
        is_admin = pyuac.isUserAdmin()
        self.global_install_checkbox_state.set(is_admin)
        global_install_checkbox = ttk.Checkbutton(
            self, variable=self.global_install_checkbox_state, command=self.on_checkbox_change
        )
        global_install_checkbox.grid(row=3, column=0, sticky="W")

        button = ttk.Button(
            self,
            text="Install",
            command=self.install,
        )
        button.grid(row=4, column=1)

    def on_checkbox_change(self):
        """On change to checkbox."""
        # Run as admin if not and it's asked for.
        if self.global_install_checkbox_state.get():
            if not pyuac.isUserAdmin():
                # First hide the window
                self.parent.parent.parent.withdraw()
                # Then run as admin which blocks until complete
                pyuac.runAsAdmin()
                # Then close the first application (which is currently hidden)
                self.parent.parent.parent.quit()

    def handle_event(self, event: events.Event):
        """Handle events on the queue."""
        if event.name == events.EventType.MSIX_METADATA_RECEIVED:
            data: msix.MsixMetadata = event.data
            title_text = f"Install {data.package_name}"
            self.title.configure(text=title_text)
            self.version_content.configure(text=data.version)
            self.author_content.configure(text=data.publisher)

    def install(self):
        """Install the MSIX."""
        self.parent.switch_frame(InstallScreen)
        event_data = {"global": self.global_install_checkbox_state.get()}
        post_backend_event(events.Event(events.EventType.INSTALL_MSIX, data=event_data))


class InstallScreen(ttk.Frame):
    pad_parameters = {"padx": 48, "pady": 54}

    def __init__(self, parent, *args, **kwargs):
        ttk.Frame.__init__(self, parent, *args, **kwargs)
        self.parent: tkinter.Tk = parent

        self.status = ttk.Label(self, text="Starting...")
        self.status.grid(row=0, column=0)

        self.progress = ttk.Progressbar(self, length=200, mode='indeterminate')
        self.progress.grid(row=1, column=0)
        self.progress.start(interval=200)

        done_button = ttk.Button(
            self, text="Done", command=lambda: self.parent.switch_frame(InfoScreenContainer)
        )
        done_button.grid(row=2, column=0)
    
    def handle_event(self, event):
        if event.name == events.EventType.INSTALL_PROGRESS_TEXT:
            text = event.data["text"]
            self.status.configure(text=text)
            try:
                progress_percentage = int(event.data["progress"])
                logger.info("Updating progress bar to: %s", progress_percentage)
                self.progress.stop()
                self.progress.step(progress_percentage)
            except KeyError:
                # Progress wasn't included in the data
                pass

async def main():
    root = tkinter.Tk()
    MainApplication(root).grid()
    root.mainloop()


if __name__ == "__main__":
    main()

import tkinter
from tkinter import ttk

# Theme
import sv_ttk


class MainApplication(ttk.Frame):
    def __init__(self, parent, *args, **kwargs):
        ttk.Frame.__init__(self, parent, *args, **kwargs)
        self.parent: tkinter.Tk = parent
        self._frame: ttk.Frame = None

        self.parent.title("Install MSIX Application")

        self.switch_frame(InfoScreen)
        sv_ttk.set_theme("dark")

    def switch_frame(self, frame: ttk.Frame):
        print("Switching to frame %s", frame)
        new_frame = frame(self)
        if self._frame is not None:
            print("Destroying frame %s", self._frame)
            self._frame.destroy()
        self._frame: ttk.Frame = new_frame
        self._frame.grid(row=0, column=0, sticky="nsew", **frame.pad_parameters)


class InfoScreen(ttk.Frame):
    pad_parameters = {"padx": 12, "pady": 24}

    def __init__(self, parent, *args, **kwargs):
        ttk.Frame.__init__(self, parent, *args, **kwargs)
        self.parent: tkinter.Tk = parent

        title = ttk.Label(self, text="Install MSIX Application")
        title.grid(row=0, column=0, sticky="W")

        author = ttk.Label(self, text="Author:")
        author.grid(row=1, column=0, sticky="W")

        author_content = ttk.Label(self, text="XYZ")
        author_content.grid(row=1, column=1, sticky="W")

        version = ttk.Label(self, text="Version:")
        version.grid(row=2, column=0, sticky="W")

        version_content = ttk.Label(self, text="v0.0.0.0")
        version_content.grid(row=2, column=1, sticky="W")

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


def main():
    root = tkinter.Tk()
    MainApplication(root).grid()
    root.geometry("300x150")
    root.mainloop()


if __name__ == "__main__":
    main()

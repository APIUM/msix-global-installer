# MSIX Global Installer

This project is a replacement for the Microsoft MSIX Installer that allows the user to install
globally if they have admin rights.

## How to use

This is intended to be used as part of a CI pipeline.

There is a data extraction / preparation step which enables faster load time.

Check this repo out and install the app using uv:

```ps
uv sync
```

Copy your MSIX file into root of this repo, then run the preparation step

```ps
uv run python extract_msix_data.py path_to_your_msix_file
```

This will write the data to `extracted`.

You then need to run the pyinstaller script.

```ps
uv run powershell ./build_exe.ps1
```

Your executable will be in dist/.

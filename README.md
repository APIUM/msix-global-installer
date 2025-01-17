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

### How to add dependencies

Copy your MSIX file and dependencies into root of this repo, then run the preparation step

```ps
uv run python extract_msix_data.py path_to_your_msix_file path_to_dependency path_to_second_dependency ...
```

The packages will be installed in reverse order with the last one specified installed first, until the
main package (first argument) is installed last.

There is no tested limit on the number of dependencies.

## Logs

Logs are enabled by default.
You can disable logging by changing ENABLE_LOG to 'False' in config.py.
Logs are stored in 'C:\\Users\\USER\\AppData\\Local\\msix_global_installer\\msix_global_installer\\Logs'.

$path = python -c "import pickle; print(pickle.load(open('extracted/data.pkl', 'rb')).package_path)"
$basename = [System.IO.Path]::GetFileNameWithoutExtension($path)
$pathexe = $basename + ".exe"
$icon = python -c "import pickle; print(pickle.load(open('extracted/data.pkl', 'rb')).icon_path)"
$add_data_msix_path = $path + ":."
pyinstaller .\src\msix_global_installer\app.py --add-data 'extracted:extracted' --add-data "$add_data_msix_path" --onefile --name $pathexe --icon $icon --noconsole
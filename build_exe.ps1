# Get picked data to get name and icon
$paths_py = python -c "import pickle; m = pickle.load(open('extracted/data.pkl', 'rb')); print([a.package_path for a in m])"
$paths_py_doublequotes = $paths_py -replace "'", '"'
$paths_json = $paths_py_doublequotes | ConvertFrom-Json
$main_app_path = $paths_json[0]
$addDataArgs = $paths_json | ForEach-Object { "--add-data `'$($_):.`'" }
$addDataString = $addDataArgs -replace "`r?`n", ""

$basename = [System.IO.Path]::GetFileNameWithoutExtension($main_app_path)
$pathexe = $basename + ".exe"
$icon = python -c "import pickle; print(pickle.load(open('extracted/data.pkl', 'rb'))[0].icon_path)"

# Build command
# This only works when first stored as a string - some powershell string issue for the add-data commands
$command_str = "pyinstaller .\src\msix_global_installer\app.py --add-data 'extracted:extracted' $addDataString --onefile --name $pathexe --icon $icon --noconsole"
Invoke-Expression $command_str
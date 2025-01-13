function Get-ParentPath {
    param([string]$path)
    
    # Check if the path is just a file (no backslashes or forward slashes)
    if ($path -notmatch '[\\/]') {
        return '.'  # Return '.' for just a file without a directory
    }
    
    # Use Split-Path to get the parent directory
    return (Split-Path $path -Parent)
}

# Get picked data to get name and icon
$paths_py = python -c "import pickle; m = pickle.load(open('extracted/data.pkl', 'rb')); print([a.package_path for a in m])"
$paths_py_doublequotes = $paths_py -replace "'", '"'
$paths_json = $paths_py_doublequotes | ConvertFrom-Json
$main_app_path = $paths_json[0]
$addDataArgs = $paths_json | ForEach-Object {
    $parent_path = Get-ParentPath $_
    "--add-data `'$($_):$parent_path`'" 
}
$addDataString = $addDataArgs -replace "`r?`n", ""

$basename = [System.IO.Path]::GetFileNameWithoutExtension($main_app_path)
$pathexe = $basename + ".exe"
$icon = python -c "import pickle; print(pickle.load(open('extracted/data.pkl', 'rb'))[0].icon_path)"

# Build command
# This only works when first stored as a string - some powershell string issue for the add-data commands
$command_str = "pyinstaller .\src\msix_global_installer\app.py --add-data 'extracted:extracted' $addDataString --onefile --name $pathexe --icon $icon --noconsole"
Write-Host "Running command: $command_str"
Invoke-Expression $command_str
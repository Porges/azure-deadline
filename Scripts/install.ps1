Param(
    [string]$deadlineRepositoryPath = $null,
    [string]$installPath = "$env:ProgramFiles\Microsoft\Azure Deadline",
    [switch]$clientOnlyInstall
)

[Net.ServicePointManager]::SecurityProtocol = "tls12, tls11, tls"

function Parse-IniFile($file) {
  $ini = @{}

  # Create a default section if none exist in the file. Like a java prop file.
  $section = "NO_SECTION"
  $ini[$section] = @{}

  switch -regex -file $file {
    "^\[(.+)\]$" {
      $section = $matches[1].Trim()
      $ini[$section] = @{}
    }
    "^\s*([^#].+?)\s*=\s*(.*)" {
      $name,$value = $matches[1..2]
      # skip comments that start with semicolon:
      if (!($name.StartsWith(";"))) {
        $ini[$section][$name] = $value.Trim()
      }
    }
  }
  $ini
}


function Create-Directory($dir)
{
    try {
        New-Item $dir -ItemType directory -Force -ea stop | Out-Null
    } catch {
        Write-Error "Could not create install directory $dir, do you have permissions?"
        exit 1
    }
}


function Install-Plugin-Dependencies()
{
    # Install the Azure cloud provider plugin dependencies
    Write-Host "Installing Azure Cloud Plugin dependencies to $installPath..."
    & pip.exe install --target="$installPath" --upgrade -r "$tempPath\azure-deadline-$version\CloudProviderPlugin\requirements.txt" 2>&1 | Out-File "$tempPath\pip.log"
    if ($LASTEXITCODE -ne 0)
    {
        Write-Error "An error occurred installing one or more packages."
        Get-Content $tempPath\pip.log | foreach {Write-Output $_}
        exit 1
    }

    # Set an environment variable so the plugin knows where to find them
    [Environment]::SetEnvironmentVariable("AZURE_DEADLINE_PATH", "$installPath", "Machine")
}


function Install-CloudProvider-Plugin()
{
    # Install the cloud plugin into the Deadline repository
    $deadlineCloudPluginPath = "$deadlineRepositoryPath\custom\cloud\AzureBatch"
    Create-Directory $deadlineCloudPluginPath
    Write-Host "Installing Azure cloud provider plugin to $deadlineCloudPluginPath..."
    Copy-Item -Path "$tempPath\azure-deadline-$version\CloudProviderPlugin\*" -Destination "$deadlineCloudPluginPath" -Exclude "test_*.py" -Force
}


function Install-DataTransfer-Plugin()
{
    # Install the data transfer plugin into the Deadline repository
    $deadlineDataXferPluginPath = "$deadlineRepositoryPath\custom\events\AzureDataTransfer"
    Create-Directory $deadlineDataXferPluginPath
    Write-Host "Installing Azure data transfer plugin to $deadlineDataXferPluginPath..."
    Copy-Item -Path "$tempPath\azure-deadline-$version\AzureDataTransferEventPlugin\*" -Destination "$deadlineDataXferPluginPath" -Exclude "test_*.py" -Force
}


if ('' -eq $deadlineRepositoryPath)
{
    $deadlineRepositoryPath = Read-Host -Prompt 'Deadline 7.2, 8, 9 or 10 Repository Path'
}

if (!(Test-Path $deadlineRepositoryPath))
{
    Write-Error "The Deadline respository path is invalid or not accessible: $deadlineRepositoryPath"
    exit 1
}

$deadlineRepoConfig = "$deadlineRepositoryPath\settings\repository.ini"
if (!(Test-Path "$deadlineRepoConfig"))
{
    Write-Error "Cannot load the Deadline repository configuration file: $deadlineRepoConfig"
    exit 1
}

$repoConfig = Parse-IniFile -file $deadlineRepoConfig
$deadlineVersion = $repoConfig["DeadlineRepository"]["Version"]
$deadlineMajorVersion = $deadlineVersion.Split(".")[0]

if (!$deadlineVersion.StartsWith("10.") -and !$deadlineVersion.StartsWith("7.2."))
{
    Write-Error "Unsupported Deadline version found: $deadlineVersion"
    exit 1
}

Write-Host "Found Deadline $deadlineVersion in $deadlineRepositoryPath"

try {
    $python = & python.exe -V 2>&1 | %{ "$_" }
} catch {
    Write-Error "Python was not found in the path."
    exit 1
}

if(!$python.StartsWith("Python 2.7"))
{
    Write-Error "Python >= 2.7 was not found in the path."
    exit 1
}

Write-Host "Found $python at $(Get-Command python.exe | Select-Object -ExpandProperty Definition)"

try {
    $pip = & pip.exe -V 2>&1 | %{ "$_" }
} catch {
    Write-Error "Pip was not found in the path."
    exit 1
}

$installPath = "$installPath $deadlineMajorVersion"
Create-Directory $installPath

$tempPath = "${env:TEMP}\Microsoft\AzureDeadline$deadlineMajorVersion"
if (Test-Path $tempPath)
{
    Remove-Item $tempPath -Force -Recurse -ea stop
}

Create-Directory $tempPath

$version = "0.1"
$file = "v${version}.zip"
$url = "https://github.com/Azure/azure-deadline/archive/$file"
$localFile = "$tempPath\$file"

# Download the release
Write-Host "Downloading release $url to $localFile"
(New-Object Net.WebClient).DownloadFile($url, "$localFile")

# Extract the release to the temp location
Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::ExtractToDirectory($localFile, $tempPath)

Install-Plugin-Dependencies

if ($clientOnlyInstall)
{
    exit 0
}

Install-CloudProvider-Plugin
Install-DataTransfer-Plugin
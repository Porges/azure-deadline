Param(
  [string]$installerPath,
  [string]$domainName = $null,
  [string]$domainOuPath = $null,
  [string]$tenantId,
  [string]$applicationId,
  [string]$keyVaultCertificateThumbprint,
  [string]$keyVaultName,
  [string]$deadlineRepositoryPath,
  [string]$deadlineLicenseServer = $null,
  [string]$deadlineLicenseMode,
  [string]$deadlineRegion,
  [string]$deadlineGroups = $null,
  [string]$deadlinePools = $null,
  [string]$smbShares = $null,
  [string]$nfsShares = $null
)

$ErrorActionPreference = "Stop"

hostname | Out-File hostname.txt

Get-PackageProvider -Name NuGet -Force
Install-Module PowerShellGet -Force

if (Get-Module -ListAvailable -Name AzureRm) {
    Write-Host "AzureRm already installed"
} else {
    Write-Host "Installing AzureRm"
    Install-Module -Name AzureRm -Repository PSGallery -Force
}

Import-Module AzureRm

Login-AzureRmAccount -ServicePrincipal -TenantId $tenantId -CertificateThumbprint $keyVaultCertificateThumbprint -ApplicationId $applicationId

$secrets = Get-AzureKeyVaultSecret -VaultName "$keyVaultName"

if ($domainName -and -Not (Get-WmiObject -Class Win32_ComputerSystem).PartOfDomain)
{
    # Make sure we have the user and password in key vault
    if (-Not ($secrets | Where-Object {$_.Name -eq "DomainJoinUserName"}) -or
        -Not ($secrets | Where-Object {$_.Name -eq "DomainJoinUserPassword"}))
    {
        Write-Host "Domain specified, but no username or password found."
        exit 1
    }

    $domainUser = (Get-AzureKeyVaultSecret -VaultName "$keyVaultName" -Name 'DomainJoinUserName').SecretValueText
    $domainPasswordSecret = Get-AzureKeyVaultSecret -VaultName "$keyVaultName" -Name 'DomainJoinUserPassword'
 
    Write-Host "Joining domain $domainName with user $domainUser"
    
    $domainCred = New-Object System.Management.Automation.PSCredential($domainUser, $domainPasswordSecret.SecretValue)
    
    if ($domainOuPath -and $domainOuPath -ne "")
    {
        Add-Computer -DomainName "$domainName" -OUPath "$domainOuPath" -Credential $domainCred -Restart -Force
    }
    else
    {
        Add-Computer -DomainName "$domainName" -Credential $domainCred -Restart -Force
    }
    
    # Pause while we wait for the restart to ensure tasks don't run
    Start-Sleep -Seconds 60
    
    exit 0
}
else
{
  Write-Host "Compute node is already domain joined, skipping."
}

# Make sure we have the user and password in key vault
if (-Not ($secrets | Where-Object {$_.Name -eq "DeadlineServiceUserName"}) -or
    -Not ($secrets | Where-Object {$_.Name -eq "DeadlineServiceUserPassword"}))
{
    Write-Host "No Deadline client service user found."
    exit 1
}

$deadlineServiceUserName = (Get-AzureKeyVaultSecret -VaultName "$keyVaultName" -Name 'DeadlineServiceUserName').SecretValueText
$deadlineServiceUserPassword = Get-AzureKeyVaultSecret -VaultName "$keyVaultName" -Name 'DeadlineServiceUserPassword'

# Mount any Windows/SMB shares that are specified
if ('' -ne $smbShares)
{
    Write-Host "Mounting SMB network drives $smbShares"
    Write-Host "Current drives: "
    Get-PSDrive -PSProvider 'FileSystem'
    $tokens = $smbShares.Split(";")
    $tokens | ForEach {
        Write-Host "Checking share $_"
        $mapping = $_.Split("=")
        $share = $mapping[0]
        $drive = $mapping[1]
        
        if ($share.StartsWith('\\') -and (-not $drive.StartsWith('/')))
        {
            if (Test-Path $drive)
            {
                Write-Host "Drive $drive is already mounted, skipping"
            }
            else 
            {
                $drive = $drive -replace ":", ""
                Write-Host "Mount share $share at $drive with user $deadlineServiceUserName"
                $serviceCred = New-Object System.Management.Automation.PSCredential($deadlineServiceUserName, $deadlineServiceUserPassword.SecretValue)
                New-PSDrive -Name $drive -Root $share -Persist -PSProvider "FileSystem" -Credential $serviceCred -Confirm:$false
            }
        }
        else
        {
            Write-Host "Skipping Linux share $_"
        }
    }
}

if ('' -ne $nfsShares)
{
    $nfsClient = Get-WindowsFeature NFS-Client
    if (-not $nfsClient.Installed)
    {
        Install-WindowsFeature -Name NFS-Client
    }
    
    Write-Host "Mounting NFS network drives $nfsShares"
    Write-Host "Current drives: "
    Get-PSDrive -PSProvider 'FileSystem'
    
    $tokens = $nfsShares.Split(";")
    $tokens | ForEach {
        Write-Host "Checking share $_"
        $mapping = $_.Split("=")
        $share = $mapping[0]
        $drive = $mapping[1]

        if ($share.StartsWith('\\') -and (-not $drive.StartsWith('/')))
        {
            if (Test-Path $drive)
            {
                Write-Host "Drive $drive is already mounted, skipping"
            }
            else 
            {
                $drive = $drive -replace ":", ""
                Write-Host "Mounting NFS share $share at $drive"
                New-PSDrive -Name $drive -Root $share -Persist -PSProvider "FileSystem" -Confirm:$false
            }
        }
        else
        {
            Write-Host "Skipping Linux share $_"
        }
    }
}

# Persist the hostname so we can fetch it later
& hostname > hostname.txt

$baseArgs = @("--mode", "unattended", "--debuglevel", "4", "--repositorydir", "`"$deadlineRepositoryPath`"", "--slavestartup", "true", "--serviceuser", "`"$deadlineServiceUserName`"", "--servicepassword", "`"$($deadlineServiceUserPassword.SecretValueText)`"", "--launcherservice", "true")
$installerArgs = {$baseArgs}.Invoke()

# Find the installer in the path
$installer = Get-ChildItem "$installerPath" | where {$_.Name -like "DeadlineClient-*-windows-installer.exe"}
if (-Not $installer)
{
    Write-Host "Cannot find Deadline client installer in app package.  Files found:"
    Get-ChildItem "$installerPath"
    exit 1
}

if (!$installer.FullName.ToLower().Contains("deadlineclient-7.2"))
{
    $installerArgs.Add("--licensemode")
    $installerArgs.Add($deadlineLicenseMode)
    
    $installerArgs.Add("--region")
    $installerArgs.Add($deadlineRegion)
    
    $certDir = "C:\Certs"
    $certPath = "$certDir\DeadlineClient.pfx"
    if ($secrets | Where-Object {$_.Name -eq "DeadlineDbClientCertificate"})
    {
        $installerArgs.Add("--dbsslcertificate")
        $installerArgs.Add("`"$certPath`"")
       
        $cert = Get-AzureKeyVaultSecret -VaultName "$keyVaultName" -Name 'DeadlineDbClientCertificate'
        $certBytes = [System.Convert]::FromBase64String($cert.SecretValueText)
        $certCollection = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2Collection
        $certCollection.Import($certBytes,$null,[System.Security.Cryptography.X509Certificates.X509KeyStorageFlags]::Exportable)
        
        $certPassword = $null
        if (($secrets | Where-Object {$_.Name -eq "DeadlineDbClientCertificatePassword"}))
        {
            $certPassword = (Get-AzureKeyVaultSecret -VaultName "$keyVaultName" -Name 'DeadlineDbClientCertificatePassword').SecretValueText
            $installerArgs.Add("--dbsslpassword")
            $installerArgs.Add("`"$certPassword`"")
        }
        
        mkdir $certDir -Force
        takeown /R /F $certDir
        icacls "$certDir" /grant ${deadlineServiceUserName}:`(OI`)`(CI`)R /T
        icacls "$certDir" /remove Everyone /T
        $protectedCertificateBytes = $certCollection.Export([System.Security.Cryptography.X509Certificates.X509ContentType]::Pkcs12, $certPassword)
        [System.IO.File]::WriteAllBytes($certPath, $protectedCertificateBytes)
    }
}

if ('' -ne $deadlineLicenseServer)
{
    $installerArgs.Add("--licenseserver")
    $installerArgs.Add($deadlineLicenseServer)
}

if ($env:APP_INSIGHTS_APP_ID -and $env:APP_INSIGHTS_INSTRUMENTATION_KEY)
{
    # Install Batch Insights 
    iex ((New-Object System.Net.WebClient).DownloadString('https://raw.githubusercontent.com/Azure/batch-insights/master/windows.ps1'))
}

# Check if the Deadline Client is already installed
$client = Get-ItemProperty HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\* | Where-Object { $_.DisplayName -eq "Deadline Client" }
if ($client)
{
    Write-Host "Deadline Client $($client.DisplayVersion) is already installed."
}
else
{
    Write-Host "Executing: $($installer.FullName) $installerArgs"
    & cmd.exe /c $($installer.FullName) $installerArgs
    $installerResult = $LastExitCode

    if ($installerResult -ne 0)
    {
        Write-Host "Deadline client installation failed with exit code $installerResult"
        exit $installerResult
    }
}

if ('' -ne $deadlineGroups)
{
    $tokens = $deadlineGroups.Split(";")
    $tokens | ForEach {
            Write-Host "Adding slave to group $_"
            & cmd.exe /c "C:\Program Files\Thinkbox\Deadline10\bin\deadlinecommand" SetGroupsForSlave $env:COMPUTERNAME $_
    }
}

if ('' -ne $deadlinePools)
{
    $tokens = $deadlinePools.Split(";")
    $tokens | ForEach {
            Write-Host "Adding slave to pool $_"
            & cmd.exe /c "C:\Program Files\Thinkbox\Deadline10\bin\deadlinecommand" SetPoolsForSlave $env:COMPUTERNAME $_
    }
}

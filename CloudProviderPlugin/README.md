
# Create the Azure Resources

Prior to installing the new Azure Batch Deadline plugin there are a few Azure resources that need to be created and configured.  These include a Resource Group with a Batch account, a Key Vault secret store and two service principals for authentication.

1.  Create a Azure Resource group.
  * This should be created in the region you plan to provision you virtual machines, and the same region any required VNet/subnet exists, if being used.  We'll use a resource group called 'Deadline' for this example.
3.  Create a Azure Batch and Storage account in the Deadline resource group.
  * The Batch account Pool Allocation mode should be 'Batch service'.
  * Note the Batch account URL - you can get this from the Properties pane.
4.  Create a Key Vault in the resource group.

## Create the Service Principals

Two service principals are required.  One with password authentication for access to the Batch account and another with certificate based authentication for Key Vault.

See this document for more information: [https://docs.microsoft.com/en-us/cli/azure/create-an-azure-service-principal-azure-cli?view=azure-cli-latest](https://docs.microsoft.com/en-us/cli/azure/create-an-azure-service-principal-azure-cli?view=azure-cli-latest)

### Create the Key Vault SP

```
# az ad sp create-for-rbac --name DeadlineKeyVaultServicePrincipal --create-cert --cert DeadlineKeyVaultCert --keyvault <KeyVaultName>
# az role assignment create --assignee <AppID> --role Reader
# az role assignment delete --assignee <AppID> --role Contributor
```

Once created, note the following information for the Key Vault Service Principal

1.  Tenant Id
2.  Application/Client Id
3.  Certificate Thumbprint - this is the certificate that was created for the service principal and put in Key Vault

Now give the Service Principal access to Key Vault.

1.  Navigate to the Resource Group -> Key Vault created above.
2.  Click 'Access policies'
3.  Add the Service Principal application id from above, and give the service principal 'Get' and 'List' permissions for Keys/Secrets/Certificates

Add the Key Vault Service Principal certificate to the Batch account.

The service principal certificate PFX created above needs to be downloaded from key vault using the Azure Portal , or alternatively use the powershell command below.

```
Install-Module -Name AzureRm -Repository PSGallery -Force
Import-Module AzureRm

Login-AzureRmAccount

$certPath = "${env:TEMP}\keyvault_serviceprincipal.pfx"
#$certPassword = Read-Host -Prompt "Enter password" -AsSecureString
$certPassword = 'ASecurePassword'
$cert = Get-AzureKeyVaultSecret -VaultName "deadlinekeyvault" -Name 'DeadlineKeyVaultCert'
$certBytes = [System.Convert]::FromBase64String($cert.SecretValueText)
$certCollection = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2Collection
$certCollection.Import($certBytes,$null,[System.Security.Cryptography.X509Certificates.X509KeyStorageFlags]::Exportable)
$protectedCertificateBytes = $certCollection.Export([System.Security.Cryptography.X509Certificates.X509ContentType]::Pkcs12, $certPassword)
[System.IO.File]::WriteAllBytes($certPath, $protectedCertificateBytes)
```

Once downloaded, upload the certificate to the Azure Batch account Certificate store using the portal.  This can be done by navigating to the Batch account and Clicking 'Certificates'.  Keep note of the Thumbprint.

### Create the Batch account Service Principal

```
# az ad sp create-for-rbac --name DeadlineBatchServicePrincipal
```

Note the following information for the Batch Service Principal

1.  Tenant Id
2.  Application/Client Id
3.  Password (or Key)

Now give the Batch Service Principal access to the Batch account you created above.  Navigate to the Resource Group -> Batch Account -> Access control (IAM).  Click '+Add' and search for the Batch account Service Principal using the application Id.  Select the Role 'Contributor' for the service principal.

### Add the Required Secrets and Certificate to Key Vault

Now navigate to the Key Vault above in the Azure portal.  We need to add the following secrets that are required by the Deadline slaves.  It's important that the certificate and secret names match below exactly.

#### The following are required for Windows render slaves

1.  DomainJoinUserName

  * AD username with permissions to join a computer to the domain

2.  DomainJoinUserPassword

  * Password for the above AD user

3.  DeadlineServiceUserName

  * Username that the deadline slave service will run as.  This can either be a local or AD user.  If AD, this user must have permission to access the Deadline repository share.

4.  DeadlineServiceUserPassword

  * The password for the above user

5.  DeadlineDbClientCertificate

  * The Deadline database certificate PFX, if used.

6.  DeadlineDbClientCertificatePassword

  * The Deadline database certificate password, if used.

#### The following are required for Linux slaves

1.  DeadlineServiceUserNameLinux

  * Username the daemon will run as

2.  DeadlineServiceUserIdLinux

  * UID for the above user, if required

3.  DeadlineServiceGroupLinux

  * Group the daemon

4.  DeadlineServiceGroupIdLinux

  * GID for the above group, if required

## VNet Setup

If using a domain, the VNet will need to be configured to use the same DNS server as the AD domain controller so the render slaves can resolve the domain name.

# Install the Cloud Provider Plugin

As a prerequisite to installing the plugin several Python dependencies need to be installed and packaged into the Deadline 'pythonsync.zip' archive.  This ZIP contains all dependent Python modules required by the plugins and is consumed by all clients and render slaves.

```
C:\DeadlineRepository10\pythonsync\pythonsync.zip
```

### Install Python 2.7
You'll need to install a copy of Python 2.7 if not available.

https://www.python.org/download/releases/2.7/

### Install the Plugin Dependencies

Start by creating a backup of pythonsync.zip by copying it somewhere safe.  Now extract the content of pythonsync.zip to a temporary location, e.g. %TEMP%\DeadlineAzureInstall.

Using pip install the extra dependencies to the same location.
```
pip install --target=%TEMP%\DeadlineAzureInstall --upgrade -r requirements.txt
```

Now ZIP the content of %TEMP%\DeadlineAzureInstall into an archive called pythonsync.zip and copy this to you Deadline repository, e.g. D:\DeadlineRepository10\pythonsync\pythonsync.zip.

*Note - All client machines will need to close the Deadline monitor, delete the cached version of pythonsync.zip and restart the Monitor. e.g. Delete %LOCALAPPDATA%\Thinkbox\Deadline10\cache\*

### Install the Azure Cloud Provider Plugin

The Azure Batch cloud provider plugin needs to be installed on the Deadline repository host at the following location, or the repository install location if the default wasn't used.

The 'AzureBatch' directory will need to be created.

```
C:\DeadlineRepository10\custom\cloud\AzureBatch
```
The following plugin files should be installed

```
AzureBatch.param
AzureBatch.py
hardware.py
images.py
mappers.py
pluginconfig.py
```


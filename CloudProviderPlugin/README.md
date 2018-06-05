# Microsoft Azure Deadline 10 Cloud Provider Plugin

Below outlines the steps required to setup the environment and install the plugin and dependencies.  In summary you'll need the following.

**Azure VNet**

You’ll need a connection to Azure over Express Route or a site to site VPN and an associated VNet/subnet.  This is the network where the cloud nodes will be deployed and needs to have access to any on prem license server, and file servers if needed.

**License Servers**

The cloud Deadline slaves will need access to your on-premise license servers for any required licenses, at a minimum this will be your Deadline license server.  If you’re using Azure pay per use licensing for 3ds max, maya, Arnold or VRay then you won’t need a license server for them. 

**Azure Resources**

Service Principals - two service principals, one with key based authentication for use with the Batch account and one with certificate based authentication for Key Vault.

Azure Batch Account – this is the Batch account that will provision the Deadline slaves.  You'll need to create and upload an application package named 'DeadlineClient' containing the Deadline client installer.

Azure Blob Storage Account – this is used for asset transfer via blob, if required.  Asset transfer can be enabled using the Deadline Azure Data Transfer Event plugin.

Key Vault – used to store the required credentials for Deadline slaves including domain users, service users, Deadline DB certs and password.

**Testing**

For testing I find it helpful to manually create a test VM in Azure on the above VNet with the Deadline client installed, both Monitor and Slave.  This is useful for validating end-to-end connectivity and that all licensing works as expected.


# Create the Azure Resources

Prior to installing the new Azure Batch Deadline plugin there are a few Azure resources that need to be created and configured.  These include a Resource Group with a Batch account, a Key Vault secret store and two service principals for authentication.

### Create the Service Principals

Two service principals are required.  One with password authentication for access to the Batch account and another with certificate based authentication for Key Vault.

See this document for more information: [https://docs.microsoft.com/en-us/cli/azure/create-an-azure-service-principal-azure-cli?view=azure-cli-latest](https://docs.microsoft.com/en-us/cli/azure/create-an-azure-service-principal-azure-cli?view=azure-cli-latest)

### Key Vault Service Principal

####  Create a Key Vault

In the resource group that will be used for the Azure resources, create a Key Vault.

#### Create the Key Vault Service Principal

```
# az ad sp create-for-rbac --name DeadlineKeyVaultServicePrincipal --create-cert --cert DeadlineKeyVaultCert --keyvault <KeyVaultName>
# az role assignment create --assignee <AppID> --role Reader
# az role assignment delete --assignee <AppID> --role Contributor
```

Once created, note the following information for the Key Vault Service Principal

* Tenant Id
* Application/Client Id
* Certificate Thumbprint

The service principal certificate created above needs to be downloaded from key vault using the Azure Portal, or alternatively use the powershell command below, and saved as a PFX.

```
Install-Module -Name AzureRm -Repository PSGallery -Force
Import-Module AzureRm

Login-AzureRmAccount

$certPath = "${env:TEMP}\keyvault_serviceprincipal.pfx"
$certPassword = 'ASecurePassword'
$cert = Get-AzureKeyVaultSecret -VaultName "deadlinekeyvault" -Name 'DeadlineKeyVaultCert'
$certBytes = [System.Convert]::FromBase64String($cert.SecretValueText)
$certCollection = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2Collection
$certCollection.Import($certBytes,$null,[System.Security.Cryptography.X509Certificates.X509KeyStorageFlags]::Exportable)
$protectedCertificateBytes = $certCollection.Export([System.Security.Cryptography.X509Certificates.X509ContentType]::Pkcs12, $certPassword)
[System.IO.File]::WriteAllBytes($certPath, $protectedCertificateBytes)
```

#### Give the Service Principal Access to Key Vault

Navigate to the Resource Group -> Key Vault created above.  Click 'Access policies' 
and add the Key Vault Service Principal application id from above, and give the service principal 'Get' and 'List' permissions for Keys/Secrets/Certificates.


### Create the Batch account Service Principal

```
# az ad sp create-for-rbac --name DeadlineBatchServicePrincipal
# az role assignment create --assignee <AppID> --role Reader
# az role assignment delete --assignee <AppID> --role Contributor
```

Note the following information for the Batch Service Principal

* Tenant Id
* Application/Client Id
* Password (or Key)

### Create the Batch and Storage

Create a Resource Group - this should be created in the region you plan to provision your virtual machines, and the same region any required VNet/subnets exists.  We'll use a resource group called 'Deadline' for this example.

Create a Azure Batch and Storage account in the above Deadline resource group. 
The Batch account Pool Allocation mode should be 'Batch service'.

#### Create the Application Package

The Deadline 10 client installer needs to be available for installation of the Deadline slaves, to facilitate this we'll create and upload an application packages, essentially a ZIP file that will be extracted onto the nodes.

Start by downloading the latest Deadline 10 client installer and unpack the files into a directory.  You'll need the installer for any operating systems you plan to provision, i.e. Windows and/or Linux.

With the installers extracted, create a ZIP file containing the installers in the root, i.e. not inside a subdirectory within the ZIP file.

Now naviagte to the Batch account in the Azure portal and select the Applications blade.  Click +Add and call the new application package 'DeadlineClient'.  Give the package a version, using the Deadline version can be handy but not required.
Now select the ZIP file you just created and click OK to upload.

Once uploaded, navigate to the application package by clicking on it and click the Default version drop down menu.  From the menu select the package you just uploaded.  Now click Save at the top of the blade.

#### Give the Batch Service Principal Access

Now give the Batch Service Principal access to the Batch account you created above.
Navigate to the Resource Group -> Batch Account -> Access control (IAM).  Click '+Add' and search for the Batch account Service Principal using the application Id from above.  Select the Role 'Contributor' for the service principal and click Save.

* Note the Batch account URL - you can get this from the Properties pane.

#### Upload the Key Vault Service Principal Certificate

The Deadline slaves will need access to Key Vault to get various credentials stored there.
To access Key Vault we'll utilise the Batch certificate store which will ensure that any required certificates are available on the Deadline slaves.
Navigate to the Azure Batch service in the portal and Click the Certificates feature.
Click +Add and select the Key Vault Service Principals certificate and then OK to upload.

### Key Vault Configuration

We need to add the following secrets that are required by the Deadline slaves.  It's important that the certificate and secret names match below exactly.

#### The following are required for Windows Deadline slaves

| Name | Type | OS | Details |
| --- | --- | --- | --- |
| DomainJoinUserName | Secret | Windows & Linux | Domain user with permissions to join a compute to the domain |
| DomainJoinUserPassword | Secret | Windows & Linux | Password for the above AD domain user |
| DeadlineServiceUserName | Secret | Windows | Username that the deadline slave service will run as.  This can either be a local or AD user.  If AD, this user must have permission to access the Deadline repository share. |
| DeadlineServiceUserPassword | Secret | Windows |The password for the above service user|
| DeadlineDbClientCertificate | Certificate | Windows & Linux |The Deadline database certificate PFX, if used.|
| DeadlineDbClientCertificatePassword| Secret | Windows & linux|The Deadline database certificate password, if used.|
| DeadlineServiceUserNameLinux | Secret | Linux | Username the daemon will run as.|
| DeadlineServiceUserIdLinux | Secret | Linux | UID for the above user, if required|
| DeadlineServiceGroupLinux | Secret | Linux | Group the daemon will run under|
| DeadlineServiceGroupIdLinux | Secret | Linux | GID for the above group, if required|


## VNet Setup

If using a domain, the VNet will need to be configured to use the same DNS server as the AD domain controller so the Deadline slaves can resolve the domain name.
To do this navigate to the VNet in the Azure portal and select DNS servers.  Select the Custom radio button and add the IP address of the on premise DNS server. 

# Install the Cloud Provider Plugin

As a prerequisite to installing the plugin several Python dependencies need to be installed and packaged into the Deadline 'pythonsync.zip' archive.  This ZIP contains all dependent Python modules required by the plugins and is consumed by all clients and Deadline slaves.

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

Now ZIP the content of %TEMP%\DeadlineAzureInstall\* into an archive called pythonsync.zip and copy this to you Deadline repository, e.g. D:\DeadlineRepository10\pythonsync\pythonsync.zip.  Note, when zipping do not include the root 'DeadlineAzureInstall' directory.

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


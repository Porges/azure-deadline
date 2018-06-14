
# Azure Cloud Provider Plugin for Deadline 10

## Installation

We've created an install script for the Azure plugins to simplify the process.

On Windows execute the following from a command prompt or powershell console with **Administrator** priviledges.

The dependencies are installed to a separate directory to avoid conflicts with the Deadline module versions.

### Repository Installation

On Windows execute the following from a command prompt or powershell console with **Administrator** priviledges.
This will install the Deadline cloud provider plugin and all required dependencies.

```
powershell -exec bypass -c "(New-Object Net.WebClient).DownloadFile('https://raw.githubusercontent.com/Azure/azure-deadline/master/Scripts/install.ps1', 'install.ps1'); ./install.ps1"
```

### Client or Balancer Installation

All Deadline clients have access to all plugins installed to the repository, however the Azure Deadline plugin dependencies will also need to be installed on any client computer that will load the plugin, like the Balancer or Monitor Cloud Console for example.

```
powershell -exec bypass -c "(New-Object Net.WebClient).DownloadFile('https://raw.githubusercontent.com/Azure/azure-deadline/master/Scripts/install.ps1', 'install.ps1'); ./install.ps1 -clientOnlyInstall"
```

# Contributing

This project welcomes contributions and suggestions.  Most contributions require you to agree to a
Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us
the rights to use your contribution. For details, visit https://cla.microsoft.com.

When you submit a pull request, a CLA-bot will automatically determine whether you need to provide
a CLA and decorate the PR appropriately (e.g., label, comment). Simply follow the instructions
provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or
contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.

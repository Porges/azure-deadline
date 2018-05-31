# Copyright (c) Microsoft Corporation
#
# All rights reserved.
#
# MIT License
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED *AS IS*, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

import traceback

from Deadline.Cloud import CloudPluginWrapper, OSImage
from FranticX import Environment2

import images

def load_config(cloud_plugin_wrapper):
    try:
        config = BatchPluginConfig(
            # Batch
            batch_url=cloud_plugin_wrapper.GetConfigEntry("BatchAccountUrl"),
            batch_sp_tenant_id=cloud_plugin_wrapper.GetConfigEntry("BatchSPTenantId"),
            batch_sp_app_id=cloud_plugin_wrapper.GetConfigEntry("BatchSPAppId"),
            batch_sp_app_key=cloud_plugin_wrapper.GetConfigEntry("BatchSPAppKey"),

            # Key Vault
            kv_name=cloud_plugin_wrapper.GetConfigEntry("KVName"),
            kv_sp_tenant_id=cloud_plugin_wrapper.GetConfigEntry("KVSPTenantId"),
            kv_sp_app_id=cloud_plugin_wrapper.GetConfigEntry("KVSPAppId"),
            kv_sp_cert_thumb=cloud_plugin_wrapper.GetConfigEntry("KVSPCertThumbprint"),

            # Domain
            domain_name=cloud_plugin_wrapper.GetConfigEntry("DomainName"),
            domain_ou_path=cloud_plugin_wrapper.GetConfigEntryWithDefault("DomainOUPath", None),

            # Networking
            subnet_id=cloud_plugin_wrapper.GetConfigEntryWithDefault("SubnetResourceId", None),
            smb_network_shares=cloud_plugin_wrapper.GetConfigEntryWithDefault("SMBNetworkShares", None),
            nfs_network_shares=cloud_plugin_wrapper.GetConfigEntryWithDefault("NFSNetworkShares", None),
            disable_remote_access=cloud_plugin_wrapper.GetBooleanConfigEntry("DisableRemoteAccess"),

            # VM Config
            vm_sizes=cloud_plugin_wrapper.GetConfigEntryWithDefault("VMSizes", 'Standard_F8;Standard_F16'),
            use_low_priority_vms=cloud_plugin_wrapper.GetBooleanConfigEntryWithDefault("UseLowPriorityVMs", False),
            windows_start_task_url=cloud_plugin_wrapper.GetConfigEntry("WindowsStartTaskUrl"),
            linux_start_task_url=cloud_plugin_wrapper.GetConfigEntry("LinuxStartTaskUrl"),
            app_licenses=cloud_plugin_wrapper.GetConfigEntryWithDefault("ApplicationLicenses", None),
            azure_region=cloud_plugin_wrapper.GetConfigEntryWithDefault("AzureRegion", None),
            # The Azure region the Batch account is in, e.g. westus2

            # Deadline
            deadline_repo_share_windows=cloud_plugin_wrapper.GetConfigEntry("DeadlineRepositoryShareOrPathWindows"),
            deadline_repo_share_linux=cloud_plugin_wrapper.GetConfigEntry("DeadlineRepositoryShareOrPathLinux"),
            deadline_region=cloud_plugin_wrapper.GetConfigEntry("DeadlineRegion"),  # The deadline region the slaves should join
            deadline_cloud_region=cloud_plugin_wrapper.GetConfigEntry("DeadlineCloudRegion"),  # Used as a moniker to separate pools
            deadline_license_server=cloud_plugin_wrapper.GetConfigEntryWithDefault("DeadlineLicenseServer", None),
            deadline_license_mode=cloud_plugin_wrapper.GetConfigEntry("DeadlineLicenseMode"),
            deadline_groups=cloud_plugin_wrapper.GetConfigEntryWithDefault("DeadlineGroups", None),
            deadline_pools=cloud_plugin_wrapper.GetConfigEntryWithDefault("DeadlinePools", None),

            # Images
            managed_image_id_1=cloud_plugin_wrapper.GetConfigEntryWithDefault("ManagedImageId1", None),
            managed_image_os_1=cloud_plugin_wrapper.GetConfigEntryWithDefault("ManagedImageOs1", None),
            managed_image_id_2=cloud_plugin_wrapper.GetConfigEntryWithDefault("ManagedImageId2", None),
            managed_image_os_2=cloud_plugin_wrapper.GetConfigEntryWithDefault("ManagedImageOs2", None),

            # Application insights
            app_insights_app_key=cloud_plugin_wrapper.GetConfigEntryWithDefault("ApplicationInsightsAppId", None),
            app_insights_instrumentation_key=cloud_plugin_wrapper.GetConfigEntryWithDefault(
                "ApplicationInsightsInstrumentationKey", None))
    except:
        traceback.print_exc()
        raise

    return config


class BatchPluginConfig:
    def __init__(self,
                 batch_url,
                 batch_sp_tenant_id,
                 batch_sp_app_id,
                 batch_sp_app_key,

                 kv_name,
                 kv_sp_tenant_id,
                 kv_sp_app_id,
                 kv_sp_cert_thumb,

                 domain_name,
                 domain_ou_path,

                 subnet_id,
                 smb_network_shares,
                 nfs_network_shares,
                 disable_remote_access,

                 vm_sizes,
                 use_low_priority_vms,
                 windows_start_task_url,
                 linux_start_task_url,
                 app_licenses,
                 azure_region,

                 deadline_repo_share_windows,
                 deadline_repo_share_linux,
                 deadline_region,
                 deadline_cloud_region,
                 deadline_license_server,
                 deadline_license_mode,
                 deadline_groups,
                 deadline_pools,

                 managed_image_id_1,
                 managed_image_os_1,
                 managed_image_id_2,
                 managed_image_os_2,

                 app_insights_app_key,
                 app_insights_instrumentation_key,

                 authority_host_uri='https://login.microsoftonline.com'):
        self.batch_url = batch_url
        self.batch_sp_tenant_id = batch_sp_tenant_id
        self.authority_uri = authority_host_uri + '/' + batch_sp_tenant_id
        self.batch_sp_app_id = batch_sp_app_id
        self.batch_sp_app_key = batch_sp_app_key

        self.kv_name = kv_name
        self.kv_sp_tenant_id = kv_sp_tenant_id
        self.kv_sp_app_id = kv_sp_app_id
        self.kv_sp_cert_thumb = kv_sp_cert_thumb

        self.domain_name = domain_name
        self.domain_ou_path = domain_ou_path

        self.subnet_id = subnet_id
        self.smb_network_shares = smb_network_shares
        self.nfs_network_shares = nfs_network_shares
        self.disable_remote_access = disable_remote_access

        self.vm_sizes = self._split_param_value(vm_sizes)
        self.use_low_priority_vms = use_low_priority_vms
        self.windows_start_task_url = windows_start_task_url
        self.linux_start_task_url = linux_start_task_url
        self.app_licenses = app_licenses
        self.azure_region = azure_region

        self.deadline_repo_share_windows = deadline_repo_share_windows
        self.deadline_repo_share_linux = deadline_repo_share_linux
        self.deadline_region = deadline_region
        self.deadline_cloud_region = deadline_cloud_region
        self.deadline_license_server = deadline_license_server
        self.deadline_license_mode = deadline_license_mode
        self.deadline_groups = deadline_groups
        self.deadline_pools = deadline_pools

        self.managed_image_id_1 = managed_image_id_1
        self.managed_image_os_1 = managed_image_os_1
        self.managed_image_id_2 = managed_image_id_2
        self.managed_image_os_2 = managed_image_os_2

        self.app_insights_app_key = app_insights_app_key
        self.app_insights_instrumentation_key = app_insights_instrumentation_key

    def get_os_images(self):
        """
        Converts an Azure managed image Ids to a Deadline.Cloud.OSImage list
        :param config: Batch configuration
        :type config: BatchConfig
        :return: OS images
        :rtype: list of Deadline.Cloud.OSImage
        """
        os_images = []
        if self.managed_image_id_1:
            osi = OSImage()
            osi.ID = self.managed_image_id_1
            osi.Description = images.get_image_display_name(self.managed_image_id_1)
            osi.Platform = Environment2.OS.Windows if self.managed_image_os_1 is "Windows" else Environment2.OS.Linux
            os_images.append(osi)

        if self.managed_image_id_2:
            osi = OSImage()
            osi.ID = self.managed_image_id_2
            osi.Description = images.get_image_display_name(self.managed_image_id_2)
            osi.Platform = Environment2.OS.Windows if self.managed_image_os_2 is "Windows" else Environment2.OS.Linux
            os_images.append(osi)

        return os_images

    @staticmethod
    def _split_param_value(value):
        if value:
            return value.split(";")
        return None

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

import sys
import time
import os.path
import traceback
import uuid

from Deadline.Scripting import *
from Deadline.Cloud import CloudPluginWrapper, CloudInstance, InstanceStatus, OSImage, HardwareType
from FranticX import Environment2
from System.IO import *

import azure.common.credentials
import azure.batch.batch_service_client as batchsc
import azure.batch.models as batchmodels

# Local plugin imports
sys.path.append(os.path.join(os.path.dirname(__file__)))
import pluginconfig
import mappers
import images
import hardware

def GetCloudPluginWrapper():
    return AzureBatchCloudPlugin()

def CleanupCloudPlugin(cloudPlugin):
    cloudPlugin.Cleanup()

class AzureBatchCloudPlugin(CloudPluginWrapper):
    def __init__(self):
        self.sms = None
        self.VerifyAccessCallback += self.VerifyAccess
        self.AvailableHardwareTypesCallback += self.GetAvailableHardwareTypes
        self.AvailableOSImagesCallback += self.GetAvailableOSImages
        self.CloneInstanceCallback += self.CloneInstance
        self.CreateInstancesCallback += self.CreateInstances
        self.GetActiveInstancesCallback += self.GetActiveInstances
        self.TerminateInstancesCallback += self.TerminateInstances
        self.GetHostnameCallback += self.GetHostname
        self.CreateImageCallback += self.CreateImage
        self.GetImageSourcesCallback += self.ImageSources
        self.StopInstancesCallback += self.StopInstances
        self.StartInstancesCallback += self.StartInstances
        self.RebootInstancesCallback += self.RebootInstances
        self.batch_config = None
        self.batch_client = None

    def _get_config(self):
        """
        Returns an instance of the Batch plugins config
        :return: BatchConfig
        """
        if not self.batch_config:
            self.batch_config = pluginconfig.load_config(self)
        return self.batch_config

    def _get_batch_client(self):
        """
        Returns an instance of the BatchClient
        :return: Batch
        """
        if not self.batch_client:
            config = self._get_config()
            self.batch_client = Batch(config)
        return self.batch_client

    def Cleanup(self):
        del self.VerifyAccessCallback
        del self.AvailableHardwareTypesCallback
        del self.AvailableOSImagesCallback
        del self.CloneInstanceCallback
        del self.CreateInstancesCallback
        del self.GetActiveInstancesCallback
        del self.TerminateInstancesCallback
        del self.GetHostnameCallback
        del self.CreateImageCallback
        del self.GetImageSourcesCallback
        del self.StopInstancesCallback
        del self.StartInstancesCallback
        del self.RebootInstancesCallback

    def VerifyAccess(self):
        client = self._get_batch_client()
        client.list_pools()
        return True

    def GetActiveInstances(self):

        config = self._get_config()

        instanceList = []

        try:
            client = self._get_batch_client()
            pools = client.list_pools()
            if pools:
                for p in pools:
                    if not p.id.startswith('{}-'.format(config.deadline_cloud_region)):
                        continue

                    if p.allocation_state == batchmodels.AllocationState.steady \
                            and p.state == batchmodels.PoolState.active \
                            and p.current_dedicated_nodes == 0 \
                            and p.current_low_priority_nodes == 0:
                        client.delete_pool(p.id)
                        try:
                            client.delete_job(p.id)
                        except:
                            # No such job
                            pass
                        continue

                    compute_nodes = client.list_compute_nodes(p.id)
                    if compute_nodes:
                        for cn in compute_nodes:
                            instance = mappers.compute_node_to_deadline_instance(p, cn)
                            instance.RegionName = config.deadline_region
                            instance.Zone = config.azure_region
                            instanceList.append(instance)

                    if p.allocation_state == batchmodels.AllocationState.resizing:
                        # If the pool is resizing, we need to return mock instances
                        # for any nodes not yet provisioned, otherwise the Balancer will
                        # think they don't exist and keep trying to scale up.
                        current_nodes = p.current_dedicated_nodes + p.current_low_priority_nodes
                        target_nodes = p.target_dedicated_nodes + p.target_low_priority_nodes
                        if current_nodes < target_nodes:
                            for i in range(target_nodes - current_nodes):
                                cn = mappers.get_mock_compute_node('not available')
                                instance = mappers.compute_node_to_deadline_instance(p, cn)
                                instance.RegionName = config.deadline_region
                                instance.Zone = config.azure_region
                                instanceList.append(instance)
        except:
            traceback.print_exc()

        return instanceList

    def GetHostname(self, instanceID):
        ClientUtils.LogText('GetHostname for {}'.format(instanceID))

        if instanceID == None or len(instanceID) == 0:
            return ""

        try:
            pool_id, compute_node_id = \
                get_pool_id_and_compute_node_id_from_instance_id(instanceID)

            client = self._get_batch_client()
            return client.get_compute_node_hostname(pool_id, compute_node_id)
        except:
            ClientUtils.LogText(traceback.format_exc())
            return ""

    def GetAvailableHardwareTypes(self):
        """

        :return:
        :rtype: list of Deadline.Cloud.HardwareType
        """
        config = self._get_config()
        return hardware.vm_sizes_to_hardware_types(config.vm_sizes)

    def GetAvailableOSImages(self):
        """

        :return: OS image list
        :rtype: list of OSImage
        """
        conf = self._get_config()
        image_list = conf.get_os_images()

        # add the default images
        image_list.extend(images.get_abr_images())

        return image_list

    def CloneInstance(self, instance, count):
        try:
            return self.CreateInstances(instance.HardwareID, instance.ImageID, count)
        except:
            ClientUtils.LogText(traceback.format_exc())

    def CreateInstances(self, hardwareID, imageID, count):
        ClientUtils.LogText(
            'Creating instances with hardware {}, imageId {}, count {}'.format(hardwareID, imageID, count))

        startedInstances = []

        config = self._get_config()
        use_low_priority = config.use_low_priority_vms

        pool_id = get_pool_name(config.deadline_cloud_region, imageID, hardwareID, use_low_priority)
        client = self._get_batch_client()

        ClientUtils.LogText('Looking for existing pool {}'.format(pool_id))

        os_images = self.GetAvailableOSImages()
        os_image = next((x for x in os_images if x.ID == imageID), None)

        if not os_image:
            ClientUtils.LogText('Failed to find image for id {}'.format(imageID))
            return startedInstances

        is_linux_pool = False
        if os_image.Platform == Environment2.OS.Linux:
            is_linux_pool = True

        pool = client.get_pool(pool_id)
        if not pool:
            ClientUtils.LogText('Did not find existing pool {}, creating new one'.format(pool_id))

            batch_image_spec = images.image_id_to_image_spec(config, imageID)

            if os_image.Platform == Environment2.OS.Windows:
                starttask_url = self.batch_config.windows_start_task_url
                starttask_script = 'deadline-starttask.ps1'
            else:
                starttask_url = self.batch_config.linux_start_task_url
                starttask_script = 'deadline-starttask.sh'

            app_pkgs = [batchmodels.ApplicationPackageReference('DeadlineClient')]
            starttask_cmd = get_deadline_starttask_cmd(self.batch_config, starttask_script, os_image)

            app_licenses = None
            if self.batch_config.app_licenses:
                app_licenses = self.batch_config.app_licenses.split(';')

            dedicated_nodes = 0 if use_low_priority else count
            low_prio_nodes = count if use_low_priority else 0

            client.create_pool(pool_id,
                               hardwareID,
                               dedicated_nodes,
                               low_prio_nodes,
                               batch_image_spec,
                               starttask_cmd,
                               starttask_url,
                               starttask_script,
                               self.batch_config.kv_sp_cert_thumb,
                               app_licenses,
                               self.batch_config.disable_remote_access,
                               app_pkgs,
                               self.batch_config.subnet_id,
                               app_insights_app_key=self.batch_config.app_insights_app_key,
                               app_insights_instrumentation_key=self.batch_config.app_insights_instrumentation_key)

            if self.batch_config.app_licenses:
                total_nodes = dedicated_nodes + low_prio_nodes
                client.create_job(pool_id, pool_id, total_nodes, is_linux_pool)

        else:
            current_dedicated = pool.target_dedicated_nodes
            current_low_prio = pool.target_low_priority_nodes

            if use_low_priority:
                current_low_prio += count
            else:
                current_dedicated += count

            try:
                client.resize_pool(pool_id,
                                   target_dedicated=current_dedicated,
                                   target_low_priority=current_low_prio)

                if self.batch_config.app_licenses:
                    total_nodes = current_dedicated + current_low_prio
                    client.create_job(pool_id, pool_id, total_nodes, is_linux_pool)
            except:
                traceback.print_exc()

        return self.GetActiveInstances()

    def TerminateInstances(self, instanceIDs):
        results = []
        ClientUtils.LogText('Terminating instance ids {}'.format(','.join(instanceIDs)))
        if instanceIDs == None or len(instanceIDs) == 0:
            return []
        pool_to_nodes = {}
        for instance_id in instanceIDs:
            pool_id, compute_node_id = \
                get_pool_id_and_compute_node_id_from_instance_id(instance_id)
            pool_nodes = pool_to_nodes.get(pool_id)
            if pool_nodes is None:
                pool_nodes = []
                pool_to_nodes[pool_id] = pool_nodes
            pool_nodes.append(compute_node_id)

        client = self._get_batch_client()
        for pool_id, nodes in pool_to_nodes.iteritems():
            if len(nodes) > 0:
                client.remove_compute_nodes(pool_id, nodes)

        return results

    def StopInstances(self, instanceIDs):
        ClientUtils.LogText('Stopping instances {}'.format(','.join(instanceIDs)))
        if instanceIDs == None or len(instanceIDs) == 0:
            return []
        return results

    def StartInstances(self, instanceIDs):
        ClientUtils.LogText('Starting instances {}'.format(','.join(instanceIDs)))
        if instanceIDs == None or len(instanceIDs) == 0:
            return []
        return results

    def RebootInstances(self, instanceIDs):
        ClientUtils.LogText('Rebooting instances {}'.format(','.join(instanceIDs)))
        if instanceIDs is None or len(instanceIDs) == 0:
            return []
        client = self._get_batch_client()
        for instance_id in instanceIDs:
            pool_id, compute_node_id = \
                get_pool_id_and_compute_node_id_from_instance_id(instance_id)
            client.reboot_compute_node(pool_id, compute_node_id)
        return results

    def CreateImage(self, source):

        result = False

        ClientUtils.LogText('Create image {}'.format(source))

        return result

    def ImageSources(self):
        sources = []

        ClientUtils.LogText('ImageSources')

        return sources


### Mappers ###

def get_pool_id_and_compute_node_id_from_instance_id(instance_id):
    tokens = instance_id.split(":")
    # return pool_id, compute_node_id
    return tokens[0], tokens[1]


def get_pool_name(cloud_region, image_id, hardware_id, use_low_priority):
    image_display_name = images.get_image_display_name(image_id)
    pool_id = '{}-{}-{}'.format(cloud_region, image_display_name, hardware_id)
    if use_low_priority:
        pool_id = '{}-lp'.format(pool_id)
    return pool_id


def get_deadline_starttask_cmd(batch_config, starttask_script, os_image):
    """
    Returns the OS specific start task command line.

    :param batch_config: Batch configuration
    :type batch_config: BatchConfig
    :param starttask_script:
    :type starttask_script:  str
    :param os_image:
    :type os_image: OSImage
    :return: start task command line
    :rtype: str
    """
    if os_image.Platform == Environment2.OS.Windows:
        deadline_cmd = 'cmd.exe /c powershell.exe .\{} ' \
                       '-installerPath "%AZ_BATCH_APP_PACKAGE_DeadlineClient%" ' \
                       '-tenantId "{}" ' \
                       '-applicationId "{}" ' \
                       '-keyVaultCertificateThumbprint "{}" ' \
                       '-keyVaultName "{}" ' \
                       '-deadlineRepositoryPath "{}" ' \
                       '-deadlineLicenseMode "{}" ' \
                       '-deadlineRegion "{}"'.format(
            starttask_script,
            batch_config.kv_sp_tenant_id,
            batch_config.kv_sp_app_id,
            batch_config.kv_sp_cert_thumb,
            batch_config.kv_name,
            batch_config.deadline_repo_share_windows,
            batch_config.deadline_license_mode,
            batch_config.deadline_region)

        if batch_config.domain_name:
            deadline_cmd += ' -domainName "{}"'.format(batch_config.domain_name)

        if batch_config.domain_ou_path:
            deadline_cmd += ' -domainOuPath \'{}\''.format(batch_config.domain_ou_path)

        if batch_config.deadline_license_server:
            deadline_cmd += ' -deadlineLicenseServer "{}"'.format(batch_config.deadline_license_server)

        if batch_config.smb_network_shares:
            deadline_cmd += ' -smbShares \'{}\''.format(batch_config.smb_network_shares)

        if batch_config.nfs_network_shares:
            deadline_cmd += ' -nfsShares \'{}\''.format(batch_config.nfs_network_shares)

        if batch_config.deadline_windows_groups:
           deadline_cmd += ' -deadlineGroups \'{}\''.format(batch_config.deadline_windows_groups)

        if batch_config.deadline_windows_pools:
           deadline_cmd += ' -deadlinePools \'{}\''.format(batch_config.deadline_windows_pools)
    else:
        deadline_cmd = '/bin/bash -c \'{} ' \
                       '--tenantId "{}" ' \
                       '--applicationId "{}" ' \
                       '--keyVaultCertificateThumbprint "{}" ' \
                       '--keyVaultName "{}" ' \
                       '--deadlineRepositoryPath "{}" ' \
                       '--deadlineLicenseMode "{}" ' \
                       '--deadlineRegion "{}"'.format(
            starttask_script,
            batch_config.kv_sp_tenant_id,
            batch_config.kv_sp_app_id,
            batch_config.kv_sp_cert_thumb,
            batch_config.kv_name,
            batch_config.deadline_repo_share_linux,
            batch_config.deadline_license_mode,
            batch_config.deadline_region)

        if batch_config.deadline_license_server:
            deadline_cmd += ' --deadlineLicenseServer "{}"'.format(batch_config.deadline_license_server)

        if batch_config.smb_network_shares:
            deadline_cmd += ' --smbShares "{}"'.format(batch_config.smb_network_shares.replace('\\', '\\\\'))

        if batch_config.nfs_network_shares:
            deadline_cmd += ' --nfsShares "{}"'.format(batch_config.nfs_network_shares.replace('\\', '\\\\'))

        if batch_config.domain_name:
            deadline_cmd += ' --domainName "{}"'.format(batch_config.domain_name)

        if batch_config.deadline_linux_groups:
           deadline_cmd += ' --deadlineGroups "{}"'.format(batch_config.deadline_linux_groups)

        if batch_config.deadline_linux_pools:
           deadline_cmd += ' --deadlinePools "{}"'.format(batch_config.deadline_linux_pools)

        deadline_cmd += '\''

    return deadline_cmd


class Batch:
    def __init__(self, batch_config):
        self.batch_config = batch_config

    def list_pools(self):
        client = self._get_batch_client()
        return client.pool.list()

    def create_job(self, job_id, pool_id, total_nodes, is_linux_pool):
        client = self._get_batch_client()
        try:
            pool_info = batchmodels.PoolInformation(pool_id=pool_id)
            job = batchmodels.JobAddParameter(
                id=job_id,
                pool_info=pool_info
            )

            try:
                client.job.add(job)
            except batchmodels.BatchErrorException as be:
                if be.error and be.error.code == 'JobExists':
                    pass
                else:
                    print('Error creating job, code={}, message={}'.format(be.error.code, be.error.message))
                    raise

            if is_linux_pool:
                cmd_line = '/bin/bash -c azure-batch-ses.sh'
                script = 'azure-batch-ses.sh'
                script_url = 'https://raw.githubusercontent.com/Azure/azure-deadline/master/CloudProviderPlugin/Scripts/azure-batch-ses.sh'
            else:
                cmd_line = 'powershell.exe -file azure-batch-ses.ps1'
                script = 'azure-batch-ses.ps1'
                script_url = 'https://raw.githubusercontent.com/Azure/azure-deadline/master/CloudProviderPlugin/Scripts/azure-batch-ses.ps1'

            task = batchmodels.TaskAddParameter(
                id='',
                command_line=cmd_line,
                resource_files=[batchmodels.ResourceFile(script_url, script)],
                constraints=batchmodels.TaskConstraints(max_task_retry_count=3),
                user_identity=batchmodels.UserIdentity(
                    auto_user=batchmodels.AutoUserSpecification(
                        scope=batchmodels.AutoUserScope.pool,
                        elevation_level=batchmodels.ElevationLevel.admin
                    ))
            )

            for i in range(total_nodes):
                task.id = str(uuid.uuid4())
                client.task.add(job_id=job.id, task=task)

        except batchmodels.BatchErrorException as be:
            if be.error:
                print('Error creating job, code={}, message={}'.format(be.error.code, be.error.message))
                if be.error.values:
                    for e in be.error.values:
                        print('Key={}, Value={}'.format(e.key, e.value))
            raise

    def delete_job(self, job_id):
        client = self._get_batch_client()
        try:
            client.job.delete(job_id)
        except batchmodels.BatchErrorException as be:
            if be.error:
                print('Error deleting job, code={}, message={}'.format(be.error.code, be.error.message))
                if be.error.values:
                    for e in be.error.values:
                        print('Key={}, Value={}'.format(e.key, e.value))
            raise

    def get_pool(self, pool_id):
        """
        Returns the specified pool, or None
        :param pool_id:
        :type pool_id: str
        :return: The pool or None
        :rtype: azure.batch.models.Pool
        """
        client = self._get_batch_client()
        try:
            return client.pool.get(pool_id)
        except batchmodels.BatchErrorException as be:
            if be.error:
                if be.error.code == 'PoolNotFound':
                    return None

                print('Error fetching pool, code={}, message={}'.format(be.error.code, be.error.message))
                if be.error.values:
                    for e in be.error.values:
                        print('Key={}, Value={}'.format(e.key, e.value))
            raise

    def delete_pool(self, pool_id):
        """
        Deletes the specified pool
        :param pool_id:
        :type pool_id: str
        """
        client = self._get_batch_client()
        try:
            return client.pool.delete(pool_id)
        except batchmodels.BatchErrorException as be:
            if be.error:
                if be.error.code == 'PoolNotFound':
                    return None
                print('Error deleting pool, code={}, message={}'.format(be.error.code, be.error.message))
                if be.error.values:
                    for e in be.error.values:
                        print('Key={}, Value={}'.format(e.key, e.value))
            raise

    def resize_pool(self, pool_id, target_dedicated, target_low_priority):
        client = self._get_batch_client()
        pool = self.get_pool(pool_id)
        if pool:
            if pool.allocation_state == batchmodels.AllocationState.resizing:
                client.pool.stop_resize(pool_id)

                while (pool.allocation_state != batchmodels.AllocationState.steady):
                    time.sleep(15)
                    pool = self.get_pool(pool_id)

            resize_param = batchmodels.PoolResizeParameter(
                target_dedicated_nodes=target_dedicated,
                target_low_priority_nodes=target_low_priority
            )
            client.pool.resize(pool_id, resize_param)

    def create_pool(self, pool_id, vm_size, target_dedicated, target_low_priority,
                    batch_image_spec, starttask_cmd,
                    starttask_url, starttask_script, sp_cert_thumb, app_licenses=None,
                    disable_remote_access=True, app_pkgs=None, subnet_id=None,
                    app_insights_app_key=None, app_insights_instrumentation_key=None):

        pool = batchmodels.PoolAddParameter(
            id=pool_id,
            display_name=pool_id,
            vm_size=vm_size,
            target_dedicated_nodes=target_dedicated,
            target_low_priority_nodes=target_low_priority,
            virtual_machine_configuration=batch_image_spec.get_virtual_machine_configuration(),
            application_package_references=app_pkgs,
            certificate_references=[batchmodels.CertificateReference(sp_cert_thumb, 'sha1')]
        )

        if app_licenses:
            pool.application_licenses = app_licenses

        pool.start_task = batchmodels.StartTask(
            command_line=starttask_cmd,
            max_task_retry_count=3,
            user_identity=batchmodels.UserIdentity(
                auto_user=batchmodels.AutoUserSpecification(
                    scope=batchmodels.AutoUserScope.pool,
                    elevation_level=batchmodels.ElevationLevel.admin
                )),
            wait_for_success=True,
            resource_files=[batchmodels.ResourceFile(starttask_url, starttask_script)]
        )

        if app_insights_app_key and app_insights_instrumentation_key:
            pool.start_task.environment_settings = [
                batchmodels.EnvironmentSetting('APP_INSIGHTS_APP_ID', app_insights_app_key),
                batchmodels.EnvironmentSetting('APP_INSIGHTS_INSTRUMENTATION_KEY', app_insights_instrumentation_key)
            ]

        if subnet_id:
            pool.network_configuration = batchmodels.NetworkConfiguration(
                subnet_id=subnet_id
            )

        if disable_remote_access:
            if pool.network_configuration is None:
                pool.network_configuration = batchmodels.NetworkConfiguration()
            endpoint_config = batchmodels.PoolEndpointConfiguration(
                inbound_nat_pools=[
                    batchmodels.InboundNATPool(
                        'DisableRDP',
                        batchmodels.InboundEndpointProtocol.tcp,
                        3389,
                        60000,
                        60099,
                        network_security_group_rules=[
                            batchmodels.NetworkSecurityGroupRule(
                                150,
                                batchmodels.NetworkSecurityGroupRuleAccess.deny,
                                '*')
                        ]
                    ),
                    batchmodels.InboundNATPool(
                        'DisableSSH',
                        batchmodels.InboundEndpointProtocol.tcp,
                        22,
                        61000,
                        61099,
                        network_security_group_rules=[
                            batchmodels.NetworkSecurityGroupRule(
                                151,
                                batchmodels.NetworkSecurityGroupRuleAccess.deny,
                                '*')
                        ]
                    )
                ]
            )
            pool.network_configuration.endpoint_configuration = endpoint_config

        try:
            client = self._get_batch_client()
            client.pool.add(pool)
        except batchmodels.BatchErrorException as be:
            if be.error:
                print('Error creating pool, code={}, message={}'.format(be.error.code, be.error.message))
                if be.error.values:
                    for e in be.error.values:
                        print('Key={}, Value={}'.format(e.key, e.value))
            raise

    def list_compute_nodes(self, pool_id):
        client = self._get_batch_client()
        pool = self.get_pool(pool_id)
        if not pool:
            return None
        return client.compute_node.list(pool_id)

    def reboot_compute_node(self, pool_id, compute_node_id):
        client = self._get_batch_client()
        pool = self.get_pool(pool_id)
        if not pool:
            return None
        client.compute_node.reboot(pool_id, compute_node_id)

    def remove_compute_nodes(self, pool_id, compute_node_ids):
        client = self._get_batch_client()
        pool = self.get_pool(pool_id)
        if not pool:
            return None
        remove_param = batchmodels.NodeRemoveParameter(
            node_list=compute_node_ids,
            node_deallocation_option=batchmodels.ComputeNodeDeallocationOption.terminate
        )
        client.pool.remove_nodes(pool_id, remove_param)

    def get_compute_node_hostname(self, pool_id, compute_node_id):
        client = self._get_batch_client()
        pool = self.get_pool(pool_id)
        if not pool:
            return None
        resp = client.file.get_from_compute_node(pool_id, compute_node_id, '/startup/wd/hostname.txt')
        print('Response: {0}'.format(resp))
        type(resp)


    def _get_batch_client(self):
        batch_client = batchsc.BatchServiceClient(
            self._get_batch_credentials(),
            base_url=self.batch_config.batch_url)
        return batch_client

    def _get_batch_credentials(self):
        resource_uri = 'https://batch.core.windows.net/'
        return azure.common.credentials.ServicePrincipalCredentials(
            self.batch_config.batch_sp_app_id,
            self.batch_config.batch_sp_app_key,
            tenant=self.batch_config.batch_sp_tenant_id,
            auth_uri=self.batch_config.authority_uri,
            resource=resource_uri,
        )

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

from Deadline.Cloud import InstanceStatus, HardwareType, CloudInstance
from azure.batch.models import ComputeNode, ComputeNodeState


def compute_node_state_to_deadline_status(compute_node_state):
    """
    Maps a Batch ComputeNodeState to a Deadline cloud instance status
    :param compute_node_state: azure.batch.models.ComputeNodeState
    :return: Deadline.Cloud.InstanceStatus
    """
    if compute_node_state == ComputeNodeState.idle:
        return InstanceStatus.Running
    if compute_node_state == ComputeNodeState.rebooting:
        return InstanceStatus.Rebooting
    if compute_node_state == ComputeNodeState.reimaging:
        return InstanceStatus.Rebooting
    if compute_node_state == ComputeNodeState.running:
        return InstanceStatus.Running
    if compute_node_state == ComputeNodeState.unusable:
        return InstanceStatus.Unknown
    if compute_node_state == ComputeNodeState.starting:
        return InstanceStatus.Pending
    if compute_node_state == ComputeNodeState.waiting_for_start_task:
        return InstanceStatus.Pending
    if compute_node_state == ComputeNodeState.start_task_failed:
        return InstanceStatus.Unknown
    if compute_node_state == ComputeNodeState.unknown:
        return InstanceStatus.Unknown
    if compute_node_state == ComputeNodeState.leaving_pool:
        return InstanceStatus.Stopping
    if compute_node_state == ComputeNodeState.offline:
        return InstanceStatus.Stopped
    if compute_node_state == ComputeNodeState.preempted:
        return InstanceStatus.Stopped
    return InstanceStatus.Unknown


def get_mock_compute_node(id):
    cn = ComputeNode()
    cn.id = id
    cn.ip_address = '169.254.0.0'
    cn.state = ComputeNodeState.starting
    return cn


def compute_node_to_deadline_instance(pool, compute_node):
    """
    Maps a Batch compute node to a Deadline cloud instance
    :param pool: The pool
    :type pool: azure.batch.models.Pool
    :param compute_node: azure.batch.models.ComputeNode
    :type compute_node: azure.batch.models.ComputeNode

    :return: The cloud instance
    :rtype: Deadline.Cloud.CloudInstance
    """
    image_id = None
    vm_config = pool.virtual_machine_configuration
    if vm_config and vm_config.image_reference:
        image_ref = vm_config.image_reference
        if image_ref.virtual_machine_image_id:
            image_id = image_ref.virtual_machine_image_id
        else:
            image_id = '{}:{}:{}:{}:{}'.format(
                image_ref.publisher,
                image_ref.offer,
                image_ref.sku,
                image_ref.version,
                vm_config.node_agent_sku_id
            )

    ci = CloudInstance()
    ci.ID = get_cloud_instance_id(pool.id, compute_node.id)
    ci.Name = compute_node.id
    ci.HardwareID = pool.vm_size
    ci.Provider = "AzureBatch"
    ci.Zone = None
    ci.ImageID = image_id
    ci.Hostname = compute_node.id
    ci.PublicIP = compute_node.ip_address
    ci.PrivateIP = compute_node.ip_address
    ci.Status = compute_node_state_to_deadline_status(compute_node.state)

    if compute_node.endpoint_configuration and compute_node.endpoint_configuration.inbound_endpoints:
        endpoints = compute_node.endpoint_configuration.inbound_endpoints
        for endpoint in endpoints:
            if endpoint.name.startswith("RDP") or endpoint.name.startswith("SSH"):
                ci.PublicIP = endpoint.public_ip_address

    return ci


def get_cloud_instance_id(pool_id, compute_node_id):
    return '{}:{}'.format(pool_id, compute_node_id)

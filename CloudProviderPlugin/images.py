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

from Deadline.Cloud import OSImage
from FranticX import Environment2

import azure.batch.models as batchmodels


class BatchImageSpec:
    def __init__(self, node_agent_sku_id, image_id=None,
                 image_publisher=None, image_offer=None, image_sku=None, image_version=None):
        self.node_agent_sku_id = node_agent_sku_id
        self.image_id = image_id
        self.image_publisher = image_publisher
        self.image_offer = image_offer
        self.image_sku = image_sku
        self.image_version = image_version

    def get_virtual_machine_configuration(self):
        if self.image_id:
            image_ref = batchmodels.ImageReference(
                virtual_machine_image_id=self.image_id
            )
        else:
            image_ref = batchmodels.ImageReference(
                publisher=self.image_publisher,
                offer=self.image_offer,
                sku=self.image_sku,
                version=self.image_version
            )

        return batchmodels.VirtualMachineConfiguration(
            image_reference=image_ref,
            node_agent_sku_id=self.node_agent_sku_id
        )


def get_image_display_name(image_id):
    if image_id.startswith("/subscription"):
        return image_id.split("/")[-1:][0]
    return image_id.split(":")[1]


def get_abr_images():
    image_list = []

    # add the Azure Batch Rendering images
    osi = OSImage()
    osi.ID = "batch:rendering-windows2016:rendering:latest:batch.node.windows amd64"
    osi.Description = "Azure Batch Windows 2016 Rendering Image"
    osi.Platform = Environment2.OS.Windows
    image_list.append(osi)

    osi = OSImage()
    osi.ID = "batch:rendering-centos73:rendering:latest:batch.node.centos 7"
    osi.Description = "Azure Batch CentOS 7.3 Rendering Image"
    osi.Platform = Environment2.OS.Linux
    image_list.append(osi)

    return image_list


osNodeAgentSkus = {
    'Windows': 'batch.node.windows amd64',
    'Ubuntu14.04': 'batch.node.ubuntu 14.04',
    'Ubuntu16.04': 'batch.node.ubuntu 16.04',
    'CentOS7': 'batch.node.centos 7'
}


def image_os_to_node_agent_sku(image_os):
    return osNodeAgentSkus[image_os]


def image_id_to_image_spec(batch_config, image_id):
    if image_id:
        if image_id.startswith("/subscriptions/"):
            if image_id == batch_config.managed_image_id_1:
                return BatchImageSpec(
                    node_agent_sku_id=image_os_to_node_agent_sku(
                        batch_config.managed_image_os_1),
                    image_id=image_id
                )
            if image_id == batch_config.managed_image_id_2:
                return BatchImageSpec(
                    node_agent_sku_id=image_os_to_node_agent_sku(
                        batch_config.managed_image_os_2),
                    image_id=image_id
                )
        else:
            tokens = image_id.split(":")
            return BatchImageSpec(
                node_agent_sku_id=tokens[4],
                image_publisher=tokens[0],
                image_offer=tokens[1],
                image_sku=tokens[2],
                image_version=tokens[3]
            )
    return None
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

import unittest
import sys
import os
import clr
sys.path.insert(0, os.environ['DEADLINE_PATH'])

from config import BatchPluginConfig
import mappers

def get_config():
    config = BatchPluginConfig(
        batch_url='https://contoso.westus2.batch.azure.com',
        batch_sp_tenant_id='abc',
        batch_sp_app_id='abc',
        batch_sp_app_key='abc',

        kv_name='testkv',
        kv_sp_tenant_id='abc',
        kv_sp_app_id='abc',
        kv_sp_cert_thumb='abc',

        domain_name='abc',
        domain_ou_path='abc',

        subnet_id='subnet',
        smb_network_shares=None,
        nfs_network_shares=None,
        disable_remote_access=False,

        vm_sizes='Standard_F16',
        use_low_priority_vms=False,
        windows_start_task_url='https://',
        linux_start_task_url='https://',
        app_licenses=None,
        azure_region='westus2',

        deadline_repo_share_windows='\\\\DeadlineRepo\\DeadlineRepository',
        deadline_repo_share_linux='/mnt/deadlinerepo',
        deadline_region='westus',
        deadline_cloud_region='azurewestus',
        deadline_license_server=None,
        deadline_license_mode='Free',
        deadline_groups='group1',
        deadline_pools='pool1',

        managed_image_id_1=None,
        managed_image_os_1=None,
        managed_image_id_2=None,
        managed_image_os_2=None,

        app_insights_app_key=None,
        app_insights_instrumentation_key=None
    )
    return config

class Tests(unittest.TestCase):
    def test(self):
        config = get_config()





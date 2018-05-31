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

from Deadline.Cloud import HardwareType

class AzureVmSpec:
    def __init__(self, vcpus, mem_mb):
        self.vcpus = vcpus
        self.mem_mb = mem_mb


AZURE_VM_SIZES = {
    # Compute Optimised
    'Standard_F2': AzureVmSpec(2, 4 * 1024),
    'Standard_F4': AzureVmSpec(4, 8 * 1024),
    'Standard_F8': AzureVmSpec(8, 16 * 1024),
    'Standard_F16': AzureVmSpec(16, 32 * 1024),

    # General purpose
    'Standard_D2_v3': AzureVmSpec(2, 8 * 1024),
    'Standard_D4_v3': AzureVmSpec(4, 16 * 1024),
    'Standard_D8_v3': AzureVmSpec(8, 32 * 1024),
    'Standard_D16_v3': AzureVmSpec(16, 64 * 1024),
    'Standard_D32_v3': AzureVmSpec(32, 128 * 1024),
    'Standard_D64_v3': AzureVmSpec(64, 256 * 1024),

    # GPU v1
    'Standard_NC6': AzureVmSpec(6, 56 * 1024),
    'Standard_NC12': AzureVmSpec(12, 112 * 1024),
    'Standard_NC24': AzureVmSpec(24, 224 * 1024),
}


def vm_sizes_to_hardware_types(vm_sizes):
    """
    Maps Azure VM sizes to Deadline HardwareType list
    :param vm_sizes: list
    :return: list of Deadline.Cloud.HardwareType
    :rtype: list of Deadline.Cloud.HardwareType
    """
    hw_types = []
    if vm_sizes:
        for vm_size in vm_sizes:
            hwt = HardwareType()
            hwt.ID = vm_size
            hwt.Name = vm_size
            hwt.RamMB = 0
            hwt.VCPUs = 0

            if vm_size in AZURE_VM_SIZES:
                vm_spec = AZURE_VM_SIZES[vm_size]
                hwt.RamMB = vm_spec.mem_mb
                hwt.VCPUs = vm_spec.vcpus

            hw_types.append(hwt)
    else:
        for vm_size, vm_spec in AZURE_VM_SIZES.iteritems():
            hwt = HardwareType()
            hwt.ID = vm_size
            hwt.Name = vm_size
            hwt.RamMB = vm_spec.mem_mb
            hwt.VCPUs = vm_spec.vcpus
            hw_types.append(hwt)
    return hw_types

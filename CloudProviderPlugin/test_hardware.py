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

import hardware


class HardwareTests(unittest.TestCase):
    def test_no_vms_returns_all(self):
        vm_sizes = None
        hardware_types = hardware.vm_sizes_to_hardware_types(vm_sizes)
        self.assertEqual(13, len(hardware_types))

    def test_empty_vms_returns_all(self):
        vm_sizes = []
        hardware_types = hardware.vm_sizes_to_hardware_types(vm_sizes)
        self.assertEqual(13, len(hardware_types))

    def test_single_vm_returns_one(self):
        vm_sizes = ['Standard_F2']
        hardware_types = hardware.vm_sizes_to_hardware_types(vm_sizes)
        self.assertEqual(1, len(hardware_types))
        self.assertEqual('Standard_F2', hardware_types[0].ID)
        self.assertEqual('Standard_F2', hardware_types[0].Name)
        self.assertEqual(4*1024, hardware_types[0].RamMB)
        self.assertEqual(2, hardware_types[0].VCPUs)

    def test_unknown_vm_still_returns_one(self):
        vm_sizes = ['Standard_F22']
        hardware_types = hardware.vm_sizes_to_hardware_types(vm_sizes)
        self.assertEqual(1, len(hardware_types))
        self.assertEqual('Standard_F22', hardware_types[0].ID)
        self.assertEqual('Standard_F22', hardware_types[0].Name)
        self.assertEqual(0, hardware_types[0].RamMB)
        self.assertEqual(0, hardware_types[0].VCPUs)


if __name__ == '__main__':
    unittest.main()

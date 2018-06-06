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

import os
import os.path
import platform
import hashlib
import time

from Deadline.Events import *

def GetDeadlineEventListener():
    return AzureDataTransfer()

def CleanupDeadlineEventListener( deadlinePlugin ):
    deadlinePlugin.Cleanup()

class AzureDataTransfer (DeadlineEventListener):

    def __init__( self ):
        # Set up the event callbacks here
        self.OnJobSubmittedCallback += self.OnJobSubmitted
        self.OnSlaveStartingJobCallback += self.OnSlaveStartingJob

    def Cleanup( self ):
        del self.OnJobSubmittedCallback
        del self.OnSlaveStartingJobCallback

    # This is called when a Slave starts a job.
    def OnSlaveStartingJob(self, slaveName, job):

        if not self.should_sync_assets(job):
            self.LogInfo('Skipping data transfer, job does not use an enabled group or pool.')
            return

        syncDirection = self.GetConfigEntry('SyncDirection')
        if syncDirection == 'UploadOnly':
            self.LogInfo('Skipping data transfer, upload only sync specified.')
            return

        accountName = self.GetConfigEntry('BlobStorageAccountName')
        accountKey = self.GetConfigEntry('BlobStorageAccountKey')
        sourceFolders = self.GetConfigEntryWithDefault('SourceFolders', None)
        destinationContainer = self.GetConfigEntry('DestinationContainer')
        destinationFolderWindows = self.GetConfigEntryWithDefault('DestinationFolderWindows', None)
        destinationFolderLinux = self.GetConfigEntryWithDefault('DestinationFolderLinux', None)
        destinationFolder = destinationFolderWindows if platform.system() is 'Windows' else destinationFolderLinux

        if not accountName:
            self.LogInfo('No account name set in the event configuration')
            return

        if not accountKey:
            self.LogInfo('No account key set in the event configuration')
            return

        if not sourceFolders:
            self.LogInfo('No source folders set in the event configuration')
            return

        if not destinationContainer:
            self.LogInfo('No destination folders set in the event configuration')
            return

        if not destinationFolder:
            self.LogInfo('No destination folder set in the event configuration')
            return

        destinationFolder = os.path.expandvars(destinationFolder)

        self.LogInfo('Downloading assets for job {} on slave {} to {}'.format(job, slaveName, destinationFolder))

        azcopyExecutable = self.get_azcopy_cmd()
        args = self.get_azcopy_download_args(
            destinationFolder, accountName, accountKey, destinationContainer)

        start = time.time()
        exit_code = self.RunProcess(azcopyExecutable, args, os.environ['TEMP'], -1)
        self.LogInfo('Downloaded container {} to folder {} in {} seconds with exit code {}'.format(
            destinationContainer, destinationFolder, (time.time() - start), exit_code))


    # This is called when a Slave starts a job.
    def OnJobSubmitted(self, job):

        if not self.should_sync_assets(job):
            self.LogInfo('Skipping data transfer, job does not use an enabled group or pool.')
            return

        syncDirection = self.GetConfigEntry('SyncDirection')
        if syncDirection == 'DownloadOnly':
            self.LogInfo('Skipping data transfer, download only sync specified.')
            return

        accountName = self.GetConfigEntry('BlobStorageAccountName')
        accountKey = self.GetConfigEntry('BlobStorageAccountKey')
        sourceFolders = self.GetConfigEntryWithDefault('SourceFolders', '')
        destinationContainer = self.GetConfigEntry('DestinationContainer')

        if not accountName:
            self.LogInfo('No account name set in the event configuration')
            return

        if not accountKey:
            self.LogInfo('No account key set in the event configuration')
            return

        if not sourceFolders:
            self.LogInfo('No source folders set in the event configuration')
            return

        if not destinationContainer:
            self.LogInfo('No destination folders set in the event configuration')
            return

        sourceFolderList = sourceFolders.split(';')

        for sourceFolder in sourceFolderList:
            if not self.usable_path_for_os(sourceFolder):
                continue
            azcopyExecutable = self.get_azcopy_cmd()
            args = self.get_azcopy_upload_args(
                sourceFolder, accountName, accountKey, destinationContainer)
            start = time.time()
            exit_code = self.RunProcess(azcopyExecutable, args, os.environ['TEMP'], -1)
            self.LogInfo('Uploaded {} to container {} in {} seconds with exit code {}'.format(
                sourceFolder, destinationContainer, (time.time() - start), exit_code))

    def get_azcopy_cmd(self):
        if platform.system() is 'Windows':
            paths = [
                '{}\Microsoft SDKs\Azure\AzCopy\AzCopy.exe'.format(os.environ['ProgramFiles(x86)']),
                '{}\Microsoft SDKs\Azure\AzCopy\AzCopy.exe'.format(os.environ['ProgramFiles'])]

            azcopyExecutable = 'AzCopy'
            for path in paths:
                self.LogInfo('Checking for AzCopy {}'.format(path))
                if os.path.isfile(path):
                    azcopyExecutable = path
                    break
        elif platform.system() is 'Linux':
            azcopyExecutable = 'azcopy'
        else:
            msg = 'Unsupported operating system {}'.format(platform.system())
            self.LogInfo(msg)
            raise RuntimeError(msg)

        return azcopyExecutable

    def get_azcopy_upload_args(self, sourceFolder, accountName, accountKey, destinationContainer):
        journal_folder = os.path.join(os.environ['TEMP'], hashlib.md5(sourceFolder).hexdigest())
        head, tail = os.path.split(sourceFolder)
        dest_folder = tail if not None else head
        if platform.system() is 'Windows':
            args = '/Source:\"{}\" /Dest:https://{}.blob.core.windows.net/{}/{} /DestKey:{} /Z:{} /S /XO /Y'.format(
                sourceFolder, accountName, destinationContainer, dest_folder, accountKey, journal_folder)
        elif platform.system() is 'Linux':
            args = '--source \"{}\" --destination https://{}.blob.core.windows.net/{}/{} --dest-key {} -z {} -s -y'.format(
                sourceFolder, accountName, destinationContainer, dest_folder, accountKey, journal_folder)
        else:
            msg = 'Unsupported operating system {}'.format(platform.system())
            self.LogInfo(msg)
            raise RuntimeError(msg)
        return args

    def get_azcopy_download_args(self, destinationFolder, accountName, accountKey, sourceContainer):
        journal_folder = os.path.join(os.environ['TEMP'], hashlib.md5(sourceContainer).hexdigest())
        if platform.system() is 'Windows':
            args = '/Source:https://{}.blob.core.windows.net/{} /Dest:\"{}\" /SourceKey:{} /Z:{} /S /MT /XN /Y'.format(
                accountName, sourceContainer, destinationFolder, accountKey, journal_folder)
        elif platform.system() is 'Linux':
            args = '--source https://{}.blob.core.windows.net/{} --destination \"{}\" --source-key {} -z {} -mt -xn -s -y'.format(
                    accountName, sourceContainer, destinationFolder, accountKey, journal_folder)
        else:
            msg = 'Unsupported operating system {}'.format(platform.system())
            self.LogInfo(msg)
            raise RuntimeError(msg)
        return args

    def usable_path_for_os(self, path):
        if self.windows_path(path) and platform.system() is 'Windows':
            return True
        if not self.windows_path(path) and platform.system() is 'Linux':
            return True
        return False

    def windows_path(self, path):
        if path.startswith('\\'):
            return True
        if ':' in path:
            return True
        return False

    def get_job_working_dir(self, slaveName, jobId):
        return '{}\Thinkbox\Deadline10\slave\{}\jobsData\{}'.format(os.environ['LOCALAPPDATA'], slaveName, job.JobId)

    def should_sync_assets(self, job):
        enabledGroups = self.GetConfigEntryWithDefault('EnabledGroups', None)
        enabledPools = self.GetConfigEntryWithDefault('EnabledPools', None)

        enabledGroupsList = []
        enabledPoolsList = []

        if enabledGroups:
            enabledGroupsList = enabledGroups.split(';')

        if enabledPools:
            enabledPoolsList = enabledPools.split(';')

        if job.JobGroup in enabledGroupsList:
            return True

        if job.JobPool in enabledPoolsList or job.JobSecondaryPool in enabledPoolsList:
            return True

        return False

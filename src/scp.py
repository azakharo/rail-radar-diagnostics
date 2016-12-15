#! python2
# -*- coding: utf-8 -*-

from os.path import dirname, basename
from contextlib import closing
import paramiko
import scpclient


def readFile(filePath, host, port, user, passwd):
    sshClient = None
    fileCont = None
    try:
        sshClient = paramiko.SSHClient()
        sshClient.load_system_host_keys()
        sshClient.set_missing_host_key_policy(paramiko.WarningPolicy())

        sshClient.connect(host, port=port, username=user, password=passwd)

        fileCont = readFileUsingConnection(sshClient, filePath)
    finally:
        sshClient.close()
    return fileCont

def readFileUsingConnection(sshClient, filePath):
    fileCont = None
    fname = basename(filePath)
    fdir = dirname(filePath)
    if not fdir.endswith("/"):  # this is important for scpclient
        fdir += "/"
    with closing(scpclient.Read(sshClient.get_transport(), fdir)) as scp:
        fileCont = scp.receive(fname)
    return fileCont

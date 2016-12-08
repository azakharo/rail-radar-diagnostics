#! python2
# -*- coding: utf-8 -*-

# ////////////////////////////////////////////////
# Logging

import logging

FORMAT = '%(message)s'
logging.basicConfig(format=FORMAT)
_logger = logging.getLogger()
_logger.setLevel(logging.DEBUG)


def log(msg):
    _logger.debug(msg)


def info(msg):
    _logger.info(msg)


def warn(msg):
    _logger.warning(msg)


def err(msg):
    _logger.error("ERROR: " + msg)


def exception(msg):
    _logger.exception(msg)

# Logging
# ////////////////////////////////////////////////


from socket import gethostname
from os.path import dirname, basename, join
import paramiko
from contextlib import closing
from scpclient import Read


isDebug = gethostname() == 'zakhar-mobl'

HOST = '127.0.0.1' if isDebug else 'unknown-host'
PORT = 2022 if isDebug else 22
USER = 'zakhar' if isDebug else 'user'
PASSWD = 'Ubuntu5' if isDebug else 'pass'

DEST_DIR = dirname(__file__)


def copyFile(filePath, destDir=DEST_DIR, host=HOST, port=PORT, user=USER, passwd=PASSWD):
    sshClient = None
    try:
        sshClient = paramiko.SSHClient()
        sshClient.load_system_host_keys()
        sshClient.set_missing_host_key_policy(paramiko.WarningPolicy)

        sshClient.connect(HOST, port=PORT, username=USER, password=PASSWD)

        fname = basename(filePath)
        fdir = dirname(filePath)
        if not fdir.endswith("/"):  # this is important for scpclient
            fdir += "/"

        with closing(Read(sshClient.get_transport(), fdir)) as scp:
            fileCont = scp.receive(fname)
            localFilePath = join(destDir, fname)
            f = open(localFilePath, "wb")
            f.write(fileCont)
            f.close()
    except:
        err("Could not copy {file} from {host}".format(file=filePath, host=host))
        raise
    finally:
        sshClient.close()


def main():
    copyFile('/home/zakhar/test_email.txt')
    info("DONE")


if __name__ == '__main__':
    main()

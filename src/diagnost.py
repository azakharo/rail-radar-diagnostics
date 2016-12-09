#! python2
# -*- coding: utf-8 -*-

import logging
from socket import gethostname
from os.path import dirname, basename, join
import paramiko
from contextlib import closing
import scpclient


isDebug = gethostname() == 'zakhar-mobl'

HOST = '127.0.0.1' if isDebug else 'unknown-host'
PORT = 2022 if isDebug else 22
USER = 'zakhar' if isDebug else 'user'
PASSWD = 'Ubuntu5' if isDebug else 'pass'


def main():
    patch_crypto_be_discovery()
    text = readFile('/home/zakhar/test_email.txt')
    log(text)
    info("DONE")

def readFile(filePath, host=HOST, port=PORT, user=USER, passwd=PASSWD):
    sshClient = None
    fileCont = None
    try:
        sshClient = paramiko.SSHClient()
        sshClient.load_system_host_keys()
        sshClient.set_missing_host_key_policy(paramiko.WarningPolicy)

        sshClient.connect(HOST, port=PORT, username=USER, password=PASSWD)

        fname = basename(filePath)
        fdir = dirname(filePath)
        if not fdir.endswith("/"):  # this is important for scpclient
            fdir += "/"

        with closing(scpclient.Read(sshClient.get_transport(), fdir)) as scp:
            fileCont = scp.receive(fname)
    except:
        err("Could not read {file} from {host}".format(file=filePath, host=host))
        raise
    finally:
        sshClient.close()
    return fileCont


# ////////////////////////////////////////////////
# Logging

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


def patch_crypto_be_discovery():
    """
    Monkey patches cryptography's backend detection.
    Objective: support pyinstaller freezing.
    """

    from cryptography.hazmat import backends

    try:
        from cryptography.hazmat.backends.commoncrypto.backend import backend as be_cc
    except ImportError:
        be_cc = None

    try:
        from cryptography.hazmat.backends.openssl.backend import backend as be_ossl
    except ImportError:
        be_ossl = None

    backends._available_backends_list = [
        be for be in (be_cc, be_ossl) if be is not None
    ]


if __name__ == '__main__':
    main()

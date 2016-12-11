#! python2
# -*- coding: utf-8 -*-

import logging
from socket import gethostname
from os.path import dirname, basename, join
from Tkinter import Tk, Frame, Label, StringVar
import paramiko
from contextlib import closing
import scpclient


isDebug = gethostname() == 'zakhar-mobl'

HOST = '127.0.0.1' if isDebug else 'unknown-host'
PORT = 2022 if isDebug else 22
USER = 'zakhar' if isDebug else 'user'
PASSWD = 'Ubuntu5' if isDebug else 'pass'

MAIN_WND_W = 640
MAIN_WND_H = 480

PARAM_FONT_SIZE = (None, 13)

def main():
    patch_crypto_be_discovery()

    # text = readFile('/home/zakhar/test_email.txt')
    # log(text)

    mainWnd = Tk()
    mainWnd.title("Диагностика")
    mainWnd.resizable(width=False, height=False)
    left = (mainWnd.winfo_screenwidth() - MAIN_WND_W) / 2
    top = (mainWnd.winfo_screenheight() - MAIN_WND_H) / 2
    mainWnd.geometry('{w}x{h}+{left}+{top}'.format(w=MAIN_WND_W, h=MAIN_WND_H, left=left, top=top))
    mainWnd.iconbitmap('favicon.ico')

    #################################################################
    # Create layout

    mainWnd.grid_columnconfigure(0, weight=1, uniform="fred")
    mainWnd.grid_columnconfigure(1, weight=1, uniform="fred")
    mainWnd.grid_columnconfigure(2, weight=1, uniform="fred")

    # Param section
    paramFrame = Frame(mainWnd, width=213.33, height=240)
    paramFrame.grid(row=0, column=0, sticky="ewns", padx=10, pady=10)
    paramFrame.grid_rowconfigure(0, weight=0)
    paramFrame.grid_rowconfigure(1, weight=0)
    paramFrame.grid_columnconfigure(0, weight=0)
    paramFrame.grid_columnconfigure(1, weight=0)

    # Param 1
    param1Label = Label(paramFrame, text="Параметр 1: ", font=PARAM_FONT_SIZE)
    param1Label.grid(row=0, column=0, sticky="nw")
    param1StrVar = StringVar()
    param1StrVar.set(str(1.25))
    param1Val = Label(paramFrame, textvariable=param1StrVar, font=PARAM_FONT_SIZE)
    param1Val.grid(row=0, column=1, sticky="nw")
    # Param 2
    param2Label = Label(paramFrame, text="Параметр 2: ", font=PARAM_FONT_SIZE)
    param2Label.grid(row=1, column=0, sticky="nw")
    param2StrVar = StringVar()
    param2StrVar.set(str(2.88))
    param2Val = Label(paramFrame, textvariable=param2StrVar, font=PARAM_FONT_SIZE)
    param2Val.grid(row=1, column=1, sticky="nw")

    # Custom widgets section
    widgetFrame = Frame(mainWnd, width=213.33, height=240, bg='green')
    widgetFrame.grid(row=0, column=1, sticky="ewns")

    # Buttons section
    buttonFrame = Frame(mainWnd, width=213.33, height=240, bg='orange')
    buttonFrame.grid(row=0, column=2, sticky="ewns")

    # Log section
    logFrame = Frame(mainWnd, width=640, height=240, bg='black')
    logFrame.grid(row=1, column=0, columnspan=3, sticky="ewns")

    # Create layout
    #################################################################

    mainWnd.mainloop()

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

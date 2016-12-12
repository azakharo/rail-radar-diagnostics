#! python2
# -*- coding: utf-8 -*-

import logging
from socket import gethostname
from os.path import dirname, basename, join
from datetime import datetime
from Tkinter import Tk, Frame, Label, StringVar, Button, Text, Scrollbar
from threading import Thread
from Queue import Queue
from time import sleep
from contextlib import closing
import paramiko
import scpclient


isDebug = gethostname() == 'zakhar-mobl'

HOST = '127.0.0.1' if isDebug else 'unknown-host'
PORT = 2022 if isDebug else 22
USER = 'zakhar' if isDebug else 'user'
PASSWD = 'Ubuntu5' if isDebug else 'pass'

MAIN_WND_W = 640
MAIN_WND_H = 480

PARAM_FONT_SIZE = (None, 13)

# StartStop button
isMonRunning = False
BTN_TEXT__START_DIAGNOST = "Запустить"
BTN_TEXT__STOP_DIAGNOST  = "Остановить"

readerThread = None
eventQueue = Queue()
mainWnd = None
param2StrVar = None
logWidget = None

def main():
    # Stuff necessary to build the exe
    patch_crypto_be_discovery()

    # Create main window
    global mainWnd
    mainWnd = Tk()
    mainWnd.title("Диагностика")
    mainWnd.resizable(width=False, height=False)
    left = (mainWnd.winfo_screenwidth() - MAIN_WND_W) / 2
    top = (mainWnd.winfo_screenheight() - MAIN_WND_H) / 2
    mainWnd.geometry('{w}x{h}+{left}+{top}'.format(w=MAIN_WND_W, h=MAIN_WND_H, left=left, top=top))
    mainWnd.iconbitmap('favicon.ico')

    # Create layout and widgets
    createLayoutAndWidgets(mainWnd)

    # Start GUI event loop
    mainWnd.mainloop()

    info("DONE")


def startMonitoring():
    # Create and run the reader thread
    readerThread = Thread(target=readerThreadFunc)
    readerThread.start()

    # Start GUI periodic checks of the queue and msg processing
    guiPeriodicCall()

def stopMonitoring():
    global readerThread
    if readerThread:
        readerThread = None


def readerThreadFunc():
    # Open connection
    sshClient = None
    try:
        sshClient = paramiko.SSHClient()
        sshClient.load_system_host_keys()
        sshClient.set_missing_host_key_policy(paramiko.WarningPolicy)

        sshClient.connect(HOST, port=PORT, username=USER, password=PASSWD)
    except:
        err("Could not connect to {host}:{port}".format(host=HOST, port=PORT))
        raise

    # Periodically read file and pass data to the UI
    while isMonRunning:
        val = float(readFileUsingConnection(sshClient, '/home/zakhar/diagnost.txt'))
        eventQueue.put({
            'name': 'param2',
            'value': val
        })
        # log("put val in the queue {}".format(val))
        sleep(1)

    # Close the connection
    sshClient.close()


def guiPeriodicCall():
    """ Check every 200 ms if there is something new in the queue. """
    if isMonRunning:
        mainWnd.after(200, guiPeriodicCall)
    processMsgsFromReader()


def processMsgsFromReader():
    """ Handle all messages currently in the queue, if any. """
    while eventQueue.qsize():
        try:
            msg = eventQueue.get(0)
            if msg['name'] == 'param2':
                prevVal = getParam2()
                param2 = msg['value']
                if param2 != prevVal:
                    # Update param2 value in the UI
                    setParam2(param2)
                    # Print log msg into the log widget
                    printLogMsg("новое значение параметра 2: {}".format(param2))
        except Queue.Empty:
            pass


def readFileUsingConnection(sshClient, filePath):
    fileCont = None
    fname = basename(filePath)
    fdir = dirname(filePath)
    if not fdir.endswith("/"):  # this is important for scpclient
        fdir += "/"
    with closing(scpclient.Read(sshClient.get_transport(), fdir)) as scp:
        fileCont = scp.receive(fname)
    return fileCont


def readFile(filePath, host=HOST, port=PORT, user=USER, passwd=PASSWD):
    sshClient = None
    fileCont = None
    try:
        sshClient = paramiko.SSHClient()
        sshClient.load_system_host_keys()
        sshClient.set_missing_host_key_policy(paramiko.WarningPolicy)

        sshClient.connect(HOST, port=PORT, username=USER, password=PASSWD)

        fileCont = readFileUsingConnection(sshClient, filePath)
    except:
        err("Could not read {file} from {host}:{port}".format(file=filePath, host=host, port=port))
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


def createLayoutAndWidgets(mainWnd):
    mainWnd.grid_columnconfigure(0, weight=1, uniform="fred")
    mainWnd.grid_columnconfigure(1, weight=1, uniform="fred")
    mainWnd.grid_columnconfigure(2, weight=1, uniform="fred")
    mainWnd.grid_rowconfigure(0, weight=1, uniform="fred2")
    mainWnd.grid_rowconfigure(1, weight=4, uniform="fred2")
    # Param section
    paramFrame = Frame(mainWnd, width=MAIN_WND_W / 3)
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
    global param2StrVar
    param2StrVar = StringVar()
    setParam2(0)
    param2Val = Label(paramFrame, textvariable=param2StrVar, font=PARAM_FONT_SIZE)
    param2Val.grid(row=1, column=1, sticky="nw")
    # Custom widgets section
    widgetFrame = Frame(mainWnd, width=MAIN_WND_W / 3)
    widgetFrame.grid(row=0, column=1, sticky="ewns")
    # Buttons section
    buttonFrame = Frame(mainWnd, width=MAIN_WND_W / 3, padx=10, pady=10)
    buttonFrame.grid(row=0, column=2, sticky="ewns")
    # StartStop button
    startStopBtnText = StringVar()
    startStopBtnText.set(BTN_TEXT__START_DIAGNOST)

    def startStopBtnClicked():
        global isMonRunning
        isMonRunning = not isMonRunning
        startStopBtnText.set(BTN_TEXT__STOP_DIAGNOST if isMonRunning else BTN_TEXT__START_DIAGNOST)
        if isMonRunning:
            startMonitoring()
        else:
            stopMonitoring()

    startStopBtn = Button(buttonFrame, textvariable=startStopBtnText, command=startStopBtnClicked,
                          font=PARAM_FONT_SIZE, width=12)
    buttonFrame.grid_columnconfigure(0, weight=1)
    startStopBtn.grid(row=0, column=0, sticky="ne")
    # Log section
    logFrame = Frame(mainWnd, width=MAIN_WND_W, padx=10, pady=10)
    logFrame.grid(row=1, column=0, columnspan=3, sticky="ewns")
    logFrame.grid_rowconfigure(0, weight=1)
    logFrame.grid_columnconfigure(0, weight=1)
    global logWidget
    logWidget = Text(logFrame, bg='white', width=40, height=13)
    logWidget.configure(state="disabled")
    logWidget.grid(row=0, column=0, sticky="nesw")
    # Vert Scrollbar
    logScrollBar = Scrollbar(logFrame, command=logWidget.yview)
    logScrollBar.grid(row=0, column=1, sticky='nsew')
    logWidget['yscrollcommand'] = logScrollBar.set


def getParam2():
    val = None
    if param2StrVar:
        val = float(param2StrVar.get())
    return val

def setParam2(val):
    if param2StrVar:
        param2StrVar.set(str(val))

def printLogMsg(msg):
    dt = datetime.now().strftime("%d.%m.%y %H:%M:%S")
    logMsg = "{dt} - {msg}\n".format(dt=dt, msg=msg)
    logWidget.configure(state="normal")
    logWidget.insert('1.0', logMsg)
    logWidget.configure(state="disabled")


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

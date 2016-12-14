#! python2
# -*- coding: utf-8 -*-

from os.path import dirname, basename, join
from datetime import datetime
from Tkinter import Tk, Frame, Label, StringVar, Button, Text, Scrollbar
from threading import Thread
from Queue import Queue
from time import sleep
from contextlib import closing
from glob import glob
from os import getcwd
import attr
import paramiko
import scpclient
from mylogging import log, info, err
from appConfig import AppConfig
from vbu_state_parsing import parseVbuStateFile
from VbuState import VbuState


MAIN_WND_W = 640
MAIN_WND_H = 480

PARAM_FONT_SIZE = (None, 13)

# StartStop button
isMonRunning = False
# BTN_TEXT__START_DIAGNOST = "Запустить"
# BTN_TEXT__STOP_DIAGNOST  = "Остановить"

appConfig = None
readerThread = None
eventQueue = Queue()
mainWnd = None
param2StrVar = None
logWidget = None
# startStopBtnText = None

vbuReaderThread = None
isVbuStateReading = False

paramFrame = None


def main():
    # Stuff necessary to build the exe
    patch_crypto_be_discovery()

    global appConfig
    # Try to find any config in the cur work dir
    configFiles = glob(join(getcwd(), "*.cfg"))
    if configFiles: # if found
        appConfig = AppConfig.readConfig(configFiles[0])
    else:
        appConfig = AppConfig()

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

    # Read VBU State
    startVbuRead()
    guiPeriodicCall()

    # Gracefully stop mon on exit
    mainWnd.wm_protocol("WM_DELETE_WINDOW", onExit)

    # Start GUI event loop
    mainWnd.mainloop()

    info("DONE")


def onExit():
    stopVbuRead()
    stopMonitoring()
    mainWnd.destroy()


#////////////////////////////////////////////////////////////////////
# Read Vbu State

def startVbuRead():
    global isVbuStateReading
    isVbuStateReading = True

    # Create and run the reader thread
    global vbuReaderThread
    vbuReaderThread = Thread(target=readVbuState)
    vbuReaderThread.start()

    # Start GUI periodic checks of the queue and msg processing
    guiPeriodicCall()

def stopVbuRead():
    global isVbuStateReading
    isVbuStateReading = False

    global vbuReaderThread
    if vbuReaderThread:
        vbuReaderThread = None

def readVbuState():
    vbuStateFileCont = None
    try:
        vbuStateFileCont = readFile(appConfig.statePath, appConfig.host, appConfig.port,
                                    appConfig.user, appConfig.passwd)
    except Exception, e:
        errMsg = "Could not read VBU State file '{file}'\n{exc}".format(file=appConfig.statePath, exc=str(e))
        err(errMsg)
        eventQueue.put({
            'name': 'error',
            'value': errMsg
        })
        return

    # Parse vbu state file
    try:
        vbuState = parseVbuStateFile(vbuStateFileCont)
    except Exception, ex:
        errMsg = "Could not parse VBU State file '{file}'\n{exc}".format(file=appConfig.statePath, exc=str(ex))
        err(errMsg)
        eventQueue.put({
            'name': 'error',
            'value': errMsg
        })
        return
    # log(vbuState)

    # Pass parsed vbu state to UI
    eventQueue.put({
        'name': 'vbuState',
        'value': vbuState
    })

    global isVbuStateReading
    isVbuStateReading = False


# Read Vbu State
#////////////////////////////////////////////////////////////////////


def startMonitoring():
    global isMonRunning
    isMonRunning = True

    # global startStopBtnText
    # startStopBtnText.set(BTN_TEXT__STOP_DIAGNOST)

    # Create and run the reader thread
    global readerThread
    readerThread = Thread(target=readerThreadFunc)
    readerThread.start()

    # Start GUI periodic checks of the queue and msg processing
    guiPeriodicCall()

def stopMonitoring():
    global isMonRunning
    isMonRunning = False

    # global startStopBtnText
    # startStopBtnText.set(BTN_TEXT__START_DIAGNOST)

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

        sshClient.connect(appConfig.host, port=appConfig.port, username=appConfig.user, password=appConfig.passwd)
    except Exception, e:
        errMsg = "Could not connect to {host}:{port}\n{exc}".format(
            host=appConfig.host, port=appConfig.port, exc=str(e))
        err(errMsg)
        eventQueue.put({
            'name': 'error',
            'value': errMsg
        })
        return

    # Periodically read file and pass data to the UI
    while isMonRunning:
        val = None

        try:
            val = float(readFileUsingConnection(sshClient, appConfig.statePath))
        except Exception, e:
            errMsg = "Could not read {file} from {host}:{port}\n{exc}".format(
                file=appConfig.statePath, host=appConfig.host, port=appConfig.port, exc=str(e))
            err(errMsg)
            eventQueue.put({
                'name': 'error',
                'value': errMsg
            })
            # Close the connection
            sshClient.close()
            return

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
    if isMonRunning or isVbuStateReading:
        mainWnd.after(200, guiPeriodicCall)
    processMsgsFromReader()


def processMsgsFromReader():
    """ Handle all messages currently in the queue, if any. """
    while eventQueue.qsize():
        try:
            msg = eventQueue.get(0)
            msgName = msg['name']
            msgVal = msg['value']
            if msgName == 'param2':
                prevVal = getParam2()
                if msgVal != prevVal:
                    # Update param2 value in the UI
                    setParam2(msgVal)
                    # Print log msg into the log widget
                    printLogMsg("новое значение параметра 2: {}".format(msgVal))
            elif msgName == 'error':
                printLogMsg(msgVal)
                stopMonitoring()
            elif msgName == 'vbuState':
                visualizeVbuState(msgVal)
        except:
            pass


def visualizeVbuState(state):
    descrs = createParamWidgetDescs(state)
    createParamWidgets(descrs)

@attr.s
class ParamWidgetDesc(object):
    label = attr.ib()
    value = attr.ib()

@attr.s
class LimitedParamWidgetDesc(ParamWidgetDesc):
    min = attr.ib()
    max = attr.ib()

    def isInBoundaries(self):
        return self.value >= self.min and self <= self.max

def createParamWidgetDescs(vbuState):
    infos = []

    # Time period
    DT_FRMT = "%H:%M:%S %d.%m.%y"
    val = "{start} - {end}".format(
        start=vbuState.dtStart.strftime(DT_FRMT),
        end=vbuState.dtFinish.strftime(DT_FRMT)
    )
    info = ParamWidgetDesc("Диапазон времени", val)
    infos.append(info)

    # Signal Min
    info = LimitedParamWidgetDesc("Миним.  уровень сигнала", vbuState.signalMin,
                           VbuState.SGNL_MIN__MIN, VbuState.SGNL_MIN__MAX)
    infos.append(info)

    # Signal Mean
    info = LimitedParamWidgetDesc("Средний уровень сигнала", vbuState.signalMean,
                           VbuState.SGNL_MEAN__MIN, VbuState.SGNL_MEAN__MAX)
    infos.append(info)

    # Signal Max
    info = LimitedParamWidgetDesc("Максим. уровень сигнала", vbuState.signalMax,
                           VbuState.SGNL_MAX__MIN, VbuState.SGNL_MAX__MAX)
    infos.append(info)

    # # Frequencies
    # info = ParamWidgetInfo("Средний уровень частот", vbuState.signalMax,
    #                        VbuState.SGNL_MAX__MIN, VbuState.SGNL_MAX__MAX)
    # infos.append(info)

    return infos

def createParamWidgets(widgetDescriptions):
    for descInd, desc in enumerate(widgetDescriptions):
        # Create label and value fields and add them to proper frame
        label = Label(paramFrame, text="{}: ".format(desc.label), font=PARAM_FONT_SIZE)
        label.grid(row=descInd, column=0, sticky="nw")
        if isinstance(desc.value, float):
            valueStr = formatFloat(desc.value)
        else:
            valueStr = desc.value
        value = Label(paramFrame, text=valueStr, font=PARAM_FONT_SIZE)
        value.grid(row=descInd, column=1, sticky="nw")

def formatFloat(val):
    return "{:9.6f}".format(val)

def readFileUsingConnection(sshClient, filePath):
    fileCont = None
    fname = basename(filePath)
    fdir = dirname(filePath)
    if not fdir.endswith("/"):  # this is important for scpclient
        fdir += "/"
    with closing(scpclient.Read(sshClient.get_transport(), fdir)) as scp:
        fileCont = scp.receive(fname)
    return fileCont


def readFile(filePath, host, port, user, passwd):
    sshClient = None
    fileCont = None
    try:
        sshClient = paramiko.SSHClient()
        sshClient.load_system_host_keys()
        sshClient.set_missing_host_key_policy(paramiko.WarningPolicy)

        sshClient.connect(host, port=port, username=user, password=passwd)

        fileCont = readFileUsingConnection(sshClient, filePath)
    except:
        err("Could not read {file} from {host}:{port}".format(file=filePath, host=host, port=port))
        raise
    finally:
        sshClient.close()
    return fileCont


def createLayoutAndWidgets(mainWnd):
    mainWnd.grid_columnconfigure(0, weight=1, uniform="fred")
    # mainWnd.grid_columnconfigure(1, weight=1, uniform="fred")
    # mainWnd.grid_columnconfigure(2, weight=1, uniform="fred")
    mainWnd.grid_rowconfigure(0, weight=1, uniform="fred2")
    mainWnd.grid_rowconfigure(1, weight=2, uniform="fred2")
    # Param section
    global paramFrame
    paramFrame = Frame(mainWnd, width=MAIN_WND_W)
    paramFrame.grid(row=0, column=0, sticky="ewns", padx=10, pady=10)
    # paramFrame.grid_rowconfigure(0, weight=0)
    # paramFrame.grid_rowconfigure(1, weight=0)
    # paramFrame.grid_columnconfigure(0, weight=0)
    # paramFrame.grid_columnconfigure(1, weight=0)
    # # Param 1
    # param1Label = Label(paramFrame, text="Параметр 1: ", font=PARAM_FONT_SIZE)
    # param1Label.grid(row=0, column=0, sticky="nw")
    # param1StrVar = StringVar()
    # param1StrVar.set(str(1.25))
    # param1Val = Label(paramFrame, textvariable=param1StrVar, font=PARAM_FONT_SIZE)
    # param1Val.grid(row=0, column=1, sticky="nw")
    # # Param 2
    # param2Label = Label(paramFrame, text="Параметр 2: ", font=PARAM_FONT_SIZE)
    # param2Label.grid(row=1, column=0, sticky="nw")
    # global param2StrVar
    # param2StrVar = StringVar()
    # setParam2(0)
    # param2Val = Label(paramFrame, textvariable=param2StrVar, font=PARAM_FONT_SIZE)
    # param2Val.grid(row=1, column=1, sticky="nw")
    # # Custom widgets section
    # widgetFrame = Frame(mainWnd, width=MAIN_WND_W / 3)
    # widgetFrame.grid(row=0, column=1, sticky="ewns")
    # # Buttons section
    # buttonFrame = Frame(mainWnd, width=MAIN_WND_W / 3, padx=10, pady=10, bg='green')
    # buttonFrame.grid(row=0, column=1, sticky="ewns")
    # # StartStop button
    # global startStopBtnText
    # startStopBtnText = StringVar()
    # startStopBtnText.set(BTN_TEXT__START_DIAGNOST)
    #
    # def startStopBtnClicked():
    #     if not isMonRunning:
    #         startMonitoring()
    #     else:
    #         stopMonitoring()
    #
    # # startStopBtn = Button(buttonFrame, textvariable=startStopBtnText, command=startStopBtnClicked,
    # #                       font=PARAM_FONT_SIZE, width=12)
    # buttonFrame.grid_columnconfigure(0, weight=1)
    # startStopBtn.grid(row=0, column=0, sticky="ne")
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

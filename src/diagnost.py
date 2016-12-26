#! python2
# -*- coding: utf-8 -*-

from os.path import join
from datetime import datetime
from Tkinter import Tk, Frame, Label, StringVar, Button, Text, Scrollbar
from threading import Thread
from Queue import Queue
from time import sleep
from glob import glob
from os import getcwd
import ctypes
import attr
from mylogging import log, info, err, warn
from appConfig import AppConfig
from VbuState import VbuState
from scp import readFileUsingConnection
from readVbuState import startVbuRead


MAIN_WND_W = 640
MAIN_WND_H = 480

PARAM_FONT_SIZE = (None, 13)
PARAM_TABLE_HDR_FONT = (None, 13, 'bold')

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

paramFrame = None
retryBtn = None

isStateReading = False


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
    mainWnd.title("Программа диагностики СРППС, версия 2.3")
    mainWnd.resizable(width=False, height=False)
    left = (mainWnd.winfo_screenwidth() - MAIN_WND_W) / 2
    top = (mainWnd.winfo_screenheight() - MAIN_WND_H) / 2
    mainWnd.geometry('{w}x{h}+{left}+{top}'.format(w=MAIN_WND_W, h=MAIN_WND_H, left=left, top=top))
    mainWnd.iconbitmap('favicon.ico')

    # Create layout and widgets
    createLayoutAndWidgets(mainWnd)

    if not ctypes.windll.shell32.IsUserAnAdmin():
        printLogMsg(u"Данное приложение должно быть запущено под учётной записью Администратора.")
    else:
        run()

        # Start GUI periodic check of input queue
        guiPeriodicCall()

        # Gracefully stop mon on exit
        mainWnd.wm_protocol("WM_DELETE_WINDOW", onExit)

    # Start GUI event loop
    mainWnd.mainloop()

    info("DONE")


def run():
    startVbuRead(appConfig, eventQueue)
    printLogMsg(u"Диагностика начата. Пожалуйста, подождите.", False)
    global isStateReading
    isStateReading = True

def onExit():
    stopMonitoring()
    mainWnd.destroy()

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
        errMsg = u"Could not connect to {host}:{port}\n{exc}".format(
            host=appConfig.host, port=appConfig.port, exc=unicode(e))
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
            errMsg = u"Could not read {file} from {host}:{port}\n{exc}".format(
                file=appConfig.statePath, host=appConfig.host, port=appConfig.port, exc=unicode(e))
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


periodicCallCount = 0

def guiPeriodicCall():
    """ Check every 200 ms if there is something new in the queue. """
    mainWnd.after(200, guiPeriodicCall)
    processMsgsFromReader()
    # Print progress indicator if vbu state is being read
    if isStateReading:
        global periodicCallCount
        periodicCallCount += 1
        if periodicCallCount % 5 == 0:
            _writeLogMsg(u'.', True)


def processMsgsFromReader():
    """ Handle all messages currently in the queue, if any. """
    while eventQueue.qsize():
        try:
            msg = eventQueue.get(0)
            msgName = msg['name']
            msgVal = msg['value']

            global isStateReading
            if isStateReading:
                isStateReading = False
                _writeLogMsg(u"\n")

            if msgName == 'param2':
                prevVal = getParam2()
                if msgVal != prevVal:
                    # Update param2 value in the UI
                    setParam2(msgVal)
                    # Print log msg into the log widget
                    printLogMsg(u"новое значение параметра 2: {}".format(msgVal))
            elif msgName == 'error':
                if msgVal == 'EthernetNotConnected':
                    printLogMsg(u'Отсутствует подключение Ethernet. Пожалуйста, подключите соответствующий кабель к этому компьютеру и нажмите кнопку "Повторить".')
                    showRetryBtn()
                elif msgVal == 'HostInaccessible':
                    printLogMsg(u'Устройство недоступно. Пожалуйста, убедитесь, что оно подключено к электропитанию и сети Ethernet. Затем нажмите кнопку "Повторить".')
                    showRetryBtn()
                else:
                    printLogMsg(msgVal)
                    printLogMsg("Диагностика завершена.")
                    stopMonitoring()
            elif msgName == 'vbuState':
                hideRetryBtn()
                visualizeVbuState(msgVal)
        except:
            pass


def visualizeVbuState(state):
    if state == None:
        printLogMsg(u"В данной конфигурации радиоканал не используется.")
        printLogMsg(u"Диагностика завершена.")
        return

    # Disp time period
    DT_FRMT = "%H:%M:%S %d.%m.%y"
    timePeriodText = "Период: {start} - {end}".format(
        start=state.dtStart.strftime(DT_FRMT),
        end=state.dtFinish.strftime(DT_FRMT)
    )
    label = Label(paramFrame, text=timePeriodText, font=PARAM_FONT_SIZE)
    label.grid(row=0, column=0, columnspan=2, sticky="nw")

    # Disp param table's header
    label = Label(paramFrame, text="Параметр", font=PARAM_TABLE_HDR_FONT)
    label.grid(row=1, column=0, sticky="nw")
    label = Label(paramFrame, text="Значение", font=PARAM_TABLE_HDR_FONT)
    label.grid(row=1, column=1, sticky="ne")
    label = Label(paramFrame, text="Допустимые значения", font=PARAM_TABLE_HDR_FONT)
    label.grid(row=1, column=2, sticky="ne")

    # Disp params
    descrs = createParamWidgetDescs(state)
    createParamWidgets(descrs)

    if isWithin(state.signalMin, VbuState.SGNL_MIN__MIN, VbuState.SGNL_MIN__MAX) and \
            isWithin(state.signalMean, VbuState.SGNL_MIN__MIN, VbuState.SGNL_MIN__MAX) and \
            isWithin(state.signalMax, VbuState.SGNL_MIN__MIN, VbuState.SGNL_MIN__MAX):
        printLogMsg(u"Параметры устройства в норме.")
    else:
        printLogMsg(u"Необходимо проверить радио тракт.")
    printLogMsg(u"Диагностика завершена.")


def isWithin(val, minVal, maxVal):
    if val:
        return val >= minVal and val <= maxVal
    else:
        return False


@attr.s
class ParamWidgetDesc(object):
    label = attr.ib()
    value = attr.ib()

@attr.s
class LimitedParamWidgetDesc(ParamWidgetDesc):
    min = attr.ib()
    max = attr.ib()

    def isInBoundaries(self):
        return self.value >= self.min and self.value <= self.max

def createParamWidgetDescs(vbuState):
    infos = []

    # Signal Min
    info = LimitedParamWidgetDesc("Миним.  уровень сигнала", vbuState.signalMin,
                           VbuState.SGNL_MIN__MIN, VbuState.SGNL_MIN__MAX)
    infos.append(info)

    # Signal Mean
    info = LimitedParamWidgetDesc("Сред. уровень сигнала", vbuState.signalMean,
                           VbuState.SGNL_MEAN__MIN, VbuState.SGNL_MEAN__MAX)
    infos.append(info)

    # Signal Max
    info = LimitedParamWidgetDesc("Максим. уровень сигнала", vbuState.signalMax,
                           VbuState.SGNL_MAX__MIN, VbuState.SGNL_MAX__MAX)
    infos.append(info)

    # Frequencies
    # for frInd, fr in enumerate(vbuState.frequencies):
    #     info = LimitedParamWidgetDesc("Сред. уровень частоты {}".format(frInd + 1), fr,
    #                            VbuState.FREQ_MIN, VbuState.FREQ_MAX)
    #     infos.append(info)

    return infos

def createParamWidgets(widgetDescriptions):
    firstRowInd = 2
    for descInd, desc in enumerate(widgetDescriptions):
        # Create label and value fields and add them to proper frame
        label = Label(paramFrame, text="{}: ".format(desc.label), font=PARAM_FONT_SIZE)
        label.grid(row=descInd + firstRowInd, column=0, sticky="nw")
        v = desc.value
        if isinstance(v, float):
            valueStr = formatFloat(v)
        else:
            valueStr = str(v)
        value = Label(paramFrame, text=valueStr, font=PARAM_FONT_SIZE)
        value.grid(row=descInd + firstRowInd, column=1, sticky="ne")
        if isinstance(desc, LimitedParamWidgetDesc):
            # Select value's color
            if desc.isInBoundaries():
                fg = 'lime green'
            else:
                fg = 'firebrick'
            value.configure(foreground=fg)
            # Output the limits
            limits = Label(paramFrame, text='[{min:6.3f}, {max:6.3f}]'.format(min=desc.min, max=desc.max),
                           font=PARAM_FONT_SIZE)
            limits.grid(row=descInd + firstRowInd, column=2, sticky="ne")

def formatFloat(val):
    return "{:9.3f}".format(val)

def createLayoutAndWidgets(mainWnd):
    mainWnd.grid_columnconfigure(0, weight=1, uniform="fred")
    # mainWnd.grid_columnconfigure(1, weight=1, uniform="fred")
    # mainWnd.grid_columnconfigure(2, weight=1, uniform="fred")
    mainWnd.grid_rowconfigure(0, weight=3, uniform="fred2")
    mainWnd.grid_rowconfigure(1, weight=2, uniform="fred2")
    # Param section
    global paramFrame
    paramFrame = Frame(mainWnd, width=MAIN_WND_W)
    paramFrame.grid(row=0, column=0, sticky="ewns", padx=10, pady=10)

    # Made the param frame's columns equal width
    paramFrame.grid_columnconfigure(0, weight=1, uniform="params-grid")
    paramFrame.grid_columnconfigure(1, weight=1, uniform="params-grid")
    paramFrame.grid_columnconfigure(2, weight=1, uniform="params-grid")

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


# def getParam2():
#     val = None
#     if param2StrVar:
#         val = float(param2StrVar.get())
#     return val
#
# def setParam2(val):
#     if param2StrVar:
#         param2StrVar.set(str(val))


def printLogMsg(msg, endLine=True):
    if not isinstance(msg, unicode):
        errMsg = "only Unicode must be passed to the log widget"
        warn(errMsg)
        raise Exception(errMsg)
    dt = datetime.now().strftime("%d.%m.%y %H:%M:%S")
    logMsg = u"{dt} - {msg}".format(dt=dt, msg=msg)
    if endLine:
        logMsg = logMsg + u'\n'
    _writeLogMsg(logMsg)

def _writeLogMsg(msg, toEnd=True):
    logWidget.configure(state="normal")
    logWidget.insert('end' if toEnd else '1.0', msg)
    logWidget.see("end")
    logWidget.configure(state="disabled")


#/////////////////////////////////////////////////////////////////////////
# Retry button

def onRetryBtnClick():
    retryBtn.configure(state="disabled")
    run()

def showRetryBtn():
    global retryBtn

    if not retryBtn:
        retryBtn = Button(paramFrame, text="Повторить", command=onRetryBtnClick,
                              font=PARAM_FONT_SIZE, width=12)
        retryBtn.grid(row=0, column=2, sticky="ne")
    else:
        enableRetryBtn()

def enableRetryBtn():
    if retryBtn:
        retryBtn.configure(state="normal")

def hideRetryBtn():
    if retryBtn:
        retryBtn.grid_remove()

# Retry button
#/////////////////////////////////////////////////////////////////////////


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

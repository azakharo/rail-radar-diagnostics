#! python2
# -*- coding: utf-8 -*-

import re
from datetime import datetime
from threading import Thread
import subprocess
from time import sleep
from paramiko.ssh_exception import AuthenticationException, NoValidConnectionsError
from scpclient import SCPError
from VbuState import VbuState
from mylogging import log, info, warn, err, exception
from scp import readFile
from windows_networking import getEthernetInfo, getWindowsCmdEncoding


VBU_LINE_DT_FRMT = "%d.%m.%y %H:%M:%S"


def startVbuRead(appCfg, uiEventQueue):
    # Create and run the reader thread
    vbuReaderThread = Thread(target=readVbuState, kwargs={'appConfig': appCfg, 'eventQueue': uiEventQueue})
    vbuReaderThread.start()

def getSubnet(ip):
    subnet = None
    matchResult = re.match("^(?P<subnet>\d+\.\d+\.\d+)\.\d+$", ip)
    if matchResult:
        subnet = matchResult.group('subnet')
    return subnet

def readVbuState(appConfig, eventQueue):
    info('Get Ethernet adapter name and connection status')
    eth = getEthernetInfo()
    if not eth:
        errMsg = u"Ethernet adapter info has NOT been found in output of ipconfig."
        err(errMsg)
        eventQueue.put({
            'name': 'error',
            'value': errMsg
        })
        return
    if not eth.isConnected:
        info("Ethernet NOT connected")
        eventQueue.put({
            'name': 'error',
            'value': 'EthernetNotConnected'
        })
        return
    # log(eth)

    # Check whether network conf is needed and perform it
    isNetworkChanged = False
    if getSubnet(appConfig.host) != getSubnet(eth.ip):
        info("Need to change Ethernet settings")
        # netsh interface ip set address name="Ethernet" source=static addr=192.168.0.1 mask=255.255.255.0 gateway=none
        winCmdEncoding = getWindowsCmdEncoding()
        iface = eth.ifaceName.encode(winCmdEncoding)
        netshArgs = ['netsh', 'interface', 'ip', 'set', 'address',
                     'name="{eth_name}"'.format(eth_name=iface),
                     'source=static',
                     'addr={subnet}.1'.format(subnet=getSubnet(appConfig.host)),
                     'mask=255.255.255.0',
                     'gateway=none']
        log(" ".join(netshArgs))
        exitCode = subprocess.call(netshArgs, shell=True)
        if exitCode == 0:
            isNetworkChanged = True
            sleep(4)
        else:
            errMsg = u"Не удалось изменить сетевые настройки. netsh вернула {exitCode}.".format(exitCode=exitCode)
            err(errMsg)
            eventQueue.put({
                'name': 'error',
                'value': errMsg
            })
            return

    # Just common code to avoid code dupl
    def handleException(errMsg, isNetworkChanged, ifaceName, eventQueue):
        exception(errMsg)
        if isNetworkChanged:
            restoreEthernetSettings(ifaceName)
        eventQueue.put({
            'name': 'error',
            'value': errMsg
        })

    # Read VBU state file content
    info("Reading VBU state file...")
    vbuStateFileCont = None
    try:
        vbuStateFileCont = readFile(appConfig.statePath, appConfig.host, appConfig.port,
                                    appConfig.user, appConfig.passwd)
    except AuthenticationException:
        errMsg = u"SSH: ошибка аутентификации."
        handleException(errMsg, isNetworkChanged, eth.ifaceName, eventQueue)
        return
    except NoValidConnectionsError:
        errMsg = u"SSH: не удалось подключиться к '{host}', порт {port}".format(host=appConfig.host, port=appConfig.port)
        handleException(errMsg, isNetworkChanged, eth.ifaceName, eventQueue)
        return
    except SCPError:
        errMsg = u"Возможно, запуск устройства был произведен менее часа назад. Необходимо повторить диагностику по истечении одного часа после запуска. Если сообщение повторится, то устройство необходимо заменить."
        handleException(errMsg, isNetworkChanged, eth.ifaceName, eventQueue)
        return
    except Exception, ex:
        errMsg = u"SSH: не удалось подключиться к '{host}:{port}' и прочитать файл '{file}'\n{exc}".format(
            host=appConfig.host, port=appConfig.port, file=appConfig.statePath, exc=unicode(ex))
        handleException(errMsg, isNetworkChanged, eth.ifaceName, eventQueue)
        return

    # Parse vbu state file
    info("Parsing VBU state file...")
    try:
        vbuState = parseVbuStateFile(vbuStateFileCont)
    except VbuEmpty:
        errMsg = u"Диагностика завершена: устройство необходимо заменить."
        handleException(errMsg, isNetworkChanged, eth.ifaceName, eventQueue)
        return
    except NoFree, ex:
        errMsg = u"Диагностика завершена: за период {t1} - {t2} не было полного освобождения всех рельсовых цепей. Повторите диагностику не ранее одного часа после момента освобождения всех рельсовых цепей.".format(
            t1=ex.t1.strftime(VBU_LINE_DT_FRMT),
            t2=ex.t2.strftime(VBU_LINE_DT_FRMT)
        )
        handleException(errMsg, isNetworkChanged, eth.ifaceName, eventQueue)
        return
    except NoFreqs:
        errMsg = u"Диагностика завершена: данное устройство не использует радиоканал."
        handleException(errMsg, isNetworkChanged, eth.ifaceName, eventQueue)
        return
    except Exception:
        errMsg = u"ОШИБКА! Не удалось разобрать содержимое файла состояния."
        handleException(errMsg, isNetworkChanged, eth.ifaceName, eventQueue)
        return
    # log(vbuState)

    # Restore ethernet settings
    if isNetworkChanged:
        restoreEthernetSettings(eth.ifaceName)

    # Pass parsed vbu state to UI
    eventQueue.put({
        'name': 'vbuState',
        'value': vbuState
    })

def restoreEthernetSettings(ifaceName):
    # netsh interface ip set address name="Ethernet" source=dhcp
    exitCode = subprocess.call(['netsh', 'interface', 'ip', 'set', 'address',
                            'name="{eth_name}"'.format(eth_name=ifaceName),
                            'source=dhcp'],
                            shell=True)
    if exitCode != 0:
        warn("restore Ethernet cmd returned {}".format(exitCode))
    return exitCode


class VbuEmpty(Exception):
    pass

class NoFree(Exception):
    def __init__(self, message, t1, t2):
        self.message = message
        self.t1 = t1
        self.t2 = t2

class NoFreqs(Exception):
    pass

def parseVbuStateFile(fileContent):
    """
    :param fileContent:
    :return: VbuState object or None
    """

    # Read lines
    lines = fileContent.split('\n')
    lines = [l.strip() for l in lines]
    lines = [l for l in lines if len(l) > 0]
    # log(len(lines))
    if len(lines) == 0:
        raise VbuEmpty(u"vbu state file is empty")

    # Find the last "free" line
    freeLine = None
    freeLineInd = -1
    for i in xrange(len(lines) - 1, -1, -1):
        l = lines[i]
        if l.startswith("free"):
            freeLine = l
            freeLineInd = i
            break
    if not freeLine:
        # необходимо найти начальное время первой записи busy Т1 и конечное время последней записи "busy" Т2
        # Get all busy lines
        busyLines = [l for l in lines if l.startswith("busy")]
        t1 = t2 = None
        if len(busyLines) > 0:
            BUSY_LINE_FRMT = "^busy\s+" \
                             "(?P<dtStart>\d{2}\.\d{2}\.\d{2}\s+\d{2}:\d{2}:\d{2})\s+" \
                             "-\s+" \
                             "(?P<dtEnd>\d{2}\.\d{2}\.\d{2}\s+\d{2}:\d{2}:\d{2})\s+" \
                            ".*" \
                            "$"
            # Get t1
            l = busyLines[0]
            # Parse the "busy" line
            matchResult = re.match(BUSY_LINE_FRMT, l)
            if not matchResult:
                raise Exception("Couldn't parse 'busy' line '{}'".format(l))
            try:
                t1 = datetime.strptime(matchResult.group('dtStart'), VBU_LINE_DT_FRMT)
            except Exception:
                err("Couldn't parse 'busy' line '{}'".format(l))
                raise

            # Get t2
            l = busyLines[-1]
            # Parse the "busy" line
            matchResult = re.match(BUSY_LINE_FRMT, l)
            if not matchResult:
                raise Exception("Couldn't parse 'busy' line '{}'".format(l))
            try:
                t2 = datetime.strptime(matchResult.group('dtEnd'), VBU_LINE_DT_FRMT)
            except Exception:
                err("Couldn't parse 'busy' line '{}'".format(l))
                raise
        # Raise exception
        raise NoFree(u"there are no 'free' lines", t1, t2)

    if freeLineInd == len(lines) - 1:
        raise NoFreqs(u"line 'free' is last in the file")

    # free 13.12.16 04:32:10 - 13.12.16 04:58:42  18001.9-19594.4  2018 2022 2027  1022 1146 1412  2646 2900 3030
    # free date_time_start - date_time_end        time_offset_start-time_offset_end
    # signal_level_min_min signal_level_min_mean signal_level_min_max
    # signal_level_mean_min signal_level_mean_mean signal_level_mean_max
    # signal_level_max_min signal_level_max_mean signal_level_max_max


    # Find next "freq" lines until "busy" or end-of-file
    nextBusyLineInd = -1
    for i in xrange(len(lines) - 1, freeLineInd, -1):
        l = lines[i]
        if l.startswith("busy"):
            nextBusyLineInd = i
            break
    # log(nextBusyLineInd)
    if nextBusyLineInd == freeLineInd + 1:
        raise NoFreqs(u"there are no 'freq' lines after 'free'")

    # Parse the "free" line
    matchResult = re.match("^free\s+"
                           "(?P<dtStart>\d{2}\.\d{2}\.\d{2}\s+\d{2}:\d{2}:\d{2})\s+"
                           "-\s+"
                           "(?P<dtEnd>\d{2}\.\d{2}\.\d{2}\s+\d{2}:\d{2}:\d{2})\s+"
                           "\d+\.\d+-\d+\.\d+\s+"
                           "\d+\s+(?P<minMean>\d+)\s+\d+\s+"
                           "\d+\s+(?P<meanMean>\d+)\s+\d+\s+"
                           "\d+\s+(?P<maxMean>\d+)\s+\d+"
                           "$", freeLine)
    if not matchResult:
        raise Exception("Couldn't parse 'free' line '{}'".format(freeLine))

    try:
        dtStart = datetime.strptime(matchResult.group('dtStart'), VBU_LINE_DT_FRMT)
        dtEnd = datetime.strptime(matchResult.group('dtEnd'), VBU_LINE_DT_FRMT)
        minMean = float(matchResult.group('minMean'))
        meanMean = float(matchResult.group('meanMean'))
        maxMean = float(matchResult.group('maxMean'))
    except Exception, ex:
        err("Couldn't parse 'free' line '{}'".format(freeLine))
        raise

    # Calculate signal numbers
    signalMin  = calcSignalVal(minMean)
    signalMean = calcSignalVal(meanMean)
    signalMax  = calcSignalVal(maxMean)

    # Parse every "freq" line and calc freq val
    freqs = []
    rangeStart = freeLineInd + 1
    rangeStop = len(lines) if nextBusyLineInd == -1 else nextBusyLineInd
    for lineInd in xrange(rangeStart, rangeStop, 1):
        line = lines[lineInd]
        # Parse freq line
        # 97000 99297 101282  5114 5706 6383  15.3 17.4 19.5
        matchResult = re.match("^"
                               "\d+\s+"
                               "(?P<freqMean>\d+)\s+"
                               ".*"
                               "$", line)
        if not matchResult:
            raise Exception("Couldn't parse 'freq' line '{}'".format(line))
        try:
            freqMean = float(matchResult.group('freqMean'))
        except Exception, ex:
            err("Couldn't parse 'freq' line '{}'".format(line))
            raise
        freq = freqMean * 0.7 * 10**-4
        freqs.append(freq)

    # Create and return VbuState
    return VbuState(dtStart, dtEnd, signalMin, signalMean, signalMax, freqs)


def calcSignalVal(val):
    return (val - 2048) / 4095 * 1.8

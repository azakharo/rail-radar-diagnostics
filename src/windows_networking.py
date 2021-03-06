#! python2
# -*- coding: utf-8 -*-

import subprocess
import re
import attr
from pyinstaller_fix import subprocess_args
from mylogging import log


@attr.s
class EthernetInfo(object):
    ifaceName = attr.ib()
    isConnected = attr.ib()
    ip = attr.ib(default=None)


def getEthernetInfo():
    # Call ipconfig /all
    ipconfigOut = subprocess.check_output(['ipconfig', '/all'], **subprocess_args(False))
    return parseIpconfigOutput(ipconfigOut)

def parseIpconfigOutput(ipconfigOut):
    winEncoding = getWindowsCmdEncoding()
    ipconfigOut = unicode(ipconfigOut, encoding=winEncoding)
    # log(ipconfigOut)
    lines = ipconfigOut.split('\n')
    lines = [l.strip() for l in lines]
    lines = [l for l in lines if len(l) > 0]

    # Get adapter lines
    adapterLines = findAdapterLines(lines)
    if not adapterLines:
        return None

    # Get Ethernet adapter line
    ethAdapterLine = findEthernetAdapterLine(adapterLines)
    # log(ethAdapterLine)
    if not ethAdapterLine:
        return None

    # Examine Ethernet adapter section and determine connection status
    lineIndStart = ethAdapterLine.lineInd + 1
    ethInd = adapterLines.index(ethAdapterLine)
    lineIndEnd = lines[-1] if ethInd == len(adapterLines) - 1 else adapterLines[ethInd + 1].lineInd - 1
    # Find
    # Media State . . . . . . . . . . . : Media disconnected
    isDisconnected = False
    for lineInd in xrange(lineIndStart, lineIndEnd + 1):
        matchResult = re.match(u"^Media State.*:\s+Media disconnected$", lines[lineInd])
        if matchResult:
            isDisconnected = True
            break
        matchResult = re.match(u"^Состояние среды.*:\s+Среда передачи недоступна.*$", lines[lineInd])
        if matchResult:
            isDisconnected = True
            break
    ipAddr = None
    if not isDisconnected:
        # Find address
        for lineInd in xrange(lineIndStart, lineIndEnd + 1):
            matchResult = re.match(u"^.*IPv4.*:\s+(?P<ip>\d+\.\d+\.\d+\.\d+).*$", lines[lineInd])
            if matchResult:
                ipAddr = matchResult.group('ip')
                break

    return EthernetInfo(ethAdapterLine.ifaceName, not isDisconnected, ipAddr)


@attr.s
class AdapterLine(object):
    ifaceName   = attr.ib()
    line        = attr.ib()
    lineInd     = attr.ib()


def findAdapterLines(lines):
    adapterLines = []

    # Find Ethernet section and examine its content
    for lineInd, line in enumerate(lines):
        # Find interface section start
        # Example:
        # Wireless LAN adapter Wi-Fi:
        matchResult = re.match(u"^.*(adapter|адаптер|Адаптер).*\s+(?P<ifaceName>.*):$", line, re.IGNORECASE)
        if matchResult:
            ifaceName = matchResult.group('ifaceName')
            adaptLine = AdapterLine(ifaceName, line, lineInd)
            adapterLines.append(adaptLine)

    return adapterLines


def findEthernetAdapterLine(adapterLines):
    if not adapterLines:
        return None

    lines = [l for l in adapterLines if l.ifaceName == u'Ethernet']
    if lines:
        return lines[0]

    lines = [l for l in adapterLines if u'Local Area Connection' in l.ifaceName]
    if lines:
        return lines[0]

    lines = [l for l in adapterLines if l.ifaceName == u'Local']
    if lines:
        return lines[0]


    lines = [l for l in adapterLines if u'Подключение по локальной сети' in l.ifaceName]
    if lines:
        return lines[0]

    return None

def getWindowsCmdEncoding():
    # Get windows console encoding
    chcpOut = subprocess.check_output(['chcp'], shell=True, **subprocess_args(False))
    matchResult = re.match("^.*:\s+(?P<codePage>.*)$", chcpOut)
    winCodePage = matchResult.group('codePage')
    return "cp" + winCodePage


if __name__ == '__main__':
    info = getEthernetInfo()
    log(info)

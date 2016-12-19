#! python2
# -*- coding: utf-8 -*-

import subprocess
import re
import attr
from mylogging import log


@attr.s
class EthernetInfo(object):
    ifaceName = attr.ib()
    isConnected = attr.ib()
    ip = attr.ib(default=None)


def getEthernetInfo():
    # Call ipconfig /all
    ipconfigOut = subprocess.check_output(['ipconfig', '/all'])
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
        matchResult = re.match("^Media State.*:\s+Media disconnected$", lines[lineInd])
        if matchResult:
            isDisconnected = True
            break
    ipAddr = None
    if not isDisconnected:
        # Find address
        for lineInd in xrange(lineIndStart, lineIndEnd + 1):
            matchResult = re.match("^.*IPv4\s+Address.*:\s+(?P<ip>\d+\.\d+\.\d+\.\d+).*$", lines[lineInd])
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
        matchResult = re.match("^.*adapter\s+(?P<ifaceName>.*):$", line)
        if matchResult:
            ifaceName = matchResult.group('ifaceName')
            adaptLine = AdapterLine(ifaceName, line, lineInd)
            adapterLines.append(adaptLine)

    return adapterLines


def findEthernetAdapterLine(adapterLines):
    if not adapterLines:
        return None

    lines = [l for l in adapterLines if l.ifaceName == 'Ethernet']
    if lines:
        return lines[0]

    lines = [l for l in adapterLines if 'Local Area Connection' in l.ifaceName]
    if lines:
        return lines[0]

    lines = [l for l in adapterLines if l.ifaceName == 'Local']
    if lines:
        return lines[0]

    # Get windows console encoding
    chcpOut = subprocess.check_output(['chcp'], shell=True)
    matchResult = re.match("^Active code page:\s+(?P<codePage>.*)$", chcpOut)
    winCodePage = matchResult.group('codePage')

    lines = [l for l in adapterLines if u'Подключение по локальной сети' in
             unicode(ifaceName, encoding="cp" + winCodePage)]
    if lines:
        return lines[0]

    return None


if __name__ == '__main__':
    info = getEthernetInfo()
    log(info)

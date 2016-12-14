#! python2
# -*- coding: utf-8 -*-

import re
from datetime import datetime
from VbuState import VbuState
from mylogging import log, err


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
        return None

    # Find the last "free" line
    freeLine = None
    freeLineInd = -1
    for i in xrange(len(lines) - 1, -1, -1):
        l = lines[i]
        if l.startswith("free"):
            freeLine = l
            freeLineInd = i
            break
    if not freeLine or freeLineInd == len(lines) - 1:
        return None
    # log(freeLine)
    # log(freeLineInd)

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
    DT_FRMT = "%d.%m.%y %H:%M:%S"

    try:
        dtStart = datetime.strptime(matchResult.group('dtStart'), DT_FRMT)
        dtEnd = datetime.strptime(matchResult.group('dtEnd'), DT_FRMT)
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
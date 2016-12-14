#! python2
# -*- coding: utf-8 -*-

import attr


@attr.s
class VbuState(object):
    dtStart     = attr.ib()
    dtFinish    = attr.ib()
    signalMin   = attr.ib()
    signalMean  = attr.ib()
    signalMax   = attr.ib()
    frequencies = attr.ib()


    #########################
    # Limits

    SGNL_MIN__MIN = -0.7
    SGNL_MIN__MAX = -0.2

    SGNL_MEAN__MIN = -0.1
    SGNL_MEAN__MAX = 0.1

    SGNL_MAX__MIN = 0.2
    SGNL_MAX__MAX = 0.7

    FREQ_MIN = 0.3
    FREQ_MAX = 0.75

    # Limits
    #########################


if __name__ == '__main__':
    from datetime import datetime
    from mylogging import log

    state1 = VbuState(datetime.now(), datetime.now(), 0, 5, 10, [1, 2, 3])
    state2 = VbuState(datetime.now(), datetime.now(), 2, 5, 8, [4, 1, 2])
    log(state1)
    log(state1 == state2)

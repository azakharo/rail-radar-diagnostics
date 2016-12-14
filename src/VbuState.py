#! python2
# -*- coding: utf-8 -*-

import attr

# Для N > 0 вывести:
#         диапазон времени date_time_start - date_time_end
#         усредненный минимальный уровень сигнала = (signal_level_min_mean - 2048) / 4095 * 1.8 Вольт (допустимый диапазон  [-0.7; -0.2])
#         усредненный средний уровень сигнала = (signal_level_mean_mean - 2048) / 4095 * 1.8 В Вольт (допустимый диапазон  [-0.1; +0.1])
#         усредненный максимальный уровень сигнала = (signal_level_min_mean - 2048) / 4095 * 1.8 В Вольт (допустимый диапазон  [+0.2; +0.7])
#         Для M=1..N  средний уровень частоты = freqM_mean * 0.7 * 1.e-4 Вольт (допустимый диапазон  [+0.3; +0.75])


@attr.s
class VbuState(object):
    dtStart     = attr.ib()
    dtFinish    = attr.ib()
    signalMin   = attr.ib()
    signalMean  = attr.ib()
    signalMax   = attr.ib()
    frequencies = attr.ib()


if __name__ == '__main__':
    from datetime import datetime
    from mylogging import log

    state1 = VbuState(datetime.now(), datetime.now(), 0, 5, 10, [1, 2, 3])
    state2 = VbuState(datetime.now(), datetime.now(), 2, 5, 8, [4, 1, 2])
    log(state1)
    log(state1 == state2)
